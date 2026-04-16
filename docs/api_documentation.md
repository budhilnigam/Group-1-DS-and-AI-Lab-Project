# PR Code Review Bot — API Documentation

---

## 1. Health & Status

### `GET /health`

Health check with basic system info.

**Response:**
```json
{
  "status": "ok",
  "processed_prs": 5,
  "repos_tracked": ["kannan-dedsec/rag-test-1", "kannan-dedsec/rag-test-2"]
}
```

### `GET /status`

Recent activity and last-checked timestamps per repo.

**Response:**
```json
{
  "recent": [
    {
      "repo": "kannan-dedsec/rag-test-1",
      "pr_number": 1,
      "processed_at": "2026-04-16T06:25:09+00:00",
      "email_sent": 1,
      "title": "added import statement",
      "pr_status": "open"
    }
  ],
  "last_checked": {
    "kannan-dedsec/rag-test-1": "2026-04-16T06:25:09+00:00"
  }
}
```

---

## 2. Inference

### `POST /api/inference`

Run code review on a specific open PR.

**Request:**
```json
{
  "pr_url": "https://github.com/owner/repo/pull/123",
  "run_rag": true,
  "run_naive": false,
  "run_static": false
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `pr_url` | string | required | GitHub PR URL |
| `run_rag` | bool | `true` | RAG-augmented review |
| `run_naive` | bool | `false` | Direct LLM review without retrieval |
| `run_static` | bool | `false` | Pylint + Flake8 analysis |

**Response (success):**
```json
{
  "RAG": [
    {
      "file": "app.py",
      "line": 42,
      "violation_type": "error",
      "violation_category": "security",
      "description": "SQL injection vulnerability detected",
      "suggestion": "Use parameterized queries"
    }
  ],
  "Naive_LLM": [],
  "Static_tool": [],
  "retrieved_chunks": ["guideline text 1", "guideline text 2"],
  "prompts": {"RAG": "..."},
  "cached_models": {"RAG": true}
}
```

**Errors:**
```json
{"error": "Invalid PR URL. Expected: https://github.com/owner/repo/pull/123"}
{"error": "Repository 'owner/repo' is not added for monitoring."}
{"error": "This PR is closed. Only open PRs can be processed."}
```

---

## 3. Evaluation

### `POST /api/evaluate`

Evaluate review models against ground truth violations.

**Single Mode Request:**
```json
{
  "code": "def foo():\n    x = 1\n    return x",
  "ground_truth": [
    {
      "file": "test.py",
      "line": 2,
      "violation_type": "style",
      "violation_category": "naming",
      "description": "Variable name too short"
    }
  ]
}
```

**Single Mode Response:**
```json
{
  "Metrics": {
    "RAG": {"Accuracy": 0.8, "Precision": 0.9, "Recall": 0.7, "F1": 0.78, "TP": 7, "FP": 1, "FN": 3},
    "Naive_LLM": {"Accuracy": 0.6, "Precision": 0.7, "Recall": 0.5, "F1": 0.58, "TP": 5, "FP": 2, "FN": 5},
    "Static_tool": {"Accuracy": 0.5, "Precision": 0.6, "Recall": 0.4, "F1": 0.48, "TP": 4, "FP": 3, "FN": 6}
  }
}
```

**Batch Mode Request:**
```json
{
  "entries": [
    {
      "id": "eval-001",
      "repo": "owner/repo",
      "source_code": "...",
      "source_path": "src/app.py",
      "ground_truth_reviews": [...]
    }
  ]
}
```

**Batch Mode Response:**
```json
{
  "batch": true,
  "results": [{"id": "eval-001", "Metrics": {...}}],
  "aggregate": {
    "RAG": {"Accuracy": 0.75, "Precision": 0.8, "Recall": 0.7, "F1": 0.74, "TP": 70, "FP": 18, "FN": 30},
    "Naive_LLM": {...},
    "Static_tool": {...}
  }
}
```

---

## 4. Schedule Management

### `GET /api/schedule`

List all repos with schedule enable/disable status.

**Response:**
```json
[
  {"repo": "kannan-dedsec/rag-test-1", "email": "21f3000990@ds.study.iitm.ac.in", "enabled": true},
  {"repo": "kannan-dedsec/rag-test-2", "email": "21f3000990@ds.study.iitm.ac.in", "enabled": false}
]
```

### `POST /api/schedule`

Enable or disable scheduled reviews for a repo.

**Request:**
```json
{"repo": "kannan-dedsec/rag-test-1", "enabled": false}
```

**Response:**
```json
{"repo": "kannan-dedsec/rag-test-1", "enabled": false}
```

### `POST /api/schedule/run`

Trigger an immediate fetch-and-review cycle for all enabled repos. Clears last-checked timestamps so all open PRs are re-scanned. Cached results are reused. Only one run can execute at a time.

**Request:** *(none)*

**Response (success):**
```json
{
  "status": "ok",
  "summary": {
    "kannan-dedsec/rag-test-1": {"processed": 2, "emails_sent": 1, "errors": 0}
  }
}
```

**Response (locked):**
```json
{"status": "error", "error": "A schedule run is already in progress. Please wait."}
```

### `GET /api/schedule/status`

Paginated list of processed PRs from the database.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `per_page` | int | 15 | Results per page |
| `search` | string | "" | Filter by repo, PR number, or title |

**Response:**
```json
{
  "recent": [{"repo": "...", "pr_number": 1, "title": "...", "processed_at": "...", "email_sent": 1, "pr_status": "open"}],
  "last_checked": {"kannan-dedsec/rag-test-1": "2026-04-16T06:25:09+00:00"},
  "total_processed": 25,
  "page": 1,
  "per_page": 15,
  "total_pages": 2
}
```

### `POST /api/schedule/refresh-status`

Sync open/closed PR states from GitHub. Marks closed PRs in the database.

**Response:**
```json
{"status": "ok", "open_count": 3}
```

### `POST /api/schedule/reprocess`

Reprocess a single PR — fetch diff, run inference (cache-aware), send email.

**Request:**
```json
{"repo": "kannan-dedsec/rag-test-1", "pr_number": 1}
```

**Response:**
```json
{
  "status": "ok",
  "pr_number": 1,
  "repo": "kannan-dedsec/rag-test-1",
  "findings": 3,
  "used_cache": true,
  "email_sent": true
}
```

---

## 5. Dashboard

### `GET /api/dashboard`

Aggregated stats for the analytics dashboard.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `repo` | string | "" | Filter by specific repo (optional) |

**Response:**
```json
{
  "repos": ["kannan-dedsec/rag-test-1", "kannan-dedsec/rag-test-2"],
  "total_prs": 10,
  "open_prs": 3,
  "closed_prs": 7,
  "emails_sent": 8,
  "total_violations": 45,
  "prs_with_violations": 6,
  "prs_clean": 4,
  "violation_categories": {"security": 5, "style": 20, "error_handling": 10, "performance": 10},
  "top_prs_by_violations": [
    {"pr_number": 3, "title": "Add auth module", "repo": "...", "count": 12}
  ]
}
```

---

## 6. Configuration

### `GET /api/config`

Get current runtime configuration. Sensitive keys are hidden.

**Response:**
```json
{
  "QDRANT_URL": {"value": "http://localhost:6333", "hidden": false},
  "GROQ_TOKEN": {"value": "***", "hidden": true},
  "GITHUB_TOKEN": {"value": "***", "hidden": true},
  "SCHEDULE_INTERVAL": {"value": 1, "hidden": false},
  "CACHE_ENABLED": {"value": true, "toggle": true},
  "LLM_MAX_RETRIES": {"value": 2, "hidden": false},
  "SMTP_USER": {"value": "user@gmail.com", "hidden": false},
  "SMTP_PASSWORD": {"value": "***", "hidden": true}
}
```

### `POST /api/config`

Update runtime configuration (no restart needed).

**Request:**
```json
{"SCHEDULE_INTERVAL": 5, "CACHE_ENABLED": false}
```

**Response:**
```json
{"updated": ["SCHEDULE_INTERVAL", "CACHE_ENABLED"]}
```

---

## 7. Repository Management

### `GET /api/repos`

List all tracked repositories.

**Response:**
```json
[
  {"repo": "kannan-dedsec/rag-test-1", "email": "21f3000990@ds.study.iitm.ac.in", "rules": 5},
  {"repo": "kannan-dedsec/rag-test-2", "email": "21f3000990@ds.study.iitm.ac.in", "rules": 2}
]
```

### `POST /api/repos`

Add a new repository for monitoring.

**Request:**
```json
{
  "repo": "owner/repo-name",
  "email": "notify@example.com",
  "rules": ["All functions must have docstrings", "Use snake_case for variable names"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `repo` | string | Yes | Repository in `owner/name` format |
| `email` | string | Yes | Notification email |
| `rules` | array | No | Custom review rules to add |

**Response:**
```json
{"status": "ok", "repo": "owner/repo-name", "email": "notify@example.com", "rules_added": 2}
```

### `DELETE /api/repos`

Remove a repo from monitoring. Deletes all cached data, custom rules, and Qdrant vectors.

**Request:**
```json
{"repo": "owner/repo-name"}
```

**Response:**
```json
{"status": "ok", "repo": "owner/repo-name"}
```

### `GET /api/repos/rules?repo=owner/repo-name`

Get custom review rules for a specific repo.

**Response:**
```json
{
  "repo": "kannan-dedsec/rag-test-1",
  "rules": [
    {"text": "All functions must have docstrings", "id": "..."},
    {"text": "Use snake_case for variable names", "id": "..."}
  ]
}
```

### `POST /api/repos/rules`

Add custom review rules to a repo. Rules are embedded and indexed in Qdrant.

**Request:**
```json
{
  "repo": "kannan-dedsec/rag-test-1",
  "rules": ["New rule 1", "New rule 2"]
}
```

**Response:**
```json
{"status": "ok", "repo": "kannan-dedsec/rag-test-1", "rules_added": 2, "chunks": [...]}
```

---

## 8. Prompt Management

### `GET /api/prompts`

Get default prompt template and any active runtime overrides.

**Response:**
```json
{
  "default": "You are a code reviewer. Given the following...",
  "RAG": "",
  "Naive_LLM": ""
}
```

### `POST /api/prompts`

Override prompt templates at runtime (resets on restart).

**Request:**
```json
{
  "RAG": "Custom RAG prompt template...",
  "Naive_LLM": ""
}
```

**Response:**
```json
{"updated": ["RAG", "Naive_LLM (reset)"]}
```

### `POST /api/prompts/reset`

Reset all prompt overrides to defaults.

**Response:**
```json
{"status": "ok", "message": "Prompts reset to default"}
```

---

## 9. Web Pages

### `GET /`

Main dashboard HTML page (Jinja2 rendered). Features: stats cards, violation charts, PR table, repo management, schedule controls, inference form, configuration panel.

---

## 10. Error Handling

All API endpoints return JSON. Errors use the format:

```json
{"error": "Description of the error"}
```

Common errors:

| Error | Cause |
|-------|-------|
| `Invalid PR URL` | URL doesn't match `https://github.com/owner/repo/pull/N` |
| `Repository not added for monitoring` | Repo not in tracked list |
| `This PR is closed` | Only open PRs can be processed |
| `Both repo and email are required` | Missing fields on add repo |
| `A schedule run is already in progress` | Concurrent run attempted |

---

## 11. Authentication

The API does not require authentication. All endpoints are publicly accessible on `localhost`. API keys (GitHub, Groq, SMTP) are server-side only and never exposed to clients (hidden in `/api/config` responses).
