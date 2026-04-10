# Milestone 5: Model Evaluation, Performance Analysis, and Error Diagnostics

## Table of Contents
1. Executive Summary
2. Problem Scope and Objective
3. Final Pipeline Used for Evaluation
4. Evaluation Dataset and Protocol Consistency
5. Evaluation Environment and Reproducibility Setup
6. Key Metrics Driving Conclusions
7. Quantitative Results
8. Evaluation Visualizations
9. Qualitative Results (Representative)
10. Error Analysis (Quantified)
11. Limitations and Real-World Validation Status
12. Conclusion and Next-Step Priorities

---

## 1. Executive Summary

This milestone evaluates the final selected variants for the Python code-review system on five violation categories:
- unused_import
- naming_convention
- indentation
- documentation_formatting
- mutable_default

### 1.1 Final Variants Used
- Static baseline: Static Tool v2
- Naive LLM baseline: Prompt v1 (selected as requested)
- RAG pipeline: single RAG + LLM strategy
- Query strategy: Variant 2 (helper/signal-based)
- Reranking: enabled with Run A configuration

### 1.2 Main Outcomes
1. Static Tool v2 gives the strongest reliability and coverage safety:
   - Empty rate = 0.0%
   - Missed violations = 109 (lowest at full-dataset scale)
2. Naive LLM v1 gives very high precision on successful outputs:
   - Micro precision = 0.9677
   - Empty rate = 49.5%
3. RAG + LLM (new S15 retrieval run) improves reliability vs Naive v1 but still trails in quality metrics:
   - Empty rate: 37.1% vs 49.5%
   - Micro recall: 0.6257 vs 0.6618
   - Micro F1: 0.7554 vs 0.7860

### 1.3 Practical Conclusion
S15 retrieval strategy clearly improves retrieval quality, and in this run RAG reliability improved substantially. However, end-to-end generation quality is still below Naive v1, so static v2 remains the deterministic backstop.

---

## 2. Problem Scope and Objective

Objective: measure whether retrieval-augmented generation improves code-review quality under a consistent protocol, and identify where the pipeline fails in practice.

Evaluation focus:
- Quality: precision, recall, F1, missed/extra violations, line localization
- Reliability: empty/non-JSON response rate
- Retrieval quality: Recall@K, Precision@K, MRR@K

---

## 3. Final Pipeline Used for Evaluation

This project uses inference-time retrieval + generation, not model fine-tuning.

Pipeline steps:
1. Input code PR/file is normalized.
2. Retrieval path (RAG only): query generation -> repo-aware retrieval -> top-k candidate chunks.
3. Reranking path (selected): weighted rerank score over retrieved candidates.
4. Generation: `openai/gpt-oss-20b` produces strict JSON findings.
5. Evaluator compares predicted category+line against ground truth.

Minimal synthetic-data context (important only):
- Synthetic repositories and injected violations provide controlled labels.
- Retrieval corpus combines coding guidelines and synthetic review comments.
- Final model-comparison dataset is `data/processed/evaluation.json`.

---

## 4. Evaluation Dataset and Protocol Consistency

### 4.1 Dataset Used for Model Comparison
- Source: `data/processed/evaluation.json`
- Total PR entries: 97
- Total ground-truth comments: 675
- Avg comments/PR: 6.96 (median 6)

### 4.2 Category Distribution

| Category | Count | Share (%) |
|---|---:|---:|
| unused_import | 193 | 28.59 |
| naming_convention | 180 | 26.67 |
| indentation | 138 | 20.44 |
| documentation_formatting | 92 | 13.63 |
| mutable_default | 72 | 10.67 |

### 4.3 Protocol Consistency Checklist

| Experiment Group | Dataset | Core Protocol | Included in Unified Model Table |
|---|---|---|---|
| Static Tool v2 | `evaluation.json` | TP/FP/FN, missed/extra, line match/mismatch | Yes |
| Naive LLM v1 | `evaluation.json` | TP/FP/FN, missed/extra, line match/mismatch, empty rate | Yes |
| RAG + LLM | `evaluation.json` | TP/FP/FN, missed/extra, line match/mismatch, empty rate | Yes |
| Query/rerank retrieval-only runs | sampled notebook runs | Recall@K, Precision@K, MRR@K | No (reported separately) |

Note: unified model conclusions are restricted to experiments that share the same dataset and scoring protocol.

---

## 5. Evaluation Environment and Reproducibility Setup

### 5.1 Hardware/Runtime
- CPU: AMD Ryzen 3 7320U (4C/8T)
- RAM: 7.24 GB
- OS: Windows 11 (10.0.26200 family)
- Python: 3.12.6 (64-bit)

### 5.2 Core Libraries
- LLM/API: groq
- Retrieval/vector: faiss-cpu, qdrant-client
- Analysis: pandas, numpy, matplotlib
- Static tools: pylint, flake8

### 5.3 Reproducibility Controls
- JSON-only parsing at evaluator stage
- Saved output artifacts under `outputs/` and `notebooks/` run folders
- Fixed reranking seed (`RANDOM_SEED=42`) in selected retrieval run
- RAG v2 evaluated with: `python src/evaluation/evaluate_llm_raw_txt.py --raw outputs/rag_llm_raw_responses_v2.txt --evaluation data/processed/evaluation.json`

---

## 6. Key Metrics Driving Conclusions

This report prioritizes three deciding metrics:
1. Empty response rate (reliability)
2. Micro F1 on analyzed comments (quality)
3. Missed violations (safety/completeness)

Supporting diagnostics:
- Micro precision/recall
- Line match and line mismatch counts
- Retrieval ranking metrics (Recall@K, Precision@K, MRR@K)

---

## 7. Quantitative Results

### 7.1 Final Variant Selection (Re-checked)

- Static: v2 selected
- Naive LLM: v1 selected
- RAG: single strategy retained
- Query strategy: Variant 2 selected
- Reranking: Run A selected

### 7.2 Unified Model Comparison (Final Variants Only)

Definitions used in this table:
- `detected_violations = GT_analyzed - missed_violations + extra_violations`
- `micro_precision = TP/(TP+FP)` where `TP = detected - extra`, `FP = extra`
- `micro_recall = TP/(TP+FN)` where `FN = missed`

| Method | Variant | GT PRs | Parsed PRs | Empty/Non-JSON PRs | Empty Rate (%) | Analyzed PRs | GT Comments (Analyzed) | Detected Violations | Missed Violations | Extra Violations | Micro Precision | Micro Recall | Micro F1 | Line Match | Line Mismatch |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Static Tool | v2 | 97 | 97 | 0 | 0.0 | 97 | 675 | 778 | 109 | 212 | 0.7275 | 0.8385 | 0.7791 | 389 | 389 |
| Naive LLM | v1 | 97 | 49 | 48 | 49.5 | 47 | 272 | 186 | 92 | 6 | 0.9677 | 0.6618 | 0.7860 | 87 | 99 |
| RAG + LLM | single + S15 retrieval | 97 | 61 | 36 | 37.1 | 60 | 342 | 225 | 128 | 11 | 0.9511 | 0.6257 | 0.7554 | 105 | 120 |

Observations from data:
1. Static v2 is the only method with zero response failures and strongest full-dataset missed-violation control.
2. Naive v1 is most precision-heavy and has the best Micro F1 among LLM-based methods in this evaluation.
3. RAG with S15 retrieval is now more reliable than Naive v1 (37.1% vs 49.5% empty rate), but has lower recall/F1 in generation outputs.

### 7.3 Category-wise Final Snapshot

| Category | Static v2 F1 | Naive v1 F1 | RAG F1 |
|---|---:|---:|---:|
| documentation_formatting | 0.1887 | 0.1818 | 0.1429 |
| indentation | 0.5440 | 0.3385 | 0.2540 |
| mutable_default | 0.9412 | 0.7391 | 0.7632 |
| naming_convention | 0.6838 | 0.9558 | 0.8112 |
| unused_import | 0.7171 | 0.9154 | 0.9300 |

Category-level conclusions:
1. Static v2 is strongest for indentation and slightly strongest for documentation_formatting.
2. Naive v1 is strongest for naming_convention.
3. RAG is strongest only for unused_import in this run; other categories remain below static or naive baselines.

### 7.4 Retrieval Ablation: Retrieval OFF vs ON

Controlled ablation setup:
- Same model family (`gpt-oss-20b`)
- Same dataset (`evaluation.json`)
- Retrieval OFF: Naive v1
- Retrieval ON: RAG + LLM

| Metric | Naive v1 (No Retrieval) | RAG + LLM (With Retrieval) | Delta (RAG - Naive) |
|---|---:|---:|---:|
| Empty rate (%) | 49.5 | 37.1 | -12.4 |
| Micro precision | 0.9677 | 0.9511 | -0.0166 |
| Micro recall | 0.6618 | 0.6257 | -0.0361 |
| Micro F1 | 0.7860 | 0.7554 | -0.0306 |
| Line match rate (%) | 46.8 | 46.7 | -0.1 |

Interpretation:
1. In this new run, retrieval (with S15 strategy) improves response reliability.
2. Quality gains from retrieval quality did not fully transfer to generation quality metrics yet.

### 7.5 Correlation Between Retrieval Quality and Generation Performance

Selected retrieval run (Run A) improvements over baseline ordering:
- Recall@5: +0.2525
- Precision@5: +0.0364
- MRR@7: +0.1003

Observed relation from available artifacts:
1. S15 demonstrates strong retrieval usefulness at retrieval stage (`retrieval_strategies.md`): precision 59.6%, category recall 96.3%, MRR 0.625, F1 0.736.
2. With S15 + Qdrant in this run, RAG response reliability improved (empty rate 37.1%).
3. Retrieval-stage gains did not fully convert to better end-to-end generation recall/F1 than Naive v1.

Critical missing data for strict statistical correlation:
- No per-PR joined retrieval-generation logs are persisted across all runs; therefore, robust Pearson/Spearman correlation coefficients cannot be computed from current artifacts.

### 7.6 Selected Retrieval Configuration and Metrics

Selected query strategy: Variant 2 (helper/signal-based).

S15 usefulness summary from retrieval strategy analysis (`docs/Milestone 5/Kannan Milestone 5 Report/retrieval_strategies.md`):
- Baseline S2 -> S15 improvements:
   - Precision: 38.6% -> 59.6%
   - Category Recall: 100.0% -> 96.3%
   - MRR: 0.455 -> 0.625
   - F1: 0.557 -> 0.736
- This confirms S15 is a strong retrieval policy for producing cleaner, better-ranked evidence context.

Selected reranking formula:

$$
\text{rerank\_score} = \text{semantic\_score} + 0.35\cdot\text{lexical\_overlap} + \text{category\_bonus} - 0.01\cdot\text{rank\_idx}
$$

Selected reranking settings:
- `TOP_N_CANDIDATES=25`
- `TOP_K_FINAL=7`
- `LEXICAL_WEIGHT=0.35`
- `CATEGORY_BONUS=0.15`
- `RANK_PENALTY=0.01`
- `MAX_PER_CATEGORY=2`

Run A retrieval deltas (reranked - baseline):
- K=1: recall +0.1364, precision +0.1212, MRR +0.1364
- K=3: recall +0.0530, precision +0.0404, MRR +0.0909
- K=5: recall +0.2525, precision +0.0364, MRR +0.1313
- K=7: recall +0.0429, precision +0.0087, MRR +0.1003

### 7.7 Evaluation Summary (Condensed)

Final summary of results:
1. Static v2: highest reliability and best safety coverage at dataset scale.
2. Naive v1: high precision but moderate recall and moderate reliability.
3. RAG with S15: reliability improved significantly, but generation quality still trails Naive v1 in this run.

---

## 8. Evaluation Visualizations

### 8.1 PR-level Retrieval Metrics (Baseline vs Reranked)
![Run A PR-level baseline vs reranked metrics](../../notebooks/rerank_simple_outputs_20260404_144238/baseline%20vs%20reranked%20PR%20level%20metrics.png)

### 8.2 Category Recall and False Positives (Baseline vs Reranked)
![Run A category recall and false positives](../../notebooks/rerank_simple_outputs_20260404_144238/recall%20and%20fp%20baseline%20and%20reranked.png)

### 8.3 Derived Confusion Matrices (Final Selected Variants)

Method to derive one-vs-rest TN per category:

$$
TN_c = \left(G - (TP_c + FN_c)\right) - FP_c
$$

where $G$ is total GT comments in the analyzed subset for that method.

#### Static Tool v2 (G = 675)

|  | Predicted Positive | Predicted Negative |
|---|---:|---:|
| Actual Positive | TP = 453 | FN = 222 |
| Actual Negative | FP = 325 | TN = 2375 |

#### Naive LLM v1 (G = 272)

|  | Predicted Positive | Predicted Negative |
|---|---:|---:|
| Actual Positive | TP = 177 | FN = 95 |
| Actual Negative | FP = 9 | TN = 1079 |

#### RAG + LLM (G = 342)

|  | Predicted Positive | Predicted Negative |
|---|---:|---:|
| Actual Positive | TP = 211 | FN = 131 |
| Actual Negative | FP = 14 | TN = 1354 |

Note: raw counts are not directly comparable across methods because analyzed subsets differ.

---

## 9. Qualitative Results (Representative)

### 9.1 Typical Success Patterns
1. `unused_import` detections are usually precise and actionable.
2. `naming_convention` detections are strong in Naive v1 and RAG successful outputs.

### 9.2 Typical Failure Patterns
1. Empty/non-JSON outputs on complex PRs (dominant failure mode in LLM-based paths).
2. Line-offset drift even when the category is correct.
3. Persistent under-detection for `documentation_formatting` and `indentation` in RAG.

---

## 10. Error Analysis (Quantified)

### 10.1 Final RAG Pipeline Error Distribution

| Error Type | Count | Denominator | Frequency |
|---|---:|---:|---:|
| Empty/non-JSON PR responses | 36 | 97 PRs | 37.1% |
| Missed violations (FN) | 128 | 342 GT comments (analyzed) | 37.4% |
| Extra violations (FP) | 11 | 225 detected comments | 4.9% |
| Line mismatch | 120 | 225 detected comments | 53.3% |

### 10.2 Final RAG Category-wise FN Frequency

| Category | FN | Share of Total FN (%) |
|---|---:|---:|
| documentation_formatting | 30 | 22.9 |
| indentation | 41 | 31.3 |
| mutable_default | 18 | 13.7 |
| naming_convention | 26 | 19.8 |
| unused_import | 16 | 12.2 |

### 10.3 What the Error Distribution Shows
1. Reliability improved meaningfully vs previous RAG run, but quality errors still dominate remaining failures.
2. `indentation` and `documentation_formatting` are still the largest category gaps.
3. Localization quality is still insufficient for robust reviewer actionability.

---

## 11. Limitations and Real-World Validation Status

### 11.1 Core Limitations
1. End-to-end RAG generation quality still lags retrieval-stage quality improvements.
2. Per-PR retrieval-generation joined logs are not available.
3. Multi-seed uncertainty estimates are not available.
4. Category imbalance affects stability of rare-category conclusions.

### 11.2 Real-World Validation Status

Current status:
- A true external real-world labeled PR benchmark was not executed in this milestone.
- Available manual holdout exists: `data/raw/eval_manual/evaluation.json` with 6 entries and 46 labeled comments.
- This holdout is manually curated, not a mined real-world PR benchmark.

Critical missing data to complete external credibility validation:
1. External PR dataset (recommended at least 30 PRs) with trusted labels for the same 5 categories.
2. End-to-end predictions on that dataset under the same protocol used in Section 7.
3. Run artifacts that include parse-failure logs and per-PR outputs.

---

## 12. Conclusion and Next-Step Priorities

Evidence-backed conclusion on RAG effectiveness:
1. S15 retrieval strategy is demonstrably useful at retrieval stage (higher precision/MRR/F1 in retrieval metrics).
2. In this new RAG run, reliability improved substantially (37.1% empty rate), but generation recall/F1 remain below Naive v1.
3. Static v2 remains essential as deterministic reliability backstop, while RAG needs generation-stage hardening.

### 12.1 Final Unified Comparison Table (Numeric)

| Method | Variant | Empty Rate (%) | Micro Precision | Micro Recall | Micro F1 | Missed Violations | Detected Violations | Extra Violations | Line Match | Line Mismatch |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Static Tool | v2 | 0.0 | 0.7275 | 0.8385 | 0.7791 | 109 | 778 | 212 | 389 | 389 |
| Naive LLM | v1 | 49.5 | 0.9677 | 0.6618 | 0.7860 | 92 | 186 | 6 | 87 | 99 |
| RAG + LLM | single + S15 retrieval | 37.1 | 0.9511 | 0.6257 | 0.7554 | 128 | 225 | 11 | 105 | 120 |

Priority next steps:
1. Reliability hardening first: JSON repair, bounded retries, schema-level validation, and fail-safe regeneration.
2. Add per-PR retrieval-generation joined logging to compute true retrieval-generation correlations.
3. Run the same protocol on a small external real-world benchmark.
4. Add multi-seed reporting with confidence intervals.