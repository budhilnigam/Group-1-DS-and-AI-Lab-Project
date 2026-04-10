# Milestone 5 Consolidated Report

This consolidated report compiles all Milestone 5 documentation into a single evaluator-facing document for academic and industry review.

---

## Master Table of Contents

1. [Synthetic Data Generation Strategy](#part-1--synthetic-data-generation-strategy)
2. [Retrieval Strategy Analysis](#part-2--retrieval-strategy-analysis)
3. [Static Analysis Tool Evaluation](#part-3--static-analysis-tool-evaluation)
4. [Prompt Engineering & Model Evaluation](#part-4--prompt-engineering--model-evaluation)

---

# Part 1 - Synthetic Data Generation Strategy

# Synthetic Data Generation Strategy: End-to-End Explanation

This project builds synthetic training-style and evaluation-style data for a RAG-based Python code review system. The goal is not to generate arbitrary Python code, but to create a controlled dataset where each code change is tied to one or more known guideline violations, and where those violations can be paired with realistic review comments. The five target categories are:

1. `unused_import`
2. `indentation`
3. `naming_convention`
4. `documentation_formatting`
5. `mutable_default`

The synthetic pipeline is spread across the notebook `notebooks/data_preprocessor.ipynb` and three main scripts:

- `scripts/create_synthetic_repos.py`
- `scripts/fetch_review_comments.py`
- `scripts/create_evaluation_dataset.py`

The process has four major stages:

1. Build the guideline-based retrieval corpus.
2. Create framework-specific synthetic repositories with clean code, then inject known violations and attach review comments.
3. Extract those review comments and merge them into the retrieval corpus as an additional knowledge source.
4. Create a separate evaluation dataset with multi-violation examples and store their ground-truth review annotations.

What follows is the complete strategy, step by step.

---

## 1. Overall Design Intent

The system is designed around a simple idea: if the final code-review model is expected to detect localized style and best-practice violations, then the data generation process must make those violations explicit, structured, and easy to evaluate.

Instead of scraping random noisy pull requests, the project creates synthetic GitHub repositories for different Python ecosystems:

- Flask
- FastAPI
- Django
- pandas-style utility modules
- scikit-learn-style utility modules

This gives the project three important advantages:

1. **Control** over the exact violation category inserted into code.
2. **Context** over repository and framework context, which matters for retrieval.
3. **Reliable ground truth**, because the project itself creates the bad code and the associated review comments.

The synthetic strategy is intentionally split into two dataset roles:

- **Retrieval/training knowledge source:** mostly single-category PRs and their review comments.
- **Evaluation set:** more difficult multi-category PRs with file snapshots and structured ground-truth review annotations.

---

## 2. Stage A: Building the Initial Retrieval Corpus from Guidelines

The notebook begins by defining two large in-memory lists:

- `COMMON_GUIDELINES`
- `REPO_GUIDELINES`

These are serialized into `data/processed/retrival_corpus.json`.

The retrieval corpus is therefore not only based on generated review comments. It starts from curated guideline chunks extracted from authoritative sources such as:

- PEP 8
- PEP 257
- Ruff
- Flake8 / pycodestyle
- Pylint
- Django coding style guidance
- pandas contribution and docstring guidance
- scikit-learn developer guidance
- Flask contribution guidance

Each chunk is stored as a dictionary with fields such as:

- `text`
- `category`
- `source_type`
- `source_path`
- `chunk_id`

This design matters because the final RAG system retrieves not just comments, but guideline evidence. The corpus therefore mixes:

- Generic Python rules
- Framework-specific conventions
- Later, synthetic review comments from PR discussions

The notebook writes this first version of the corpus before any synthetic GitHub repository generation starts.

---

## 3. Stage B: Creating Synthetic Repositories with Clean Baseline Code

The script `scripts/create_synthetic_repos.py` is responsible for generating the synthetic repositories and populating them with realistic clean files.

### 3.1 Repository Scope

For each framework, the script targets a repository named:

- `synthetic-flask`
- `synthetic-fastapi`
- `synthetic-django`
- `synthetic-pandas`
- `synthetic-sklearn`

These repositories are created under the authenticated GitHub user given by the repo token. The script checks whether the repository already exists. If it does, it skips repository creation and moves on.

### 3.2 Baseline File Templates

The script contains a `FILE_LISTS` constant. For each framework it defines around 20 realistic Python file paths and short descriptions. Examples include:

- Flask blueprints, forms, models, middleware, tests
- FastAPI routers, schemas, CRUD modules, dependencies, tests
- Django settings, views, serializers, signals, template tags, tests
- pandas ETL and utility modules
- scikit-learn preprocessing, evaluation, pipeline, model utilities

The important point is that the project does not generate meaningless toy files. It generates modules that look like plausible framework-specific project code.

### 3.3 Clean Code Generation with an LLM

For each file description, `generate_python_file()` asks an LLM to produce clean, idiomatic Python code. The prompt explicitly requests:

- Syntactically valid Python
- PEP 8 style
- 4-space indentation
- `snake_case` naming
- Organized imports
- Docstrings
- Type hints where appropriate
- A realistic module matching the given framework and file purpose

The script uses an `LLMClient` that calls the GitHub Models API with a model cascade. If one model is rate-limited or fails, the client rotates through the configured models and tokens.

### 3.4 Validation and Fallback Strategy

The generated code is validated with `compile()`. If validation fails, the script:

1. Retries once with an error-aware regeneration prompt, and
2. If that also fails, falls back to a minimal stub module.

This is an important quality-control step. The pipeline wants the repository's main branch to contain clean baseline code before any violations are injected.

### 3.5 Guidelines File per Repository

Each synthetic repository also receives a `guidelines.md` file. The script tries to build it from JSON guideline chunk files in `data/raw/guidelines_raw`. If such files are unavailable, it falls back to LLM-generated Markdown guidelines.

This gives each repository an explicit local coding-guideline document, which is consistent with the project's aim of repo-aware code review.

### 3.6 Commit to Main

Once `README.md`, `guidelines.md`, and all generated Python files are ready, the script commits them to the main branch using GitHub's low-level blobs, trees, commits, and refs APIs. At this point each repository represents a clean code base with no intentional violations on main.

---

## 4. Stage C: Injecting Single Violation Types into PR Branches

After creating the clean repository, the same script creates synthetic pull requests that intentionally introduce one violation category per PR.

This single-category PR generation is the core training-style synthetic data strategy used for review-comment collection.

### 4.1 PR Count and Rotation

The script takes a target number of PRs per repository, defaulting to 20. It counts existing PRs and only creates the missing number. Violation categories are assigned cyclically across PRs using the fixed order:

- `unused_import`
- `indentation`
- `naming_convention`
- `documentation_formatting`
- `mutable_default`

This ensures coverage across categories instead of letting the distribution be random or skewed.

### 4.2 File Selection

For each PR, the script chooses a Python file from the repository and creates a branch named like:

- `violation/unused-import-7`
- `violation/naming-convention-13`

The branch name matters later because `fetch_review_comments.py` parses the branch name to recover the violation category.

### 4.3 LLM-Based Violation Injection

The function `inject_violations()` takes the clean file content and instructs the LLM to rewrite the full file while introducing one specific violation type.

The violation prompts are category-specific:

- **`unused_import`:** add unused imports at the top of the file.
- **`indentation`:** change some blocks to 2-space, 6-space, or mixed indentation.
- **`naming_convention`:** rename functions or variables to camelCase.
- **`documentation_formatting`:** break or remove docstrings and create malformed formatting.
- **`mutable_default`:** replace `None` defaults with `[]`, `{}`, or `set()`.

The LLM is asked to output two things:

1. The full modified file, and
2. A JSON array listing the violated lines and descriptions.

This is important because the pipeline needs not only bad code, but also a structured mapping from changed lines to intended violations.

### 4.4 Deterministic Fallback Injection

If the LLM is unavailable or produces unusable output, the script falls back to deterministic transformations in `_fallback_inject()`. Examples:

- Prepend unused imports
- Convert `snake_case` names to `camelCase`
- Change `=None` to `=[]`
- Alter indentation on selected lines
- Break one-line docstrings into malformed multi-line versions

This fallback keeps the pipeline robust. Synthetic data generation does not stop just because the LLM response is invalid or rate-limited.

### 4.5 Validation Policy

Most injected files are still validated with `compile()`. Indentation violations are the exception because they may intentionally create syntax-breaking code.

This design is deliberate. Some categories, especially indentation, are defined by structural mistakes that can make code unparsable. The project accepts that because the goal is to evaluate review detection of localized style issues, not to preserve executable behavior.

---

## 5. Stage D: Generating Synthetic Review Comments for the Violations

Once the violated file is created, `create_synthetic_repos.py` also generates the corresponding review comments that simulate human PR feedback.

### 5.1 Comment Generation Strategy

For each detected or declared violation, the script extracts a small code window around the target line and asks the LLM to produce a short, constructive, human-sounding code review comment.

The prompt instructs the model to behave like a senior reviewer and explicitly discourages robotic language such as mentioning a violation label directly.

### 5.2 Review Style Constraints

The comments are intended to be:

- Concise
- Localized to a specific line
- Phrased like PR review feedback
- Grounded in what is visible in the code snippet

This matters because the final downstream system is not evaluated only on rule detection. It also needs to produce realistic review language.

### 5.3 Fallback Review Comments

If the LLM cannot generate a comment, the script uses category-specific comment templates. For example:

- **Unused import** comments say the import is not used and should be removed.
- **Mutable default** comments explain that mutable defaults persist across calls.
- **Naming** comments point back to PEP 8 `snake_case` conventions.

Again, the pipeline is designed to be robust under API failures.

### 5.4 Posting Comments to GitHub PRs

The modified file is committed on the PR branch, a pull request is opened, and the review comments are posted back to GitHub as review comments.

If inline PR review posting fails, the script falls back to a standard issue comment headed by `"Code Review Comments:"`. That fallback format is later parsed by `fetch_review_comments.py`.

### 5.5 Why This Stage Exists

This step converts raw synthetic code edits into synthetic reviewer discourse. That is critical because the retrieval corpus later includes previously accepted review comments as a knowledge source, not just rule text.

---

## 6. Stage E: Extracting Review Comments into a Review-Comment Dataset

The next script, `scripts/fetch_review_comments.py`, converts the GitHub PR discussions into a structured local JSON dataset.

### 6.1 What It Reads

For each repository, the script fetches:

- All pull requests
- Inline review comments on each PR
- Issue comments on each PR

It only keeps PRs whose branch names match the pattern `violation/<slug>-<number>`.

This means the review-comment extraction stage is intentionally aimed at the single-violation PRs, not the evaluation PRs.

### 6.2 How the Category Is Recovered

The branch slug is mapped back to one of the five categories through `BRANCH_CATEGORY_MAP`. That means the category label for each review comment is not inferred semantically after the fact. It is recovered from the controlled PR generation process.

This is one of the main reasons the synthetic strategy yields reliable labels.

### 6.3 Inline and Fallback Comment Handling

The script supports three kinds of comments:

- Inline PR review comments
- Fallback issue comments created when inline review posting failed
- General issue comments if they are long enough to be useful

Fallback issue comments are parsed with a regular expression that extracts:

- `file_path`
- `line_number`
- `comment_text`

### 6.4 Deduplication and Output Format

All collected comments are deduplicated using a tuple of:

- `text`
- `category`
- `framework`
- `file_path`
- `commit_sha`

The output is written to `data/raw/review_comments/review.json`.

Each entry contains fields such as:

- `text`
- `category`
- `source_type` (e.g., `django_review_comment`)
- `source_path` (built from repo, file path, and commit SHA)
- `chunk_id`

### 6.5 Why This Matters

This stage transforms PR discussion data into retrieval chunks that can later be retrieved just like guideline chunks. In other words, the knowledge base is not limited to formal coding rules. It also includes reviewer phrasing and examples of how humans discuss those rule violations.

---

## 7. Stage F: Merging Review Comments into the Retrieval Corpus

The notebook then merges the newly extracted review comment dataset into the existing retrieval corpus.

The merge logic:

1. Loads `data/processed/retrival_corpus.json`
2. Loads `data/raw/review_comments/review.json`
3. Removes duplicates by `chunk_id`
4. Appends the new review-comment chunks
5. Writes the merged corpus back to `retrival_corpus.json`

This produces a combined retrieval store containing both:

- Formal coding guidance
- Synthetic historical review comments

That combined corpus is later indexed and retrieved by the RAG review model.

---

## 8. Stage G: Building the Evaluation Dataset with Multi-Violation PRs

The script `scripts/create_evaluation_dataset.py` creates a harder evaluation set. This stage differs from the earlier PR generation in an important way: each eval PR may contain **multiple violation categories** in the same file.

### 8.1 Why Evaluation Is Separate

The training-style retrieval data is mostly built from single-category PRs because they make the source of each review comment easy to control and label.

The evaluation set is harder on purpose. Real code often contains overlapping issues, so the evaluation set uses violation combinations rather than one clean category per PR.

### 8.2 Predefined Violation Combinations

The script defines `VIOLATION_COMBOS`, for example:

- `[unused_import]`
- `[naming_convention]`
- `[unused_import, indentation]`
- `[naming_convention, mutable_default]`
- `[unused_import, documentation_formatting]`
- `[unused_import, indentation, naming_convention]`
- `[naming_convention, mutable_default, documentation_formatting]`

This means the evaluation data is still controlled, but it is more varied and closer to real review conditions than the single-violation PRs.

### 8.3 Source Files for Evaluation

The eval script works against the same synthetic repositories, but creates new branches named like:

- `eval/unused-import-indentation-3`

It selects a target file, loads the clean main-branch version, and then calls `inject_multi_violations()` to insert all requested categories into the same file.

### 8.4 Multi-Violation Injection

The LLM is prompted to apply every requested category to the same file and emit:

1. The complete modified file, and
2. A JSON array of violated lines, categories, and descriptions.

As with the earlier script, there is a deterministic fallback, `_fallback_multi_inject()`, which can insert combinations of unused imports, camelCase names, mutable defaults, broken docstrings, and non-4-space indentation even if the LLM fails.

### 8.5 PR Creation and Ground-Truth Review Generation

For each violation detail in the multi-violation file, the script generates a review comment. These are stored as structured ground truth instead of being posted and later scraped. Each evaluation entry contains:

- `id`
- `repo`
- `source_path`
- `source_file`
- `ground_truth_reviews`

Each `ground_truth_reviews` item includes:

- `line_number`
- `violation_category`
- `review_comment`

This is the core labeled evaluation format used later by the review pipeline.

---

## 9. Stage H: Reconstructing Eval Labels from Existing PRs When Needed

If evaluation PRs already exist and the script does not create new ones, it can rebuild evaluation data from existing GitHub PRs using `fetch_existing_eval_data()`.

This uses a rule-based detector rather than trusting old metadata. The detector scans the final file content and identifies the five target categories using heuristics.

Examples:

- **`unused_import`:** parse import lines and check whether imported names appear elsewhere.
- **`naming_convention`:** detect camelCase in function names, parameters, attributes, and variables.
- **`indentation`:** detect non-4-space block indentation while ignoring continuation contexts.
- **`mutable_default`:** detect list and dict literal defaults in function signatures.
- **`documentation_formatting`:** detect misplaced module docstrings, split one-line docstrings, and docstring indentation mismatches.

This stage exists so the evaluation dataset can be rebuilt from GitHub state even if the original in-memory generation metadata is unavailable.

---

## 10. Stage I: Writing the Evaluation Dataset to Disk

After building the evaluation entries, the script writes them to:

- `data/processed/evaluation.json`

It also saves each source file to:

- `data/processed/evaluation_files/`

Before saving, it strips giveaway comments that would make the task trivial, such as comments literally saying:

- `unused_import`
- `mutable_default`
- `renamed`
- `violation`
- `stub for`

This is an important **anti-leakage step**. The downstream model should infer the violation from code, not from explicit comments left by the synthetic pipeline.

The `source_file` field in each JSON entry is rewritten to point to the saved file inside `evaluation_files/`.

---

## 11. Stage J: Manual Augmentation of the Evaluation Set

The notebook adds one more step after automatic evaluation generation. It loads manual data from:

- `data/raw/eval_manual/evaluation.json`
- `data/raw/eval_manual/eval_files/`

It then:

1. Checks for duplicate IDs
2. Copies the manual source files into `data/processed/evaluation_files/`
3. Rewrites `source_file` paths to the processed location
4. Appends the manual entries to the generated evaluation dataset

This means the final evaluation set is not purely synthetic. It is a hybrid of:

- Automatically generated evaluation PR examples
- Manually curated framework-specific examples

That hybrid strategy improves coverage and helps counteract weaknesses in fully synthetic data.

---

## 12. Notebook Orchestration: How the Pieces Connect in Practice

The notebook `data_preprocessor.ipynb` orchestrates the full process in this order:

1. Define and export the guideline-based retrieval corpus.
2. Create synthetic repositories with clean code and single-violation PRs by running `scripts/create_synthetic_repos.py`.
3. Fetch PR review comments by running `scripts/fetch_review_comments.py`.
4. Merge those review comments into the retrieval corpus.
5. Create the evaluation dataset by running `scripts/create_evaluation_dataset.py`.
6. Merge in the manual evaluation entries.
7. Plot summary statistics for the retrieval corpus and evaluation dataset.

So the synthetic data strategy is not one script. It is a pipeline where the output of one stage becomes the input to the next.

---

## 13. Why This Strategy Is Effective

This synthetic strategy is effective for the project's stated goal because it optimizes for label control, framework context, and evaluation clarity.

### 13.1 Controlled Labels

Because the project itself inserts the violation, it knows the intended category. That is more reliable than inferring labels from noisy real-world PRs.

### 13.2 Framework-Aware Context

The synthetic repos are framework-specific, so the downstream RAG system can retrieve both generic Python guidance and framework-specific conventions.

### 13.3 Review-Language Grounding

The pipeline does not stop at generating bad code. It also generates PR review comments and feeds them back into the retrieval corpus. That gives the final system access to both rules and reviewer phrasing.

### 13.4 Robustness to LLM Failure

Every critical LLM-dependent stage has deterministic fallbacks:

- Code generation fallback stubs
- Deterministic violation injection
- Deterministic review comment templates
- Heuristic reconstruction for evaluation labels

This makes the dataset generation process reproducible enough to rerun even when model calls fail intermittently.

### 13.5 Harder Evaluation Than Training Data

Single-violation PRs make the knowledge base clean and easy to label. Multi-violation evaluation PRs make the final benchmark harder and more realistic. That split is a good experimental design choice.

---

## 14. Important Limitations and Design Tradeoffs

The strategy is strong, but it is not perfect.

### 14.1 Synthetic Bias

Because both the code changes and many of the review comments are LLM-generated, the final dataset may reflect the style preferences of the prompting setup.

### 14.2 Limited Realism of Some Injected Errors

Some injected issues, especially indentation or docstring formatting errors, may look more artificial than naturally occurring review problems.

### 14.3 GitHub-State Dependence

Part of the pipeline depends on GitHub repository state, PR existence, branch names, and successful API calls. Reproducibility depends on that state being stable.

### 14.4 Evaluation Repos Are Logically Separate, Not Physically Separate Repos

The evaluation set uses `eval/*` branches inside the same synthetic repositories, not entirely different repositories. The project mitigates this by keeping eval examples out of the review-comment extraction flow, but the split is branch-based rather than repo-based.

### 14.5 Some Fields Contain Generated Descriptions Rather Than True Human Reviews

When evaluation data is reconstructed from existing PRs, the fallback detector may populate `ground_truth_reviews` with rule descriptions instead of human-like PR comments. That is useful structurally, but not identical to authentic review language.

---

## 15. Final Summary

End to end, the synthetic data generation strategy works like this:

1. Build a retrieval corpus from authoritative coding-guideline chunks.
2. Create realistic clean Python repositories for five frameworks.
3. Introduce controlled single-category violations in PR branches.
4. Generate reviewer-style comments for those violations and post them to PRs.
5. Scrape those PR comments back into a structured review-comment dataset.
6. Merge the comments into the retrieval corpus so the RAG system can retrieve both formal rules and reviewer phrasing.
7. Build a separate evaluation dataset using harder multi-violation files.
8. Save the evaluation examples as file snapshots plus structured ground-truth review annotations.
9. Augment the evaluation set with manual examples.

The result is a controlled synthetic ecosystem designed specifically for the project's research question: **whether retrieved project-specific knowledge helps an LLM generate better Python code review comments for localized guideline violations**.

---

# Part 2 - Retrieval Strategy Analysis

# Retrieval Strategy Analysis

> **Evaluation**: 102 files, 721 ground-truth reviews across 5 violation categories.
> **Corpus**: 505 FAISS-indexed chunks (BAAI/bge-large-en-v1.5, 1024-dim, IndexFlatIP).
> **Top-k**: 10 chunks per file.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Evaluation Metrics](#2-evaluation-metrics)
3. [Diagnostic Analysis](#3-diagnostic-analysis)
4. [Strategies - Baseline (S1-S6)](#4-strategies---baseline-s1-s6)
5. [Strategies - Improved (S7-S16)](#5-strategies---improved-s7-s16)
6. [Full Results Table](#6-full-results-table)
7. [Per-Category Recall Breakdown](#7-per-category-recall-breakdown)
8. [What Worked and Why](#8-what-worked-and-why)
9. [What Didn't Work and Why](#9-what-didnt-work-and-why)
10. [Production Recommendation](#10-production-recommendation)

---

## 1. Problem Statement

In production, our RAG pipeline receives a **code diff** and must retrieve the most relevant guideline/review chunks from the corpus to support an LLM in detecting violations. At retrieval time, we know:

- The code diff (full source)
- The 5 violation categories we care about
- Optionally, the repo framework (django, flask, fastapi, pandas, sklearn)

We do **not** know which violations are actually present - that's what the LLM will decide. The retrieval strategy must provide high-quality context without ground-truth hints.

### Corpus Structure

| Source Type | Count | Examples |
|---|---|---|
| Review comments (repo-specific) | 289 | `django_review_comment`, `flask_review_comment` |
| General linter rules | 128 | `ruff`, `flake8`, `pylint`, `pep8`, `pep257` |
| Repo guidelines | 88 | `django_guidelines`, `pandas_guidelines` |

| Category | Chunks | % of Corpus |
|---|---|---|
| documentation_formatting | 155 | 30.7% |
| naming_convention | 107 | 21.2% |
| indentation | 90 | 17.8% |
| unused_import | 81 | 16.0% |
| mutable_default | 72 | 14.3% |

### Evaluation Set

| Category | Violation Count | File Count |
|---|---|---|
| naming_convention | 214 | 54 |
| unused_import | 193 | 63 |
| indentation | 138 | 27 |
| documentation_formatting | 104 | 27 |
| mutable_default | 72 | 26 |

- **Average GT categories per file**: 1.9
- **Files with only 1 GT category**: 41 (40%)
- **Files with 2 GT categories**: 31 (30%)
- **Files with 3+ GT categories**: 30 (30%)

---

## 2. Evaluation Metrics

| Metric | Definition |
|---|---|
| **Precision** | `relevant_retrieved / total_retrieved` - fraction of retrieved chunks whose category matches a GT violation in the file |
| **Category Recall** | For each GT category in a file, is at least one chunk of that category in the top-10? Averaged across all (file, category) pairs, then across all 5 categories |
| **MRR (Mean Reciprocal Rank)** | For each (file, GT category), find the rank of the first matching chunk. MRR = average of `1/rank` across all such pairs. Higher -> relevant chunks appear earlier |
| **F1** | Harmonic mean of Precision and Avg Category Recall |

---

## 3. Diagnostic Analysis

Before designing improved strategies, we ran diagnostics to identify failure modes.

### Finding 1: Blind Retrieval Wastes 60%+ Budget

The biggest precision killer: when we retrieve 2 chunks per category for all 5 categories (as in S2), but the file only has 1-2 GT categories, the majority of slots are wasted.

**Example** - file `synthetic-django_PR_21` has GT = `{unused_import}` only:
- S2 retrieves: `unused_import(2), indentation(2), naming_convention(2), doc_formatting(2), mutable_default(2)`
- Precision: 2/10 = **20%** - 80% of budget wasted on irrelevant categories

This pattern affects 41 files (40% of dataset) that have only 1 GT category.

### Finding 2: Tiny Score Gap Between Relevant and Irrelevant

```
Relevant chunks:   mean_score = 0.739
Irrelevant chunks: mean_score = 0.709
Score gap:         0.030
```

The embedding model can't clearly separate relevant vs irrelevant chunks by score alone. Simple score thresholding won't help - we need category-level intelligence.

### Finding 3: doc_formatting <-> indentation Cross-Confusion

Queries like "documentation_formatting violation in Python code" return indentation chunks at positions 3-4 because docstring indentation issues are semantically close to general indentation. The score 0.731 for indentation chunks is very close to 0.743 for actual doc_formatting chunks.

### Finding 4: Repo Hint Doesn't Filter at Embedding Level

Adding "django" or "fastapi" to queries does not reliably return chunks from that repo's source type. Embedding similarity doesn't capture metadata-level filtering.

### Finding 5: Category Prediction from Code is Feasible

Simple regex heuristics can predict categories with useful precision:

| Category | Heuristic Precision | Heuristic Recall |
|---|---|---|
| unused_import | 62% | 100% |
| naming_convention | 53% | 94% |
| indentation | 27% | 96% |
| documentation_formatting | 26% | 100% |
| mutable_default | 27% | 100% |

Precision is low (many false positives), but **recall is near-perfect** - heuristics almost never miss a real category. This makes them safe for budget allocation: filter down from 5 to 2-3 categories without losing coverage.

---

## 4. Strategies - Baseline (S1-S6)

### S1: Code Only

**Approach**: Use the first 500 characters of raw code as the FAISS query.

```python
retrieve(code[:500], top_k=10)
```

**Hypothesis**: Code snippets will semantically match guideline chunks that discuss similar patterns.

**Result**: P=44.1%, R=73.1%, MRR=0.375, F1=0.550

**Why it partially works**: When code has obvious patterns (e.g., `import os` at top), the embedding finds import-related chunks. But code syntax doesn't reliably match natural-language guidelines.

**Why it fails**: 73.1% recall - misses categories whose violations aren't syntactically obvious in the first 500 chars. Indentation violations (59.3% recall) and unused_import (60.3%) are particularly missed.

---

### S2: Per-Category (Uniform)

**Approach**: One query per category (`"unused_import violation in Python code"`), 2 results each, merge to 10.

```python
for cat in CATEGORIES:
    q = f"{cat} violation in Python code"
    hits = retrieve(q, top_k=2)
    results.extend(hits)
```

**Hypothesis**: Category-specific queries will each retrieve on-target chunks.

**Result**: P=38.6%, R=100.0%, MRR=0.455, F1=0.557

**Why it works**: Each category query returns chunks of that category with high fidelity (except doc_formatting, which sometimes pulls indentation). 100% recall - every GT category gets at least one matching chunk.

**Why precision is low**: For a file with 1 GT category, 8/10 slots are wasted on the other 4 categories. The average 1.9 categories/file makes uniform allocation fundamentally wasteful.

---

### S3: Code + Category

**Approach**: Combine code prefix (200 chars) with each category name.

```python
for cat in CATEGORIES:
    q = f"Code review for {cat} violation: {code[:200]}"
    hits = retrieve(q, top_k=2)
```

**Result**: P=42.0%, R=92.3%, MRR=0.458, F1=0.577

**Why it partially works**: Code context steers the embedding slightly toward relevant chunks. Best MRR of baseline strategies (0.458).

**Why it fails**: Recall drops to 92.3% because code context can interfere with category matching - for rare categories (indentation 88.9%, doc_formatting 77.8%), the code prefix dominates the query embedding and dilutes the category signal.

---

### S4: Repo + Category

**Approach**: Query with repo framework name + category.

```python
q = f"{repo_hint} {cat} code review guidelines and best practices"
```

**Result**: P=38.3%, R=100.0%, MRR=0.453, F1=0.554

**Why it works**: Similar to S2 with 100% recall. Repo hint provides slight context.

**Why precision is same as S2**: As diagnosed, the embedding model doesn't effectively filter by repo metadata. "django unused_import" and "fastapi unused_import" return the same chunks.

---

### S5: Hybrid (Code + Category)

**Approach**: Half budget for code-based retrieval, half for repo+category.

```python
code_hits = retrieve(code[:500], top_k=5)
for cat in CATEGORIES:
    hits = retrieve(f"{repo_hint} {cat} ...", top_k=1)
```

**Result**: P=45.7%, R=81.2%, MRR=0.397, F1=0.585

**Why precision is decent**: Code-based half naturally focuses on present patterns. 45.7% is the best precision among baselines.

**Why recall drops**: Only 1 slot per category in the category half -> doc_formatting (48.1%) and mutable_default (57.7%) are squeezed out since code-based retrieval favors common categories.

---

### S6: Code + Repo + Category (Keyword-Heavy)

**Approach**: Hand-crafted keyword-rich queries per category with repo hint.

```python
# Example for mutable_default:
q = f"{repo_hint} mutable default argument list dict set function parameter"
```

**Result**: P=37.6%, R=100.0%, MRR=0.450, F1=0.547

**Why it doesn't improve**: Despite more specific keywords, the uniform 2-per-category budget still wastes slots. And code-specific import analysis (like S6 does for unused_import) adds noise rather than precision.

---

## 5. Strategies - Improved (S7-S16)

These strategies were designed based on the diagnostic findings above.

### S7: Heuristic Filtering

**Approach**: Predict which categories are likely present using code regex heuristics. Only retrieve for categories with confidence >= 1.

```python
preds = predict_categories(code)
active_cats = [c for c, s in preds.items() if s >= 1]
per_cat_k = max(2, top_k // len(active_cats))
for cat in active_cats:
    q = f"{cat} violation in Python code"
    retrieve(q, top_k=per_cat_k)
```

**Heuristics used**:
- **unused_import**: Check if imported names appear in the rest of the code body
- **naming_convention**: Detect camelCase functions, lowercase class names, camelCase variables
- **indentation**: Detect mixed tabs/spaces, non-multiple-of-4 indent levels
- **documentation_formatting**: Check for docstring presence and formatting issues
- **mutable_default**: Regex match `def foo(x=[], y={}, z=set())` patterns

**Result**: P=45.4%, R=100.0%, MRR=0.473, F1=0.624

**Why it works well**: By filtering from 5 to ~3 active categories, budget per category increases from 2 to ~3. This eliminates wasted slots. 100% recall maintained because heuristics have near-100% recall.

**Improvement**: +7pp precision, +18pp MRR, +7pp F1 over S2 baseline.

---

### S8: Adaptive Budget

**Approach**: Like S7, but allocate budget *proportionally* to confidence: high=3 slots, medium=2, low=1, zero=0.

```python
budget = {cat: {3:3, 2:2, 1:1, 0:0}[conf] for cat, conf in preds.items()}
```

**Result**: P=57.9%, R=99.2%, MRR=0.497, F1=0.732

**Why it's much better**: High-confidence categories (the ones that usually are actually present) get 3 slots. Zero-confidence categories get nothing. Budget directly tracks reality.

**Why recall is 99.2% not 100%**: mutable_default drops to 96.2% - in 1 file, the heuristic assigns confidence 0 and no slots. Acceptable tradeoff.

---

### S9: Two-Phase (Code -> Category)

**Approach**: Phase 1 - retrieve by code to detect categories. Phase 2 - per-category retrieval for detected + heuristic categories.

**Result**: P=47.1%, R=75.8%, MRR=0.372, F1=0.581

**Why it failed**: Phase 1 code retrieval is unreliable for category detection (S1 only gets 73% recall). The two-phase approach inherits S1's weakness and doesn't improve on simpler heuristics.

---

### S10: Refined Queries

**Approach**: Replace generic `"unused_import violation in Python code"` with keyword-rich queries:

```python
REFINED_QUERIES = {
    "unused_import":             "unused import module not used remove F401 W0611",
    "indentation":               "indentation whitespace spaces tabs alignment PEP8 E1 W1",
    "naming_convention":         "naming convention snake_case CamelCase PEP8 variable function class name",
    "documentation_formatting":  "docstring formatting summary description numpy google style pep257 D100 D200",
    "mutable_default":           "mutable default argument list dict set function parameter B006 W0102",
}
```

**Result**: P=38.6%, R=100.0%, MRR=0.455, F1=0.557

**Why the same as S2**: With uniform 2-per-category budget, refined queries don't help precision - the bottleneck is budget allocation, not query quality. The queries are better (less cross-category confusion), but the improvement only shows when combined with other techniques.

---

### S11: Refined + Heuristic

**Approach**: Combine S10's queries with S7's heuristic filtering.

**Result**: P=45.4%, R=100.0%, MRR=0.473, F1=0.624

**Same as S7**: The heuristic filtering dominates. Refined queries have marginal impact when the budget is already well-allocated.

---

### S12: Score Reranking

**Approach**: Overfetch (4 per category for all 5), then rerank by boosting chunks whose category matches high-confidence predictions.

```python
boost = {3: +0.10, 2: +0.05, 1: +0.02, 0: -0.05}[confidence]
rerank_score = faiss_score + boost
```

**Result**: P=60.1%, R=88.1%, MRR=0.555, F1=0.715

**Why MRR is excellent**: Reranking pushes relevant category chunks to top positions. MRR jumps from 0.455 to 0.555 - relevant context appears ~2 positions earlier on average.

**Why recall drops**: With only 10 final slots, suppressing low-confidence category chunks can push them entirely out. Indentation drops to 55.6% recall - the heuristic often assigns low confidence to indentation (it's hard to detect from regex), so it gets demoted below the top-10 cutoff.

---

### S13: Adaptive + Refined + Repo

**Approach**: S7's filtering + S10's refined queries + S6's repo-aware queries.

**Result**: P=45.4%, R=100.0%, MRR=0.473, F1=0.624

**Same as S7/S11**: Repo hint adds no value (Finding 4). Three-way combination doesn't exceed any component.

---

### S14: Adaptive Budget + Reranking

**Approach**: S8's budget allocation + S12's reranking.

```python
budget: high=4, med=3, low=2, zero=1
boost: {3: 0.12, 2: 0.06, 1: 0.02, 0: -0.03}
```

**Result**: P=56.4%, R=92.6%, MRR=0.573, F1=0.701

**Why it's strong**: Combines S8's precision gains with S12's MRR gains. Budget ensures good coverage, reranking optimizes ordering.

**Why recall drops slightly**: min 1 slot for zero-confidence categories, but reranking can still push those chunks below rank 10. Indentation at 63.0%.

---

### S15: Adaptive + Reranking + Refined Queries (This is what we went with)

**Approach**: Triple combination - S8's adaptive budget + S12's reranking + S10's refined queries.

```python
# 1. Predict categories from code
preds = predict_categories(code)

# 2. Adaptive budget
budget = {3:4, 2:3, 1:2, 0:1}[confidence]

# 3. Retrieve with refined queries
for cat, k in budget.items():
    q = REFINED_QUERIES[cat]
    retrieve(q, top_k=k)

# 4. Rerank by heuristic confidence
rerank_score = faiss_score + {3:0.12, 2:0.06, 1:0.02, 0:-0.03}[conf]
```

**Result**: **P=59.6%, R=96.3%, MRR=0.625, F1=0.736**

**Why this is the best**:
- Refined queries fix doc<->indentation confusion, improving per-query precision
- Adaptive budget focuses slots on likely categories, eliminating waste
- Reranking pushes the most relevant chunks to the top, maximizing MRR
- The three techniques are *complementary* - each addresses a different failure mode

**Per-category recall**: unused_import 100%, indentation 92.6%, naming_convention 100%, doc_formatting 88.9%, mutable_default 100%.

---

### S16: Reranking + Guarantee

**Approach**: Like S12 but reserves 1 slot per category before reranking to guarantee recall.

```python
# Reserve best chunk per category first
for cat in CATEGORIES:
    results.append(best_per_cat[cat])
# Fill remaining 5 slots from reranked list
```

**Result**: P=55.5%, R=100.0%, MRR=0.540, F1=0.714

**Why recall is perfect**: Hard guarantee of 1 chunk per category. No category can be squeezed out.

**Why precision/MRR are lower than S15**: The 5 guaranteed slots include zero-confidence categories, reducing both precision and MRR compared to the adaptive approach.

---

## 6. Full Results Table

| Strategy | Precision | Cat Recall | MRR | F1 | Key Technique |
|---|---|---|---|---|---|
| S1_code_only | 44.1% | 73.1% | 0.375 | 0.550 | Raw code as query |
| S2_per_category | 38.6% | 100.0% | 0.455 | 0.557 | 1 query per category, 2 each |
| S3_code_plus_category | 42.0% | 92.3% | 0.458 | 0.577 | Code prefix + category |
| S4_repo_category | 38.3% | 100.0% | 0.453 | 0.554 | Repo + category keywords |
| S5_hybrid | 45.7% | 81.2% | 0.397 | 0.585 | Half code + half category |
| S6_code_repo_category | 37.6% | 100.0% | 0.450 | 0.547 | Code + repo + category |
| S7_heuristic_filter | 45.4% | 100.0% | 0.473 | 0.624 | Filter by predicted cats |
| **S8_adaptive_budget** | **57.9%** | 99.2% | 0.497 | **0.732** | Budget ∝ confidence |
| S9_two_phase | 47.1% | 75.8% | 0.372 | 0.581 | Code detect -> category |
| S10_refined_queries | 38.6% | 100.0% | 0.455 | 0.557 | Keyword-rich queries |
| S11_refined_heuristic | 45.4% | 100.0% | 0.473 | 0.624 | Refined + filter |
| **S12_score_rerank** | **60.1%** | 88.1% | 0.555 | 0.715 | Overfetch + heuristic rerank |
| S13_adapt_refined_repo | 45.4% | 100.0% | 0.473 | 0.624 | Filter + refined + repo |
| S14_adapt_rerank | 56.4% | 92.6% | 0.573 | 0.701 | Adaptive + rerank |
| ⭐ **S15_adapt_rerank_refined** | **59.6%** | **96.3%** | **0.625** | **0.736** | **Adaptive + rerank + refined** |
| S16_rerank_guarantee | 55.5% | 100.0% | 0.540 | 0.714 | Rerank + guaranteed slots |

---

## 7. Per-Category Recall Breakdown

| Strategy | unused_import | indentation | naming_conv | doc_format | mutable_def |
|---|---|---|---|---|---|
| S1_code_only | 60.3% | 59.3% | 94.4% | 66.7% | 84.6% |
| S2_per_category | 100% | 100% | 100% | 100% | 100% |
| S5_hybrid | 100% | 100% | 100% | 48.1% | 57.7% |
| S7_heuristic_filter | 100% | 100% | 100% | 100% | 100% |
| S8_adaptive_budget | 100% | 100% | 100% | 100% | 96.2% |
| S12_score_rerank | 100% | **55.6%** | 100% | 85.2% | 100% |
| ⭐ S15 | 100% | **92.6%** | 100% | 88.9% | 100% |
| S16_rerank_guarantee | 100% | 100% | 100% | 100% | 100% |

**Indentation** and **documentation_formatting** are the hardest categories for reranking strategies because:
- Indentation heuristic has low confidence accuracy (27% precision)
- doc_formatting <-> indentation semantic overlap causes confusion

---

## 8. What Worked and Why

### 1. Heuristic Category Prediction (+7pp precision)

Lightweight regex inspection of code to predict likely violation categories. The key insight: even crude heuristics with 27% precision but 96-100% recall are extremely useful for **budget allocation** - they safely eliminate 2-3 categories per file, freeing slots for predicted ones.

### 2. Confidence-Weighted Budget Allocation (+19pp precision over S2)

Instead of uniform 2 chunks per category, allocating 4/3/2/1/0 slots based on confidence matches real-world distributions. A file with clear `=[]` patterns gets 4 mutable_default slots; a file with no function definitions gets 0 mutable_default slots.

### 3. Heuristic Reranking (+0.17 MRR over S2)

After retrieval, boosting FAISS scores for chunks whose category matches high-confidence predictions pushes relevant chunks 2-3 positions higher. This is cheap (no re-embedding) and highly effective.

### 4. Refined Queries (+0.02 MRR, reduces cross-confusion)

Including linter rule codes (`F401`, `D200`, `B006`) and specific terminology in queries reduces semantic overlap between categories. Most impactful for doc_formatting <-> indentation disambiguation.

### 5. Triple Combination (S15: all three together)

The three techniques are complementary:
- Budget allocation solves **precision waste** (the #1 problem)
- Reranking solves **MRR/ordering** (relevant chunks appear first)
- Refined queries solve **cross-category confusion** (doc <-> indent)

No single technique alone achieves F1 > 0.63. Together: **0.736**.

---

## 9. What Didn't Work and Why

### 1. Raw Code as Query (S1, S9)

Code syntax doesn't align well with natural-language guideline chunks in embedding space. The model was trained for semantic similarity, not code-to-guideline matching.

### 2. Repo Hint in Queries (S4, S6, S13)

Adding "django" or "fastapi" to queries doesn't filter results by repo source type. The embedding model treats these as general context words, not metadata filters. To leverage repo information, we'd need explicit metadata filtering (e.g., FAISS post-filter by source_repo).

### 3. Two-Phase Detection (S9)

Using Phase 1 code retrieval to *detect* categories, then Phase 2 per-category retrieval for only detected ones. Failed because Phase 1 category detection accuracy is only ~73% - worse than simple regex heuristics (96-100% recall).

### 4. Refined Queries Alone (S10)

Better queries don't help when the budget allocation is wasteful. Uniform 2-per-category with refined queries = same as uniform 2-per-category with generic queries. The bottleneck is allocation, not query quality.

### 5. Guarantee Slots (S16) vs Adaptive (S15)

Reserving 1 hard slot per category ensures 100% recall but wastes 1-3 slots on zero-confidence categories, costing ~4pp precision and ~0.08 MRR compared to the adaptive approach.

---

## 10. Production Recommendation

### Selected: Strategy S15 (Adaptive + Rerank + Refined)

| Metric | S2 Baseline | S15 Final | Δ Relative |
|---|---|---|---|
| Precision | 38.6% | 59.6% | **+54%** |
| Category Recall | 100.0% | 96.3% | -3.7% |
| MRR | 0.455 | 0.625 | **+37%** |
| F1 | 0.557 | 0.736 | **+32%** |

**Why S15 over S16 (100% recall)**:

The 3.7% recall loss in S15 (from 100% -> 96.3%) affects only indentation (92.6%) and doc_formatting (88.9%). These 2 categories are:
1. The ones with highest semantic overlap (hardest to retrieve correctly anyway)
2. Less critical than unused_import and mutable_default (which are functional bugs)

The tradeoff - gaining +4pp precision and +0.085 MRR - is worth it because:
- Higher precision = less noise for the LLM = fewer hallucinated violations
- Higher MRR = important context appears first in the prompt = better LLM performance

**Implementation**: Integrated into `scripts/retrieve.py` as `retrieve_with_context(code, top_k)`.

```python
from retrieve import retrieve_with_context

# In the RAG pipeline:
chunks = retrieve_with_context(code_diff, top_k=10)
# chunks are reranked - most relevant appear first
```

**CLI usage**:
```bash
# S15 production mode:
python scripts/retrieve.py code path/to/file.py -k 10

# Basic single-query mode (still available):
python scripts/retrieve.py query "unused import" -k 5
```

---

# Part 3 - Static Analysis Tool Evaluation

# Static Analysis Tool Evaluation

This document describes how static analysis tools are used as the baseline violation detector in the pipeline, what each tool covers, where the gaps are, how extensions fill those gaps, and how tool detections are compared against evaluation ground truth.

---

## 1. Tools Used

Two standard Python linters form the static analysis backbone:

| Tool | Purpose | Key Plugins |
|------|---------|-------------|
| **Flake8** | Fast style and import checker | `pycodestyle` (E/W), `pyflakes` (F), `pep8-naming` (N8xx), `flake8-bugbear` (B), `flake8-docstrings` (D) |
| **Pylint** | Deep semantic linter | Built-in checkers for naming, imports, docstrings, dangerous defaults |

Both tools are run on every evaluation file. Their outputs are merged by `(category, line)` to remove duplicates where both tools flag the same issue.

---

## 2. Violation Category Coverage

Each tool's error codes are mapped to one of the five target categories:

### 2.1 Flake8 Code Mapping

| Category | Flake8 Codes | Source Plugin |
|----------|-------------|---------------|
| `indentation` | E101, E111-E133, W191 | pycodestyle |
| `naming_convention` | N801-N818 | pep8-naming |
| `unused_import` | F401 | pyflakes |
| `mutable_default` | B006, B008 | flake8-bugbear |
| `documentation_formatting` | D100-D499 | flake8-docstrings (pydocstyle) |

### 2.2 Pylint Code Mapping

| Category | Pylint Codes / Symbols |
|----------|----------------------|
| `indentation` | W0311 (`bad-indentation`) |
| `naming_convention` | C0103 (`invalid-name`), C0104, C0105, C0132, C2401, W3201 |
| `unused_import` | W0611 (`unused-import`), W0614, W0404, W0406 |
| `mutable_default` | W0102 (`dangerous-default-value`) |
| `documentation_formatting` | C0114-C0116 (`missing-*-docstring`), C0112 (`empty-docstring`), C0199 |

### 2.3 Detection Results on the Evaluation Set

Running both tools on 103 evaluation files produces **1,269 total detections**:

| Category | Detections |
|----------|-----------|
| `indentation` | 404 |
| `naming_convention` | 338 |
| `documentation_formatting` | 271 |
| `unused_import` | 167 |
| `mutable_default` | 89 |

---

## 3. Per-Category Limitations and Gaps

### 3.1 `mutable_default` - Full Coverage (100%)

Both flake8-bugbear (`B006`) and pylint (`W0102`) reliably detect `=[]`, `={}`, and `=set()` in function signatures. Every ground-truth mutable default violation is caught with an exact file + category + line match. **No gaps**.

### 3.2 `naming_convention` - Strong Coverage (94.9%)

Flake8 `pep8-naming` catches camelCase function names, arguments, and variables. Pylint `C0103` adds coverage for shorter names and class attributes. The 5.1% miss comes from:

- **Variable assignments** inside function bodies where `camelCase` is used but the variable is not a function-level name (some tools only flag definitions, not assignments).
- **Attribute names** on instances that neither tool flags reliably.

Category-level matching (same file, same category, different line) recovers 7 additional matches, bringing effective match rate to ~95%.

### 3.3 `unused_import` - Good Coverage (86.0%)

Pyflakes `F401` and pylint `W0611` detect most unused imports. The 14% miss comes from:

- **Framework-level imports with side effects** (e.g., Django signal handlers or Flask extensions where the import is unused in the local file but loads a module).
- **Wildcard re-exports** where flake8/pylint cannot confirm usage across modules.
- **Conditional or `TYPE_CHECKING`-guarded imports** that confuse static analysis.

### 3.4 `indentation` - Moderate Coverage (76.1%)

Flake8 pycodestyle `E1xx` and pylint `W0311` detect non-4-space indentation and mixed tabs/spaces. The 23.9% miss comes from:

- **Syntax-breaking indentation** - some injected violations produce unparseable files. When `compile()` fails, flake8/pylint refuse to run at all, producing zero detections for the entire file.
- **Continuation-line indentation** that the tools accept as valid alignment style even when the ground truth considers it a violation.
- **2-space or 6-space indentation applied consistently** - some linter configurations accept non-4-space indentation if it is internally consistent.

### 3.5 `documentation_formatting` - Weak Coverage (31.7%)

This is the largest gap. Flake8 `pydocstyle` (D-codes) and pylint `C011x` detect missing docstrings and some formatting issues, but they cannot detect:

- **Docstring indentation mismatches** - the GT frequently flags "Docstring indentation doesn't match block," which no standard tool checks.
- **Framework-specific docstring conventions** - Django test preamble conventions ("Tests that..." is discouraged), pandas NumPy-style parameter formatting, sklearn docstring standards.
- **Semantic docstring quality** - whether a docstring accurately describes the function, uses the correct section headers, or follows Google vs NumPy style.
- **Split one-line docstrings** - malformed multi-line versions of what should be a single-line docstring.

---

## 4. Extensions to Fill the Gaps

The pipeline does **not** attempt to add more static tools to fill the `documentation_formatting` gap. Instead, the system relies on:

1. **RAG retrieval** - the retrieval corpus contains both formal docstring guidelines (PEP 257, framework-specific conventions) and synthetic review comments about docstring issues. The LLM can use retrieved context to generate review comments about docstring problems that no static tool would flag.

2. **LLM inference** - the final code review model receives the code and retrieved context, and can detect semantic docstring issues (wrong style, missing sections, preamble usage) that are inherently beyond the scope of rule-based tools.

3. **Heuristic category prediction** - the `predict_categories()` function in `retrieve.py` uses regex-based heuristics to detect potential `documentation_formatting` issues (missing docstrings, indentation mismatches, split one-liners) and boosts retrieval budget for that category accordingly.

This is a deliberate design choice: static tools provide a high-confidence baseline for the four "structural" categories, while the RAG + LLM pipeline handles the "semantic" documentation category where tools fail.

---

## 5. Ground Truth Comparison Strategy

### 5.1 Three-Tier Matching

The comparison between static tool detections and evaluation ground truth uses a three-tier matching strategy, applied in order of decreasing strictness:

**Tier 1 - Exact Match (file + category + line)**

A static detection matches a GT review if both share the same filename, violation category, and line number. This is the strictest and most reliable match.

**Tier 2 - Semantic Match (documentation_formatting only)**

For `documentation_formatting` violations that fail exact match, the system uses embedding-based semantic similarity. Both the GT `review_comment` and every static tool `message` in the same file (with category `documentation_formatting`) are encoded with the `BAAI/bge-large-en-v1.5` model. The best cosine similarity between the GT text and any static message is computed. If it exceeds the threshold, the pair is considered matched.

This tier exists because documentation violations often appear at different lines (a static tool might flag line 1 for a module-level docstring issue, while the GT flags line 23 for indentation inside the same docstring) but describe the same underlying problem.

**Tier 3 - Category Match (same file + same category, any line)**

For non-documentation violations that fail exact match, if the static tool found *any* violation of the same category in the same file, it counts as a category-level match. This handles cases where the GT and tool disagree on the exact line but agree on the issue.

### 5.2 Metrics

| Metric | Definition |
|--------|-----------|
| Exact match | GT violations matched at file + category + line |
| Semantic match | doc_formatting violations matched by embedding similarity |
| Category match | Non-doc violations matched at file + category (any line) |
| False negative (miss) | GT violations not matched by any tier |
| False positive (extra) | Static detections with no corresponding GT violation |

### 5.3 Results Summary

| Category | GT | Exact | Semantic | CatMatch | Miss | Match Rate |
|----------|-----|-------|----------|----------|------|-----------|
| `mutable_default` | 72 | 72 | 0 | 0 | 0 | **100.0%** |
| `naming_convention` | 214 | 196 | 0 | 7 | 11 | **94.9%** |
| `unused_import` | 193 | 166 | 0 | 0 | 27 | **86.0%** |
| `indentation` | 138 | 105 | 0 | 0 | 33 | **76.1%** |
| `documentation_formatting` | 104 | 33 | 0 | 0 | 71 | **31.7%** |
| **Total** | **721** | **572** | **0** | **7** | **142** | **80.3%** |

Overall: **579 / 721** GT violations matched (80.3%), with **728 false positives** (static detections that have no GT counterpart).

---

## 6. Empirical Threshold Selection for Semantic Matching

### 6.1 Methodology

The semantic similarity threshold for `documentation_formatting` matching was determined empirically using a dedicated threshold sweep:

1. Collected all 77 GT `documentation_formatting` violations that have at least one static `documentation_formatting` detection in the same file.
2. For each pair, computed the best cosine similarity between the GT `review_comment` embedding and all static tool message embeddings in the same file.
3. Tested thresholds from 0.30 to 0.80 and measured the match rate at each.

### 6.2 Threshold Sweep Results

| Threshold | Matched | Missed | Total | Rate |
|-----------|---------|--------|-------|------|
| 0.30 | 77 | 0 | 77 | 100.0% |
| 0.45 | 77 | 0 | 77 | 100.0% |
| 0.55 | 77 | 0 | 77 | 100.0% |
| 0.60 | 76 | 1 | 77 | 98.7% |
| 0.65 | 66 | 11 | 77 | 85.7% |
| 0.70 | 57 | 20 | 77 | 74.0% |
| 0.75 | 54 | 23 | 77 | 70.1% |
| 0.80 | 2 | 75 | 77 | 2.6% |

### 6.3 Similarity Distribution

| Statistic | Value |
|-----------|-------|
| Min (p0) | 0.5804 |
| p25 | 0.6980 |
| Median (p50) | 0.7904 |
| p75 | 0.7904 |
| Mean | 0.7529 |
| Std | 0.0656 |
| Max (p100) | 0.8365 |

### 6.4 Threshold Choice

The threshold is set at **0.80** (`DOC_SIM_THRESHOLD`). This is a conservative choice that prioritizes precision over recall in the semantic matching tier:

- At 0.80, only 2/77 pairs match - this means the semantic tier is essentially inactive, and the comparison is dominated by exact and category-level matching.
- The distribution clusters around 0.75-0.79 (median 0.79), meaning most GT-static pairs are semantically related but fall just below the strict threshold.
- The reasoning: a lower threshold (e.g., 0.65) would match more pairs but risks conflating genuinely different issues (e.g., "missing docstring" vs. "docstring indentation mismatch"). In the evaluation context, it is better to honestly report what static tools miss rather than inflate their coverage through loose matching.

The key takeway is that **documentation_formatting is the category where static tools fundamentally fall short**, and the semantic matching analysis confirms this quantitatively rather than just asserting it.

---

## 7. Key Takeaways

1. **Static tools cover 80.3% of GT violations overall** - strong for 4/5 categories.
2. **`documentation_formatting` is the clear weak point** at 31.7% - this is where RAG + LLM adds the most value.
3. **`mutable_default` is fully solved** by existing tools (100% match rate).
4. **False positives are high** (728 extra detections) - static tools are noisy. The pipeline's job is not just to detect violations but to generate contextual, human-like review comments, which static tools cannot do.
5. **The three-tier matching strategy** (exact -> semantic -> category) provides a fair comparison that accounts for line-number disagreements without inflating accuracy.

---

# Part 4 - Prompt Engineering & Model Evaluation

# Prompt Engineering & Model Evaluation

> **Evaluation**: 1 PR (synthetic-django_PR_21), 3 ground-truth violations (all `unused_import` on lines 9, 10, 11).
> **Models tested**: 7 local Ollama models (see §2).
> **Prompt configurations**: 72 (64 single-issue + 8 multi-issue).
> **Metrics**: Exact match (line + category), Category-F1 (precision / recall / F1), valid-JSON rate.
> **Script**: `scripts/evaluate_prompts.py` - reproduces all results.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Models Evaluated](#2-models-evaluated)
3. [Prompt Design Space](#3-prompt-design-space)
4. [Evaluation Metrics](#4-evaluation-metrics)
5. [Per-Model Results](#5-per-model-results)
6. [Strategy Comparison - Minimal vs CoT](#6-strategy-comparison---minimal-vs-cot)
7. [Mode Comparison - LLM vs RAG](#7-mode-comparison---llm-vs-rag)
8. [Detection Type - Single vs Multi](#8-detection-type---single-vs-multi)
9. [Hint Effectiveness](#9-hint-effectiveness)
10. [Best Config Per Model](#10-best-config-per-model)
11. [What Worked](#11-what-worked)
12. [What Failed](#12-what-failed)
13. [Final Selection - Top 2 Models](#13-final-selection---top-2-models)
14. [Final Selection - Top 3 Prompts](#14-final-selection---top-3-prompts)
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
| gemma4:latest | - | 25,522ms | Google latest-gen |
| llama3.1:8b | 8B | 4,742ms | Meta general-purpose, fastest |
| deepseek-coder:6.7b | 6.7B | 8,230ms | Code-specialised |
| codellama:7b-instruct | 7B | 7,799ms | Meta code-instruct |
| mistral:7b-instruct | 7B | 8,772ms | Mistral instruction-tuned |

---

## 3. Prompt Design Space

### 3.1 Strategies

**Minimal** - Role -> Code -> [hints] -> Categories -> Output format. No reasoning steps.

**Chain-of-Thought (CoT)** - Role -> Step-by-step reasoning instructions -> Code -> [hints] -> Categories -> Output format. The LLM is guided through 6-8 explicit reasoning steps before producing JSON.

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

For multi-issue: only `no_hints` and `ground_truth` (no line hints - realistic production setting).

### 3.4 RAG Mode

In RAG mode, the prompt includes retrieved coding guidelines from the FAISS corpus (S15 production strategy: `retrieve_with_context(code)`, top-k=10 chunks, BAAI/bge-large-en-v1.5 embeddings).

---

## 4. Evaluation Metrics

| Metric | Definition |
|--------|-----------|
| **Exact Match** | Does the predicted `(line_number, violation_category)` pair exactly match any ground-truth pair? Binary 0/1 per response |
| **Category Precision** | `true_positive_categories / predicted_categories` - what fraction of predicted categories are correct? |
| **Category Recall** | `true_positive_categories / ground_truth_count` - what fraction of GT violations are covered? |
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

- **phi4 and qwen2.5-coder** achieve perfect scores (F1=0.500, 100% valid JSON) across every config tested - zero failures.
- **codellama** also achieves perfect valid-JSON rate and F1, with the fastest latency among reliable models.
- **gemma4** has perfect F1 when it produces valid JSON, but fails on 20% of responses.
- **mistral** is the weakest: only 76.2% precision (predicts wrong categories 24% of the time).
- **llama3.1** is the fastest (4.7s avg) but has lower valid-JSON rate (94.4%) due to CoT multi-issue failures.

---

## 6. Strategy Comparison - Minimal vs CoT

| Strategy | Runs | Valid JSON | Avg F1 | Precision | Recall |
|----------|------|-----------|--------|-----------|--------|
| **Minimal** | 161 | **98%** | **0.471** | **94.3%** | **31.4%** |
| CoT | 36 | 89% | 0.422 | 84.4% | 28.1% |

### Why Minimal Wins

1. **Higher valid-JSON rate** (98% vs 89%): CoT prompts encourage reasoning text, and some models emit their step-by-step analysis instead of (or alongside) the JSON, breaking parsability.
2. **Higher precision**: Without intermediate reasoning, models are less likely to hallucinate extra violations or misclassify categories.
3. **Simpler prompts = more predictable behavior** across model families.

### Where CoT Fails

- CoT multi-issue (all 4 configs) produced **0% valid JSON** on llama3.1:8b - the model outputs full reasoning text and never produces the requested JSON array.
- CoT single-issue with `no_hints`, `exact_line`, `line_range_±2`, `line_range_±3` on llama3.1 had F1=0.000.

---

## 7. Mode Comparison - LLM vs RAG

| Mode | Runs | Valid JSON | Avg F1 | Precision | Recall |
|------|------|-----------|--------|-----------|--------|
| **LLM** | 132 | **98%** | **0.465** | **93.1%** | **31.0%** |
| RAG | 65 | 91% | 0.458 | 91.5% | 30.5% |

### Why LLM Slightly Edges Out RAG

1. **Shorter prompts** = less opportunity for the model to get confused or lose format compliance.
2. The test entry's violations (`unused_import`) are straightforward - models detect them from code alone without needing guidelines.
3. RAG's longer prompts lower the valid-JSON rate from 98% to 91% - some models struggle with the additional context.

### When RAG May Help

RAG is expected to differentiate on harder categories like `documentation_formatting` and `naming_convention` where coding guidelines provide specific rules the LLM might not know. This test entry (all `unused_import`) doesn't exercise that advantage.

---

## 8. Detection Type - Single vs Multi

| Type | Runs | Valid JSON | Avg F1 | Avg Exact Match |
|------|------|-----------|--------|-----------------|
| Multi (valid only) | 8 | 50% | **0.500** | **1.00** |
| Single | 189 | **98%** | 0.462 | 0.83 |

### Trade-offs

- **Multi-issue detection** achieves higher F1 when it works (can find multiple violations per file), but has a catastrophic 50% valid-JSON failure rate - all from CoT multi configs.
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
| 4 | line_range+ground_truth (all ±N) | **0.500** | 0.80-1.00 | 100% | 100% |
| 5 | line_range_±1 | 0.467 | 0.60 | 93.3% | 94% |
| 6 | exact_line+line_range (±1/±3) | 0.450 | 0.90 | 90.0% | 100% |
| 7 | line_range_±2 | 0.433 | 0.60 | 86.7% | 94% |
| 8 | **no_hints** | **0.412** | 0.82 | 82.4% | 85% |
| 9 | exact_line (alone) | 0.400 | 0.80 | 80.0% | 94% |
| 10 | line_range_±3 (alone) | 0.400 | 0.47 | 80.0% | 100% |

### Key Findings

1. **Any hint with `ground_truth` guarantees F1=0.500** - unsurprising since the review comment essentially gives away the answer.
2. **`no_hints` outperforms `exact_line` alone** (F1 0.412 vs 0.400) - giving just a line number without context can actually confuse some models.
3. **`line_range_±1` is the best non-cheating hint** (F1=0.467) - a narrow range focuses the model without over-constraining it.
4. **Wider ranges (±3) are worse** than narrower ones - too much search space dilutes the signal.

---

## 10. Best Config Per Model

| Model | Best Config | F1 | Top 3 |
|-------|------------|-----|-------|
| **phi4:14b** | All configs tied at 0.500 | 0.500 | (no variation - every config perfect) |
| **qwen2.5-coder:14b** | All configs tied at 0.500 | 0.500 | (no variation - every config perfect) |
| **codellama:7b-instruct** | `minimal_single_llm_exact_line+line_range_±2` | 0.500 | All tied at F1=0.500 |
| **gemma4:latest** | `minimal_single_llm_*` (16 valid out of 20) | 0.500 | All valid ones scored 0.500 |
| **deepseek-coder:6.7b** | `minimal_single_llm_exact_line+ground_truth` | 0.500 | `exact_line+lr_±2` (0.500), `exact_line` (0.500) |
| **llama3.1:8b** | `minimal_multi_llm_ground_truth` | 0.500 | `minimal_single_rag_*+ground_truth`, `cot_single_rag_no_hints` |
| **mistral:7b-instruct** | `minimal_single_llm_no_hints` | 0.500 | `llm_exact_line+lr_±2` (0.500), `llm_exact_line+lr_±1` (0.500) |

---

## 11. What Worked

### 1. Minimal strategy + LLM mode
The simplest prompts produce the most reliable results. Direct instruction without reasoning steps yields higher valid-JSON rates and equal or better accuracy.

### 2. phi4 and qwen2.5-coder - zero-failure models
Both 14B models achieved **100% valid JSON** and **100% correct category** across every single prompt configuration tested. They are robust to prompt variation.

### 3. Hint combinations with `ground_truth`
Providing the actual review comment as a hint guarantees correct output - useful for validating the pipeline works end-to-end before removing hints.

### 4. `line_range_±1` as practical hint
Among non-cheating hints, a tight line range (±1) gives the best boost without providing the exact answer.

### 5. SHA256 caching
The caching system (`data/llm_cache/<sha256>.json`) makes re-evaluation instant (197 cached results = 0ms per call on re-run).

---

## 12. What Failed

### 1. CoT multi-issue prompts - catastrophic JSON failure
All 4 CoT multi-issue configs (both LLM and RAG modes) produced **0% valid JSON** on llama3.1:8b. The model follows the CoT steps and outputs reasoning text instead of pure JSON. This is a fundamental failure mode of step-by-step prompting when requesting structured output from smaller models.

### 2. gemma4 - 20% invalid JSON
Despite perfect accuracy when it does produce JSON, gemma4 fails to generate valid JSON on 4 of 20 calls. These failures appear in RAG configs where the longer prompt causes the model to emit commentary.

### 3. mistral - worst precision (76.2%)
Mistral frequently predicts the wrong violation category, especially `naming_convention` instead of `unused_import`. It also fails entirely on RAG `no_hints` configs (F1=0.000).

### 4. deepseek-coder with `no_hints` - F1=0.000
Without any hints, deepseek-coder predicts the wrong category on this eval entry. It needs at least `exact_line` or `ground_truth` to succeed.

### 5. RAG's longer prompts reduce JSON compliance
RAG mode drops valid-JSON rate from 98% (LLM) to 91%, with no compensating accuracy gain on this `unused_import`-only eval entry.

### 6. `exact_line` alone is counterproductive
Giving just the line number (without ground_truth or line_range context) performs worse than `no_hints` (F1 0.400 vs 0.412). The line hint may cause models to fixate on what's at that line rather than analyzing the code correctly.

---

## 13. Final Selection - Top 2 Models

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

- **codellama** (7B) is perfect on F1 but hasn't been tested on as many configs; latency is lower (7.8s) - worth considering as a fast backup.
- **gemma4**: Perfect when valid, but 20% invalid-JSON rate makes it unreliable for automated pipelines.
- **llama3.1**: Fastest (4.7s) but drops on CoT configs; acceptable for minimal-only usage.
- **deepseek-coder**: Fails without hints.
- **mistral**: Lowest precision - too many category misclassifications.

---

## 14. Final Selection - Top 3 Prompts

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
| Practical | Yes - no GT required |

**Why chosen**: Requires zero ground-truth information. This is the only realistic production prompt - it receives only the code file and must detect violations independently.

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
| Practical | Yes - uses retrieval pipeline |

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
| Practical | Yes - finds multiple violations per file |

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

Results are cached in `data/llm_cache/` - re-runs are instant.
