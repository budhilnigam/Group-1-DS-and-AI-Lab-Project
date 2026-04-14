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
        # migrate: add prompt_hash column if missing
        cols = [row[1] for row in c.execute("PRAGMA table_info(processed_prs)").fetchall()]
        if "prompt_hash" not in cols:
            c.execute("ALTER TABLE processed_prs ADD COLUMN prompt_hash TEXT DEFAULT ''")
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


def cache_pr(repo, pr_number, head_sha, result_json, email_sent=False, prompt_hash=""):
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        c.execute(
            """INSERT OR REPLACE INTO processed_prs
               (repo, pr_number, head_sha, result_json, processed_at, email_sent, prompt_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (repo, pr_number, head_sha, result_json, now, int(email_sent), prompt_hash),
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


def recent_prs(limit=10):
    with _conn() as c:
        rows = c.execute(
            "SELECT repo, pr_number, head_sha, processed_at, email_sent FROM processed_prs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def pr_count():
    with _conn() as c:
        row = c.execute("SELECT COUNT(*) as cnt FROM processed_prs").fetchone()
    return row["cnt"]
