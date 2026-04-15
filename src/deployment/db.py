import sqlite3
from pathlib import Path
from datetime import datetime, timezone
import hashlib

DB_PATH = Path(__file__).parent / "review_app.db"


def compute_prompt_hash(final_prompt: str, model: str = "", temperature: float = 0) -> str:
    """Return SHA-256 hex digest of the final prompt + model + temperature."""
    content = f"{final_prompt}\n__model__={model}\n__temperature__={temperature}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _conn():
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c


def init_db():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS processed_prs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo TEXT NOT NULL,
                pr_number INTEGER NOT NULL,
                head_sha TEXT NOT NULL,
                result_json TEXT,
                processed_at TEXT NOT NULL,
                email_sent INTEGER DEFAULT 0,
                prompt_hash TEXT DEFAULT ''
            )
        """)
        c.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_pr_prompt
            ON processed_prs(repo, pr_number, head_sha, prompt_hash)
        """)
        # migrate: add columns if missing
        cols = [row[1] for row in c.execute("PRAGMA table_info(processed_prs)").fetchall()]
        if "prompt_hash" not in cols:
            c.execute("ALTER TABLE processed_prs ADD COLUMN prompt_hash TEXT DEFAULT ''")
        if "title" not in cols:
            c.execute("ALTER TABLE processed_prs ADD COLUMN title TEXT DEFAULT ''")
        if "pr_status" not in cols:
            c.execute("ALTER TABLE processed_prs ADD COLUMN pr_status TEXT DEFAULT 'open'")
        # migrate: drop old unique index that lacks prompt_hash
        try:
            c.execute("DROP INDEX IF EXISTS uq_pr")
        except Exception:
            pass
        c.execute("""
            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)


def is_pr_cached(repo, pr_number, head_sha, prompt_hash=""):
    with _conn() as c:
        row = c.execute(
            "SELECT 1 FROM processed_prs WHERE repo=? AND pr_number=? AND head_sha=? AND prompt_hash=?",
            (repo, pr_number, head_sha, prompt_hash),
        ).fetchone()
    return row is not None


def get_cached_result(repo, pr_number, head_sha):
    with _conn() as c:
        row = c.execute(
            "SELECT result_json FROM processed_prs WHERE repo=? AND pr_number=? AND head_sha=?",
            (repo, pr_number, head_sha),
        ).fetchone()
    return row["result_json"] if row else None


def get_latest_cached_result(repo, pr_number, prompt_hash=""):
    with _conn() as c:
        row = c.execute(
            "SELECT result_json FROM processed_prs WHERE repo=? AND pr_number=? AND prompt_hash=? ORDER BY processed_at DESC LIMIT 1",
            (repo, pr_number, prompt_hash),
        ).fetchone()
    return row["result_json"] if row else None


def get_latest_cached_result_any(repo, pr_number):
    """Get the most recent cached result for a PR regardless of prompt_hash."""
    with _conn() as c:
        row = c.execute(
            "SELECT result_json FROM processed_prs WHERE repo=? AND pr_number=? AND result_json IS NOT NULL ORDER BY processed_at DESC LIMIT 1",
            (repo, pr_number),
        ).fetchone()
    return row["result_json"] if row else None


def cache_pr(repo, pr_number, head_sha, result_json, email_sent=False, prompt_hash="", title=""):
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        # Preserve existing pr_status; default to 'open' for new PRs
        existing = c.execute(
            "SELECT pr_status FROM processed_prs WHERE repo=? AND pr_number=? ORDER BY id DESC LIMIT 1",
            (repo, pr_number),
        ).fetchone()
        status = existing["pr_status"] if existing and existing["pr_status"] else "open"
        c.execute(
            """INSERT OR REPLACE INTO processed_prs
               (repo, pr_number, head_sha, result_json, processed_at, email_sent, prompt_hash, title, pr_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (repo, pr_number, head_sha, result_json, now, int(email_sent), prompt_hash, title, status),
        )


def update_email_sent(repo, pr_number, email_sent):
    """Update email_sent and processed_at on the most recent row for this repo/pr."""
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        c.execute(
            "UPDATE processed_prs SET email_sent=?, processed_at=? WHERE id = ("
            "  SELECT id FROM processed_prs WHERE repo=? AND pr_number=? ORDER BY id DESC LIMIT 1"
            ")",
            (int(email_sent), now, repo, pr_number),
        )


def get_last_checked(repo):
    with _conn() as c:
        row = c.execute(
            "SELECT value FROM app_state WHERE key=?",
            (f"last_checked:{repo}",),
        ).fetchone()
    return row["value"] if row else None


def set_last_checked(repo, timestamp_iso):
    with _conn() as c:
        if timestamp_iso is None:
            c.execute("DELETE FROM app_state WHERE key=?", (f"last_checked:{repo}",))
        else:
            c.execute(
                "INSERT OR REPLACE INTO app_state (key, value) VALUES (?, ?)",
                (f"last_checked:{repo}", timestamp_iso),
            )


def recent_prs(limit=10, offset=0, search="", only_open=True):
    # Use a subquery to get latest status per PR, then filter
    base = (
        "SELECT repo, pr_number, MAX(processed_at) as processed_at, "
        "MAX(email_sent) as email_sent, MAX(title) as title, "
        "(SELECT pr_status FROM processed_prs p2 "
        " WHERE p2.repo=processed_prs.repo AND p2.pr_number=processed_prs.pr_number "
        " ORDER BY p2.processed_at DESC LIMIT 1) as pr_status "
        "FROM processed_prs"
    )
    conditions = []
    params = []
    if search:
        like = f"%{search}%"
        conditions.append("(repo LIKE ? OR CAST(pr_number AS TEXT) LIKE ? OR title LIKE ?)")
        params.extend([like, like, like])
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    group_having = " GROUP BY repo, pr_number"
    if only_open:
        group_having += " HAVING pr_status='open'"
    with _conn() as c:
        rows = c.execute(
            base + where + group_having + " ORDER BY processed_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
    return [dict(r) for r in rows]


def pr_count(search="", only_open=True):
    inner = (
        "SELECT "
        "(SELECT pr_status FROM processed_prs p2 "
        " WHERE p2.repo=processed_prs.repo AND p2.pr_number=processed_prs.pr_number "
        " ORDER BY p2.processed_at DESC LIMIT 1) as pr_status "
        "FROM processed_prs"
    )
    conditions = []
    params = []
    if search:
        like = f"%{search}%"
        conditions.append("(repo LIKE ? OR CAST(pr_number AS TEXT) LIKE ? OR title LIKE ?)")
        params.extend([like, like, like])
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    group_having = " GROUP BY repo, pr_number"
    if only_open:
        group_having += " HAVING pr_status='open'"
    with _conn() as c:
        row = c.execute(
            "SELECT COUNT(*) as cnt FROM (" + inner + where + group_having + ")",
            params,
        ).fetchone()
    return row["cnt"] if row else 0


def update_pr_statuses(open_prs):
    """Mark PRs as open or closed based on the set of currently open PR numbers.
    open_prs: dict of {(repo, pr_number): title}"""
    with _conn() as c:
        all_prs = c.execute(
            "SELECT DISTINCT repo, pr_number FROM processed_prs"
        ).fetchall()
        for row in all_prs:
            key = (row["repo"], row["pr_number"])
            if key in open_prs:
                c.execute(
                    "UPDATE processed_prs SET pr_status='open', title=? WHERE repo=? AND pr_number=?",
                    (open_prs[key], key[0], key[1]),
                )
            else:
                c.execute(
                    "UPDATE processed_prs SET pr_status='closed' WHERE repo=? AND pr_number=?",
                    (key[0], key[1]),
                )


def dashboard_stats(repo_filter=""):
    """Aggregate stats for the dashboard, optionally filtered by repo."""
    import json as _json
    with _conn() as c:
        # Get all distinct repos
        all_repos = [r["repo"] for r in c.execute(
            "SELECT DISTINCT repo FROM processed_prs"
        ).fetchall()]

        # Get latest result per PR (deduplicated)
        q = ("SELECT repo, pr_number, result_json, pr_status, email_sent, title "
             "FROM processed_prs WHERE id IN ("
             "  SELECT MAX(id) FROM processed_prs GROUP BY repo, pr_number"
             ") AND result_json IS NOT NULL")
        params = []
        if repo_filter:
            q += " AND repo=?"
            params.append(repo_filter)
        rows = c.execute(q, params).fetchall()

    total_prs = len(rows)
    open_prs = sum(1 for r in rows if r["pr_status"] == "open")
    closed_prs = total_prs - open_prs
    emails_sent = sum(1 for r in rows if r["email_sent"])

    violation_categories = {}
    pr_violation_counts = []  # (pr_number, title, count)
    prs_with_violations = 0
    prs_clean = 0
    total_violations = 0

    for r in rows:
        try:
            data = _json.loads(r["result_json"])
            reviews = data.get("reviews", [])
        except Exception:
            reviews = []
        count = len(reviews)
        total_violations += count
        if count > 0:
            prs_with_violations += 1
        else:
            prs_clean += 1
        pr_violation_counts.append({
            "pr_number": r["pr_number"],
            "title": r["title"] or f"PR #{r['pr_number']}",
            "repo": r["repo"],
            "count": count,
        })
        for rv in reviews:
            cat = rv.get("violation_category", "unknown")
            violation_categories[cat] = violation_categories.get(cat, 0) + 1

    # Top 10 PRs by violation count
    pr_violation_counts.sort(key=lambda x: x["count"], reverse=True)

    return {
        "repos": all_repos,
        "total_prs": total_prs,
        "open_prs": open_prs,
        "closed_prs": closed_prs,
        "emails_sent": emails_sent,
        "total_violations": total_violations,
        "prs_with_violations": prs_with_violations,
        "prs_clean": prs_clean,
        "violation_categories": violation_categories,
        "top_prs_by_violations": pr_violation_counts[:15],
    }


def delete_repo_data(repo):
    """Delete all processed PR rows and app_state entries for a repo."""
    with _conn() as c:
        c.execute("DELETE FROM processed_prs WHERE repo=?", (repo,))
        c.execute("DELETE FROM app_state WHERE key=?", (f"last_checked:{repo}",))
