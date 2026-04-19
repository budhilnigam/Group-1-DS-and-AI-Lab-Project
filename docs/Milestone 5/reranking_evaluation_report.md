# Milestone 5: Reranking Evaluation Report (Final Sweep)

This report documents the finalized reranking comparison from the notebook workflow and includes only the latest run outputs used for final conclusions.

## Scope

The reranking study evaluates retrieval ordering quality before LLM generation. It compares:
- baseline retrieval order (no rerank)
- balanced reranking
- semantic_lean reranking
- diversity_lexical reranking

The comparison is done at K = 1, 3, 5, 7 using:
- Recall@K
- Precision@K
- MRR@K

## Notebook Workflow (Conceptual)

The finalized notebook process is:
1. Build query text from PR-level signals.
2. Retrieve a fixed candidate pool from the vector index.
3. Re-score candidates using semantic relevance plus lexical/category alignment.
4. Apply category diversity control during top-K selection.
5. Compare baseline vs three reranking configurations with shared sampled PRs.
6. Select one configuration using average and K=7 performance.

## Fixed Evaluation Setup

- RANDOM_SEED = 42
- SAMPLE_SIZE = 50
- TOP_N_CANDIDATES = 25
- TOP_K_FINAL = 7

Compared reranking sets:
- balanced: LEXICAL_WEIGHT 0.35, CATEGORY_BONUS 0.15, RANK_PENALTY 0.01, MAX_PER_CATEGORY 2
- semantic_lean: LEXICAL_WEIGHT 0.20, CATEGORY_BONUS 0.10, RANK_PENALTY 0.005, MAX_PER_CATEGORY 3
- diversity_lexical: LEXICAL_WEIGHT 0.50, CATEGORY_BONUS 0.25, RANK_PENALTY 0.02, MAX_PER_CATEGORY 1

## Final Results (Latest Run)

Average metrics across K:

| Config | Recall@K | Precision@K | MRR@K | Composite Score |
|---|---:|---:|---:|---:|
| diversity_lexical | 0.8475 | 0.5763 | 0.6365 | 0.6868 |
| baseline | 0.7100 | 0.7454 | 0.5777 | 0.6777 |
| semantic_lean | 0.7442 | 0.7141 | 0.5747 | 0.6776 |
| balanced | 0.7900 | 0.6502 | 0.5917 | 0.6773 |

K=7 snapshot:

| Config | Recall@7 | Precision@7 | MRR@7 |
|---|---:|---:|---:|
| baseline | 0.8233 | 0.7029 | 0.6121 |
| balanced | 0.9867 | 0.5170 | 0.6466 |
| semantic_lean | 0.9417 | 0.6257 | 0.6267 |
| diversity_lexical | 0.9933 | 0.4827 | 0.6940 |

## Final Selection

Selected reranking configuration: diversity_lexical

Reason for selection:
- strongest high-K coverage (highest Recall@7)
- best ranking quality (highest MRR@7)
- best overall composite score across K

## Visual Artifacts (Final)

- docs/Milestone 6/assets/reranking_simple_comparison/metrics_vs_k.png
- docs/Milestone 6/assets/reranking_simple_comparison/average_metrics_by_config.png
- docs/Milestone 6/assets/reranking_simple_comparison/category_false_positives_k7.png
- docs/Milestone 6/assets/reranking_simple_comparison/category_recall_k7.png
- docs/Milestone 6/assets/reranking_simple_comparison/category_precision_k7.png
- docs/Milestone 6/assets/reranking_simple_comparison/summary_metrics.csv
- docs/Milestone 6/assets/reranking_simple_comparison/category_metrics.csv
- docs/Milestone 6/assets/reranking_simple_comparison/rerank_configs.csv
