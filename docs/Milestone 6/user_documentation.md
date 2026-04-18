# PR Code Review Bot — User Documentation

**Project:** Group-1 DS and AI Lab Project  
**Submitted by:** Kannan S (21f3000990)  
**Date:** 16 April 2026

---

## 1. Getting Started

The PR Code Review Bot automatically reviews pull requests on your GitHub repositories using AI-powered analysis. It identifies code quality issues, style violations, and potential bugs, then sends findings via email.

### Quick Start (Manual)

```bash
# Start Qdrant (vector database)
docker run -d -p 6333:6333 qdrant/qdrant

# Install dependencies
cd src/deployment
pip install -r requirements.txt

# Configure (edit with your API keys)
nano config.properties

# Launch the web server (includes built-in asyncio scheduler for PR polling & email)
python3 -m uvicorn app:app --host 0.0.0.0 --port 8080
```

**Dashboard:** http://localhost:8080

### Quick Start (Setup Script)

The project includes platform-specific setup scripts that handle everything automatically — installing dependencies, starting Qdrant via Docker, and starting the web server (which runs the built-in asyncio scheduler for PR polling).

**macOS / Linux:**
```bash
cd src/deployment
chmod +x setup.sh
./setup.sh
```

**Windows:**
```cmd
cd src\deployment
setup.bat
```

Both scripts perform the same steps:
1. Install Python dependencies from `requirements.txt`
2. Check Docker is installed and running
3. Start Qdrant container (`qdrant_review`) on port 6333 — reuses existing container if found
4. Launch the Uvicorn web server on port 8080 (includes the asyncio background scheduler)

Press `Ctrl+C` to stop.

---

## 2. Dashboard Overview

The main dashboard at `/` displays:

- **Stats Cards** — Total PRs, Open PRs, Closed PRs, Emails Sent, Total Violations, Clean PRs, PRs with Issues
- **Violation Categories Chart** — Bar chart breakdown by category (security, style, error_handling, etc.)
- **Top PRs by Violation Count** — Ranked list of most problematic PRs
- **Repository Filter** — Dropdown to filter all stats by a specific repo

### Dashboard Screenshots

![](../../screenshots/Screenshot%20(1470).png)

![](../../screenshots/Screenshot%20(1471).png)

![](../../screenshots/Screenshot%20(1472).png)

---

## 3. Features & How to Use

### 3.1 Repository Management

**View Repos:**  
Navigate to the Repos section. Shows all tracked repositories with their notification email and number of custom rules.

**Add a Repo:**
1. Click "Add Repository"
2. Enter repo in `owner/name` format (e.g., `kannan-dedsec/rag-test-1`)
3. Enter notification email address
4. Optionally add custom review rules (one per line)
5. Click Submit

**Remove a Repo:**  
Click the delete icon next to the repo and confirm. This deletes all cached PR data, custom rules, and Qdrant vectors for that repo.

### 3.2 Custom Review Rules

Each repo can have custom rules that augment the base 505 guidelines. Rules are embedded and stored in Qdrant for RAG retrieval.

**Add Rules:**
1. Go to Repos → select a repo → Rules
2. Enter rules as text (one guideline per entry)
3. Click Add Rules

Rules are chunked, embedded, and indexed in Qdrant immediately.

**Example rules:**
- "All database queries must use parameterized statements"
- "Functions must not exceed 50 lines"
- "Use typing annotations for all public function parameters"

### 3.3 Running Code Reviews

**Automatic (Scheduled):**  
The bot runs a background scheduler every N minutes (configurable via `SCHEDULE_INTERVAL`). It checks all enabled repos for new/updated open PRs and reviews them automatically.

**Manual Trigger ("Run Now"):**
1. Go to the Schedule section
2. Click "Run Now"

This clears last-checked timestamps and re-scans all open PRs. Cached results are reused (no duplicate LLM calls).

**Single PR Inference:**
1. Go to the Inference section
2. Paste a PR URL (e.g., `https://github.com/owner/repo/pull/123`)
3. Select analysis modes:
   - **RAG** — AI review augmented with retrieved guidelines (recommended)
   - **Naive LLM** — Direct LLM review without retrieval
   - **Static Tool** — Pylint + Flake8 analysis
4. Click Run

Results show violations with file, line, category, and explanation.

### Inference Screenshots

![](../../screenshots/Screenshot%20(1474).png)

![](../../screenshots/Screenshot%20(1475).png)

![](../../screenshots/Screenshot%20(1476).png)

![](../../screenshots/Screenshot%20(1477).png)

![](../../screenshots/Screenshot%20(1478).png)

![](../../screenshots/Screenshot%20(1479).png)

**Reprocess a PR:**  
From the schedule activity log, click "Reprocess" on any PR. This re-fetches the diff, runs inference (uses cache if available), and resends the email notification.

### 3.4 Schedule Management

- **View Schedule** — Shows all repos with their enabled/disabled status
- **Enable/Disable** — Toggle the switch next to a repo name. Disabled repos are skipped during scheduled runs.
- **Refresh PR Status** — Click "Refresh Status" to sync open/closed PR states from GitHub
- **Activity Log** — Paginated list of processed PRs with search by repo name, PR number, or title

### Schedule Screenshots

![](../../screenshots/Screenshot%20(1473).png)

### 3.5 Configuration

Runtime configuration can be adjusted from the dashboard without restarting:

| Setting | Description | Default |
|---------|-------------|---------|
| `SCHEDULE_INTERVAL` | Minutes between auto-scans | 1 |
| `CACHE_ENABLED` | Use cached results (toggle) | true |
| `LLM_MAX_RETRIES` | Retry count for failed LLM calls | 2 |

> API keys are hidden in the UI for security.
### Configuration Screenshots

![](../../screenshots/Screenshot%20(1486).png)

![](../../screenshots/Screenshot%20(1487).png)

![](../../screenshots/Screenshot%20(1488).png)

![](../../screenshots/Screenshot%20(1489).png)

### 3.6 Prompt Customization

- **View Prompts** — Shows the default review prompt template and any active overrides
- **Override Prompts** — Edit the RAG or Naive LLM prompt template and click Save
- **Reset Prompts** — Click "Reset to Default" to clear all overrides

Overrides are runtime-only and reset on server restart.

### 3.7 Evaluation Mode

For benchmarking the review system against ground truth:

**Single Evaluation:**  
Paste code and ground truth violations → returns precision, recall, F1, and accuracy per model.

**Batch Evaluation:**  
Submit a JSON with multiple entries → returns per-entry and aggregate metrics across all models.

### Evaluation Screenshots

![](../../screenshots/Screenshot%20(1480).png)

![](../../screenshots/Screenshot%20(1481).png)

![](../../screenshots/Screenshot%20(1482).png)

![](../../screenshots/Screenshot%20(1483).png)

![](../../screenshots/Screenshot%20(1484).png)

![](../../screenshots/Screenshot%20(1485).png)

---

## 4. Email Notifications

When violations are found, the bot sends an email containing:

- Repository name and PR number
- PR title and link to GitHub
- List of violations with:
  - File path and line number
  - Violation category
  - Description and suggestion

**Email setup:** Configure `SMTP_HOST`, `SMTP_USER`, and `SMTP_PASSWORD` in `config.properties`. Gmail requires an [App Password](https://myaccount.google.com/apppasswords) (not your regular password).

---

## 5. How the Review Pipeline Works

```
1. FETCH     → Bot fetches the PR diff from GitHub API
2. EMBED     → PR code is embedded using BAAI/bge-large-en-v1.5
3. RETRIEVE  → Similar guidelines retrieved from Qdrant (base + repo rules)
4. PROMPT    → Retrieved context + PR code assembled into review prompt
5. INFER     → Prompt sent to Groq LLM for analysis
6. PARSE     → LLM response parsed into structured violations
7. CACHE     → Results cached in SQLite (keyed by repo + PR + SHA + prompt hash)
8. NOTIFY    → Violations emailed to repo's configured address
9. DISPLAY   → Results shown on dashboard with analytics
```

---

## 6. Troubleshooting

| Issue | Fix |
|-------|-----|
| "Repository not tracked" error | Add the repo via Dashboard → Repos → Add Repository |
| No email received | Check SMTP settings in Configuration. Verify email address. Check spam folder. Gmail requires an App Password. |
| "Schedule run already in progress" | Wait for the current run to complete. Only one run executes at a time. |
| PR shows as "closed" but it's open | Click "Refresh Status" to sync PR states from GitHub. |
| Same violations after code fix | Push a new commit to the PR to get a fresh review (cache keys include HEAD SHA). |
| Qdrant connection refused | Ensure Qdrant is running: `docker run -d -p 6333:6333 qdrant/qdrant` |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` in `src/deployment/` |

---

## 7. Background Scheduler

The application runs a built-in asyncio background scheduler inside the FastAPI process — no separate worker, broker, or queue is required. The scheduler is started on application startup and polls all enabled repos for new/updated open PRs every `SCHEDULE_INTERVAL` minutes.

### How It Works

- On startup, `app.py` creates an asyncio background task via `asyncio.create_task(_background_scheduler())`.
- The loop calls `fetch_and_review_prs()` (from `worker.py`), then `await asyncio.sleep(SCHEDULE_INTERVAL * 60)` before the next tick.
- A `threading.Lock` (`_schedule_lock`) prevents overlapping runs if a cycle takes longer than the interval.
- The scheduler shuts down automatically when the Uvicorn server exits.

### Manual Trigger

You can also trigger a review cycle on demand from the dashboard via **Schedule → Run Now**, which calls the same `fetch_and_review_prs()` function without waiting for the next tick.

> **Note:** No Redis, RabbitMQ, or separate worker process is needed. The scheduler lives inside the same FastAPI process as the web server.

---

## 8. Setup Scripts

Two platform-specific scripts automate the full startup process.

### macOS / Linux — `setup.sh`

```bash
cd src/deployment
chmod +x setup.sh
./setup.sh
```

**What it does:**
1. Installs dependencies via `pip3 install -r requirements.txt`
2. Checks Docker is installed and running
3. Starts Qdrant container (`qdrant_review`) on port 6333 — creates or reuses
4. Waits up to 30 seconds for Qdrant health check
5. Kills any existing process on port 8080
6. Starts Uvicorn on port 8080 (which runs the asyncio scheduler inside the same process)

### Windows — `setup.bat`

```cmd
cd src\deployment
setup.bat
```

**What it does:**
1. Installs dependencies via `pip install -r requirements.txt`
2. Checks Docker is running
3. Starts Qdrant container (`qdrant_review`) on port 6333 — creates or reuses
4. Waits up to 30 seconds for Qdrant health check
5. Starts Uvicorn on port 8080 (which runs the asyncio scheduler inside the same process)

### Key Differences

| Aspect | macOS/Linux (`setup.sh`) | Windows (`setup.bat`) |
|--------|--------------------------|------------------------|
| Python command | `python3` / `pip3` | `python` / `pip` |
| Port cleanup | `lsof -ti :8080 \| xargs kill -9` | Not automated |

---

## 9. Local Development Setup

### Prerequisites

- Python 3.9+
- Docker (for Qdrant)
- GitHub Personal Access Token
- Groq API key
- Gmail App Password

### Manual Steps

```bash
cd src/deployment
pip install -r requirements.txt
# Edit config.properties with your API keys
docker run -d -p 6333:6333 qdrant/qdrant
python3 -m uvicorn app:app --host 0.0.0.0 --port 8080
```

### Using Setup Script

```bash
# macOS/Linux
cd src/deployment && ./setup.sh

# Windows
cd src\deployment && setup.bat
```

Open http://localhost:8080
