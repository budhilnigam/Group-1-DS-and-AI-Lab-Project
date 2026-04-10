# Milestone 5 - Query Strategy Evaluation Summary (Variant 2 vs Variant 1)

This report compares two query-strategy runs saved from the Strategy-2 retrieval notebook and explains how query construction changes affected coverage, precision, and recall behavior.

Important naming clarification used in this report:
- Folder `notebooks/v2/` corresponds to **Query Strategy Variant 2** (helper/signal-based).
- Folder `notebooks/v3/` corresponds to **Query Strategy Variant 1** (regex/string-based).  
	The previous label "v3" referred to run folder naming, not a third query strategy.

## Artifacts
- Query strategy implementation: `src/rag_model/query_strategy.py`
- Strategy comparison notebook: `notebooks/retrieval_query_strategy_2_helper_func.ipynb`
- Variant 2 run metrics: `notebooks/v2/stats_df.csv`, `notebooks/v2/coverage_df.csv`
- Variant 1 run metrics (saved under v3 folder): `notebooks/v3/stats_df.csv`, `notebooks/v3/coverage_df.csv`

## Retrieval Preprocessing / Pipeline Overview
Before ranking metrics are computed, the project applies the following preprocessing and retrieval controls:

1. Entry and source preparation
- Evaluation entries are sampled from `evaluation.json`.
- Each entry resolves to a source file path and source text.

2. Query text generation (variant-dependent)
- Variant 1 (regex/string-based): query text is built from fast regex heuristics over source text.
- Variant 2 (helper/signal-based): query text is built from static-analysis helper signals.

3. Repo-aware retrieval filtering
- Query vectors are searched in Qdrant.
- Retrieval filter includes common source types (`pep8`, `flake8`, `pylint`, `ruff`, `pep257`) and repo-family-aware source types (e.g., `<family>_guidelines`, `<family>_review_comment`).
- This reduces cross-repo noise and keeps retrieval context domain-aware.

4. Category extraction and metric computation
- Retrieved payloads are normalized into target categories.
- PR-level and category-level metrics are computed at K = 1, 3, 5, 7.

## Evaluation Objective
Evaluate query-generation behavior for retrieval by measuring:
- PR coverage at multiple K values
- Per-category recall/precision and TP/FP trends
- Trade-offs between early precision and high-K coverage

## Exact Conceptual Difference: Variant 1 vs Variant 2 Query Strategy
1. Variant 1 (regex/string-based; folder `v3`)
- Uses direct regex/statistical hints from file text (imports, camelCase, mutable defaults, indentation counts, docstring counts).
- Faster and broader retrieval behavior.
- Tends to increase high-K recall but can increase FP due to coarse signal granularity.

2. Variant 2 (helper/signal-based; folder `v2`)
- Uses helper/static-signal functions (`naming`, `indent`, `mutable_default`, `documentation`, `unused_import`).
- More targeted signal composition.
- Tends to preserve cleaner early precision and lower FP, but may miss broader matches.

3. Precision-vs-recall behavior
- Variant 2 is precision-oriented and tighter at small K.
- Variant 1 is recall-oriented at larger K with broader retrieval spread.

4. Category imbalance risk
- Variant 1 strongly boosts some categories (`unused_import`, `indentation`, `documentation_formatting`) at high K, but can under-represent `mutable_default` depending on lexical cues.

## High-level Metrics

### PR Coverage by K

| k | Variant 2 coverage | Variant 1 coverage |
|---|---:|---:|
| 1 | 0.6667 | 0.4545 |
| 3 | 0.7273 | 0.8182 |
| 5 | 0.7879 | 0.8788 |
| 7 | 0.8485 | 0.8788 |

### Macro (category-averaged) Snapshot

| k | Variant 2 recall | Variant 2 precision | Variant 1 recall | Variant 1 precision |
|---|---:|---:|---:|---:|
| 1 | 0.4015 | 0.7087 | 0.1935 | 0.4458 |
| 3 | 0.4628 | 0.6543 | 0.3948 | 0.3459 |
| 5 | 0.5028 | 0.6286 | 0.5952 | 0.3762 |
| 7 | 0.5514 | 0.6289 | 0.7247 | 0.3942 |

## Per-category Snapshot at K=7

### Variant 2 (helper/signal-based, folder `v2`)

| category | precision | recall | TP | FP |
|---|---:|---:|---:|---:|
| naming_convention | 0.7000 | 0.8235 | 14 | 6 |
| unused_import | 0.8750 | 0.3333 | 7 | 1 |
| indentation | 0.4444 | 0.8000 | 4 | 5 |
| mutable_default | 1.0000 | 0.6000 | 6 | 0 |
| documentation_formatting | 0.1250 | 0.2000 | 1 | 7 |

### Variant 1 (regex/string-based, folder `v3`)

| category | precision | recall | TP | FP |
|---|---:|---:|---:|---:|
| naming_convention | 0.5000 | 0.8235 | 14 | 14 |
| unused_import | 0.6774 | 1.0000 | 21 | 10 |
| indentation | 0.2174 | 1.0000 | 5 | 18 |
| mutable_default | 0.0000 | 0.0000 | 0 | 0 |
| documentation_formatting | 0.1818 | 0.8000 | 4 | 18 |

## Observations
1. Variant 1 improved retrieval breadth at larger K values.
This is visible in higher coverage at K=3/5/7 and higher macro recall at K=5/7.

2. Variant 2 is stronger for early precision and cleaner retrieval.
At K=1 and K=3, Variant 2 has clearly better macro precision and lower FP pressure.

3. Variant 1 over-retrieves in some categories.
`indentation` and `documentation_formatting` show large FP growth at K=7.

4. `mutable_default` is a critical weakness for Variant 1 in this run.
Recall fell from 0.6000 (Variant 2) to 0.0000 (Variant 1), indicating weak lexical/query signal coverage for this category.

5. `unused_import` shifts strongly toward recall under Variant 1.
Recall improved from 0.3333 to 1.0000, but with more false positives.

## Limitations Noticed
1. Query strategy alone cannot guarantee balanced category coverage.
The regex-focused Variant 1 can boost broad retrieval while missing category-specific cases like `mutable_default`.

2. Category sensitivity is coupled to query tokenization style.
Categories that require semantic context (not explicit lexical clues) are harder for regex-oriented query generation.

3. Current retrieval depends on available candidate chunks after repo-aware filtering.
If filtered candidate pools under-represent a category, query strategy changes alone may not recover it.

4. Query-stage metrics are from sampled notebook runs.
These are project-valid directional results, but final operational conclusions require multi-seed/full-corpus confirmation.

## Conclusion
Variant 2 (helper/signal-based) is the cleaner precision-oriented query baseline, while Variant 1 (regex/string-based, folder `v3`) improves high-K coverage and recall. From the project perspective, the main gap is category robustness: Variant 1 struggles on `mutable_default` because its query evidence is too lexical/coarse for that violation type in current candidate pools. The practical path is to keep repo-aware filtering and pair Variant 1 breadth with reranking/calibration and category-aware boosting for `mutable_default`.
