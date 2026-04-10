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
