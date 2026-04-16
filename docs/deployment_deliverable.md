# PR Code Review Bot — Deployment Deliverable
---

## 1. Project Overview

The PR Code Review Bot is an automated code review system that monitors GitHub repositories for open pull requests, performs AI-powered code analysis using RAG (Retrieval-Augmented Generation), and delivers review findings via email.

### Key Capabilities

- Automated PR monitoring with configurable schedule intervals
- RAG-based code review using Qdrant vector DB + BAAI/bge-large-en-v1.5 embeddings
- LLM inference via Groq API (Llama-based models)
- Static analysis via Pylint and Flake8
- Per-repo custom review rules with Qdrant vector indexing
- Email notifications with violation summaries
- Web dashboard with analytics and repo management

---

## 2. Architecture

```
+-------------------+     +-------------------+     +-------------------+
|   GitHub Repos    |     |   Qdrant (Local)  |     |   Groq LLM API   |
|  (Source PRs)     |     |  localhost:6333   |     |  (Inference)      |
+--------+----------+     +--------+----------+     +--------+----------+
         |                         |                         |
         v                         v                         v
+------------------------------------------------------------------------+
|                        FastAPI Application                              |
|  app.py  |  worker.py  |  single_pr_model_output_metrics.py            |
|                                                                         |
|  - Background scheduler (asyncio)                                       |
|  - RAG pipeline: embed → retrieve → prompt → LLM → parse               |
|  - REST API endpoints (21 routes)                                       |
|  - Jinja2 HTML dashboard                                                |
+--------+---------------------------------------------------------------+
         |                         |
         v                         v
+-------------------+     +-------------------+
|   SQLite DB       |     |   SMTP Server     |
|  review_app.db    |     |  (Gmail)          |
+-------------------+     +-------------------+
```

---

## 3. Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Web Framework | FastAPI + Uvicorn | >= 0.128 |
| LLM Provider | Groq API | >= 1.0 |
| Vector Database | Qdrant (local Docker) | >= 1.12 |
| Embedding Model | BAAI/bge-large-en-v1.5 | HuggingFace |
| Relational Database | SQLite | Built-in |
| Static Analysis | Pylint, Flake8 | >= 3.0 |
| Templating | Jinja2 | >= 3.1 |
| Task Queue | Celery (defined, unused at runtime) | >= 5.4 |
| Source Control | GitHub | — |

---

## 4. Deployment Infrastructure

### 4.1 Local Machine

| Item | Detail |
|------|--------|
| Host | `localhost` |
| Port | `8080` |
| URL | `http://localhost:8080` |
| Start Command | `python3 -m uvicorn app:app --host 0.0.0.0 --port 8080` |
| Working Directory | `src/deployment/` |

### 4.2 Qdrant (Vector Database)

| Item | Detail |
|------|--------|
| URL | `http://localhost:6333` |
| Run via | `docker run -p 6333:6333 qdrant/qdrant` |
| Collection | `guideline_embeddings` |
| Corpus | `retrival_corpus.json` (505 base guidelines) + `repo_corpus.json` (per-repo rules) |

### 4.3 SQLite (Relational Database)

| Item | Detail |
|------|--------|
| File | `src/deployment/review_app.db` |
| Auto-created | Yes, on first startup via `init_db()` |
| Tables | `processed_prs`, `app_state` |

### 4.4 External APIs

| Service | Purpose | Config Key |
|---------|---------|------------|
| GitHub API | Fetch PR diffs, comments, status | `GITHUB_TOKEN` |
| Groq API | LLM inference for code review | `GROQ_TOKEN` |
| Gmail SMTP | Send email notifications | `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` |

---

## 5. Configuration

All configuration is in `src/deployment/config.properties`:

```properties
# Model & Retrieval
MODEL = openai/gpt-oss-20b
DEFAULT_COLLECTION_NAME = guideline_embeddings
DEFAULT_EMBED_MODEL = BAAI/bge-large-en-v1.5
DEFAULT_TOP_N_CANDIDATES = 25
DEFAULT_TOP_K_FINAL = 7
LEXICAL_WEIGHT = 0.35
CATEGORY_BONUS = 0.15
RANK_PENALTY = 0.01
MAX_PER_CATEGORY = 2
PROMPT_PATH = prompts/v1.txt
CORPUS_PATH = corpus/retrival_corpus.json

# API Keys
GITHUB_TOKEN = <your_github_pat>
GROQ_TOKEN = <your_groq_api_key>
QDRANT_URL = http://localhost:6333

# Email
SMTP_HOST = smtp.gmail.com
SMTP_PORT = 587
SMTP_USER = <your_email>
SMTP_PASSWORD = <your_app_password>

# Repos to monitor (JSON map of repo → notification email)
REPOS_MAIL_MAP = {"owner/repo": "notify@example.com"}

# Scheduler
SCHEDULE_INTERVAL = 1
CACHE_ENABLED = true
LLM_MAX_RETRIES = 2
```

---

## 6. Database Schema

### Table: `processed_prs`

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | Row ID |
| repo | TEXT NOT NULL | Repository (owner/name) |
| pr_number | INTEGER NOT NULL | PR number |
| head_sha | TEXT NOT NULL | Commit SHA |
| result_json | TEXT | JSON review results |
| processed_at | TEXT NOT NULL | ISO timestamp |
| email_sent | INTEGER DEFAULT 0 | 1 if email sent |
| prompt_hash | TEXT DEFAULT '' | SHA-256 of final prompt |
| title | TEXT DEFAULT '' | PR title |
| pr_status | TEXT DEFAULT 'open' | open / closed |

**Unique Index:** `uq_pr_prompt` on `(repo, pr_number, head_sha, prompt_hash)`

### Table: `app_state`

| Column | Type | Description |
|--------|------|-------------|
| key | TEXT PRIMARY KEY | State key |
| value | TEXT NOT NULL | State value |

Used for: `last_checked:<repo>` timestamps.

---

## 7. File Structure

```
src/deployment/
├── app.py                           # FastAPI app, routes, scheduler
├── worker.py                        # Config loading, GitHub API, review logic
├── single_pr_model_output_metrics.py # RAG retrieval, prompt building, LLM calls
├── db.py                            # SQLite data layer
├── config.properties                # Configuration (not committed)
├── requirements.txt                 # Python dependencies
├── review_app.db                    # SQLite database (auto-created)
├── prompts/
│   └── v1.txt                       # Review prompt template
├── corpus/
│   ├── retrival_corpus.json         # 505 base guideline chunks
│   └── repo_corpus.json             # Per-repo custom rule chunks
├── templates/
│   └── index.html                   # Jinja2 dashboard template
└── static/                          # CSS/JS assets
```

---

## 8. Deployment Steps

### Prerequisites

- Python 3.9+
- Docker (for Qdrant)
- GitHub Personal Access Token (with repo read access)
- Groq API key
- Gmail App Password (for email notifications)

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/budhilnigam/Group-1-DS-and-AI-Lab-Project.git
cd Group-1-DS-and-AI-Lab-Project

# 2. Start Qdrant
docker run -d -p 6333:6333 qdrant/qdrant

# 3. Install dependencies
cd src/deployment
pip install -r requirements.txt

# 4. Configure
# Edit config.properties with your API keys, email settings, and repos

# 5. Start the application
python3 -m uvicorn app:app --host 0.0.0.0 --port 8080

# 6. Open dashboard
# http://localhost:8080
```

### What Happens on Startup

1. `init_db()` — creates SQLite tables if they don't exist
2. `sync_corpus_to_qdrant()` — loads base + repo corpus into Qdrant
3. Background scheduler starts — polls repos every `SCHEDULE_INTERVAL` minutes

---

## 9. Key Design Decisions

1. **SQLite for persistence** — zero-config, file-based, no external DB server needed.
2. **Qdrant for vector search** — efficient similarity search for RAG retrieval with hybrid scoring.
3. **Asyncio scheduler** — native `asyncio.create_task` instead of Celery, eliminating Redis/RabbitMQ dependency.
4. **Config.properties** — simple key-value config file for all settings, kept out of git via `.gitignore`.
5. **Prompt hash caching** — results are cached by `(repo, pr_number, head_sha, prompt_hash)` so prompt changes trigger re-review without re-fetching.
6. **Two-way corpus sync** — corpus files and Qdrant collection are synced on startup, supporting both file-first and Qdrant-first workflows.

---

## 10. Repository Information

| Item | Value |
|------|-------|
| Repository | `budhilnigam/Group-1-DS-and-AI-Lab-Project` |
| Branch | `main` |
| Local URL | `http://localhost:8080` |
