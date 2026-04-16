import json
import re
import asyncio
import logging
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

from db import init_db, recent_prs, pr_count, get_last_checked, get_latest_cached_result, get_latest_cached_result_any, set_last_checked, compute_prompt_hash, cache_pr, update_email_sent, update_pr_statuses, dashboard_stats
from worker import (
    sync_corpus_to_qdrant, fetch_and_review_prs, REPOS_MAIL_MAP, _fetch_pr_diff, _fetch_pr_info, _fetch_pr_comments, _fetch_open_prs,
    runtime_config, schedule_enabled, get_config, add_repo, remove_repo, add_repo_rules, get_repo_rules,
    QDRANT_URL, QDRANT_API_KEY, GROQ_TOKEN, GITHUB_TOKEN, COLLECTION, EMBED_MODEL,
    PROMPT_PATH, SCHEDULE_INTERVAL, CACHE_ENABLED, LLM_MAX_RETRIES,
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
)

log = logging.getLogger(__name__)
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
HIDDEN_KEYS = {"GITHUB_TOKEN", "GROQ_TOKEN", "SMTP_PASSWORD"}


def _cache_read_enabled():
    """Return True if cache reads are enabled (runtime override or default)."""
    val = str(get_config("CACHE_ENABLED")).lower()
    return val in ("true", "1", "yes")

# In-memory prompt overrides (reset on restart). Only used by inference/eval, NOT schedule.
prompt_overrides: dict[str, str] = {}  # keys: "RAG", "Naive_LLM"

_schedule_lock = threading.Lock()


async def _background_scheduler():
    """Run fetch_and_review_prs at the configured SCHEDULE_INTERVAL (minutes)."""
    while True:
        interval = int(get_config("SCHEDULE_INTERVAL"))
        await asyncio.sleep(interval * 60)
        if not _schedule_lock.acquire(blocking=False):
            log.info("Background scheduler: skipped, another run is in progress")
            continue
        try:
            log.info("Background scheduler: starting PR review cycle (interval=%dm)", interval)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, fetch_and_review_prs)
            log.info("Background scheduler: cycle complete")
        except Exception:
            log.exception("Background scheduler: cycle failed")
        finally:
            _schedule_lock.release()


@asynccontextmanager
async def lifespan(application):
    init_db()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, sync_corpus_to_qdrant)
    task = asyncio.create_task(_background_scheduler())
    yield
    task.cancel()


app = FastAPI(title="PR Code Review Bot", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Pages ----
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    sched_status = {
        "recent": recent_prs(limit=15),
        "last_checked": {repo: get_last_checked(repo) for repo in REPOS_MAIL_MAP},
        "total_processed": pr_count(),
        "page": 1, "per_page": 15,
        "total_pages": max(1, -(-pr_count() // 15)),
    }
    sched_repos = [
        {"repo": repo, "email": email, "enabled": schedule_enabled.get(repo, True)}
        for repo, email in REPOS_MAIL_MAP.items()
    ]
    config_keys = {
        "QDRANT_URL": QDRANT_URL, "GROQ_TOKEN": GROQ_TOKEN, "GITHUB_TOKEN": GITHUB_TOKEN,
        "SCHEDULE_INTERVAL": SCHEDULE_INTERVAL,
        "CACHE_ENABLED": CACHE_ENABLED, "LLM_MAX_RETRIES": LLM_MAX_RETRIES,
        "SMTP_USER": SMTP_USER, "SMTP_PASSWORD": SMTP_PASSWORD,
    }
    config_data = {}
    for k, default_val in config_keys.items():
        val = runtime_config.get(k, default_val)
        if k in HIDDEN_KEYS:
            config_data[k] = {"value": "***", "hidden": True}
        elif k == "CACHE_ENABLED":
            config_data[k] = {"value": str(val).lower() in ("true", "1", "yes"), "toggle": True}
        else:
            config_data[k] = {"value": val, "hidden": False}
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "sched_status_json": json.dumps(sched_status),
            "sched_repos_json": json.dumps(sched_repos),
            "config_data_json": json.dumps(config_data),
        },
    )


# ---- Health / Status ----
@app.get("/health")
def health():
    return {
        "status": "ok",
        "processed_prs": pr_count(),
        "repos_tracked": list(REPOS_MAIL_MAP.keys()),
    }


@app.get("/status")
def status():
    activity = recent_prs(limit=10)
    last_checked = {repo: get_last_checked(repo) for repo in REPOS_MAIL_MAP}
    return {"recent": activity, "last_checked": last_checked}


# ---- Custom Inference ----
@app.post("/api/inference")
async def api_inference(request: Request):
    body = await request.json()
    pr_url = body.get("pr_url", "").strip()
    run_rag = body.get("run_rag", True)
    run_naive = body.get("run_naive", False)
    run_static = body.get("run_static", False)

    # parse owner/repo/number from URL
    m = re.match(r"https?://github\.com/([^/]+/[^/]+)/pull/(\d+)", pr_url)
    if not m:
        return {"error": "Invalid PR URL. Expected: https://github.com/owner/repo/pull/123"}

    repo, pr_number = m.group(1), int(m.group(2))
    repo_short = repo.split("/")[-1]

    # Validate repo is in tracked list
    if repo not in REPOS_MAIL_MAP:
        return {"error": f"Repository '{repo}' is not added for monitoring. Only tracked repos can be processed."}

    # Validate PR is open
    try:
        pr_state, pr_title = _fetch_pr_info(repo, pr_number)
    except Exception as e:
        return {"error": f"Failed to fetch PR info: {e}"}
    if pr_state != "open":
        return {"error": f"This PR is {pr_state}. Only open PRs can be processed."}

    try:
        diff = _fetch_pr_diff(repo, pr_number)
    except Exception as e:
        return {"error": f"Failed to fetch PR diff: {e}"}

    # Fetch PR comments (non-blocking, best effort)
    try:
        pr_comments = _fetch_pr_comments(repo, pr_number)
    except Exception:
        pr_comments = []

    from single_pr_model_output_metrics import (
        prepare_rag_prompt, build_prompt, _call_llm_with_retry,
        run_static_tool_on_code,
        _load_prompt_v1, _extract_added_lines_from_diff,
    )
    from groq import Groq

    qdrant_url = get_config("QDRANT_URL")
    groq_key = get_config("GROQ_TOKEN")
    prompt_path = get_config("PROMPT_PATH")
    collection = get_config("DEFAULT_COLLECTION_NAME")
    embed_model = get_config("DEFAULT_EMBED_MODEL")
    max_retries = int(get_config("LLM_MAX_RETRIES"))

    result = {}
    prompts = {}
    cached_models = {}

    # normalize diff for naive/static
    code = diff
    if code.lstrip().startswith("diff --git") or "@@ " in code:
        code = _extract_added_lines_from_diff(code)

    if run_rag:
        # 1. retrieval + prompt building (cheap)
        prep = prepare_rag_prompt(
            pr_code=diff, pr_id=f"PR #{pr_number}", qdrant_url=qdrant_url,
            prompt_path=prompt_path, repo_name=repo_short,
            collection_name=collection, embed_model_name=embed_model,
            prompt_template_override=prompt_overrides.get("RAG"),
            qdrant_api_key=get_config("QDRANT_API_KEY"),
        )
        p_hash = compute_prompt_hash(prep["prompt"], prep["model"], prep["temperature"])

        # 2. check cache with final-prompt hash
        cached = get_latest_cached_result(repo, pr_number, p_hash) if _cache_read_enabled() else None
        if cached:
            try:
                cached_data = json.loads(cached)
                result["RAG"] = cached_data.get("reviews", [])
                result["retrieved_chunks"] = cached_data.get("retrieved_chunks", [])
                prompts["RAG"] = cached_data.get("prompt_used", "")
                cached_models["RAG"] = True
            except Exception:
                cached = None

        if not cached:
            # 3. LLM call (expensive) — only if cache miss
            client = Groq(api_key=groq_key)
            reviews, retries = _call_llm_with_retry(client, prep["prompt"], max_retries)
            chunks = prep["chunks"]
            result["RAG"] = reviews
            result["retrieved_chunks"] = [{"text": c["text"], "score": round(c.get("rerank_score", 0), 4), "category": c.get("category", "")} for c in chunks]
            prompts["RAG"] = prep["prompt"]
            # write to cache
            cache_pr(repo, pr_number, "inference", json.dumps({
                "reviews": reviews, "retrieved_chunks": result["retrieved_chunks"], "prompt_used": prep["prompt"],
            }), prompt_hash=p_hash)

    if run_naive:
        prompt_template = _load_prompt_v1(Path("."), explicit_path=prompt_path)
        naive_override = prompt_overrides.get("Naive_LLM")
        if naive_override:
            prompt_template = naive_override
        prompt = build_prompt(prompt_template, f"PR #{pr_number}", code, None)
        from single_pr_model_output_metrics import MODEL as LLM_MODEL
        n_hash = compute_prompt_hash(prompt, LLM_MODEL, 0)

        cached = get_latest_cached_result(repo, pr_number, n_hash) if _cache_read_enabled() else None
        if cached:
            try:
                cached_data = json.loads(cached)
                result["Naive_LLM"] = cached_data.get("reviews", [])
                prompts["Naive_LLM"] = cached_data.get("prompt_used", "")
                cached_models["Naive_LLM"] = True
            except Exception:
                cached = None

        if not cached:
            client = Groq(api_key=groq_key)
            reviews, _ = _call_llm_with_retry(client, prompt, max_retries)
            result["Naive_LLM"] = reviews
            prompts["Naive_LLM"] = prompt
            cache_pr(repo, pr_number, "inference", json.dumps({
                "reviews": reviews, "prompt_used": prompt,
            }), prompt_hash=n_hash)

    if run_static:
        findings, _ = run_static_tool_on_code(code)
        result["Static_tool"] = findings

    if prompts:
        result["prompts_used"] = prompts
    if cached_models:
        result["_cached"] = cached_models

    result["pr_meta"] = {
        "title": pr_title,
        "number": pr_number,
        "repo": repo,
        "diff": diff,
        "comments": pr_comments,
    }

    return result


# ---- Evaluation ----
@app.post("/api/evaluate")
async def api_evaluate(request: Request):
    body = await request.json()

    # Batch mode: entries list from evaluation JSON
    entries = body.get("entries")
    if entries and isinstance(entries, list):
        return _run_batch_eval(entries)

    code = body.get("code", "")
    ground_truth = body.get("ground_truth", [])

    if not code.strip():
        return {"error": "Code is empty"}
    if not ground_truth:
        return {"error": "Ground truth is empty"}

    from single_pr_model_output_metrics import run_eval_on_code

    result = run_eval_on_code(
        pr_code=code,
        ground_truth=ground_truth,
        qdrant_url=get_config("QDRANT_URL"),
        groq_api_key=get_config("GROQ_TOKEN"),
        prompt_path=get_config("PROMPT_PATH"),
        collection_name=get_config("DEFAULT_COLLECTION_NAME"),
        embed_model_name=get_config("DEFAULT_EMBED_MODEL"),
        max_retries=int(get_config("LLM_MAX_RETRIES")),
        rag_prompt_override=prompt_overrides.get("RAG"),
        naive_prompt_override=prompt_overrides.get("Naive_LLM"),
    )
    return result


def _run_batch_eval(entries):
    """Process a list of evaluation entries (from evaluation.json format)."""
    from single_pr_model_output_metrics import run_eval_on_code

    data_dir = Path(__file__).resolve().parents[2] / "data" / "processed"
    results = []
    agg = {m: {"TP": 0, "FP": 0, "FN": 0} for m in ("RAG", "Naive_LLM", "Static_tool")}

    for entry in entries:
        eid = entry.get("id", "unknown")
        repo = entry.get("repo", "")
        source_path = entry.get("source_path", "")
        gt = entry.get("ground_truth_reviews", [])

        # Resolve code: source_code (inline) OR source_file (path)
        code = entry.get("source_code", "")
        if not code:
            rel = entry.get("source_file", "")
            if not rel:
                results.append({"id": eid, "error": "No source_code or source_file"})
                continue
            fpath = data_dir / rel
            if not fpath.exists():
                results.append({"id": eid, "error": f"File not found: {rel}"})
                continue
            code = fpath.read_text(encoding="utf-8", errors="ignore")

        if not code.strip():
            results.append({"id": eid, "error": "Empty source code"})
            continue

        repo_name = repo.split("/")[-1] if repo else None
        try:
            r = run_eval_on_code(
                pr_code=code,
                ground_truth=gt,
                qdrant_url=get_config("QDRANT_URL"),
                groq_api_key=get_config("GROQ_TOKEN"),
                prompt_path=get_config("PROMPT_PATH"),
                repo_name=repo_name,
                collection_name=get_config("DEFAULT_COLLECTION_NAME"),
                embed_model_name=get_config("DEFAULT_EMBED_MODEL"),
                max_retries=int(get_config("LLM_MAX_RETRIES")),
                rag_prompt_override=prompt_overrides.get("RAG"),
                naive_prompt_override=prompt_overrides.get("Naive_LLM"),
            )
            r["id"] = eid
            r["source_path"] = source_path
            results.append(r)
            # accumulate TP/FP/FN for aggregate metrics
            for m in ("RAG", "Naive_LLM", "Static_tool"):
                met = r.get("Metrics", {}).get(m, {})
                agg[m]["TP"] += met.get("TP", 0)
                agg[m]["FP"] += met.get("FP", 0)
                agg[m]["FN"] += met.get("FN", 0)
        except Exception as exc:
            log.exception("Batch eval failed for %s", eid)
            results.append({"id": eid, "error": str(exc)})

    # Compute aggregate metrics from accumulated counts
    agg_metrics = {}
    for m in ("RAG", "Naive_LLM", "Static_tool"):
        tp, fp, fn = agg[m]["TP"], agg[m]["FP"], agg[m]["FN"]
        prec = tp / (tp + fp) if (tp + fp) else 0
        rec = tp / (tp + fn) if (tp + fn) else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
        acc = tp / (tp + fp + fn) if (tp + fp + fn) else 0
        agg_metrics[m] = {"Accuracy": acc, "Precision": prec, "Recall": rec, "F1": f1,
                          "TP": tp, "FP": fp, "FN": fn}

    return {"batch": True, "results": results, "aggregate": agg_metrics}


# ---- Schedule ----
@app.get("/api/schedule")
def api_schedule_get():
    return [
        {"repo": repo, "email": email, "enabled": schedule_enabled.get(repo, True)}
        for repo, email in REPOS_MAIL_MAP.items()
    ]


@app.post("/api/schedule")
async def api_schedule_post(request: Request):
    body = await request.json()
    repo = body.get("repo", "")
    enabled = body.get("enabled", True)
    if repo not in REPOS_MAIL_MAP:
        return {"error": f"Unknown repo: {repo}"}
    schedule_enabled[repo] = bool(enabled)
    return {"repo": repo, "enabled": schedule_enabled[repo]}


@app.post("/api/schedule/run")
def api_schedule_run():
    """Trigger an immediate PR fetch-and-review cycle (synchronous).
    Clears last_checked so ALL open PRs are re-scanned (cached ones still skip).
    """
    if not _schedule_lock.acquire(blocking=False):
        return {"status": "error", "error": "A schedule run is already in progress. Please wait."}
    try:
        init_db()
        for repo in REPOS_MAIL_MAP:
            set_last_checked(repo, None)
        summary = fetch_and_review_prs()
        return {"status": "ok", "summary": summary}
    except Exception as e:
        log.exception("Run Now failed")
        return {"status": "error", "error": str(e)}
    finally:
        _schedule_lock.release()


@app.get("/api/schedule/status")
def api_schedule_status(page: int = 1, per_page: int = 15, search: str = ""):
    """Return paginated processed PRs from DB for the schedule activity log."""
    offset = (page - 1) * per_page
    rows = recent_prs(limit=per_page, offset=offset, search=search)
    last_checked = {repo: get_last_checked(repo) for repo in REPOS_MAIL_MAP}
    total = pr_count(search=search)
    return {"recent": rows, "last_checked": last_checked, "total_processed": total,
            "page": page, "per_page": per_page, "total_pages": max(1, -(-total // per_page))}


@app.post("/api/schedule/refresh-status")
def api_refresh_pr_status():
    """Fetch open PRs from GitHub and mark closed ones in the DB."""
    open_prs = {}  # {(repo, pr_number): title}
    for repo in REPOS_MAIL_MAP:
        try:
            prs = _fetch_open_prs(repo)
            for pr in prs:
                open_prs[(repo, pr["number"])] = pr.get("title", "")
        except Exception:
            log.exception("Failed to fetch open PRs for %s", repo)
    update_pr_statuses(open_prs)
    return {"status": "ok", "open_count": len(open_prs)}


@app.post("/api/schedule/reprocess")
async def api_schedule_reprocess(request: Request):
    """Reprocess a single PR: fetch diff, run RAG inference (use cache if hit), send email."""
    body = await request.json()
    repo = body.get("repo", "").strip()
    pr_number = body.get("pr_number")

    if not repo or not pr_number:
        return {"error": "repo and pr_number are required"}
    pr_number = int(pr_number)

    from single_pr_model_output_metrics import prepare_rag_prompt, _call_llm_with_retry
    from worker import send_review_email
    from groq import Groq

    # First, try to get any existing cached result for this PR (fast path)
    cached = get_latest_cached_result_any(repo, pr_number) if _cache_read_enabled() else None
    used_cache = False
    reviews = []
    if cached:
        try:
            cached_data = json.loads(cached)
            reviews = cached_data.get("reviews", [])
            used_cache = True
        except Exception:
            cached = None

    if not cached:
        # Fetch diff
        try:
            diff = _fetch_pr_diff(repo, pr_number)
        except Exception as e:
            return {"error": f"Failed to fetch PR diff: {e}"}

        repo_short = repo.split("/")[-1] if "/" in repo else repo
        qdrant_url = get_config("QDRANT_URL")
        groq_key = get_config("GROQ_TOKEN")
        prompt_path = get_config("PROMPT_PATH")
        collection = get_config("DEFAULT_COLLECTION_NAME")
        embed_model = get_config("DEFAULT_EMBED_MODEL")
        max_retries = int(get_config("LLM_MAX_RETRIES"))

        # Prepare RAG prompt
        try:
            prep = prepare_rag_prompt(
                pr_code=diff, pr_id=f"PR #{pr_number}", qdrant_url=qdrant_url,
                prompt_path=prompt_path, repo_name=repo_short,
                collection_name=collection, embed_model_name=embed_model,
                qdrant_api_key=get_config("QDRANT_API_KEY"),
            )
        except Exception as e:
            return {"error": f"RAG retrieval failed: {e}"}

        try:
            client = Groq(api_key=groq_key)
            reviews, retries = _call_llm_with_retry(client, prep["prompt"], max_retries)
        except Exception as e:
            return {"error": f"Inference failed: {e}"}

    # Send email
    email = REPOS_MAIL_MAP.get(repo, "")
    email_ok = False
    if email:
        pr_title = f"PR #{pr_number} (reprocessed)"
        pr_url = f"https://github.com/{repo}/pull/{pr_number}"
        email_ok = send_review_email(repo, pr_number, pr_title, pr_url, reviews, email)

    # Update processed_at and email_sent on existing row
    update_email_sent(repo, pr_number, email_ok)

    return {
        "status": "ok",
        "pr_number": pr_number,
        "repo": repo,
        "findings": len(reviews),
        "used_cache": used_cache,
        "email_sent": email_ok,
    }


# ---- Dashboard ----
@app.get("/api/dashboard")
def api_dashboard(request: Request):
    repo = request.query_params.get("repo", "")
    return dashboard_stats(repo_filter=repo)


# ---- Configuration ----
@app.get("/api/config")
def api_config_get():
    keys = {
        "QDRANT_URL": QDRANT_URL, "GROQ_TOKEN": GROQ_TOKEN, "GITHUB_TOKEN": GITHUB_TOKEN,
        "SCHEDULE_INTERVAL": SCHEDULE_INTERVAL,
        "CACHE_ENABLED": CACHE_ENABLED, "LLM_MAX_RETRIES": LLM_MAX_RETRIES,
        "SMTP_USER": SMTP_USER, "SMTP_PASSWORD": SMTP_PASSWORD,
    }
    out = {}
    for k, default_val in keys.items():
        val = runtime_config.get(k, default_val)
        if k in HIDDEN_KEYS:
            out[k] = {"value": "***", "hidden": True}
        elif k == "CACHE_ENABLED":
            out[k] = {"value": str(val).lower() in ("true", "1", "yes"), "toggle": True}
        else:
            out[k] = {"value": val, "hidden": False}
    return out


@app.post("/api/config")
async def api_config_post(request: Request):
    body = await request.json()
    updated = []
    for k, v in body.items():
        runtime_config[k] = v
        updated.append(k)
    return {"updated": updated}


# ---- Repository Management ----
@app.get("/api/repos")
def api_repos_get():
    return [{"repo": r, "email": e, "rules": len(get_repo_rules(r))} for r, e in REPOS_MAIL_MAP.items()]


@app.post("/api/repos")
async def api_repos_add(request: Request):
    body = await request.json()
    repo = body.get("repo", "").strip()
    email = body.get("email", "").strip()
    rules = body.get("rules", [])
    if not repo or not email:
        return {"error": "Both repo (owner/name) and email are required."}
    if "/" not in repo:
        return {"error": "Repo must be in owner/name format."}
    if repo in REPOS_MAIL_MAP:
        return {"error": f"Repository '{repo}' is already tracked."}
    add_repo(repo, email)
    chunks = []
    if rules:
        chunks = add_repo_rules(repo, rules)
    return {"status": "ok", "repo": repo, "email": email, "rules_added": len(chunks)}


@app.delete("/api/repos")
async def api_repos_remove(request: Request):
    body = await request.json()
    repo = body.get("repo", "").strip()
    if not repo:
        return {"error": "repo is required."}
    if repo not in REPOS_MAIL_MAP:
        return {"error": f"Repository '{repo}' is not tracked."}
    remove_repo(repo)
    return {"status": "ok", "repo": repo}


@app.get("/api/repos/rules")
def api_repos_rules_get(repo: str = ""):
    if not repo or repo not in REPOS_MAIL_MAP:
        return {"error": "Unknown or missing repo."}
    return {"repo": repo, "rules": get_repo_rules(repo)}


@app.post("/api/repos/rules")
async def api_repos_rules_add(request: Request):
    body = await request.json()
    repo = body.get("repo", "").strip()
    rules = body.get("rules", [])
    if not repo or repo not in REPOS_MAIL_MAP:
        return {"error": "Unknown or missing repo."}
    if not rules:
        return {"error": "No rules provided."}
    chunks = add_repo_rules(repo, rules)
    return {"status": "ok", "repo": repo, "rules_added": len(chunks), "chunks": chunks}


# ---- Prompt Overrides (runtime only, reset on restart) ----
@app.get("/api/prompts")
def api_prompts_get():
    from single_pr_model_output_metrics import _load_prompt_v1
    default = _load_prompt_v1(Path("."), explicit_path=get_config("PROMPT_PATH"))
    return {
        "default": default,
        "RAG": prompt_overrides.get("RAG", ""),
        "Naive_LLM": prompt_overrides.get("Naive_LLM", ""),
    }


@app.post("/api/prompts")
async def api_prompts_post(request: Request):
    body = await request.json()
    updated = []
    for key in ("RAG", "Naive_LLM"):
        val = body.get(key, "").strip()
        if val:
            prompt_overrides[key] = val
            updated.append(key)
        elif key in body and not val:
            prompt_overrides.pop(key, None)
            updated.append(f"{key} (reset)")
    return {"updated": updated}


@app.post("/api/prompts/reset")
def api_prompts_reset():
    prompt_overrides.clear()
    return {"status": "ok", "message": "Prompts reset to default"}
