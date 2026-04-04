# Milestone 5 - RAG + LLM Evaluation Summary (Single Strategy)

This report evaluates the RAG-augmented LLM pipeline using a single prompting/retrieval strategy and the combined raw output file.

## Artifacts
- RAG notebook: `notebooks/rag_llm.ipynb`
- Raw combined responses: `outputs/rag_llm_raw_responses_combined.txt`
- Evaluator: `src/evaluation/evaluate_llm_raw_txt.py`
- Ground truth: `data/processed/evaluation.json`

## Evaluation Objective
Measure how well the RAG + LLM pipeline detects the 5 target violation categories against ground truth, using the same metric framework as other project reports:
- PR-level coverage and failure rate
- Violation count comparison
- Category-wise precision/recall/F1
- Line-number match behavior

## Pipeline Configuration (from notebook)
The notebook uses one RAG strategy (no prompt/query variants):
- Model: `openai/gpt-oss-20b`
- Retrieval method: `query_strategy(...)` from `src/rag_model/query_strategy.py`
- Retrieval top-k: `RETRIEVAL_TOP_K = 5`
- Batch size: `BATCH_SIZE = 1`
- File truncation limit: `MAX_CHARS_PER_FILE = 8000`
- Context guardrails: `MODEL_CONTEXT_LIMIT = 8192`, `MAX_OUTPUT_TOKENS = 800`
- Prompt rule: max 5 findings per PR, with retrieved chunks included as supporting context

Note: the combined raw file appears to include multiple execution segments/restarts (batch numbering restarts and duplicated ranges), so this report reflects the consolidated output exactly as stored.

## High-level Metrics

| Metric | Value |
|---|---:|
| Ground-truth PRs | 97 |
| Predicted PRs with parsed JSON | 36 |
| PRs ignored due to empty/non-JSON response | 72 |
| Ignored-response rate (vs 97 PRs) | 74.2% |
| Analyzed PRs (non-empty parsed predictions) | 34 |
| LLM comments (analyzed PRs) | 125 |
| Ground-truth comments (analyzed PRs) | 161 |
| Missed violations | 42 |
| Extra violations | 6 |
| PRs with equal counts | 18 |
| Line matches (using llm_line + 1) | 60 |
| Line mismatches | 65 |
| Line match rate | 48.0% |

## Category-wise Results

| Category | Precision | Recall | F1 | TP | FP | FN | Line Match | Line Mismatch |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| documentation_formatting | 0.0000 | 0.0000 | 0.0000 | 0 | 3 | 15 | 0 | 3 |
| indentation | 0.2000 | 0.1111 | 0.1429 | 1 | 4 | 8 | 0 | 5 |
| mutable_default | 1.0000 | 0.9231 | 0.9600 | 12 | 0 | 1 | 2 | 10 |
| naming_convention | 0.9677 | 0.8108 | 0.8824 | 30 | 1 | 7 | 8 | 23 |
| unused_import | 1.0000 | 0.8506 | 0.9193 | 74 | 0 | 13 | 50 | 24 |

## Observations
1. Overall response reliability is the main bottleneck.
A large share of PRs (72/97) were ignored because responses were empty or non-JSON, which dominates end-to-end effectiveness more than category quality on successful PRs.

2. On successful PRs, precision is strong for 3 categories.
`unused_import` and `mutable_default` both achieved precision 1.0, and `naming_convention` reached 0.9677 precision.

3. `documentation_formatting` and `indentation` remain weak.
`documentation_formatting` produced no true positives, and `indentation` had very low recall (0.1111), indicating these categories are still difficult even with retrieved context.

4. Line localization is moderate, not robust.
Line match rate is 48.0% (60/125), so about half of predicted comments are category-correct but line-offset or incorrect in location.

5. Retrieval did not eliminate output fragility.
Even with guideline chunks added to prompts, the combined run still shows many empty/non-JSON responses. This suggests runtime robustness and output formatting compliance are still key failure modes.

## RAG-specific Failure Patterns Noticed in Raw File
- Multiple clearly truncated JSON outputs (responses cut mid-object/string).
- Long stretches of blank responses between valid batches.
- Repeated batch numbering resets indicate multiple sessions were concatenated.

These patterns are consistent with API/runtime interruptions, context/token pressure, or partial generation termination before valid JSON closure.

## Limitations
1. Combined file is not a single clean run.
Because `rag_llm_raw_responses_combined.txt` aggregates multiple sessions, run-level reproducibility is lower than a single timestamped output artifact.

2. Notebook constants may differ from final combined execution.
The currently visible notebook values may not exactly match every appended segment in the combined file.

3. Evaluator parses only valid JSON sections.
Malformed/truncated sections are treated as ignored, which is correct for scoring but reduces analyzable coverage.

## Conclusion
The single-strategy RAG + LLM pipeline shows good category precision when it returns valid JSON, especially for `unused_import`, `mutable_default`, and `naming_convention`. However, the dominant issue is response reliability: 74.2% of PRs were ignored due to empty/non-JSON outputs in the combined artifact. For this setup, improving output robustness (JSON validity, retry/recovery, and run segmentation hygiene) is the highest-impact next step, ahead of additional category tuning.