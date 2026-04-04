# Prompt Engineering & Model Evaluation

> **Evaluation**: 1 PR (synthetic-django_PR_21), 3 ground-truth violations (all `unused_import` on lines 9, 10, 11).
> **Models tested**: 7 local Ollama models (see §2).
> **Prompt configurations**: 72 (64 single-issue + 8 multi-issue).
> **Metrics**: Exact match (line + category), Category-F1 (precision / recall / F1), valid-JSON rate.
> **Script**: `scripts/evaluate_prompts.py` — reproduces all results.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Models Evaluated](#2-models-evaluated)
3. [Prompt Design Space](#3-prompt-design-space)
4. [Evaluation Metrics](#4-evaluation-metrics)
5. [Per-Model Results](#5-per-model-results)
6. [Strategy Comparison — Minimal vs CoT](#6-strategy-comparison--minimal-vs-cot)
7. [Mode Comparison — LLM vs RAG](#7-mode-comparison--llm-vs-rag)
8. [Detection Type — Single vs Multi](#8-detection-type--single-vs-multi)
9. [Hint Effectiveness](#9-hint-effectiveness)
10. [Best Config Per Model](#10-best-config-per-model)
11. [What Worked](#11-what-worked)
12. [What Failed](#12-what-failed)
13. [Final Selection — Top 2 Models](#13-final-selection--top-2-models)
14. [Final Selection — Top 3 Prompts](#14-final-selection--top-3-prompts)
15. [Reproducing Results](#15-reproducing-results)

---

## 1. Problem Statement

Given a Python source file, the LLM must detect code-review violations and return structured JSON with `line_number`, `violation_category`, and `review_comment`.

We vary four axes:
- **Strategy**: Minimal (direct instruction) vs Chain-of-Thought (step-by-step reasoning)
- **Detection scope**: Single-issue (find one violation) vs Multi-issue (find all violations)
- **Mode**: LLM-only vs RAG (retrieved coding guidelines prepended)
- **Hint level**: 16 hint combinations for single-issue, 2 for multi-issue

Multi-issue detection deliberately receives **no line-number hints** (only `no_hints` and `ground_truth`), because in production the system doesn't know where violations are.

### Configuration Count

| Detection | Hint Combos | × Strategies | × Modes | Configs |
|-----------|-------------|--------------|---------|---------|
| Single    | 16          | 2            | 2       | **64**  |
| Multi     | 2           | 2            | 2       | **8**   |
| **Total** |             |              |         | **72**  |

---

## 2. Models Evaluated

All models run locally via Ollama at `localhost:11434`, temperature=0.0, max_tokens=1024.

| Model | Size | Avg Latency | Notes |
|-------|------|-------------|-------|
| qwen2.5-coder:14b | 14B | 16,981ms | Code-specialised |
| phi4:14b | 14B | 16,322ms | Microsoft general-purpose |
| gemma4:latest | — | 25,522ms | Google latest-gen |
| llama3.1:8b | 8B | 4,742ms | Meta general-purpose, fastest |
| deepseek-coder:6.7b | 6.7B | 8,230ms | Code-specialised |
| codellama:7b-instruct | 7B | 7,799ms | Meta code-instruct |
| mistral:7b-instruct | 7B | 8,772ms | Mistral instruction-tuned |

---

## 3. Prompt Design Space

### 3.1 Strategies

**Minimal** — Role → Code → [hints] → Categories → Output format. No reasoning steps.

**Chain-of-Thought (CoT)** — Role → Step-by-step reasoning instructions → Code → [hints] → Categories → Output format. The LLM is guided through 6-8 explicit reasoning steps before producing JSON.

### 3.2 Output Formats

Single-issue expects a JSON object:
```json
{"line_number": 9, "violation_category": "unused_import", "review_comment": "..."}
```

Multi-issue expects a JSON array:
```json
[{"line_number": 9, "violation_category": "unused_import", "review_comment": "..."}, ...]
```

RAG variants add a `"guideline_chunks_used"` field.

### 3.3 Hint Combinations

| Hint | Description |
|------|-------------|
| `exact_line` | Exact line number of the violation |
| `line_range_±N` | Line range ±1, ±2, or ±3 around the actual line |
| `ground_truth` | The ground-truth review comment verbatim |

For single-issue: all 16 combos of `{none, exact_line} × {none, ±1, ±2, ±3} × {none, ground_truth}`.

For multi-issue: only `no_hints` and `ground_truth` (no line hints — realistic production setting).

### 3.4 RAG Mode

In RAG mode, the prompt includes retrieved coding guidelines from the FAISS corpus (S15 production strategy: `retrieve_with_context(code)`, top-k=10 chunks, BAAI/bge-large-en-v1.5 embeddings).

---

## 4. Evaluation Metrics

| Metric | Definition |
|--------|-----------|
| **Exact Match** | Does the predicted `(line_number, violation_category)` pair exactly match any ground-truth pair? Binary 0/1 per response |
| **Category Precision** | `true_positive_categories / predicted_categories` — what fraction of predicted categories are correct? |
| **Category Recall** | `true_positive_categories / ground_truth_count` — what fraction of GT violations are covered? |
| **Category F1** | Harmonic mean of precision and recall |
| **Valid JSON %** | Fraction of responses that parse as valid JSON (critical for pipeline reliability) |

**Note**: Single-issue detection can only find 1 of 3 GT violations, so recall is capped at 33.3% and F1 at 0.500.

---

## 5. Per-Model Results

197 total inference calls (72 configs × llama3.1 + 21 configs each × 6 other models).

| Model | Calls | Valid JSON | Avg F1 | Avg Precision | Avg Recall | Avg Latency |
|-------|-------|-----------|--------|---------------|------------|-------------|
| **phi4:14b** | 21 | **100%** | **0.500** | 100% | 33.3% | 16,322ms |
| **qwen2.5-coder:14b** | 21 | **100%** | **0.500** | 100% | 33.3% | 16,981ms |
| codellama:7b-instruct | 21 | **100%** | **0.500** | 100% | 33.3% | 7,799ms |
| gemma4:latest | 20 | 80% | **0.500** | 100% | 33.3% | 25,522ms |
| deepseek-coder:6.7b | 21 | 100% | 0.476 | 95.2% | 31.7% | 8,230ms |
| llama3.1:8b | 72 | 94.4% | 0.441 | 88.2% | 29.4% | 4,742ms |
| mistral:7b-instruct | 21 | 100% | 0.381 | 76.2% | 25.4% | 8,772ms |

### Key Observations

- **phi4 and qwen2.5-coder** achieve perfect scores (F1=0.500, 100% valid JSON) across every config tested — zero failures.
- **codellama** also achieves perfect valid-JSON rate and F1, with the fastest latency among reliable models.
- **gemma4** has perfect F1 when it produces valid JSON, but fails on 20% of responses.
- **mistral** is the weakest: only 76.2% precision (predicts wrong categories 24% of the time).
- **llama3.1** is the fastest (4.7s avg) but has lower valid-JSON rate (94.4%) due to CoT multi-issue failures.

---

## 6. Strategy Comparison — Minimal vs CoT

| Strategy | Runs | Valid JSON | Avg F1 | Precision | Recall |
|----------|------|-----------|--------|-----------|--------|
| **Minimal** | 161 | **98%** | **0.471** | **94.3%** | **31.4%** |
| CoT | 36 | 89% | 0.422 | 84.4% | 28.1% |

### Why Minimal Wins

1. **Higher valid-JSON rate** (98% vs 89%): CoT prompts encourage reasoning text, and some models emit their step-by-step analysis instead of (or alongside) the JSON, breaking parsability.
2. **Higher precision**: Without intermediate reasoning, models are less likely to hallucinate extra violations or misclassify categories.
3. **Simpler prompts = more predictable behavior** across model families.

### Where CoT Fails

- CoT multi-issue (all 4 configs) produced **0% valid JSON** on llama3.1:8b — the model outputs full reasoning text and never produces the requested JSON array.
- CoT single-issue with `no_hints`, `exact_line`, `line_range_±2`, `line_range_±3` on llama3.1 had F1=0.000.

---

## 7. Mode Comparison — LLM vs RAG

| Mode | Runs | Valid JSON | Avg F1 | Precision | Recall |
|------|------|-----------|--------|-----------|--------|
| **LLM** | 132 | **98%** | **0.465** | **93.1%** | **31.0%** |
| RAG | 65 | 91% | 0.458 | 91.5% | 30.5% |

### Why LLM Slightly Edges Out RAG

1. **Shorter prompts** = less opportunity for the model to get confused or lose format compliance.
2. The test entry's violations (`unused_import`) are straightforward — models detect them from code alone without needing guidelines.
3. RAG's longer prompts lower the valid-JSON rate from 98% to 91% — some models struggle with the additional context.

### When RAG May Help

RAG is expected to differentiate on harder categories like `documentation_formatting` and `naming_convention` where coding guidelines provide specific rules the LLM might not know. This test entry (all `unused_import`) doesn't exercise that advantage.

---

## 8. Detection Type — Single vs Multi

| Type | Runs | Valid JSON | Avg F1 | Avg Exact Match |
|------|------|-----------|--------|-----------------|
| Multi (valid only) | 8 | 50% | **0.500** | **1.00** |
| Single | 189 | **98%** | 0.462 | 0.83 |

### Trade-offs

- **Multi-issue detection** achieves higher F1 when it works (can find multiple violations per file), but has a catastrophic 50% valid-JSON failure rate — all from CoT multi configs.
- **Single-issue** is far more reliable (98% valid JSON) but recall-capped at 33.3%.
- **Practical recommendation**: Use single-issue for reliability; use multi-issue only with minimal strategy.

---

## 9. Hint Effectiveness

Ranked by average F1 across all models that used each hint type:

| Rank | Hint Combination | F1 | Exact Match | Precision | Valid % |
|------|------------------|----|-------------|-----------|---------|
| 1 | exact_line+ground_truth | **0.500** | 1.00 | 100% | 100% |
| 2 | exact_line+line_range+ground_truth (all ±N) | **0.500** | 1.00 | 100% | 100% |
| 3 | ground_truth (alone) | **0.500** | 1.00 | 100% | 86% |
| 4 | line_range+ground_truth (all ±N) | **0.500** | 0.80–1.00 | 100% | 100% |
| 5 | line_range_±1 | 0.467 | 0.60 | 93.3% | 94% |
| 6 | exact_line+line_range (±1/±3) | 0.450 | 0.90 | 90.0% | 100% |
| 7 | line_range_±2 | 0.433 | 0.60 | 86.7% | 94% |
| 8 | **no_hints** | **0.412** | 0.82 | 82.4% | 85% |
| 9 | exact_line (alone) | 0.400 | 0.80 | 80.0% | 94% |
| 10 | line_range_±3 (alone) | 0.400 | 0.47 | 80.0% | 100% |

### Key Findings

1. **Any hint with `ground_truth` guarantees F1=0.500** — unsurprising since the review comment essentially gives away the answer.
2. **`no_hints` outperforms `exact_line` alone** (F1 0.412 vs 0.400) — giving just a line number without context can actually confuse some models.
3. **`line_range_±1` is the best non-cheating hint** (F1=0.467) — a narrow range focuses the model without over-constraining it.
4. **Wider ranges (±3) are worse** than narrower ones — too much search space dilutes the signal.

---

## 10. Best Config Per Model

| Model | Best Config | F1 | Top 3 |
|-------|------------|-----|-------|
| **phi4:14b** | All configs tied at 0.500 | 0.500 | (no variation — every config perfect) |
| **qwen2.5-coder:14b** | All configs tied at 0.500 | 0.500 | (no variation — every config perfect) |
| **codellama:7b-instruct** | `minimal_single_llm_exact_line+line_range_±2` | 0.500 | All tied at F1=0.500 |
| **gemma4:latest** | `minimal_single_llm_*` (16 valid out of 20) | 0.500 | All valid ones scored 0.500 |
| **deepseek-coder:6.7b** | `minimal_single_llm_exact_line+ground_truth` | 0.500 | `exact_line+lr_±2` (0.500), `exact_line` (0.500) |
| **llama3.1:8b** | `minimal_multi_llm_ground_truth` | 0.500 | `minimal_single_rag_*+ground_truth`, `cot_single_rag_no_hints` |
| **mistral:7b-instruct** | `minimal_single_llm_no_hints` | 0.500 | `llm_exact_line+lr_±2` (0.500), `llm_exact_line+lr_±1` (0.500) |

---

## 11. What Worked

### 1. Minimal strategy + LLM mode
The simplest prompts produce the most reliable results. Direct instruction without reasoning steps yields higher valid-JSON rates and equal or better accuracy.

### 2. phi4 and qwen2.5-coder — zero-failure models
Both 14B models achieved **100% valid JSON** and **100% correct category** across every single prompt configuration tested. They are robust to prompt variation.

### 3. Hint combinations with `ground_truth`
Providing the actual review comment as a hint guarantees correct output — useful for validating the pipeline works end-to-end before removing hints.

### 4. `line_range_±1` as practical hint
Among non-cheating hints, a tight line range (±1) gives the best boost without providing the exact answer.

### 5. SHA256 caching
The caching system (`data/llm_cache/<sha256>.json`) makes re-evaluation instant (197 cached results = 0ms per call on re-run).

---

## 12. What Failed

### 1. CoT multi-issue prompts — catastrophic JSON failure
All 4 CoT multi-issue configs (both LLM and RAG modes) produced **0% valid JSON** on llama3.1:8b. The model follows the CoT steps and outputs reasoning text instead of pure JSON. This is a fundamental failure mode of step-by-step prompting when requesting structured output from smaller models.

### 2. gemma4 — 20% invalid JSON
Despite perfect accuracy when it does produce JSON, gemma4 fails to generate valid JSON on 4 of 20 calls. These failures appear in RAG configs where the longer prompt causes the model to emit commentary.

### 3. mistral — worst precision (76.2%)
Mistral frequently predicts the wrong violation category, especially `naming_convention` instead of `unused_import`. It also fails entirely on RAG `no_hints` configs (F1=0.000).

### 4. deepseek-coder with `no_hints` — F1=0.000
Without any hints, deepseek-coder predicts the wrong category on this eval entry. It needs at least `exact_line` or `ground_truth` to succeed.

### 5. RAG's longer prompts reduce JSON compliance
RAG mode drops valid-JSON rate from 98% (LLM) to 91%, with no compensating accuracy gain on this `unused_import`-only eval entry.

### 6. `exact_line` alone is counterproductive
Giving just the line number (without ground_truth or line_range context) performs worse than `no_hints` (F1 0.400 vs 0.412). The line hint may cause models to fixate on what's at that line rather than analyzing the code correctly.

---

## 13. Final Selection — Top 2 Models

### Primary: **qwen2.5-coder:14b**

| Metric | Value |
|--------|-------|
| Valid JSON | 100% (21/21) |
| Category F1 | 0.500 (perfect for single-issue) |
| Precision | 100% |
| Robustness | Zero failures across all configs |
| Latency | ~17s per call |

**Why**: Code-specialised 14B model. Perfect reliable output, handles every prompt variant without failure. Best choice when accuracy matters.

### Secondary: **phi4:14b**

| Metric | Value |
|--------|-------|
| Valid JSON | 100% (21/21) |
| Category F1 | 0.500 (perfect for single-issue) |
| Precision | 100% |
| Robustness | Zero failures across all configs |
| Latency | ~16s per call |

**Why**: Microsoft's general-purpose model matches qwen2.5-coder on every metric and is marginally faster. Good fallback if the primary model is unavailable.

### Why not others?

- **codellama** (7B) is perfect on F1 but hasn't been tested on as many configs; latency is lower (7.8s) — worth considering as a fast backup.
- **gemma4**: Perfect when valid, but 20% invalid-JSON rate makes it unreliable for automated pipelines.
- **llama3.1**: Fastest (4.7s) but drops on CoT configs; acceptable for minimal-only usage.
- **deepseek-coder**: Fails without hints.
- **mistral**: Lowest precision — too many category misclassifications.

---

## 14. Final Selection — Top 3 Prompts

### 1. `minimal_single_llm_no_hints` (Production Default)

```
Role: Expert Python code reviewer
Task: Analyse code for violations
Hints: None
Output: Single JSON object
```

| Metric | Value |
|--------|-------|
| F1 (phi4/qwen) | 0.500 |
| F1 (averaged) | 0.429 |
| Valid JSON | 100% (top models) |
| Practical | Yes — no GT required |

**Why chosen**: Requires zero ground-truth information. This is the only realistic production prompt — it receives only the code file and must detect violations independently.

### 2. `minimal_single_rag_no_hints` (Production with RAG)

```
Role: Expert Python code reviewer
Context: Retrieved coding guidelines (10 chunks from FAISS)
Task: Analyse code for violations
Hints: None
Output: Single JSON object with guideline_chunks_used
```

| Metric | Value |
|--------|-------|
| F1 (top models) | 0.500 |
| F1 (averaged) | 0.417 |
| Valid JSON | 86% (RAG penalty) |
| Practical | Yes — uses retrieval pipeline |

**Why chosen**: Adds retrieved guidelines for harder categories (doc_formatting, naming_convention). Expected to outperform LLM-only on diverse eval entries.

### 3. `minimal_multi_llm_no_hints` (Multi-Issue Exploration)

```
Role: Expert Python code reviewer
Task: Analyse code for ALL violations
Hints: None
Output: JSON array
```

| Metric | Value |
|--------|-------|
| F1 | 0.500 |
| Valid JSON | 100% (minimal strategy) |
| Practical | Yes — finds multiple violations per file |

**Why chosen**: Only the minimal variant of multi-issue produces reliable JSON. Captures all violations in one call instead of needing multiple single-issue passes.

### Why These Three

| Requirement | Prompt 1 | Prompt 2 | Prompt 3 |
|-------------|----------|----------|----------|
| No ground-truth needed | ✓ | ✓ | ✓ |
| No line hints needed | ✓ | ✓ | ✓ |
| Reliable JSON output | ✓ | ~86% | ✓ |
| Uses RAG context | ✗ | ✓ | ✗ |
| Finds all violations | ✗ | ✗ | ✓ |

Together they cover: fast baseline (1), guideline-augmented detection (2), and comprehensive multi-issue detection (3).

---

## 15. Reproducing Results

```bash
# First eval entry, all 7 models, all 72 configs (504 calls)
python scripts/evaluate_prompts.py

# Quick verification with one model (72 calls, ~5 min)
python scripts/evaluate_prompts.py --models llama3.1:8b

# Multi-issue configs only
python scripts/evaluate_prompts.py --detection multi

# Minimal strategy, RAG mode only
python scripts/evaluate_prompts.py --strategy minimal --mode rag

# First 10 eval entries (broader evaluation)
python scripts/evaluate_prompts.py --max-entries 10
```

Results are cached in `data/llm_cache/` — re-runs are instant.
