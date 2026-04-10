# Milestone 5 Report

## 1. Project Overview and Recap of Previous Milestone

This milestone evaluates the RAG-based LLM pipeline developed in the previous milestone.

In the earlier stage, the system consisted of:

- A synthesized evaluation dataset of PR-level examples with ground-truth review comments.
- A retrieval corpus of guideline chunks and review-comment-linked knowledge items.
- A retrieval layer built on Qdrant and sentence-transformer embeddings.
- A generation layer that compares `naive_llm`, `rag_llm`, and static tool-based outputs.

The final pipeline used in this milestone can be summarized as:

1. Load PR or review-comment prompts from the evaluation set.
2. Retrieve relevant guideline chunks from the vector database.
3. Optionally apply prompt variations and query strategy variations.
4. Generate LLM outputs using the naive baseline, RAG pipeline, or static tools.
5. Parse raw outputs and compare them against ground truth.

Observations:

- The previous milestone established the retrieval and generation pipeline, but did not yet provide a full evaluation narrative.
- This milestone focuses on dataset characterization, retrieval quality, generation quality, and error patterns.

Limitations:

- The report currently uses placeholder values and should be updated with final numbers after the last evaluation run.
- Some sections are intentionally written to be easy to fill in with tables, plots, and exact values.

## 2. Evaluation Dataset and EDA

### 2.1 Evaluation Dataset: `evaluation.json`

The evaluation dataset contains synthesized PR-level examples used to measure retrieval and generation performance.

Suggested dataset statistics to report:

| Statistic | Value |
| --- | ---: |
| Total PR entries | 240 |
| Total repositories represented | 6 |
| Total ground-truth review comments | 1,180 |
| Average review comments per PR | 4.92 |
| Median review comments per PR | 5 |
| Minimum review comments per PR | 1 |
| Maximum review comments per PR | 11 |

Recommended composition summary:

| Repo | PR count | Review comments | Percentage of dataset |
| --- | ---: | ---: | ---: |
| django | 62 | 308 | 25.8% |
| flask | 48 | 221 | 20.0% |
| fastapi | 41 | 196 | 17.1% |
| pandas | 38 | 187 | 15.8% |
| scikit-learn | 31 | 149 | 12.9% |
| misc | 20 | 119 | 8.4% |

Violation category distribution in `ground_truth_reviews`:

| Violation category | Count | Share |
| --- | ---: | ---: |
| naming_convention | 312 | 26.4% |
| unused_import | 204 | 17.3% |
| indentation | 178 | 15.1% |
| documentation_formatting | 164 | 13.9% |
| mutable_default | 138 | 11.7% |
| exception_handling | 102 | 8.6% |
| magic_number | 82 | 7.0% |

Suggested plots:

- Bar chart of PR counts by repository.
- Histogram of review-comment counts per PR.
- Stacked bar chart of violation category counts by repository.
- Heatmap of repo versus category frequency.

Observations:

- The dataset is moderately imbalanced, with naming and import-related violations appearing most often.
- A small number of repositories contribute a large share of the samples, so repo-specific bias should be considered.

Limitations:

- The evaluation set is synthesized, so the category frequencies may not fully reflect real-world project distributions.
- The dataset may overrepresent common static-analysis style issues compared with more contextual review feedback.

### 2.2 Retrieval Corpus: `retrieval_corpus.json`

The retrieval corpus contains guideline chunks and associated review-comment references used for vector retrieval.

Suggested corpus statistics to report:

| Statistic | Value |
| --- | ---: |
| Total guideline chunks | 3,420 |
| Unique guideline documents | 612 |
| Total repo-specific chunks | 2,980 |
| Repo-agnostic chunks | 440 |
| Average chunks per violation category | 488.6 |

Violation-category distribution in the retrieval corpus:

| Violation category | Chunk count | Share |
| --- | ---: | ---: |
| naming_convention | 724 | 21.2% |
| unused_import | 591 | 17.3% |
| indentation | 488 | 14.3% |
| documentation_formatting | 476 | 13.9% |
| mutable_default | 411 | 12.0% |
| exception_handling | 382 | 11.2% |
| magic_number | 348 | 10.2% |

Repo distribution for guideline chunks and review-comment-linked entries:

| Repo | Guideline chunks | Review-comment-linked chunks | Share |
| --- | ---: | ---: | ---: |
| django | 980 | 214 | 32.8% |
| flask | 742 | 173 | 24.9% |
| fastapi | 603 | 142 | 20.3% |
| pandas | 414 | 102 | 13.9% |
| scikit-learn | 281 | 77 | 9.4% |

Suggested plots:

- Bar chart of corpus chunks by violation category.
- Bar chart of repo-specific chunk counts.
- Side-by-side comparison of corpus distribution versus evaluation distribution.

Observations:

- The retrieval corpus is denser than the evaluation set, which is expected because multiple guideline chunks can map to a single issue type.
- Repo-specific chunks are concentrated in a few repositories, which may improve retrieval accuracy for those repos but reduce generalization.

Limitations:

- Chunk counts are sensitive to the chunking strategy and overlap settings.
- Some guideline chunks may be semantically redundant, which can inflate retrieval hits without improving answer quality.

## 3. Evaluation Environment and Reproducibility

The following environment was used to run the retrieval and LLM evaluation experiments.

| Item | Setup |
| --- | --- |
| Operating system | Windows 11 |
| Python version | 3.11.x |
| Runtime | Local virtual environment |
| Embedding model | BAAI/bge-large-en-v1.5 |
| Vector database | Qdrant at `localhost:6333` |
| Retrieval library | `qdrant-client` |
| LLM experimentation | `naive_llm`, `rag_llm`, static tool baseline |
| Data analysis | `pandas`, `matplotlib`, `seaborn` |
| Evaluation parsing | Custom Python script |

Runtime setup:

- The notebook `retrieval_query_strategy_2_helper_func.ipynb` was executed in a local notebook kernel.
- The Qdrant collection `guideline_embeddings` was queried using sentence-transformer embeddings.
- Evaluation outputs were parsed from raw text and compared with the ground-truth labels.

Reproducibility notes:

- Random sampling for retrieval experiments used a fixed seed of 42.
- Retrieval settings such as `top_k` and the embedding model name should be recorded in the final report.
- The raw outputs and evaluation files should be archived alongside the report for exact reruns.

Observations:

- The setup is reproducible as long as the same vector collection and embedding model are available.
- The notebook-based workflow makes it easy to regenerate plots, but it is sensitive to environment drift.

Limitations:

- Hardware details should be inserted from the actual machine used for the final run.
- If Qdrant or the embedding model changes, the retrieval results will not be directly comparable.

## 4. Metrics Used for Evaluation

### 4.1 Retrieval Metrics

For retrieval query strategies, the following metrics are used across multiple `k` values, typically `k = 1, 3, 5, 7`.

| Metric | Definition | Why it is appropriate |
| --- | --- | --- |
| Recall@K | Fraction of relevant categories present in the top-K retrieved chunks | Measures how well the system retrieves relevant evidence for downstream generation |
| Precision@K | Fraction of top-K retrieved chunks that are relevant | Measures retrieval noise and ranking quality |
| MRR@K | Mean reciprocal rank of the first relevant chunk | Rewards early placement of useful chunks |

These metrics are appropriate because the task is evidence retrieval for LLM assistance rather than exact document classification.

### 4.2 Generation and Review Metrics

The LLM output evaluation script computes category-level and line-level metrics from raw responses.

| Metric | Definition | Why it is appropriate |
| --- | --- | --- |
| Precision | Correct predicted violation categories divided by all predicted categories | Measures how often the model avoids false positives |
| Recall | Correct predicted violation categories divided by ground-truth categories | Measures how many true issues the model captures |
| F1 score | Harmonic mean of precision and recall | Provides a balanced summary for imbalanced labels |
| Line match count | Predicted line number matches the ground-truth line number after the evaluation adjustment | Measures whether the model points to the right code location |
| Missed violations | Ground-truth violations not predicted by the model | Captures under-detection |
| Extra violations | Predicted violations beyond the ground truth count | Captures over-generation |
| Parsed PR count | Number of PRs with usable model output | Indicates coverage of the system |
| Ignored PRs | PRs with no LLM response or unusable output | Indicates failure rate in the generation pipeline |

Observations:

- Retrieval metrics are useful for understanding evidence quality before generation.
- Precision and recall are both necessary because the task involves multiple possible error categories and imbalanced outputs.
- Line-level matching helps verify whether the model not only identifies the right issue type but also points to the correct location.

Limitations:

- Category-level scores may not capture the full semantic quality of review comments.
- Line match scoring is sensitive to small offsets, formatting differences, and annotation conventions.

## 5. Retrieval Query Strategy Experiments

Only one retrieval query strategy has been used so far, but the report should be written to allow additional strategies to be added later.

### 5.1 Current Query Strategy

Current strategy name: `Strategy 2 - Intelligent helper-function query generation`

This strategy builds the retrieval query from the available PR context and helper logic in the notebook `retrieval_query_strategy_2_helper_func.ipynb`.

Suggested retrieval-quality table:

| Strategy | K | Recall@K | Precision@K | MRR@K |
| --- | ---: | ---: | ---: | ---: |
| Strategy 2 | 1 | 0.41 | 0.58 | 0.46 |
| Strategy 2 | 3 | 0.63 | 0.44 | 0.53 |
| Strategy 2 | 5 | 0.74 | 0.37 | 0.56 |
| Strategy 2 | 7 | 0.81 | 0.31 | 0.58 |

You can later add more rows for alternative strategies such as:

- Keyword-only retrieval query.
- Prompt-expanded retrieval query.
- Repo-aware retrieval query.
- Hybrid query strategy.

Suggested plots:

- Line plot of Recall@K, Precision@K, and MRR@K over K.
- Stacked bar chart of category-level recall contribution by K.

Observations:

- Recall tends to improve as K increases, while precision usually decreases.
- MRR is most useful when the ranking of the first relevant result matters more than the total number of retrieved chunks.

Limitations:

- Current results reflect only one query strategy, so cross-strategy conclusions are still tentative.
- Retrieval metrics are calculated on sampled evaluation entries, so they may differ from a full-dataset run.

## 6. Prompting Strategy Experiments

Several prompting strategies were explored before settling on the current baseline and RAG setup.

Suggested prompt variants to describe:

1. Direct answer prompt with no retrieval context.
2. Retrieval-augmented prompt with top-K guideline chunks.
3. Structured prompt asking for category, line number, and review comment.
4. Short-form response prompt for concise review comments.

Suggested comparative table for prompting strategies:

| Prompting strategy | Description | Strengths | Weaknesses |
| --- | --- | --- | --- |
| Baseline prompt | No retrieved context | Simple and fast | Weak factual grounding |
| RAG prompt | Uses retrieved guideline chunks | Better grounding and category alignment | Sensitive to retrieval noise |
| Structured prompt | Forces output schema | Easier parsing | Can feel rigid and reduce naturalness |
| Concise prompt | Encourages brief review comments | Cleaner outputs | May miss nuance |

Observations:

- Retrieval context generally improves groundedness, especially when the prompt asks for a specific violation category and review style.
- Structured prompts are easier to evaluate because they reduce parsing ambiguity.

Limitations:

- Prompt sensitivity can make results unstable across sampling runs.
- Short prompts may under-explain the reasoning behind a predicted review comment.

## 7. Comparative LLM Results

This section compares `naive_llm`, `rag_llm`, and the static tool baseline.

### 7.1 Overall Performance Table

Use the following as a placeholder table and replace the values after the final evaluation run.

| Model | PRs processed | Review comments processed | PRs ignored due to no LLM response | Precision | Recall | F1 | Line matches | Line mismatches |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| naive_llm | 120 | 486 | 8 | 0.52 | 0.47 | 0.49 | 214 | 272 |
| rag_llm | 120 | 498 | 3 | 0.66 | 0.61 | 0.63 | 309 | 189 |
| static tools | 120 | 472 | 6 | 0.60 | 0.55 | 0.57 | 276 | 196 |

### 7.2 Category-Wise Metrics

Suggested category-wise table:

| Category | Precision | Recall | F1 | TP | FP | FN | Line match | Line mismatch |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| naming_convention | 0.71 | 0.68 | 0.69 | 88 | 36 | 41 | 77 | 52 |
| unused_import | 0.64 | 0.60 | 0.62 | 61 | 34 | 40 | 49 | 46 |
| indentation | 0.58 | 0.55 | 0.56 | 45 | 33 | 37 | 39 | 41 |
| documentation_formatting | 0.63 | 0.57 | 0.60 | 52 | 31 | 39 | 44 | 45 |
| mutable_default | 0.67 | 0.59 | 0.63 | 39 | 19 | 27 | 31 | 25 |

### 7.3 How to Present the Comparison

The report can include one or more of the following plots:

- Grouped bar chart of precision, recall, and F1 by model.
- Heatmap of category-wise F1 scores across models.
- Bar chart of ignored PR count by model.
- Scatter plot showing line matches versus line mismatches.

Observations:

- The RAG-based model is expected to outperform the naive baseline because it uses retrieved evidence.
- The static tool baseline may produce more stable outputs than naive generation, but can still be limited by retrieval and prompt framing.
- The number of ignored PRs is important because a model with slightly higher F1 but many empty responses may not be operationally useful.

Limitations:

- The placeholder values must be replaced with the final run outputs before submission.
- If the models were evaluated on different subsets or in different orders, the comparison should state that clearly.

## 8. Qualitative Results

This section should show example model outputs, both correct and incorrect.

### 8.1 Successful Predictions

Example format:

| PR ID | Ground truth | Model output | Notes |
| --- | --- | --- | --- |
| PR-014 | `naming_convention` at line 42 | Correctly identified naming issue and line 42 | Good alignment with ground truth |
| PR-087 | `unused_import` at line 18 | Suggested removing unused import | Concise and correct |

### 8.2 Failure Cases

Example format:

| PR ID | Ground truth | Model output | Failure type |
| --- | --- | --- | --- |
| PR-031 | `indentation` at line 55 | Predicted `documentation_formatting` | Wrong category |
| PR-104 | `mutable_default` at line 27 | No response generated | Missing output |
| PR-119 | `exception_handling` at line 63 | Correct category but wrong line number | Location mismatch |

Observations:

- Successful cases usually correspond to clear, local code issues with strong lexical signals.
- Failure cases often happen when the issue is subtle, context dependent, or weakly represented in retrieval.

Limitations:

- Qualitative examples should be selected carefully to avoid cherry-picking only strong or weak cases.
- A small number of examples is useful for readability, but the chosen examples should represent the broader failure distribution.

## 9. Error Analysis

The main error patterns observed during evaluation can be grouped as follows:

1. Category confusion between similar violations such as `naming_convention` and `documentation_formatting`.
2. Line-number offsets caused by extraction or formatting differences.
3. Over-generation of extra violations in longer PRs.
4. Missing outputs from the LLM pipeline, leading to ignored PRs in the final metrics.
5. Retrieval noise where top-K chunks are relevant to the repository but not the specific issue.

Suggested error-analysis table:

| Error pattern | Example symptom | Possible reason | Suggested fix |
| --- | --- | --- | --- |
| Wrong category | Predicted a different violation type | Ambiguous prompt or weak retrieval | Improve prompt schema and retrieval filtering |
| Wrong line number | Correct issue but wrong location | Offset in annotation or parser mismatch | Validate line normalization logic |
| Extra violations | More predictions than ground truth | Overly verbose generation | Constrain output format |
| Empty response | No usable output | Generation failure or parsing issue | Add retry handling and stricter output validation |
| Retrieval noise | Irrelevant top-K chunks | Query not specific enough | Refine query strategy |

Observations:

- Many errors are not purely model errors; some come from retrieval quality, parsing, or formatting mismatches.
- Improving output schema consistency may give a measurable gain even without changing the base model.

Limitations:

- The current error analysis is based on aggregate outputs and sample inspection, so it may miss rare but important failure modes.
- Some apparent mistakes may actually reflect ambiguity in the ground truth itself.

## 10. Key Observations, Limitations, and Anomalies

Key observations:

- Retrieval quality improves the factual grounding of the generated reviews.
- RAG-based generation is expected to outperform the naive baseline on precision and F1.
- Query strategy and prompt structure have a visible impact on both retrieval quality and final review quality.
- The evaluation framework should report both answer quality and output coverage, since empty responses are a practical failure mode.

Limitations:

- The dataset is synthesized and may not fully capture real code review behavior.
- The evaluation is sensitive to category imbalance and to the exact chunking strategy used for the corpus.
- Some metrics, especially line-level matching, may penalize near-miss predictions that are otherwise semantically correct.

Anomalies observed during evaluation:

- Some PRs produce no LLM response and therefore must be excluded from metric calculations.
- In a few cases, the model predicts the correct category but the wrong line number.
- Retrieval sometimes returns semantically close but not directly relevant guideline chunks, especially for repo-specific cases.

## 11. Final Summary

This milestone completes the main evaluation story for the RAG-based LLM project.

It covers:

- EDA of `evaluation.json` and `retrieval_corpus.json`.
- Retrieval experiments using top-K quality metrics across multiple K values.
- Prompting strategy comparisons.
- Final model comparison for `naive_llm`, `rag_llm`, and static tools.
- Quantitative and qualitative error analysis.

Before submission, replace the placeholder values with the final computed statistics and attach the relevant plots.
