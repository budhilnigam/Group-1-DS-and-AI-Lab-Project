import json
import re
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

from db import init_db, recent_prs, pr_count, get_last_checked, get_latest_cached_result, set_last_checked, compute_prompt_hash, cache_pr
from worker import (
    sync_corpus_to_qdrant, fetch_and_review_prs, REPOS_MAIL_MAP, _fetch_pr_diff,
    runtime_config, schedule_enabled, get_config,
    QDRANT_URL, GROQ_TOKEN, GITHUB_TOKEN, COLLECTION, EMBED_MODEL,
    PROMPT_PATH, SCHEDULE_INTERVAL, CACHE_ENABLED, LLM_MAX_RETRIES,
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
)

log = logging.getLogger(__name__)
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
HIDDEN_KEYS = {"GITHUB_TOKEN", "GROQ_TOKEN", "SMTP_PASSWORD"}

SCHEDULE_MINUTES = 60  # background auto-run interval


async def _background_scheduler():
    """Run fetch_and_review_prs every SCHEDULE_MINUTES in the background."""
    while True:
        await asyncio.sleep(SCHEDULE_MINUTES * 60)
        log.info("Background scheduler: starting PR review cycle")
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, fetch_and_review_prs)
            log.info("Background scheduler: cycle complete")
        except Exception:
            log.exception("Background scheduler: cycle failed")


@asynccontextmanager
async def lifespan(application):
    init_db()
    sync_corpus_to_qdrant.delay()
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
        "recent": recent_prs(limit=20),
        "last_checked": {repo: get_last_checked(repo) for repo in REPOS_MAIL_MAP},
        "total_processed": pr_count(),
    }
    sched_repos = [
        {"repo": repo, "email": email, "enabled": schedule_enabled.get(repo, True)}
        for repo, email in REPOS_MAIL_MAP.items()
    ]
    config_keys = {
        "QDRANT_URL": QDRANT_URL, "GROQ_TOKEN": GROQ_TOKEN, "GITHUB_TOKEN": GITHUB_TOKEN,
        "DEFAULT_COLLECTION_NAME": COLLECTION, "DEFAULT_EMBED_MODEL": EMBED_MODEL,
        "PROMPT_PATH": PROMPT_PATH, "SCHEDULE_INTERVAL": SCHEDULE_INTERVAL,
        "CACHE_ENABLED": CACHE_ENABLED, "LLM_MAX_RETRIES": LLM_MAX_RETRIES,
        "SMTP_HOST": SMTP_HOST, "SMTP_PORT": SMTP_PORT,
        "SMTP_USER": SMTP_USER, "SMTP_PASSWORD": SMTP_PASSWORD,
    }
    config_data = {}
    for k, default_val in config_keys.items():
        val = runtime_config.get(k, default_val)
        if k in HIDDEN_KEYS:
            config_data[k] = {"value": "***", "hidden": True}
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

    try:
        diff = _fetch_pr_diff(repo, pr_number)
    except Exception as e:
        return {"error": f"Failed to fetch PR diff: {e}"}

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
        )
        p_hash = compute_prompt_hash(prep["prompt"], prep["model"], prep["temperature"])

        # 2. check cache with final-prompt hash
        cached = get_latest_cached_result(repo, pr_number, p_hash)
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
        prompt = build_prompt(prompt_template, f"PR #{pr_number}", code, None)
        from single_pr_model_output_metrics import MODEL as LLM_MODEL
        n_hash = compute_prompt_hash(prompt, LLM_MODEL, 0)

        cached = get_latest_cached_result(repo, pr_number, n_hash)
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

    return result


# ---- Evaluation ----
@app.post("/api/evaluate")
async def api_evaluate(request: Request):
    body = await request.json()
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
    )
    return result


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
    try:
        init_db()
        for repo in REPOS_MAIL_MAP:
            set_last_checked(repo, None)
        summary = fetch_and_review_prs()
        return {"status": "ok", "summary": summary}
    except Exception as e:
        log.exception("Run Now failed")
        return {"status": "error", "error": str(e)}


@app.get("/api/schedule/status")
def api_schedule_status():
    """Return recent processed PRs from DB for the schedule activity log."""
    rows = recent_prs(limit=20)
    last_checked = {repo: get_last_checked(repo) for repo in REPOS_MAIL_MAP}
    total = pr_count()
    return {"recent": rows, "last_checked": last_checked, "total_processed": total}


# ---- Configuration ----
@app.get("/api/config")
def api_config_get():
    keys = {
        "QDRANT_URL": QDRANT_URL, "GROQ_TOKEN": GROQ_TOKEN, "GITHUB_TOKEN": GITHUB_TOKEN,
        "DEFAULT_COLLECTION_NAME": COLLECTION, "DEFAULT_EMBED_MODEL": EMBED_MODEL,
        "PROMPT_PATH": PROMPT_PATH, "SCHEDULE_INTERVAL": SCHEDULE_INTERVAL,
        "CACHE_ENABLED": CACHE_ENABLED, "LLM_MAX_RETRIES": LLM_MAX_RETRIES,
        "SMTP_HOST": SMTP_HOST, "SMTP_PORT": SMTP_PORT,
        "SMTP_USER": SMTP_USER, "SMTP_PASSWORD": SMTP_PASSWORD,
    }
    out = {}
    for k, default_val in keys.items():
        val = runtime_config.get(k, default_val)
        if k in HIDDEN_KEYS:
            out[k] = {"value": "***", "hidden": True}
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
