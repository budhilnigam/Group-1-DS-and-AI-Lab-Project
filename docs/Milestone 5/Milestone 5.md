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
- Reranking: finalized three-set sweep (`balanced`, `semantic_lean`, `diversity_lexical`), selected `balanced`

### 1.2 Main Outcomes
1. Static Tool v2 gives the strongest reliability and coverage safety:
   - Empty rate = 0.0%
   - Missed violations = 109 (lowest at full-dataset scale)
2. Naive LLM v1 gives very high precision on successful outputs:
   - Micro precision = 0.9698
   - Empty rate = 44.3%
3. RAG + LLM improves quality on successful outputs vs Naive v1:
   - Micro recall: 0.6964 vs 0.6226
   - Micro F1: 0.8083 vs 0.7583
   - But reliability is worse: empty/non-JSON = 53.6%

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
- Fixed reranking setup for comparison (`RANDOM_SEED=42`, `SAMPLE_SIZE=50`, `TOP_N_CANDIDATES=25`, `TOP_K_FINAL=7`)

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
- Reranking: `diversity_lexical` selected from latest three-set sweep

### 7.2 Unified Model Comparison (Final Variants Only)

Definitions used in this table:
- `detected_violations = GT_analyzed - missed_violations + extra_violations`
- `micro_precision = TP/(TP+FP)` where `TP = detected - extra`, `FP = extra`
- `micro_recall = TP/(TP+FN)` where `FN = missed`

| Method | Variant | GT PRs | Parsed PRs | Empty/Non-JSON PRs | Empty Rate (%) | Analyzed PRs | GT Comments (Analyzed) | Detected Violations | Missed Violations | Extra Violations | Micro Precision | Micro Recall | Micro F1 | Line Match | Line Mismatch |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Static Tool | v2 | 97 | 97 | 0 | 0.0 | 97 | 675 | 778 | 109 | 212 | 0.7275 | 0.8385 | 0.7791 | 389 | 389 |
| Naive LLM | v1 | 97 | 54 | 43 | 44.3 | 52 | 310 | 199 | 117 | 6 | 0.9698 | 0.6226 | 0.7583 | 91 | 108 |
| RAG + LLM | single | 97 | 45 | 52 | 53.6 | 43 | 224 | 162 | 68 | 6 | 0.9630 | 0.6964 | 0.8083 | 67 | 95 |

Observations from data:
1. Static v2 is the only method with zero response failures and strongest full-dataset missed-violation control.
2. Naive v1 is most precision-heavy but has lower recall than RAG.
3. RAG gives best Micro F1 on successful outputs, but worst reliability.

### 7.3 Category-wise Final Snapshot

| Category | Static v2 F1 | Naive v1 F1 | RAG F1 |
|---|---:|---:|---:|
| documentation_formatting | 0.1887 | 0.1818 | 0.0606 |
| indentation | 0.5440 | 0.3385 | 0.4118 |
| mutable_default | 0.9412 | 0.5938 | 0.8889 |
| naming_convention | 0.6838 | 0.8732 | 0.9333 |
| unused_import | 0.7171 | 0.9073 | 0.9263 |

Category-level conclusions:
1. Static v2 is strongest for indentation and slightly strongest for documentation_formatting.
2. RAG is strongest for naming_convention and unused_import on successful outputs.
3. Static v2 remains strongest for mutable_default at dataset scale.

### 7.4 Retrieval Ablation: Retrieval OFF vs ON

Controlled ablation setup:
- Same model family (`gpt-oss-20b`)
- Same dataset (`evaluation.json`)
- Retrieval OFF: Naive v1
- Retrieval ON: RAG + LLM

| Metric | Naive v1 (No Retrieval) | RAG + LLM (With Retrieval) | Delta (RAG - Naive) |
|---|---:|---:|---:|
| Empty rate (%) | 44.3 | 53.6 | +9.3 |
| Micro precision | 0.9698 | 0.9630 | -0.0068 |
| Micro recall | 0.6226 | 0.6964 | +0.0738 |
| Micro F1 | 0.7583 | 0.8083 | +0.0500 |
| Line match rate (%) | 45.7 | 41.4 | -4.3 |

Interpretation:
1. Retrieval increases recall and overall F1 on successful outputs.
2. Retrieval increases failure rate in the current implementation.

### 7.5 Reranking Evaluation (Latest Sweep Only)

We evaluated reranking as a ranking-quality study, not a generation study. The notebook compares four systems under the same sampled PR set:
1. baseline retrieval order (no reranking)
2. balanced reranking
3. semantic_lean reranking
4. diversity_lexical reranking

All systems are compared on PR-level Recall@K, Precision@K, and MRR@K for K in {1, 3, 5, 7}, then summarized by average metric and composite score.

Latest finalized sweep (single run) results:

| Config | Recall@K (avg) | Precision@K (avg) | MRR@K (avg) | Composite |
|---|---:|---:|---:|---:|
| diversity_lexical | 0.8475 | 0.5763 | 0.6365 | 0.6868 |
| baseline | 0.7100 | 0.7454 | 0.5777 | 0.6777 |
| semantic_lean | 0.7442 | 0.7141 | 0.5747 | 0.6776 |
| balanced | 0.7900 | 0.6502 | 0.5917 | 0.6773 |

K=7 snapshot (most relevant for final retrieval context size):

| Config | Recall@7 | Precision@7 | MRR@7 |
|---|---:|---:|---:|
| baseline | 0.8233 | 0.7029 | 0.6121 |
| balanced | 0.9867 | 0.5170 | 0.6466 |
| semantic_lean | 0.9417 | 0.6257 | 0.6267 |
| diversity_lexical | 0.9933 | 0.4827 | 0.6940 |

Interpretation:
1. Reranking increases high-K coverage and ranking quality (especially Recall@7 and MRR@7).
2. Different reranking settings shift the recall-precision balance.
3. `balanced` was selected because it gives the best final trade-off for downstream prompting: near-ceiling Recall@7, substantially better precision than `diversity_lexical`, and stronger MRR than `semantic_lean`.

### 7.6 Selected Retrieval Configuration and Reranking Concept

Selected query strategy: Variant 2 (helper/signal-based).

Reranking concept used in the notebook:
1. Retrieve a candidate pool per PR query.
2. Re-score candidates using semantic similarity plus lexical/category alignment.
3. Apply diversity control with a per-category cap to avoid repeated same-category results.
4. Keep top-7 final chunks for downstream prompting.

Selected reranking settings:
- `TOP_N_CANDIDATES=25`
- `TOP_K_FINAL=7`
- `LEXICAL_WEIGHT=0.35`
- `CATEGORY_BONUS=0.15`
- `RANK_PENALTY=0.01`
- `MAX_PER_CATEGORY=2`

Why `balanced` is the final choice:
- It keeps Recall@7 at 0.9867, which is already near the ceiling for this sweep.
- It preserves better Precision@7 than `diversity_lexical`, which makes the final context less noisy.
- It is the most even operating point for downstream LLM prompting, where over-aggressive retrieval can crowd out useful context.

### 7.7 Evaluation Summary (Condensed)

Final summary of results:
1. Static v2: highest reliability and best safety coverage at dataset scale.
2. Naive v1: high precision but moderate recall and moderate reliability.
3. RAG: best Micro F1 on successful responses, but reliability bottleneck dominates practical deployment risk.

---

## 8. Evaluation Visualizations

### 8.1 Metric-vs-K Curves (Baseline and Three Rerank Sets)
![Metric-vs-K curves](../Milestone 6/assets/reranking_simple_comparison/metrics_vs_k.png)

### 8.2 Summary Metrics at K=7
![Summary metrics at K=7](../Milestone 6/assets/reranking_simple_comparison/average_metrics_by_config.png)

### 8.3 Category False Positives at K=7
![Category false positives at K=7](../Milestone 6/assets/reranking_simple_comparison/category_false_positives_k7.png)

### 8.4 Category Recall at K=7
![Category recall at K=7](../Milestone 6/assets/reranking_simple_comparison/category_recall_k7.png)

### 8.5 Category Precision at K=7
![Category precision at K=7](../Milestone 6/assets/reranking_simple_comparison/category_precision_k7.png)

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

#### Naive LLM v1 (G = 310)

|  | Predicted Positive | Predicted Negative |
|---|---:|---:|
| Actual Positive | TP = 188 | FN = 122 |
| Actual Negative | FP = 11 | TN = 1229 |

#### RAG + LLM (G = 224)

|  | Predicted Positive | Predicted Negative |
|---|---:|---:|
| Actual Positive | TP = 155 | FN = 69 |
| Actual Negative | FP = 7 | TN = 889 |

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
| Empty/non-JSON PR responses | 52 | 97 PRs | 53.6% |
| Missed violations (FN) | 68 | 224 GT comments (analyzed) | 30.4% |
| Extra violations (FP) | 6 | 162 detected comments | 3.7% |
| Line mismatch | 95 | 162 detected comments | 58.6% |

### 10.2 Final RAG Category-wise FN Frequency

| Category | FN | Share of Total FN (%) |
|---|---:|---:|
| documentation_formatting | 29 | 42.6 |
| unused_import | 14 | 20.6 |
| indentation | 15 | 22.1 |
| naming_convention | 5 | 7.4 |
| mutable_default | 6 | 8.8 |

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
| Naive LLM | v1 | 44.3 | 0.9698 | 0.6226 | 0.7583 | 117 | 199 | 6 | 91 | 108 |
| RAG + LLM | Query Strategy v2 and Prompt Strategy v1| 53.6 | 0.9630 | 0.6964 | 0.8083 | 68 | 162 | 6 | 67 | 95 |

Priority next steps:
1. Reliability hardening first: JSON repair, bounded retries, schema-level validation, and fail-safe regeneration.
2. Add per-PR retrieval-generation joined logging to compute true retrieval-generation correlations.
3. Run the same protocol on a small external real-world benchmark.
4. Add multi-seed reporting with confidence intervals.