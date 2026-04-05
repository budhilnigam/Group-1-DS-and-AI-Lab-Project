# Local Model Analysis — RAG-based Code Review with phi4:14b

**Author:** Kannan S (21f3000990)  
**Date:** April 2026  
**Branch:** `kannan-local-models-analysis`

---

## TL;DR

We evaluated three baselines for automated Python code review: a **Static analysis** baseline (flake8 + pylint), a **LLM-only** baseline (phi4:14b with no retrieval), and a **RAG** baseline (phi4:14b + retrieved coding guidelines). The evaluation was done on 103 files with 721 ground-truth violations across 5 categories. Static analysis dominated with macro F1 = 0.578, while LLM achieved 0.206 and RAG 0.108. The retrieval system itself performed well (Recall@10 = 0.97, MRR = 0.96), but the LLM struggled to translate retrieved context into accurate line-level predictions. Static tools had the highest hallucination rate (52.2%) due to over-detection, while LLM (37.0%) and RAG (39.5%) were more precise but missed most violations.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Evaluation Dataset](#2-evaluation-dataset)
3. [Tools and Infrastructure](#3-tools-and-infrastructure)
4. [Retrieval Corpus](#4-retrieval-corpus)
5. [Prompt Engineering](#5-prompt-engineering)
6. [Production Prompt Configuration](#6-production-prompt-configuration)
7. [Three Baselines](#7-three-baselines)
8. [Classification Metrics](#8-classification-metrics)
9. [Per-Category F1 Scores](#9-per-category-f1-scores)
10. [Retrieval Quality](#10-retrieval-quality)
11. [Hallucination Analysis](#11-hallucination-analysis)
12. [Grounding Analysis](#12-grounding-analysis)
13. [Latency Comparison](#13-latency-comparison)
14. [Limitations and How We Addressed Them](#14-limitations-and-how-we-addressed-them)
15. [Scripts Reference](#15-scripts-reference)
16. [How to Reproduce](#16-how-to-reproduce)
17. [Notebooks](#17-notebooks)
18. [Visualizations](#18-visualizations)

---

## 1. Problem Statement

The goal is to investigate whether **retrieved project-specific knowledge improves LLM code review comments** compared to general-purpose LLMs and static analysis tools.

We focus on **single-file Python PR diffs** (≤200 modified lines), detecting **guideline violations only** — no functional correctness, security, or architecture issues. The system generates localized, line-level style comments with explicit guideline references.

**Five violation categories:**

| Category | What it covers |
|---|---|
| `unused_import` | Imports declared but never used (F401, W0611) |
| `indentation` | Mixed tabs/spaces, non-4-space indent, alignment issues (E1xx, W0311) |
| `naming_convention` | Non-snake_case functions, non-CamelCase classes, bad variable names (N8xx, C0103) |
| `documentation_formatting` | Missing or malformed docstrings (D1xx-D4xx, C0114-C0116) |
| `mutable_default` | Mutable objects (list, dict, set) as function default arguments (B006, W0102) |

---

## 2. Evaluation Dataset

| Property | Value |
|---|---|
| Total evaluation entries | 103 |
| Total ground-truth reviews | 721 |
| Source files directory | `data/processed/evaluation_files/` |
| Evaluation JSON | `data/processed/evaluation.json` |
| Framework repos | flask, fastapi, pandas, sklearn, django |
| PR types | Synthetic (LLM-generated violations) + Manual (hand-annotated) |

**How the dataset was built:**

1. **Synthetic repos** — We created GitHub repos (`synthetic-{framework}`) with 20 PRs each, where violations were injected into clean code files using LLM-based injection + regex fallback (`scripts/create_synthetic_repos.py`).
2. **Review comments** — PR review comments were collected from these synthetic repos (`scripts/fetch_review_comments.py`) and merged into the retrieval corpus.
3. **Manual entries** — 6 hand-annotated framework-specific files were added (Django models/tests, FastAPI users, Flask blog, Pandas cleaning, Sklearn estimator).
4. **Evaluation dataset creation** — `scripts/create_evaluation_dataset.py` matched source files to ground-truth reviews by path/category/timestamp.

Each evaluation entry has this structure:
```json
{
  "id": "<unique_id>",
  "source_file": "evaluation_files/synthetic-django_PR_21_admin.py",
  "repo": "synthetic-django",
  "ground_truth_reviews": [
    {
      "line_number": 15,
      "violation_category": "unused_import",
      "review_comment": "Module 'os' is imported but never used.",
      "match_confidence": 1.0
    }
  ]
}
```

The `data_preprocessor.ipynb` notebook handles the entire data pipeline — corpus creation, synthetic repo generation, review collection, and evaluation dataset assembly.

---

## 3. Tools and Infrastructure

### 3.1 LLM Inference

| Component | Details |
|---|---|
| Model | **phi4:14b** (Microsoft, 14B parameters) |
| Runtime | **Ollama** (local, no API dependency) |
| Temperature | 0.0 (deterministic) |
| Max tokens | 1024 |
| Retry logic | Up to 4 attempts for valid JSON |
| Caching | SHA256 hash of (prompt + code + model + temperature) → JSON file in `data/llm_cache/` |
| Cache location | `data/llm_cache/{sha256_hash}.json` |

The caching mechanism ensures reproducibility — every inference result is stored and reused on subsequent runs. The cache key is computed as:
```python
hashlib.sha256(f"{prompt}|{code}|{model}|{temperature}".encode()).hexdigest()
```

### 3.2 Static Analysis Tools

| Tool | Rules used | Categories covered |
|---|---|---|
| **flake8** | E101-E131, W191, F401, N801-N818, B006, B008, D100-D417 | All 5 |
| **flake8-bugbear** | B006, B008 | mutable_default |
| **flake8-docstrings** | D100-D417 | documentation_formatting |
| **pep8-naming** | N801-N818 | naming_convention |
| **pylint** | W0311, C0103-C0105, W0611, W0614, W0404, W0406, W0102, C0114-C0116, C0112, C0199 | All 5 |

The category mapping is defined in `scripts/evaluate_static_analysis.py` through `FLAKE8_MAP` and `PYLINT_MAP` dictionaries that translate tool-specific error codes to our 5 categories.

**Pylint config used:**
```
--disable=all --enable=W0311,C0103,W0611,W0102,C0114,C0115,C0116
```

### 3.3 Retrieval System

| Component | Details |
|---|---|
| Embedding model | **BAAI/bge-large-en-v1.5** (SentenceTransformers) |
| Vector dimension | 1024 |
| Index type | **FAISS IndexFlatIP** (inner product similarity) |
| Top-K | 10 chunks per query |
| Strategy | **S15** (adaptive budget + refined queries + heuristic reranking) |
| Corpus size | 216+ guideline chunks |

The S15 retrieval strategy in `scripts/retrieve.py` works in 4 steps:
1. **Category prediction** — heuristic regex analysis of code to predict which categories are likely present (confidence 0–3)
2. **Adaptive budget** — allocate retrieval slots per category based on confidence: `{3: 4, 2: 3, 1: 2, 0: 1}` slots
3. **Refined queries** — category-specific keyword-rich queries (e.g., `"unused import module not used remove F401 W0611"` for unused_import)
4. **Heuristic reranking** — boost scores by confidence: `{3: +0.12, 2: +0.06, 1: +0.02, 0: -0.03}`

S15 was selected from 16 strategies tested in `scripts/evaluate_retrieval.py`:
- Precision: 59.6%, Recall: 96.3%, MRR: 0.625

### 3.4 Python Dependencies

From `requirements.txt`:

| Package | Purpose |
|---|---|
| `faiss-cpu` | Vector similarity search index |
| `sentence-transformers` | BAAI/bge-large-en-v1.5 embeddings |
| `flake8` | Base linter |
| `flake8-bugbear` | Mutable default detection (B006) |
| `flake8-docstrings` | Docstring rules (D-series) |
| `pep8-naming` | Naming convention rules (N-series) |
| `pylint` | Secondary linter |
| `numpy` | Array operations |
| `pandas` | Data manipulation |
| `scikit-learn` | Evaluation metrics |
| `matplotlib` | Visualization |
| `python-dotenv` | Environment variable loading |
| `requests` | HTTP for GitHub API |
| `tqdm` | Progress bars |
| `groq` | API-based LLM inference (optional, not used in local analysis) |

---

## 4. Retrieval Corpus

The retrieval corpus is stored in `data/processed/retrival_corpus.json` and contains 216+ chunks organized by category and source.

### Sources

| Source | Type | Categories covered |
|---|---|---|
| PEP 8 | Official Python style guide | indentation, naming_convention |
| PEP 257 | Docstring conventions | documentation_formatting |
| Ruff | Fast Python linter rules | All 5 |
| Flake8 / pycodestyle | Linter error codes | indentation, unused_import |
| Pylint | Static analysis messages | All 5 |
| Django coding style | Framework guidelines | naming, imports, docs, indentation |
| Pandas contributing guide | Framework guidelines | imports, docs, naming |
| Scikit-learn developer guide | Framework guidelines | naming, imports, docs, mutable_default |
| Flask contributing guide | Framework guidelines | docs |
| Synthetic review comments | From PR reviews on synthetic repos | All 5 |

### Chunk Design

Following research from [arxiv.org/pdf/2603.06976](https://arxiv.org/pdf/2603.06976) and [arxiv.org/pdf/2505.21700](https://arxiv.org/pdf/2505.21700):
- Each chunk contains **one idea** (single guideline or rule)
- Chunk size: **68–128 tokens** for optimal retrieval
- No duplicate guidelines
- Each chunk has: `text`, `category`, `source_type`, `source_path`, `chunk_id`

Example chunk:
```json
{
  "text": "F401: Module imported but unused. Remove the import or use it.",
  "category": "unused_import",
  "source_type": "ruff",
  "source_path": "https://docs.astral.sh/ruff/rules/unused-import/",
  "chunk_id": "chunk_0066"
}
```

The corpus was built in `notebooks/data_preprocessor.ipynb`:
1. **COMMON_GUIDELINES** — 128 chunks from PEP 8/257, Ruff, Flake8, Pylint
2. **REPO_GUIDELINES** — 88 chunks from Django, Pandas, Scikit-learn, Flask guidelines
3. **Review comments** — merged from `data/raw/review_comments/review.json` (chunk_0217+)

---

## 5. Prompt Engineering

### 5.1 Models Evaluated

We tested **7 local Ollama models** across 72 prompt configurations (64 single-issue + 8 multi-issue) using `scripts/evaluate_prompts.py`:

| Model | Size | Avg Latency | Valid JSON % | Avg F1 | Notes |
|---|---|---|---|---|---|
| **phi4:14b** | 14B | 16,322ms | **100%** | **0.500** | Zero failures across all configs |
| **qwen2.5-coder:14b** | 14B | 16,981ms | **100%** | **0.500** | Code-specialized, equally reliable |
| **codellama:7b-instruct** | 7B | 7,799ms | **100%** | **0.500** | Fast, 100% valid JSON |
| **gemma4:latest** | — | 25,522ms | 80% | 0.500 | Perfect when valid, 20% failure rate |
| **deepseek-coder:6.7b** | 6.7B | 8,230ms | 100% | 0.476 | Reduced precision (95.2%) |
| **llama3.1:8b** | 8B | 4,742ms | 94.4% | 0.441 | Fastest but CoT multi-issue failures |
| **mistral:7b-instruct** | 7B | 8,772ms | 100% | 0.381 | Weakest precision (76.2%) |

**phi4:14b** was selected as the production model for this analysis — it has perfect reliability (100% valid JSON) and highest F1 across all configurations.

### 5.2 Prompt Dimensions Tested

The 72 configurations come from a Cartesian product of 4 dimensions:

**Strategy (2 variants):**
- **Minimal** — Direct instruction: Role → Code → Categories → Output format
- **Chain-of-Thought (CoT)** — Adds 6–8 step explicit reasoning chain

**Result:** Minimal wins (98% valid JSON vs 89% for CoT, higher precision).

**Detection Scope (2 variants):**
- **Single-issue** — Find one violation per call (64 configs)
- **Multi-issue** — Find all violations per call (8 configs)

**Result:** Multi-issue is more efficient but less reliable with CoT. Minimal+multi works well.

**Mode (2 variants):**
- **LLM-only** — Code analysis without retrieval context
- **RAG** — Code + retrieved coding guidelines prepended

**Result:** LLM slightly edges RAG on simple categories (F1 0.465 vs 0.458). RAG expected to help on harder categories.

**Hints (2–16 variants):**
- For single-issue: 16 combinations of `{none, exact_line} × {none, ±1, ±2, ±3} × {none, ground_truth}`
- For multi-issue: Only `no_hints` and `ground_truth` (realistic production setting)

**Result:** `no_hints` is the only realistic production prompt. Adding hints improves scores but is not available at inference time.

### 5.3 Key Findings

1. **Minimal > CoT** — Chain-of-thought reasoning added no accuracy benefit and caused JSON parsing failures (especially with llama3.1:8b multi-issue: 0% valid JSON).
2. **phi4:14b and qwen2.5-coder:14b tied at the top** — Both achieve perfect F1 (0.500) and 100% valid JSON. phi4:14b was chosen for slightly faster inference.
3. **No hints = realistic production** — The `no_hints` variant is the only one that doesn't require ground truth information at inference time.
4. **RAG adds overhead for marginal gain on simple categories** — but is critical for harder categories where the LLM needs domain knowledge.

Full analysis: `docs/prompt_evaluation.md`

---

## 6. Production Prompt Configuration

Based on prompt evaluation, the final production prompts are:

### LLM-only Baseline: `minimal_multi_llm_no_hints`

```
Role: You are a Python code reviewer...
Code: {source_code}
Categories: [unused_import, indentation, naming_convention, documentation_formatting, mutable_default]
Output: JSON array of {line_number, violation_category, review_comment}
```

### RAG Baseline: `minimal_multi_rag_no_hints`

```
Role: You are a Python code reviewer...
Guidelines: {top_10_retrieved_chunks}
Code: {source_code}
Categories: [unused_import, indentation, naming_convention, documentation_formatting, mutable_default]
Output: JSON array of {line_number, violation_category, review_comment, guideline_chunks_used}
```

The RAG prompt prepends the top-10 retrieved guideline chunks (from S15 strategy) before the code, allowing the model to reference specific rules in its review.

---

## 7. Three Baselines

### Baseline 1: Static Analysis (flake8 + pylint)

| Property | Value |
|---|---|
| Tools | flake8 (with bugbear, docstrings, pep8-naming) + pylint |
| Total predictions | 1,269 violations |
| Files with violations | 93 / 103 |
| How it works | Run both linters on each file, map error codes to 5 categories via FLAKE8_MAP/PYLINT_MAP |
| Deterministic | Yes |
| Requires LLM | No |

### Baseline 2: LLM-only (phi4:14b, no retrieval)

| Property | Value |
|---|---|
| Model | phi4:14b via Ollama |
| Prompt | `minimal_multi_llm_no_hints` |
| Total predictions | 219 violations |
| Valid JSON responses | 62 / 103 (60.2%) |
| Files with predictions | 102 / 103 |
| How it works | Send code + category list to LLM, parse JSON response |
| Deterministic | Nominally (temp=0.0), but GPU float variance exists |

### Baseline 3: RAG (phi4:14b + S15 retrieval)

| Property | Value |
|---|---|
| Model | phi4:14b via Ollama |
| Prompt | `minimal_multi_rag_no_hints` |
| Retrieval | S15, BAAI/bge-large-en-v1.5, FAISS IndexFlatIP, top-10 |
| Total predictions | 114 violations |
| Valid JSON responses | 102 / 103 (99.0%) |
| Files with predictions | 103 / 103 |
| How it works | Retrieve top-10 guideline chunks → prepend to prompt → LLM generates review |
| Deterministic | Nominally, cached results used |

Interesting: RAG produces far fewer predictions (114 vs 219 for LLM-only) — the retrieved guidelines appear to make the model more conservative, only flagging violations it can back up with evidence.

---

## 8. Classification Metrics

### Scoring Method

Two matching protocols are used (implemented in `score_all()` function, Cell 8 of pipeline.ipynb):

1. **Exact match** — prediction matches ground truth if `line_number == gt_line_number AND violation_category == gt_category`
2. **±1 Relaxed match** — `abs(pred_line - gt_line) ≤ 1 AND violation_category == gt_category`

Metrics computed:
- **Per-category**: TP, FP, FN → Precision, Recall, F1
- **Macro F1**: Average F1 across all 5 categories (preferred — treats each category equally despite class imbalance)
- **Micro F1**: Global TP/FP/FN aggregation → Precision, Recall, F1

### Aggregate Results

| Baseline | Match | Macro F1 | Micro Precision | Micro Recall | Micro F1 |
|---|---|---|---|---|---|
| **Static** | Exact | **0.578** | 42.6% | **75.0%** | 54.3% |
| **Static** | ±1 Relaxed | **0.578** | 42.6% | 75.0% | 54.3% |
| **LLM** | Exact | 0.206 | **57.5%** | 17.5% | 26.8% |
| **LLM** | ±1 Relaxed | 0.225 | 57.5% | 17.5% | 26.8% |
| **RAG** | Exact | 0.108 | 55.1% | 8.6% | 14.9% |
| **RAG** | ±1 Relaxed | 0.122 | 55.1% | 8.6% | 14.9% |

**Key observations:**
- Static has the highest recall (75%) because linters produce many violations — they catch most issues but also flag many false positives
- LLM and RAG have higher precision (57.5%, 55.1%) but very low recall (17.5%, 8.6%) — they're accurate when they flag something, but miss most violations
- ±1 relaxed only slightly helps LLM (0.206 → 0.225) and RAG (0.108 → 0.122), meaning most errors are off by more than 1 line or wrong category entirely
- Static scores are identical for exact and relaxed because linter line numbers are always precise

---

## 9. Per-Category F1 Scores

### Exact Match F1

| Category | Static | LLM | RAG |
|---|---|---|---|
| `unused_import` | **0.90** | 0.56 | 0.38 |
| `indentation` | **0.39** | 0.00 | 0.00 |
| `naming_convention` | **0.64** | 0.13 | 0.04 |
| `documentation_formatting` | **0.18** | 0.00 | 0.00 |
| `mutable_default` | **0.78** | 0.33 | 0.13 |

**Analysis:**

- **unused_import** — Best category for all baselines. Static achieves F1=0.90 because flake8's F401 is near-perfect for this. LLM (0.56) and RAG (0.38) can identify unused imports but sometimes get the line number wrong.
- **indentation** — LLM and RAG score **0.00**. The models simply cannot detect whitespace issues from code text. Static catches these via pycodestyle rules (E1xx) but only reaches F1=0.39 because many indentation violations in the ground truth are subtle.
- **naming_convention** — Static dominates (0.64) using pep8-naming rules (N8xx). LLM can sometimes spot obvious camelCase (0.13), RAG barely detects any (0.04).
- **documentation_formatting** — Both LLM and RAG score **0.00**. Docstring formatting violations require understanding expected docstring structure, which neither model handles well. Static reaches only 0.18 because many doc violations are subjective.
- **mutable_default** — Static excels (0.78) via flake8-bugbear B006. LLM can spot obvious `def f(x=[])` patterns (0.33), RAG less so (0.13).

---

## 10. Retrieval Quality

Evaluated using the RAG baseline's retrieval system (BAAI/bge-large-en-v1.5 + FAISS IndexFlatIP, S15 strategy).

### Metrics at Different K Values

| K | Recall@K | Precision@K | MRR |
|---|---|---|---|
| 1 | 0.60 | **0.94** | 0.94 |
| 3 | 0.76 | 0.89 | 0.95 |
| 5 | 0.86 | 0.81 | 0.96 |
| 10 | **0.97** | 0.59 | 0.96 |

**Definitions:**
- **Recall@K** — Fraction of ground-truth categories with ≥1 matching chunk in top-K results
- **Precision@K** — Fraction of top-K chunks whose category matches a ground-truth category
- **MRR** — Mean Reciprocal Rank: average of 1/rank for the first relevant chunk

**Analysis:**

The retrieval system itself is strong:
- At K=10 (our production setting), we achieve **97% recall** — almost every relevant guideline category is represented
- **MRR = 0.96** means the first relevant chunk appears at rank 1 in 96% of queries
- The precision–recall tradeoff is expected: at K=1 precision is 94% but recall is only 60%; at K=10 recall hits 97% but precision drops to 59%

This confirms the retrieval pipeline is **not the bottleneck** — the issue is the LLM's ability to use the retrieved chunks effectively for line-level prediction.

---

## 11. Hallucination Analysis

A prediction is counted as **hallucinated** if no ground-truth violation exists within ±1 line with the same category.

| Baseline | Hallucinated | Total Predictions | Hallucination Rate |
|---|---|---|---|
| **Static** | 662 | 1,269 | **52.2%** |
| **LLM** | 81 | 219 | **37.0%** |
| **RAG** | 45 | 114 | **39.5%** |

**Analysis:**

- **Static has the highest hallucination rate (52.2%)** — this is because linters flag everything that matches their rules, regardless of whether it's actually a violation in context. Over half of static predictions don't match any ground-truth review.
- **LLM has the lowest hallucination rate (37.0%)** — when the model makes a prediction, it's more likely to be correct. But it makes far fewer predictions overall.
- **RAG is slightly worse than LLM (39.5% vs 37.0%)** — surprising, since retrieved guidelines should help. This may be because RAG sometimes flags violations based on retrieved rules that don't actually apply to the specific code.

---

## 12. Grounding Analysis

A prediction is **grounded** if it's backed by evidence — either a linter rule (Static) or a retrieved guideline chunk (RAG).

| Baseline | Grounding Rate | Grounded / Total | Explanation |
|---|---|---|---|
| **Static** | **100.0%** | 1,269 / 1,269 | Every prediction comes from a linter rule (F401, E111, etc.) |
| **LLM** | **0.0%** | 0 / 219 | No retrieval context — predictions are based purely on model knowledge |
| **RAG** | **100.0%** | 114 / 114 | Every prediction's category matches at least one retrieved chunk |

**Analysis:**

- Static is fully grounded by design — every violation maps to a specific error code
- LLM has **zero grounding** because there's no external evidence system. The model generates reviews from training data alone
- RAG achieves **100% grounding** — the S15 strategy ensures relevant chunks are always retrieved, and the model's predictions align with retrieved categories. However "grounded" doesn't mean "correct" — a prediction can be grounded (backed by a real guideline) but still hallucinated (wrong line or wrong applicability)

---

## 13. Latency Comparison

Measured per-file inference time across all 103 evaluation files.

| Baseline | Mean Latency | P95 Latency | Notes |
|---|---|---|---|
| **Static** | **679 ms** | 679 ms | flake8 + pylint per file |
| **LLM** | 11,783 ms | 27,328 ms | phi4:14b inference only |
| **RAG** | 15,611 ms | 19,475 ms | Retrieval (~4s) + phi4:14b inference |

**Analysis:**

- Static is **~17× faster** than LLM and **~23× faster** than RAG on average
- LLM has the highest P95 (27.3s) — some files cause extremely long generation times, likely due to complex or long code
- RAG's mean is ~4s higher than LLM (retrieval overhead), but its P95 (19.5s) is actually lower — the retrieved guidelines may help the model generate responses more efficiently for complex files
- For a production system, static analysis is the only baseline that could run in real-time PRs. LLM/RAG baselines would need async processing

---

## 14. Limitations and How We Addressed Them

### 14.1 Static Analysis Limitations

| Limitation | Evidence | Mitigation |
|---|---|---|
| **Over-detection** (high false positive rate) | 52.2% hallucination rate, 1269 predictions for 721 GT reviews | Accepted as inherent to rule-based tools; provides high recall as a tradeoff |
| **No semantic understanding** | Can't tell if an import is used via `__all__` or dynamic lookup | N/A — fundamental limitation of AST-based tools |
| **Rigid rules** | Can't detect subtle naming issues (e.g., slightly misleading names) | Complemented with LLM baselines |
| **Category mapping is manual** | FLAKE8_MAP/PYLINT_MAP are hand-crafted | Validated against PEP 8 and tool documentation |

### 14.2 LLM-only Limitations

| Limitation | Evidence | Mitigation |
|---|---|---|
| **JSON parse failures** | Only 62/103 valid JSON (60.2% success rate) | Used `minimal` template (dropped CoT), `multi-issue` format, max 4 retries |
| **Zero F1 on indentation and documentation** | F1 = 0.00 for both categories | These categories require structural code understanding that text-based LLMs lack |
| **No grounding** | 0% grounding rate | This is by design — LLM-only has no external evidence. Addressed by the RAG baseline |
| **High latency variance** | P95 = 27,328ms (some files take 27s) | Caching via SHA256 hash ensures repeated runs are instant |
| **Non-deterministic outputs** | GPU floating-point variance at temp=0.0 | All results cached in `data/llm_cache/` for reproducibility |

### 14.3 RAG Limitations

| Limitation | Evidence | Mitigation |
|---|---|---|
| **Lowest recall** (8.6%) | Only 114 predictions total — very conservative | Model becomes too cautious with guidelines; could tune prompt to encourage more predictions |
| **Same category gaps as LLM** | 0.00 F1 on indentation and documentation | Retrieval can surface relevant chunks (Recall@10=0.97) but model can't use them for line-level detection |
| **Retrieval adds latency** | +~4s per file (15.6s vs 11.8s mean) | S15 strategy is already optimized from 16 tested strategies |
| **Higher hallucination than LLM** | 39.5% vs 37.0% | Retrieved chunks sometimes include rules that don't apply to the specific code, misleading the model |

### 14.4 General Limitations

| Limitation | Evidence | Mitigation |
|---|---|---|
| **Small evaluation dataset** | 103 files, 721 violations — limited statistical significance | Best available with synthetic + manual data generation |
| **Single model** | Only phi4:14b used for production analysis | Full prompt evaluation tested 7 models; phi4:14b was the top performer |
| **Single-file only** | No cross-file context (e.g., imports used in other modules) | Scope constraint from problem statement; standard for PR review tools |
| **Five categories only** | Ignores security, performance, architecture issues | Intentional focus on style violations per problem statement |
| **Synthetic ground truth** | Many GT reviews were LLM-generated | Supplemented with 6 manual files; cross-validated during dataset creation |

### 14.5 Experiment History — Failed Approaches

From `docs/experiment_log.md`, several approaches were tried and abandoned:

1. **Dense-only retrieval (early approach)** — PEP 8 chunks dominated regardless of repo type; framework-specific guidelines never surfaced. Fixed by adding repo-aware chunking and S15 adaptive strategy.

2. **Semantic-only indentation matching** — Pure text embeddings miss structural whitespace properties. Accepted as fundamental limitation.

3. **TinyLlama (1.1B)** — RAG significantly underperformed LLM-only (macro F1 0.215 vs 0.240). Root causes: category label leakage in evidence formatting, context overflow at ~1400 tokens, no confidence gating. Fixed by using phi4:14b (14B) with larger context window.

4. **Chain-of-Thought prompts** — All top-15 configs use `minimal` template. CoT added JSON parsing failures, especially on smaller models. Dropped entirely.

5. **Mutable default detection (early)** — F1 was 0.00 until heuristic `detect_mutable_default()` regex was added to `retrieve.py`. After fix: F1 jumped to 0.59–0.64.

---

## 15. Scripts Reference

### `scripts/llm_inference.py` — LLM Inference with Caching

**Purpose:** Run inference via local Ollama models with JSON validation and SHA256 caching.

| Function | What it does |
|---|---|
| `infer_ollama()` | Call Ollama HTTP API, return JSON string |
| `infer_one()` | Single inference with full metadata tracking |
| `run_inference()` | Batch inference across models with retries |
| `_cache_key()` | SHA256 hash of (prompt, code, model, temperature) |
| `_is_valid_json_response()` | Validates JSON structure before caching |

```bash
python scripts/llm_inference.py --prompt "Review this code" --code-file example.py --model phi4:14b
```

### `scripts/retrieve.py` — FAISS Retrieval (S15 Strategy)

**Purpose:** Retrieve relevant coding guideline chunks from FAISS index.

| Function | What it does |
|---|---|
| `retrieve(query, top_k)` | Basic FAISS similarity search |
| `retrieve_with_context(code, top_k)` | S15 production strategy with adaptive budget |
| `predict_categories(code)` | Heuristic regex-based category prediction |

```bash
# Basic query
python scripts/retrieve.py query "unused import" -k 10 --json

# S15 strategy (production)
python scripts/retrieve.py code example.py -k 10 --json
```

### `scripts/evaluate_static_analysis.py` — Static Analysis Baseline

**Purpose:** Run flake8 + pylint, map violations to 5 categories, compare vs ground truth.

| Command | What it does |
|---|---|
| `cmd_scan()` | Run linters on evaluation files |
| `cmd_compare()` | Match violations vs ground truth (exact, category, semantic) |
| `cmd_sweep()` | Find optimal similarity threshold for doc-formatting |
| `cmd_inspect()` | Examine unique text patterns |

```bash
python scripts/evaluate_static_analysis.py scan
python scripts/evaluate_static_analysis.py compare
```

### `scripts/evaluate_prompts.py` — Prompt Configuration Evaluation

**Purpose:** Systematically evaluate prompt templates × hint combinations × models.

Evaluates 72 configurations across 7 models. Produces leaderboard sorted by F1.

```bash
# Full evaluation (all models, all configs)
python scripts/evaluate_prompts.py

# Single model
python scripts/evaluate_prompts.py --models phi4:14b

# Specific config
python scripts/evaluate_prompts.py --models phi4:14b --detection multi --strategy minimal --mode llm
```

### `scripts/create_synthetic_repos.py` — Synthetic Repository Generation

**Purpose:** Create GitHub repos with intentional code violations for evaluation.

Generates 20 clean Python files per framework, then creates PRs with injected violations:
- **Injection methods:** LLM-based code modification + regex fallback
- **Violation types:** unused_import, indentation, naming_convention, documentation_formatting, mutable_default

```bash
python scripts/create_synthetic_repos.py \
  --repo-token $GITHUB_REPO \
  --llm-token $GITHUB_LLM_TOKEN \
  --repos flask fastapi pandas sklearn django \
  --num-prs 20 \
  --guidelines-dir data/raw/guidelines_raw
```

### `scripts/create_evaluation_dataset.py` — Evaluation Dataset Builder

**Purpose:** Create `evaluation.json` from source files and collected review comments.

```bash
python scripts/create_evaluation_dataset.py \
  --repo-token $GITHUB_REPO \
  --llm-token $GITHUB_LLM_TOKEN \
  --repos flask fastapi pandas sklearn django \
  --num-prs 20 \
  --output data/processed/evaluation.json
```

### `scripts/fetch_review_comments.py` — Review Comment Collector

**Purpose:** Fetch PR review comments from synthetic repos, deduplicate, format as corpus chunks.

```bash
python scripts/fetch_review_comments.py \
  --repos flask fastapi pandas sklearn django \
  --start-chunk 217 \
  --output data/raw/review_comments/review.json
```

---

## 16. How to Reproduce

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.ai/) installed with `phi4:14b` model pulled
- GitHub token (for synthetic repo creation only — not needed if using cached data)

### Step 1: Install Dependencies

```bash
cd Group-1-DS-and-AI-Lab-Project
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Pull the LLM Model

```bash
ollama pull phi4:14b
```

### Step 3: Set Up Environment

Create a `.env` file (not committed):
```
GITHUB_REPO=<github_token>
GITHUB_LLM_TOKEN=<github_token>
```

### Step 4: Run Data Preprocessing (Optional)

The retrieval corpus and evaluation dataset are already in `data/processed/`. To regenerate from scratch:

```bash
# Open and run all cells in:
notebooks/data_preprocessor.ipynb
```

This will:
1. Build retrieval corpus from COMMON_GUIDELINES + REPO_GUIDELINES
2. Create synthetic repos with violations (requires GitHub token)
3. Fetch review comments
4. Merge into final corpus
5. Build evaluation dataset

### Step 5: Run the Pipeline

```bash
# Open and run all cells (1-12) in:
notebooks/pipeline.ipynb
```

Cell-by-cell:
- **Cells 1–2:** Imports, data loading (103 entries, 721 GT reviews)
- **Cell 3:** LLM-only baseline (Baseline 2)
- **Cell 4:** RAG baseline (Baseline 3)
- **Cells 5–6:** Aggregate comparison and per-PR delta
- **Cell 7:** Static baseline loading (Baseline 1) + re-extract all predictions
- **Cell 8:** Enhanced scoring with exact and ±1 relaxed matching
- **Cell 9:** Retrieval quality metrics (Recall@K, Precision@K, MRR)
- **Cell 10:** Grounding and hallucination analysis
- **Cell 11:** Latency analysis (re-runs flake8+pylint for timing)
- **Cell 12:** All visualizations (7 plots)

### Using Cached Results

All LLM inference results are cached in `data/llm_cache/`. If you have the cache files, the pipeline will skip actual LLM calls and use cached responses, making the notebook run much faster. The cache uses SHA256 hashes, so identical queries always return the same result.

---

## 17. Notebooks

### `notebooks/data_preprocessor.ipynb`

**Purpose:** End-to-end data pipeline — from raw guidelines to evaluation-ready dataset.

| Section | What it does |
|---|---|
| Retrieval Corpus | Defines 128 COMMON_GUIDELINES + 88 REPO_GUIDELINES, saves to `retrival_corpus.json` |
| Corpus Visualization | Bar charts of chunks per source type and category |
| Synthetic Repos | Calls `create_synthetic_repos.py` to generate violation PRs |
| Review Comments | Calls `fetch_review_comments.py` to collect PR reviews |
| Corpus Merge | Merges review comments into retrieval corpus (no duplicates) |
| Merged Analysis | Visualizes final corpus distribution |
| Evaluation Dataset | Calls `create_evaluation_dataset.py` + merges manual entries |
| Dataset Analysis | Visualizes evaluation entries per repo and per category |

### `notebooks/pipeline.ipynb`

**Purpose:** Full evaluation pipeline — inference, scoring, retrieval quality, hallucination, grounding, latency, visualizations.

| Cell | Content |
|---|---|
| 1 | Markdown: experiment setup description |
| 2 | Imports, data loading (103 entries, 721 GT reviews) |
| 3 | Baseline 2: LLM-only inference → `llm_results` |
| 4 | Baseline 3: RAG inference → `rag_results` |
| 5 | Aggregate comparison table |
| 6 | Per-PR delta table (LLM vs RAG) |
| 7 | Static baseline + re-extract all predictions from cache |
| 8 | `score_all()` — exact + ±1 relaxed matching, per-category P/R/F1, macro/micro F1 |
| 9 | Retrieval metrics: Recall@K, Precision@K, MRR at K=1,3,5,10 |
| 10 | Hallucination rate + grounding rate for all 3 baselines |
| 11 | Latency analysis: re-runs static tools for timing, extracts LLM/RAG times from cache |
| 12 | 7 visualization plots |

---

## 18. Visualizations

The pipeline generates 7 plots (Cell 12 of pipeline.ipynb), saved to `data/processed/`:

1. **Macro F1 Score Comparison** — Grouped bar chart: Static (0.578) vs LLM (0.206/0.225) vs RAG (0.108/0.122) for exact and ±1 relaxed matching.

2. **Per-Category F1 Score** — Grouped bar chart showing F1 for all 5 categories across 3 baselines. Highlights that indentation and documentation_formatting are 0.00 for LLM/RAG.

3. **Retrieval Quality Metrics** — Grouped bar chart: Recall@K, Precision@K, MRR at K=1,3,5,10. Shows retrieval system performs well (Recall@10=0.97).

4. **Hallucination Rate Comparison** — Bar chart with percentage labels and raw counts: Static 52.2% (662/1269), LLM 37.0% (81/219), RAG 39.5% (45/114).

5. **Grounding Rate Comparison** — Bar chart: Static 100% (rule-based), LLM 0% (no retrieval), RAG 100% (category matches chunk). Annotated with explanations.

6. **Latency Comparison** — Grouped bar (mean vs P95): Static 679ms, LLM 11,783/27,328ms, RAG 15,611/19,475ms.

7. **Precision vs Recall Scatter** — Each point = one baseline across all 103 files. Shows Static's high-recall/low-precision trade-off vs LLM/RAG's low-recall/higher-precision positioning.

---

## Summary of Key Results

| Metric | Static | LLM | RAG |
|---|---|---|---|
| Macro F1 (exact) | **0.578** | 0.206 | 0.108 |
| Macro F1 (±1 relaxed) | **0.578** | 0.225 | 0.122 |
| Micro Precision | 42.6% | **57.5%** | 55.1% |
| Micro Recall | **75.0%** | 17.5% | 8.6% |
| Hallucination Rate | 52.2% | **37.0%** | 39.5% |
| Grounding Rate | **100%** | 0% | **100%** |
| Mean Latency | **679ms** | 11,783ms | 15,611ms |
| Total Predictions | 1,269 | 219 | 114 |

**Bottom line:** Static analysis tools still outperform local LLMs for rule-based Python code review. The retrieval system works well (97% recall at K=10), but the LLM struggles to translate retrieved guidelines into accurate line-level predictions. LLM and RAG baselines show higher precision but dramatically lower recall. The main gaps are in indentation and documentation formatting, where both LLM and RAG score 0.00 F1.
