import json
import smtplib
import logging
import io
import configparser
from email.mime.text import MIMEText
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen, build_opener, ProxyHandler
from urllib.error import HTTPError, URLError


_no_proxy_opener = build_opener(ProxyHandler({}))

from celery import Celery

from db import init_db, is_pr_cached, cache_pr, get_last_checked, set_last_checked, compute_prompt_hash


BASE_DIR = Path(__file__).parent
_raw = "[default]\n" + (BASE_DIR / "config.properties").read_text()
cfg = configparser.ConfigParser()
cfg.read_string(_raw)
_s = "default"

QDRANT_URL = cfg.get(_s, "QDRANT_URL", fallback="").strip()
GROQ_TOKEN = cfg.get(_s, "GROQ_TOKEN", fallback="").strip()
GITHUB_TOKEN = cfg.get(_s, "GITHUB_TOKEN", fallback="").strip()

COLLECTION = cfg.get(_s, "DEFAULT_COLLECTION_NAME", fallback="guideline_embeddings").strip()
EMBED_MODEL = cfg.get(_s, "DEFAULT_EMBED_MODEL", fallback="BAAI/bge-large-en-v1.5").strip()
PROMPT_PATH = str(BASE_DIR / cfg.get(_s, "PROMPT_PATH", fallback="prompts/v1.txt").strip())
CORPUS_PATH = str(BASE_DIR / cfg.get(_s, "CORPUS_PATH", fallback="corpus/retrival_corpus.json").strip())

REPOS_MAIL_MAP = json.loads(cfg.get(_s, "REPOS_MAIL_MAP", fallback="{}"))
SCHEDULE_INTERVAL = cfg.getint(_s, "SCHEDULE_INTERVAL", fallback=5)
CACHE_ENABLED = cfg.getboolean(_s, "CACHE_ENABLED", fallback=True)
LLM_MAX_RETRIES = cfg.getint(_s, "LLM_MAX_RETRIES", fallback=2)

SMTP_HOST = cfg.get(_s, "SMTP_HOST", fallback="").strip()
SMTP_PORT = cfg.getint(_s, "SMTP_PORT", fallback=587)
SMTP_USER = cfg.get(_s, "SMTP_USER", fallback="").strip()
SMTP_PASSWORD = cfg.get(_s, "SMTP_PASSWORD", fallback="").strip()

log = logging.getLogger(__name__)


runtime_config = {}
schedule_enabled = {repo: True for repo in REPOS_MAIL_MAP}


def get_config(key):
    """Return runtime override if set, else the file-loaded default."""
    defaults = {
        "QDRANT_URL": QDRANT_URL, "GROQ_TOKEN": GROQ_TOKEN, "GITHUB_TOKEN": GITHUB_TOKEN,
        "DEFAULT_COLLECTION_NAME": COLLECTION, "DEFAULT_EMBED_MODEL": EMBED_MODEL,
        "PROMPT_PATH": PROMPT_PATH, "CORPUS_PATH": CORPUS_PATH,
        "SCHEDULE_INTERVAL": SCHEDULE_INTERVAL, "CACHE_ENABLED": CACHE_ENABLED,
        "SMTP_HOST": SMTP_HOST, "SMTP_PORT": SMTP_PORT,
        "SMTP_USER": SMTP_USER, "SMTP_PASSWORD": SMTP_PASSWORD,
        "LLM_MAX_RETRIES": LLM_MAX_RETRIES,
    }
    return runtime_config.get(key, defaults.get(key, ""))


broker_path = BASE_DIR / "celery_broker.db"
results_path = BASE_DIR / "celery_results.db"

app = Celery(
    "worker",
    broker=f"sqla+sqlite:///{broker_path}",
    backend=f"db+sqlite:///{results_path}",
)
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    beat_schedule={
        "poll-prs": {
            "task": "worker.fetch_and_review_prs",
            "schedule": SCHEDULE_INTERVAL * 60,  # seconds
        },
    },
)


GH_API = "https://api.github.com"


def _gh_headers():
    h = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"token {GITHUB_TOKEN}"
    return h


def _gh_get(url, accept=None):
    headers = _gh_headers()
    if accept:
        headers["Accept"] = accept
    req = Request(url, headers=headers)
    with _no_proxy_opener.open(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def _fetch_open_prs(repo, since_iso=None):
    url = f"{GH_API}/repos/{repo}/pulls?state=open&sort=updated&direction=desc&per_page=100"
    try:
        data = json.loads(_gh_get(url))
    except (HTTPError, URLError, Exception) as e:
        log.error("GitHub API error for %s: %s", repo, e)
        return []
    if not since_iso:
        return data
    since_dt = datetime.fromisoformat(since_iso.replace("Z", "+00:00"))
    return [pr for pr in data if datetime.fromisoformat(pr["updated_at"].replace("Z", "+00:00")) > since_dt]


def _fetch_pr_info(repo, pr_number):
    """Return (state, title) for a single PR. state is 'open', 'closed', or 'merged'."""
    url = f"{GH_API}/repos/{repo}/pulls/{pr_number}"
    data = json.loads(_gh_get(url))
    state = data.get("state", "unknown")
    if state == "closed" and data.get("merged_at"):
        state = "merged"
    return state, data.get("title", "")


def _fetch_pr_diff(repo, pr_number):
    url = f"{GH_API}/repos/{repo}/pulls/{pr_number}"
    return _gh_get(url, accept="application/vnd.github.v3.diff")



@app.task(name="worker.sync_corpus_to_qdrant")
def sync_corpus_to_qdrant():
    from qdrant_client import QdrantClient, models
    from sentence_transformers import SentenceTransformer

    if not QDRANT_URL:
        log.warning("QDRANT_URL not set, skipping corpus sync")
        return "skipped"

    corpus = json.loads(Path(CORPUS_PATH).read_text("utf-8"))
    client = QdrantClient(url=QDRANT_URL)
    encoder = SentenceTransformer(EMBED_MODEL)

    
    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION not in collections:
        
        sample_vec = encoder.encode(corpus[0]["text"]).tolist()
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=models.VectorParams(size=len(sample_vec), distance=models.Distance.COSINE),
        )
        _upload_chunks(client, encoder, corpus)
        return f"created collection, uploaded {len(corpus)} chunks"

    
    existing_ids = set()
    offset = None
    while True:
        result = client.scroll(COLLECTION, limit=500, offset=offset, with_payload=["chunk_id"])
        points, offset = result
        for p in points:
            cid = (p.payload or {}).get("chunk_id", "")
            existing_ids.add(cid)
        if offset is None:
            break

    corpus_ids = {c["chunk_id"] for c in corpus}
    missing_ids = corpus_ids - existing_ids
    if not missing_ids:
        return "corpus already in sync"

    missing_chunks = [c for c in corpus if c["chunk_id"] in missing_ids]
    _upload_chunks(client, encoder, missing_chunks)
    return f"uploaded {len(missing_chunks)} new chunks"


def _chunk_id_to_int(chunk_id):
    """Convert 'chunk_0001' to 1. Falls back to hash if format differs."""
    import re
    m = re.match(r"chunk_(\d+)", chunk_id)
    return int(m.group(1)) if m else abs(hash(chunk_id)) % (2**63)


def _upload_chunks(client, encoder, chunks):
    from qdrant_client import models

    texts = [c["text"] for c in chunks]
    vectors = encoder.encode(texts, show_progress_bar=False).tolist()

    points = []
    for chunk, vec in zip(chunks, vectors):
        points.append(models.PointStruct(
            id=_chunk_id_to_int(chunk["chunk_id"]),
            vector=vec,
            payload={
                "text": chunk["text"],
                "category": chunk.get("category", ""),
                "source_type": chunk.get("source_type", ""),
                "source_path": chunk.get("source_path", ""),
                "chunk_id": chunk["chunk_id"],
            },
        ))
    # batch upsert in groups of 100
    for i in range(0, len(points), 100):
        client.upsert(COLLECTION, points=points[i:i + 100])



@app.task(name="worker.fetch_and_review_prs")
def fetch_and_review_prs():
    from single_pr_model_output_metrics import prepare_rag_prompt, _call_llm_with_retry
    from groq import Groq

    init_db()
    now = datetime.now(timezone.utc).isoformat()
    summary = {"processed": [], "skipped": 0, "errors": [], "started_at": now}

    for repo, email in REPOS_MAIL_MAP.items():
        if not schedule_enabled.get(repo, True):
            log.info("Repo %s: schedule disabled, skipping", repo)
            continue
        since = get_last_checked(repo)
        prs = _fetch_open_prs(repo, since_iso=since)
        log.info("Repo %s: %d PRs to process (since %s)", repo, len(prs), since or "start")

        for pr in prs:
            pr_number = pr["number"]
            head_sha = pr["head"]["sha"]
            pr_title = pr.get("title", "")
            pr_url = pr.get("html_url", "")

            try:
                diff = _fetch_pr_diff(repo, pr_number)
            except HTTPError as e:
                log.error("Failed to fetch diff for PR #%d: %s", pr_number, e)
                summary["errors"].append(f"PR #{pr_number}: fetch diff failed")
                continue

            repo_short = repo.split("/")[-1] if "/" in repo else repo

            try:
                prep = prepare_rag_prompt(
                    pr_code=diff, pr_id=f"PR #{pr_number}", qdrant_url=QDRANT_URL,
                    prompt_path=PROMPT_PATH, repo_name=repo_short,
                    collection_name=COLLECTION, embed_model_name=EMBED_MODEL,
                )
            except Exception:
                log.exception("RAG retrieval failed for PR #%d (%s)", pr_number, repo)
                summary["errors"].append(f"PR #{pr_number}: retrieval failed")
                continue

            p_hash = compute_prompt_hash(prep["prompt"], prep["model"], prep["temperature"])

            if CACHE_ENABLED and is_pr_cached(repo, pr_number, head_sha, p_hash):
                log.info("PR #%d (%s) cached, skipping", pr_number, repo)
                summary["skipped"] += 1
                continue

            try:
                client = Groq(api_key=GROQ_TOKEN)
                reviews, retries = _call_llm_with_retry(client, prep["prompt"], int(get_config("LLM_MAX_RETRIES")))
                chunks = prep["chunks"]
                result = {
                    "reviews": reviews,
                    "chunks_used": len(chunks),
                    "retries": retries,
                    "retrieved_chunks": [{"text": c["text"], "score": round(c.get("rerank_score", 0), 4), "category": c.get("category", "")} for c in chunks],
                    "prompt_used": prep["prompt"],
                }
            except Exception:
                log.exception("Inference failed for PR #%d (%s)", pr_number, repo)
                summary["errors"].append(f"PR #{pr_number}: inference failed")
                continue

            email_ok = send_review_email(repo, pr_number, pr_title, pr_url, result["reviews"], email)

            cache_pr(repo, pr_number, head_sha, json.dumps(result), email_sent=email_ok, prompt_hash=p_hash, title=pr_title)
            log.info("Processed PR #%d (%s), %d findings", pr_number, repo, len(result["reviews"]))
            summary["processed"].append({
                "repo": repo, "pr": pr_number, "title": pr_title,
                "findings": len(result["reviews"]), "email_sent": email_ok,
            })

        set_last_checked(repo, now)

    summary["finished_at"] = datetime.now(timezone.utc).isoformat()
    return summary



def send_review_email(repo, pr_number, pr_title, pr_url, reviews, to_email):
    if not SMTP_HOST or not SMTP_USER:
        log.warning("SMTP not configured, skipping email for PR #%d", pr_number)
        return False

    if reviews:
        lines = []
        for i, r in enumerate(reviews, 1):
            lines.append(f"  {i}. Line {r['line_number']} [{r['violation_category']}]: {r['review_comment']}")
        body_findings = "\n".join(lines)
    else:
        body_findings = "  No violations detected."

    body = f"""Automated Code Review for PR #{pr_number}
Repository: {repo}
Title: {pr_title}
URL: {pr_url}

Findings:
{body_findings}

-- Automated Code Review Bot
"""

    msg = MIMEText(body)
    msg["Subject"] = f"Code Review: PR #{pr_number} — {repo}"
    msg["From"] = SMTP_USER
    msg["To"] = to_email

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASSWORD)
            s.send_message(msg)
        return True
    except Exception:
        log.exception("Failed to send email for PR #%d to %s", pr_number, to_email)
        return False
