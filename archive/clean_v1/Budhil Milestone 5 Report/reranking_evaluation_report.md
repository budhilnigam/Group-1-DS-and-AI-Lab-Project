# Milestone 5 - Re-ranking Evaluation Summary (Baseline vs Re-ranked)

This report compares baseline retrieval ordering against the reranking stage. It now includes two saved reranking runs (with different tuning/code states) so all values map to existing artifacts on disk.

## Artifacts
- Query strategy implementation: `src/rag_model/query_strategy.py`
- Re-ranking notebook: `notebooks/reranking_simple_comparison.ipynb`
- Run A outputs (earlier tuning):
	- `notebooks/rerank_simple_outputs_20260404_144238/overall_metrics.csv`
	- `notebooks/rerank_simple_outputs_20260404_144238/category_metrics.csv`
	- `notebooks/rerank_simple_outputs_20260404_144238/pr_rows.csv`
- Run B outputs (later tuning):
	- `notebooks/rerank_simple_outputs_20260404_150553/overall_metrics.csv`
	- `notebooks/rerank_simple_outputs_20260404_150553/category_metrics.csv`
	- `notebooks/rerank_simple_outputs_20260404_150553/pr_rows.csv`

## Evaluation Objective
Evaluate whether reranking improves ranking quality after candidate retrieval, using:
- PR-level Recall@K, Precision@K, Modified MRR@K
- Category-level TP/FP changes
- High-K gains without unacceptable category-level regressions

## Exact Conceptual Changes From Baseline to Re-ranked
1. Two-stage ranking
Baseline uses retrieval order directly. Re-ranked mode rescored candidates before final top-K selection.

2. Composite rerank score
Re-ranked mode combines semantic score, lexical overlap, category bonus, and a rank penalty.

3. Duplicate-category control (later tuning)
Later tuning introduced a per-category cap to reduce repeated same-category predictions in final top-K.

4. Same candidate pool
Within each run, baseline and reranked use the same retrieved candidate pool. Differences are due to ordering logic.

## Hyperparameter Tuning Used in Notebook

The reranking logic in `notebooks/reranking_simple_comparison.ipynb` uses the following explicit hyperparameters:

- `RANDOM_SEED = 42`
- `SAMPLE_SIZE = 50`
- `TOP_N_CANDIDATES = 25`
- `TOP_K_FINAL = 7`
- `LEXICAL_WEIGHT = 0.35`
- `CATEGORY_BONUS = 0.15`
- `RANK_PENALTY = 0.01`
- `MAX_PER_CATEGORY = 2`

Rerank score formulation used in the notebook:

$$
rerank\_score = semantic\_score + 0.35 \cdot lexical\_overlap + category\_bonus - 0.01 \cdot rank\_idx
$$

Where:
- `semantic_score` is the Qdrant similarity score.
- `lexical_overlap` is token overlap between query text and candidate chunk text.
- `category_bonus` is `+0.15` only when the candidate category string appears in the query text.
- `rank_idx` is the original retrieval index (0-based), so later candidates get penalized.

Final selection policy:
- Candidates are sorted by `rerank_score` descending.
- At most `MAX_PER_CATEGORY=2` items per category are allowed in final top-K.
- Selection stops at `TOP_K_FINAL=7`.

### What This Tuning Implies for Observed Metrics

1. Stronger early-rank quality is expected.
The lexical and category terms (`0.35`, `0.15`) boost candidates that are textually/category aligned with the query, which typically improves Recall@K and MRR at moderate/high K.

2. Reduced duplicate-category dominance is expected.
`MAX_PER_CATEGORY=2` prevents one dominant category from occupying most top-7 slots, which can improve overall PR-level coverage but may hurt a category if relevant items are sparse.

3. Retrieval-depth trade-off remains.
`TOP_N_CANDIDATES=25` bounds the reranker search space. If a true positive is absent from those 25, reranking cannot recover it.

4. Sample-level sensitivity remains.
`SAMPLE_SIZE=50` and single-seed (`42`) means results are sensitive to sample composition. Category swings between Run A and Run B can occur even with nearby tuning states.

### Run A vs Run B Interpretation With Tuning Context

- The two runs were produced under different notebook/code states, but the reranking family is the same: weighted composite scoring with category-cap selection.
- The observed differences (especially `mutable_default` behavior) are consistent with calibration sensitivity around the same tuning framework: small shifts in score calibration, retrieval mix, or category representation can cause large per-category changes while still improving aggregate metrics at higher K.
- Because the report artifacts do not persist a full run-time config snapshot (weights, cap, and query-builder variant per run), the safest project-level claim is that both runs are valid outcomes of the same rerank design under different tuning/calibration states.

## High-level Metrics (Run A: `rerank_simple_outputs_20260404_144238`)

| mode | k | recall_at_k | precision_at_k | mrr_at_k |
|---|---:|---:|---:|---:|
| baseline | 1 | 0.1439 | 0.3030 | 0.1439 |
| baseline | 3 | 0.5556 | 0.3939 | 0.3237 |
| baseline | 5 | 0.5960 | 0.3758 | 0.3338 |
| baseline | 7 | 0.9167 | 0.3896 | 0.3826 |
| reranked | 1 | 0.2803 | 0.4242 | 0.2803 |
| reranked | 3 | 0.6086 | 0.4343 | 0.4146 |
| reranked | 5 | 0.8485 | 0.4121 | 0.4651 |
| reranked | 7 | 0.9596 | 0.3983 | 0.4830 |

### Delta (Run A, reranked - baseline)

| k | delta_recall | delta_precision | delta_mrr |
|---|---:|---:|---:|
| 1 | +0.1364 | +0.1212 | +0.1364 |
| 3 | +0.0530 | +0.0404 | +0.0909 |
| 5 | +0.2525 | +0.0364 | +0.1313 |
| 7 | +0.0429 | +0.0087 | +0.1003 |

**Fig R1 - Run A PR-level baseline vs reranked metrics across K**

![Fig R1 - Run A PR-level baseline vs reranked metrics across K](../../notebooks/rerank_simple_outputs_20260404_144238/baseline%20vs%20reranked%20PR%20level%20metrics.png)

## High-level Metrics (Run B: `rerank_simple_outputs_20260404_150553`)

| mode | k | recall_at_k | precision_at_k | mrr_at_k |
|---|---:|---:|---:|---:|
| baseline | 1 | 0.2146 | 0.3636 | 0.2146 |
| baseline | 3 | 0.3763 | 0.3131 | 0.2866 |
| baseline | 5 | 0.5404 | 0.2970 | 0.3229 |
| baseline | 7 | 0.5606 | 0.2597 | 0.3257 |
| reranked | 1 | 0.2146 | 0.3636 | 0.2146 |
| reranked | 3 | 0.3586 | 0.3131 | 0.2652 |
| reranked | 5 | 0.6768 | 0.3030 | 0.3357 |
| reranked | 7 | 0.8485 | 0.3463 | 0.3603 |

### Delta (Run B, reranked - baseline)

| k | delta_recall | delta_precision | delta_mrr |
|---|---:|---:|---:|
| 1 | +0.0000 | +0.0000 | +0.0000 |
| 3 | -0.0177 | +0.0000 | -0.0215 |
| 5 | +0.1364 | +0.0061 | +0.0129 |
| 7 | +0.2879 | +0.0866 | +0.0345 |

**Fig R3 - Run B PR-level baseline vs reranked metrics across K**

![Fig R3 - Run B PR-level baseline vs reranked metrics across K](../../notebooks/rerank_simple_outputs_20260404_150553/baseline%20vs%20reranked%20PR%20level%20metrics.png)

## Per-category Snapshot at K=7

### Run A (earlier tuning)

| category | baseline_recall | reranked_recall | baseline_precision | reranked_precision |
|---|---:|---:|---:|---:|
| naming_convention | 0.7647 | 1.0000 | 0.4815 | 0.5152 |
| unused_import | 1.0000 | 1.0000 | 0.6364 | 0.6364 |
| indentation | 0.6000 | 1.0000 | 0.3000 | 0.2941 |
| mutable_default | 1.0000 | 0.7000 | 0.3030 | 0.2593 |
| documentation_formatting | 1.0000 | 1.0000 | 0.1923 | 0.1923 |

**Fig R2 - Run A category recall and false positives (baseline vs reranked)**

![Fig R2 - Run A category recall and false positives (baseline vs reranked)](../../notebooks/rerank_simple_outputs_20260404_144238/recall%20and%20fp%20baseline%20and%20reranked.png)

### Run B (later tuning)

| category | baseline_recall | reranked_recall | baseline_precision | reranked_precision |
|---|---:|---:|---:|---:|
| naming_convention | 1.0000 | 1.0000 | 0.5152 | 0.5152 |
| unused_import | 0.3333 | 1.0000 | 0.6364 | 0.6364 |
| indentation | 1.0000 | 1.0000 | 0.1515 | 0.1515 |
| mutable_default | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| documentation_formatting | 1.0000 | 1.0000 | 0.1515 | 0.1515 |

**Fig R4 - Run B category recall and false positives (baseline vs reranked)**

![Fig R4 - Run B category recall and false positives (baseline vs reranked)](../../notebooks/rerank_simple_outputs_20260404_150553/recall%20and%20fp%20baseline%20and%20reranked.png)

## Why Category-wise Can Be Worse Than Baseline
1. Objective mismatch between global ranking and per-category balance
The reranker is optimized for overall PR-level ranking quality, not explicitly for equal performance across all categories.

2. Category cap and score weights can suppress low-frequency categories
When score weights or cap settings favor dominant categories, a category like `mutable_default` can be pushed out of top-K.

3. Retrieval bottleneck cannot be fixed by reranking
If relevant `mutable_default` candidates are missing/rare in the candidate pool, reranking cannot recover them.

4. Trade-off behavior is expected
Improving early rank and overall MRR can still reduce one category’s recall if calibration is not category-aware.

## Observations
1. Run A shows strong reranking gains across all K values.
Reranked exceeds baseline in recall, precision, and MRR at K=1/3/5/7.

2. Run B shows mixed behavior at low K but clear gains at high K.
At K=3, reranked is slightly lower in recall/MRR; at K=7, reranked is much better.

3. The two folders represent different tuning/code states.
This is why conclusions differ if only one folder is reported.

4. `mutable_default` is the key limitation in later tuning.
In Run B it remains 0 recall for both baseline and reranked, indicating a retrieval/query coverage issue, not only rerank ordering.

## Limitations Noticed
1. Hyperparameter snapshots are stored implicitly by run output folder and notebook state.
Exact numeric settings should be logged explicitly per run for strict reproducibility.

2. Single-seed runs are sensitive.
Both folders are valid, but a multi-seed mean/std report is needed for final claims.

3. Category-level metrics are highly distribution-dependent.
Small category counts can cause large swings in recall/precision across runs.

## Conclusion
Yes, both result folders should be reported. Run A and Run B both exist and contain valid but different outcomes due to different tuning/code states. The corrected interpretation is:
- reranking is beneficial overall, especially at larger K;
- category-wise regressions can occur when scoring/capping is not category-aware;
- next step is explicit per-run hyperparameter logging plus category-aware calibration (especially for `mutable_default`).
