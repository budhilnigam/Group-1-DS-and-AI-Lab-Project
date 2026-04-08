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
3. RAG + LLM improves quality on successful outputs vs Naive v1:
   - Micro recall: 0.7391 vs 0.6618
   - Micro F1: 0.8322 vs 0.7860
   - But reliability is worse: empty/non-JSON = 74.2%

### 1.3 Practical Conclusion
RAG is effective for quality when responses are valid, but current end-to-end effectiveness is constrained by output reliability. Static v2 remains the deterministic backstop.

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

---

## 5. Evaluation Environment and Reproducibility Setup

### 5.1 Hardware/Runtime
- CPU: AMD Ryzen 3 7320U (4C/8T)
- RAM: 8 GB
- OS: Windows 11 
- Python: 3.12.6 (64-bit)

### 5.2 Core Libraries
- LLM/API: groq (openai/gpt-oss-20b)
- Retrieval/vector: faiss-cpu, qdrant-client
- Analysis: pandas, numpy, matplotlib
- Static tools: pylint, flake8

### 5.3 Reproducibility Controls
- JSON-only parsing at evaluator stage
- Saved output artifacts under `outputs/` and `notebooks/` run folders
- Fixed reranking seed (`RANDOM_SEED=42`) in selected retrieval run

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
| RAG + LLM | single | 97 | 36 | 72 | 74.2 | 34 | 161 | 125 | 42 | 6 | 0.9520 | 0.7391 | 0.8322 | 60 | 65 |

Observations from data:
1. Static v2 is the only method with zero response failures and strongest full-dataset missed-violation control.
2. Naive v1 is most precision-heavy but has lower recall than RAG.
3. RAG gives best Micro F1 on successful outputs, but worst reliability.

### 7.3 Category-wise Final Snapshot

| Category | Static v2 F1 | Naive v1 F1 | RAG F1 |
|---|---:|---:|---:|
| documentation_formatting | 0.1887 | 0.1818 | 0.0000 |
| indentation | 0.5440 | 0.3385 | 0.1429 |
| mutable_default | 0.9412 | 0.7391 | 0.9600 |
| naming_convention | 0.6838 | 0.9558 | 0.8824 |
| unused_import | 0.7171 | 0.9154 | 0.9193 |

Category-level conclusions:
1. Static v2 is strongest for indentation and slightly strongest for documentation_formatting.
2. Naive v1 is strongest for naming_convention.
3. RAG is strongest for mutable_default and unused_import on successful outputs.

### 7.4 Retrieval Ablation: Retrieval OFF vs ON

Controlled ablation setup:
- Same model family (`gpt-oss-20b`)
- Same dataset (`evaluation.json`)
- Retrieval OFF: Naive v1
- Retrieval ON: RAG + LLM

| Metric | Naive v1 (No Retrieval) | RAG + LLM (With Retrieval) | Delta (RAG - Naive) |
|---|---:|---:|---:|
| Empty rate (%) | 49.5 | 74.2 | +24.7 |
| Micro precision | 0.9677 | 0.9520 | -0.0157 |
| Micro recall | 0.6618 | 0.7391 | +0.0773 |
| Micro F1 | 0.7860 | 0.8322 | +0.0462 |
| Line match rate (%) | 46.8 | 48.0 | +1.2 |

Interpretation:
1. Retrieval increases recall and overall F1 on successful outputs.
2. Retrieval increases failure rate in the current implementation.

### 7.5 Correlation Between Retrieval Quality and Generation Performance

Selected retrieval run (Run A) improvements over baseline ordering:
- Recall@5: +0.2525
- Precision@5: +0.0364
- MRR@7: +0.1003

Observed relation from available artifacts:
1. Better retrieval ranking quality aligns with better generation recall/F1 (RAG vs no-retrieval baseline).
2. Larger retrieval context also aligns with worse output reliability (higher empty/non-JSON rate).

Critical missing data for strict statistical correlation:
- No per-PR joined retrieval-generation logs are persisted across all runs; therefore, robust Pearson/Spearman correlation coefficients cannot be computed from current artifacts.

### 7.6 Selected Retrieval Configuration and Metrics

Selected query strategy: Variant 2 (helper/signal-based).

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
3. RAG: best Micro F1 on successful responses, but reliability bottleneck dominates practical deployment risk.

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

#### RAG + LLM (G = 161)

|  | Predicted Positive | Predicted Negative |
|---|---:|---:|
| Actual Positive | TP = 117 | FN = 44 |
| Actual Negative | FP = 8 | TN = 636 |

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
| Empty/non-JSON PR responses | 72 | 97 PRs | 74.2% |
| Missed violations (FN) | 42 | 161 GT comments (analyzed) | 26.1% |
| Extra violations (FP) | 6 | 125 detected comments | 4.8% |
| Line mismatch | 65 | 125 detected comments | 52.0% |

### 10.2 Final RAG Category-wise FN Frequency

| Category | FN | Share of Total FN (%) |
|---|---:|---:|
| documentation_formatting | 15 | 34.1 |
| unused_import | 13 | 29.5 |
| indentation | 8 | 18.2 |
| naming_convention | 7 | 15.9 |
| mutable_default | 1 | 2.3 |

### 10.3 What the Error Distribution Shows
1. Reliability failures dominate all other error classes.
2. For successful generations, `documentation_formatting` and `indentation` remain the main category gaps.
3. Localization quality is still insufficient for robust reviewer actionability.

---

## 11. Limitations

1. The Groq API context window for `gpt-oss-20b` is limited to approximately 8K tokens; for longer inputs, the model may consume most of the token budget during reasoning and fail to produce complete structured output.
2. Per-PR retrieval-generation joined logs are not available.
3. Multi-seed uncertainty estimates are not available.
4. Category imbalance affects stability of rare-category conclusions.
5. The current evaluation has not yet been validated on an external real-world labeled dataset; conclusions are therefore limited to the synthetic/manual benchmark setup used in this milestone.

---

## 12. Conclusion and Next-Step Priorities

Evidence-backed conclusion on RAG effectiveness:
1. RAG improves recall and Micro F1 on successful outputs compared with no-retrieval Naive v1.
2. RAG currently underperforms for end-to-end reliability due to very high empty/non-JSON rate.
3. Static v2 remains essential as a deterministic reliability backstop.

### 12.1 Final Unified Comparison Table (Numeric)

| Method | Variant (Best) | Empty Rate (%) | Micro Precision | Micro Recall | Micro F1 | Missed Violations | Detected Violations | Extra Violations | Line Match | Line Mismatch |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Static Tool | v2 | 0.0 | 0.7275 | 0.8385 | 0.7791 | 109 | 778 | 212 | 389 | 389 |
| Naive LLM | v1 | 49.5 | 0.9677 | 0.6618 | 0.7860 | 92 | 186 | 6 | 87 | 99 |
| RAG + LLM | Query Strategy v2 and Prompt Strategy v1| 74.2 | 0.9520 | 0.7391 | 0.8322 | 42 | 125 | 6 | 60 | 65 |

Priority next steps:
1. Reliability hardening first: JSON repair, bounded retries, schema-level validation, and fail-safe regeneration.
2. Add per-PR retrieval-generation joined logging to compute true retrieval-generation correlations.
3. Run the same protocol on a small external real-world benchmark.
4. Add multi-seed reporting with confidence intervals.