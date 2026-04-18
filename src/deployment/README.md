# PR Code Review Bot

Automated pull request code review system that uses RAG (Retrieval-Augmented Generation) to review Python code for style violations. It fetches open PRs from GitHub, runs them through three analysis methods (RAG-based LLM, naive LLM, and static tools), and sends email reports with findings.

## What it does

- Monitors configured GitHub repositories for open pull requests
- Fetches the diff of each PR and analyzes the changed Python files
- Runs three review methods on each file:
  - **RAG**: retrieves relevant coding guidelines from a vector database, feeds them as context to an LLM
  - **Naive LLM**: sends the code directly to the LLM without retrieval context
  - **Static tools**: runs pylint and flake8 on the code
- Checks for five violation categories: naming conventions, unused imports, indentation, mutable defaults, documentation formatting
- Sends an email report to the configured address with all findings
- Caches results so the same PR commit is not reviewed twice
- Provides a web UI for manual inference, evaluation, scheduling, and configuration

## Architecture

```
Browser (UI)
    |
FastAPI web server (app.py)
    |
    +-- /api/inference     ->  single_pr_model_output_metrics.py  ->  Groq LLM API
    +-- /api/eval          ->  single_pr_model_output_metrics.py  ->  Groq LLM API
    +-- /api/schedule/run  ->  worker.py (fetch_and_review_prs)   ->  GitHub API
    |
    +-- Qdrant vector DB (stores guideline embeddings from corpus/)
    +-- SQLite (review_app.db - stores processed PRs and app state)
    |
Background scheduler (asyncio task inside app.py)
    +-- periodic task: fetch_and_review_prs every SCHEDULE_INTERVAL minutes
    +-- startup task: sync_corpus_to_qdrant (loads corpus/retrival_corpus.json into Qdrant)
```

The RAG pipeline works like this:

1. On startup, the 505 guideline chunks from `corpus/retrival_corpus.json` are embedded using `BAAI/bge-large-en-v1.5` and stored in Qdrant
2. When reviewing a file, the code is embedded and the top-k most relevant guidelines are retrieved
3. The retrieved guidelines plus the code are sent to the Groq LLM with a structured prompt from `prompts/v1.txt`
4. The LLM returns a JSON list of violations with line numbers, categories, and comments

## Folder structure

```
deployment/
    app.py                          - FastAPI web server, routes, background scheduler
    worker.py                       - GitHub API calls, email sending, Qdrant sync, scheduled review task
    db.py                           - SQLite data layer (processed PRs, app state)
    single_pr_model_output_metrics.py - LLM inference, RAG retrieval, static analysis, evaluation
    config.properties               - all configuration (tokens, DB URLs, SMTP, schedule settings)
    requirements.txt                - Python dependencies
    setup.sh                        - setup and run script (Mac/Linux)
    setup.bat                       - setup and run script (Windows)
    templates/
        index.html                  - single-page web UI with four tabs
    prompts/
        v1.txt                      - LLM prompt template for code review
    corpus/
        retrival_corpus.json        - 505 coding guideline chunks for RAG
```

## Prerequisites

- Python 3.9 or later
- Docker (for Qdrant vector database)

## Before running

Open `config.properties` and fill in the following values.

**Required** (app will not work without these):

| Property | What to put |
|---|---|
| GITHUB_TOKEN | GitHub personal access token with `repo` scope. Generate one at https://github.com/settings/tokens |
| GROQ_TOKEN | Groq API key. Get one at https://console.groq.com/keys |
| REPOS_MAIL_MAP | JSON object mapping GitHub repos to email addresses, e.g. `{"owner/repo": "you@example.com"}` |

**Optional** (app works without these, but email notifications will be skipped):

| Property | What to put |
|---|---|
| SMTP_HOST | SMTP server, default is `smtp.gmail.com` |
| SMTP_PORT | SMTP port, default is `587` |
| SMTP_USER | your email address used to send reports |
| SMTP_PASSWORD | app password for the email account (for Gmail, generate at https://myaccount.google.com/apppasswords) |

Everything else in `config.properties` has working defaults and does not need to be changed.

## How to run

### Mac / Linux

```bash
chmod +x setup.sh
./setup.sh
```

### Windows

```
setup.bat
```

The script will:
1. Install Python dependencies from requirements.txt
2. Start Qdrant in Docker (pulls the image if needed)
3. Start the FastAPI web server on port 8080 (includes a built-in asyncio background scheduler)

Open http://127.0.0.1:8080 in your browser after everything starts.

## config.properties reference

| Property | Description |
|---|---|
| MODEL | LLM model name used for inference via Groq API |
| DEFAULT_COLLECTION_NAME | Qdrant collection name for storing guideline embeddings |
| DEFAULT_EMBED_MODEL | Sentence transformer model used to embed code and guidelines |
| DEFAULT_TOP_N_CANDIDATES | number of candidate chunks retrieved before re-ranking |
| DEFAULT_TOP_K_FINAL | number of final chunks passed to the LLM as context |
| LEXICAL_WEIGHT | weight given to lexical (keyword) matching during re-ranking |
| CATEGORY_BONUS | bonus score for chunks matching the detected violation category |
| RANK_PENALTY | penalty applied per rank position during re-ranking |
| MAX_PER_CATEGORY | max chunks kept per category after re-ranking |
| PROMPT_PATH | path to the LLM prompt template file |
| CORPUS_PATH | path to the JSON file containing guideline chunks |
| GITHUB_TOKEN | GitHub personal access token for API access |
| GROQ_TOKEN | Groq API key for LLM inference |
| QDRANT_URL | URL of the Qdrant vector database |
| SMTP_HOST | SMTP server hostname for sending email reports |
| SMTP_PORT | SMTP server port |
| SMTP_USER | SMTP login username (email address) |
| SMTP_PASSWORD | SMTP login password or app password |
| REPOS_MAIL_MAP | JSON mapping of GitHub repos to notification email addresses |
| SCHEDULE_INTERVAL | how often (in minutes) the background scheduler checks for new PRs |
| CACHE_ENABLED | if true, skip PRs that have already been reviewed at the same commit |
| LLM_MAX_RETRIES | number of times to retry LLM calls if the response is empty |

## Web UI tabs

**Custom Inference** - paste a GitHub PR URL or raw code, pick which review methods to run, and see results immediately.

**Evaluation** - paste a GitHub PR URL to run all three methods and get a comparison table with precision, recall, and latency for each method.

**Schedule** - view configured repositories, enable/disable them, trigger a manual review cycle with "Run Now", and see the activity log of processed PRs.

**Configuration** - view and update any config.properties value at runtime without restarting the server. Sensitive values (tokens, passwords) are masked.
