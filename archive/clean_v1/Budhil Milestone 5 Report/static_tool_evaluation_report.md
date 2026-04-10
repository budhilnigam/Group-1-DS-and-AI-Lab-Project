# Milestone 5 - Static-tool Evaluation Summary (v1 vs v2)

This report compares two static-tool evaluation runs against the same evaluation corpus and focuses on how conceptual changes in v2 affected precision, recall, and F1.

## Artifacts
- Original evaluator backup: `src/evaluation/static_tool_eval_v1.py`
- Current evaluator (v2 logic): `src/evaluation/static_tool_eval_v2.py`
- v1 results file: `outputs/static_tool_results_v1.txt`
- v2 results file: `outputs/static_tool_results_v2.txt`

## Evaluation Objective
Use static analyzers (pylint + flake8), map their findings to the 5 target violation categories, and evaluate predictions against ground truth using the same TP/FP/FN and precision/recall/F1 formulas as the LLM evaluator.

## Exact Conceptual Changes From v1 to v2
1. Tool invocation reliability
v1 relied on tool launchers from PATH. v2 invokes analyzers through the active interpreter to avoid environment/launcher mismatches.

2. Violation mapping strictness
v1 used broader mappings from linter signals to categories, which captured more potential matches but also many irrelevant findings. v2 narrowed mappings to higher-confidence linter signals to reduce noisy category assignments.

3. Duplicate and near-duplicate handling
v1 effectively counted many repeated/nearby findings separately. v2 added explicit deduplication and merging of neighboring findings (within a small line window), reducing repeated FP inflation.

4. Line alignment tolerance
v1 used stricter line matching behavior. v2 introduced relaxed matching/neighbor-aware handling so semantically same findings reported one line apart are less likely to be penalized.

5. Overall scoring behavior trade-off
v1 behavior favored recall (especially for several categories), while v2 prioritized precision and cleaner signal quality.

## High-level Metrics

### v1
- analyzed_pr_count: 87
- missed_violations: 0
- extra_violations: 901
- equal_violations_prs: 1
- line_match_total: 759
- line_mismatch_total: 731

### v2
- analyzed_pr_count: 87
- missed_violations: 23
- extra_violations: 212
- equal_violations_prs: 24
- line_match_total: 389
- line_mismatch_total: 389

## Per-category Snapshot (v1)

| category | precision | recall | f1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| documentation_formatting | 0.2239 | 0.1948 | 0.2083 | 15 | 52 | 62 |
| indentation | 0.1535 | 1.0000 | 0.2662 | 105 | 579 | 0 |
| mutable_default | 1.0000 | 0.9583 | 0.9787 | 69 | 0 | 3 |
| naming_convention | 0.5106 | 1.0000 | 0.6760 | 169 | 162 | 0 |
| unused_import | 0.4897 | 1.0000 | 0.6574 | 166 | 173 | 0 |

## Per-category Snapshot (v2)

| category | precision | recall | f1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| documentation_formatting | 0.2239 | 0.1948 | 0.2083 | 15 | 52 | 62 |
| indentation | 0.4234 | 1.0000 | 0.5949 | 105 | 143 | 0 |
| mutable_default | 1.0000 | 0.8889 | 0.9412 | 64 | 0 | 8 |
| naming_convention | 0.5556 | 0.9467 | 0.7002 | 160 | 128 | 9 |
| unused_import | 0.9820 | 0.6566 | 0.7870 | 109 | 2 | 57 |

## Observations
1. v1 had very high false positives across multiple categories.
This is most visible in `indentation` (FP 579), `unused_import` (FP 173), and `naming_convention` (FP 162), which made many v1 predictions noisy even though recall was high.

2. v1 clearly had higher recall than v2 for most non-documentation categories.
For example, `unused_import` and `naming_convention` moved from recall 1.0000 in v1 to 0.6566 and 0.9467 in v2. This is expected from stricter filtering.

3. v2 is much cleaner in precision-sensitive categories.
The strongest example is `unused_import`, where precision increased from 0.4897 to 0.9820 after reducing noisy mappings.

4. `mutable_default` is very accurately identified by static tools.
It remains the most reliable category across both runs with precision 1.0000 in v1 and v2 and consistently high recall (0.9583 in v1, 0.8889 in v2).

5. `indentation` improved substantially in v2.
Precision rose from 0.1535 to 0.4234 while maintaining recall 1.0000, resulting in a large F1 increase (0.2662 to 0.5949).

6. `documentation_formatting` remained unchanged and weak.
Both runs show the same low precision/recall profile, indicating that current static mappings do not capture this category effectively.

## Conclusion
v1 is recall-heavy but too noisy for practical use due to very high FP counts. v2 introduces conceptually cleaner filtering and consolidation, significantly reducing FP while improving F1 in key categories (`indentation`, `unused_import`, and `naming_convention`), with a controlled recall trade-off. For this project objective, v2 is the better operational baseline.
