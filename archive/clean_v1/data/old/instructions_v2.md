# 🧠 0. Objective

Build a **RAG-based LLM Code Review Agent** that:

* Works on:

  * django
  * scikit-learn
  * pandas
  * fastapi
  * flask

* Detects:

  1. naming conventions
  2. unused imports
  3. mutable default arguments
  4. indentation / spacing
  5. repo-specific guideline violations

---

# ⚙️ 1. High-Level Architecture

```text
PR Diff
   ↓
AST-aware chunking
   ↓
Embedding (bge-large)
   ↓
Qdrant (with metadata)
   ↓
Filtered Retrieval (multi-source)
   ↓
Reranking (optional)
   ↓
LLM (gpt-oss)
   ↓
Structured output (violations + comments)
```

---

# 🌐 2. PR Collection (STRICT)

## Allowed repos ONLY:

```text
django/django
pandas-dev/pandas
scikit-learn/scikit-learn
fastapi/fastapi
pallets/flask
```

---

## Query:

```bash
is:pr is:merged repo:<repo> language:Python comments:>0
```

---

## Filters:

### MUST:

* reviewer ≠ author
* ignore bots
* diff ≤ 200 lines
* only `.py` files

---

# 📦 3. Dataset Schema (MANDATORY)

Every sample:

```json
{
  "repo": "django",
  "file": "models.py",
  "chunk_id": "c1",
  "diff_structured": [
    {"type": "context", "old_line": 1, "new_line": 1, "content": "def func():"},
    {"type": "deletion", "old_line": 2, "new_line": null, "content": "    old"},
    {"type": "addition", "old_line": null, "new_line": 2, "content": "    new"}
  ],

  "violations": [
    {
      "type": "mutable_default",
      "line": 12,
      "review_comment": "Avoid mutable default..."
    }
  ]
}
```

---



# 🧬 6. Unified Embedding Schema

All entries must follow:

```json
{
  "type": "guideline | diff | review",
  "text": "...",
  "repo": "django",
  "file": "...",
  "function": "...",
  "violation_type": "..."
}
```

---

# 🧠 7. Embedding

Use:

* `BAAI/bge-large-en-v1.5`

---

## Embed:

### 1. Guidelines

### 2. Diff chunks (AST-based)

### 3. Review comments

---

# 🗄️ 8. Vector DB

## Use:

* Qdrant

---

## Collection schema:

```json
{
  "vector": [...],
  "payload": {
    "repo": "...",
    "type": "...",
    "violation_type": "...",
    "file": "...",
    "function": "..."
  }
}
```

---

# 🔍 9. Metadata-Aware Retrieval (CORE)

## MUST IMPLEMENT

---

## Step 1: Filter

```json
{
  "must": [
    {"key": "repo", "match": "django"}
  ]
}
```

---

## Step 2: Multi-source retrieval

Retrieve separately:

### A. Guidelines

```json
"type": "guideline"
```

### B. Past reviews

```json
"type": "review"
```

### C. Similar diffs

```json
"type": "diff"
```

---

## Step 3: Merge context

```text
[Guideline]
[Similar past review]
[Current diff]
```

---

## ⚠️ DO NOT:

* retrieve only guidelines
* ignore review comments

---

# 🔁 10. Reranking (OPTIONAL BUT STRONG)

Use:

* cross-encoder (ms-marco)

OR

* LLM scoring

---

# 🧪 11. Train / Validation / Test

## Split:

```text
70 / 15 / 15
```

---

## Stratification:

* maintain distribution of 5 violation classes

---

# 📊 12. Evaluation

---

# 🎯 A. Detection

Multi-label classification:

* Micro F1
* Macro F1
* Precision / Recall

---

# 🧠 B. Comment Quality

---

## 1. Semantic similarity

Use:

* BERTScore

---

## 2. LLM Judge

Score:

* correctness
* clarity
* usefulness

---

## 3. Rule-based validation

---

# ⚖️ 13. Baselines

Compare with:

* pylint
* flake8
* LLM without RAG

---

# 🚀 14. Deployment Design

---

## Step 1: Repo onboarding

* parse guidelines
* generate embeddings
* insert into Qdrant

---

## Step 2: PR trigger

* fetch diff
* run pipeline

---

## Step 3: Output

* structured violations
* comments

---

# 🧾 15. File Structure

```text
src/
  data_processing/
    <repo_name>/
      v1/
        <repo_name>_prs.json
        <repo_name>_pr_state.json

data/
  raw/
    guidelines/
    prs/

  processed/
    dataset.jsonl
    guideline_chunks/
    embedding_ready/

  vector_db/

results/
  predictions.jsonl
  metrics.json
```

---

# 🔥 16. Critical Rules

* MUST use metadata filtering
* MUST include review comments in retrieval
* MUST support multiple violations per chunk

---

# 🏁 17. Success Criteria

Your system should:

* match static tools on detection
* outperform LLM (no RAG) on consistency
* generate **repo-aware review comments**

---

# 💡 Final Instruction

> Focus on **retrieval quality, not model size**
