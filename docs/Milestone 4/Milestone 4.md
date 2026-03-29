# Milestone 4: Data Preparation, Preprocessing, and Chunking

## 1. Data Preparation and Preprocessing

The primary goal of this stage was to construct a high-quality, ground-truth dataset from thousands of historical Pull Requests (PRs). We transitioned from a simple "crawl and store" approach to a multi-stage, "Linter-in-the-Loop" pipeline to ensures the data is both structurally sound and perfectly labeled.

### 1.1 Evolution of Extraction Scripts
*   **Failed/Deleted Attempt: Repository-Specific Extraction (`django_pr_extraction.py`)**
    *   **Thought Process**: Initially, we created standalone scripts for each target repository (e.g., `django`, `flask`). This allowed for quick prototyping and hardcoding repo-specific API paths.
    *   **Results**: While functional for a single repository, it was unscalable. It led to code duplication and inconsistent error handling across different repos.
    *   **Reason for Change**: We needed a unified, parameter-driven architecture that could handle any GitHub repository via CLI arguments.

*   **Final Implementation: Unified Multiprocessing Pipeline (`pr_extraction.py`)**
    *   **Process**: Developed a robust core extraction engine that uses the GitHub REST API to fetch PR comments, diffs, and head SHAs.
    *   **Key Features**:
        *   **State Persistence**: Uses a `processed_prs.json` file to resume extraction if the script is interrupted or hits a rate limit.
        *   **Parallel Execution**: Wrapped the main logic in a PowerShell/Python orchestration script to process 5 repositories (`django`, `flask`, `scikit-learn`, `pandas`, `fastapi`) concurrently using `subprocess.Popen`.
    *   **Outcome**: Successfully scaled data collection to a target of 150 PRs per repository, generating a massive initial pool of PR-line-comment triplets.

### 1.2 Filtering Heuristics and Noise Reduction
To ensure the LLM learns from "expert" correctional reviews rather than general discussion, we implemented a strict "Signal-to-Noise" filter:
*   **Author-Reviewer Identity Check**
    *   **Logic**: `reviewer_login != author_login`
    *   **Motivation**: Authors often leave comments on their own PRs (e.g., "I will fix this later"). These are not "reviews" in the correctional sense and introduce noise.
*   **Automated Bot Filtering**
    *   **Logic**: Regex-based exclusion for common bot patterns (`*bot*`, `codecov`, `github-actions`).
    *   **Motivation**: CI/CD bots generate standardized, repetitive reports (e.g., "Coverage decreased by 0.1%"). This noise would confuse the RAG retriever and LLM.
*   **Semantic Signal Word Filtering**
    *   **Approach 1: Character Length (Failed)**:
        *   We initially kept all comments longer than 30 characters.
        *   **Result**: Captured too many polite but useless comments like "This looks great! Just one minor thing, can you add a test?"
    *   **Approach 2: Keyword Boosting (Final)**:
        *   We prioritize comments containing correctional signal words: `should`, `avoid`, `naming`, `unused`, `fix`, `mutable`, `convention`, `standard`, `style`.
        *   **Observation**: This significantly increased the density of actual code-style violations in the dataset.
*   **Diff Context Constraints**
    *   **Logic**: Discard PRs with diffs exceeding 200 lines.
    *   **Reasoning**: Massive PRs often involve mechanical changes (e.g., dependency lock updates) where style violations are less focused. Smaller, targeted PRs provide higher-quality learning samples for the agent.

### 1.3 Automated Violation Labeling (Static Analysis)
This was the most critical evolution *after* basic extraction. We needed to map unstructured human comments to 5 specific violation categories.
*   **The "Linter-in-the-Loop" Strategy**
    *   **Thought Process**: Humans are inconsistent. One reviewer might call an unused import "cruft," while another calls it "unnecessary." However, static analysis tools are deterministic. 
    *   **Execution**: 
        1. Fetch the full source code of the file at the specific commit (SHA) where the comment was made.
        2. Run **Flake8** and **Pylint** on that specific file.
        3. Match the linter's line-specific error code to our predefined categories.
*   **Mapping Mechanism**:
    *   `F401` (Flake8) -> **unused_import**
    *   `E1xx` (Flake8) -> **indentation**
    *   `W0102` (Pylint) -> **mutable_default**
    *   `C0103` (Pylint) -> **naming_convention**
*   **Failed Attempt: Manual/LLM Labeling**
    *   **Alternative**: We considered using an LLM to label the comments.
    *   **Why Discarded**: Too expensive and prone to hallucination at the data preparation scale. Static analysis provides the "ground truth" we need for a scientific evaluation.

---

## 2. Chunking Strategies

Chunking is the bridge between the raw file content and the LLM's context window. We evolved from naive line-based windows to structure-aware blocks.

### 2.1 Experimental Strategies (Failed)
*   **Strategy A: Fixed-Size Sliding Window (±10 Lines)**
    *   **Thought Process**: Take the line of the violation and include 10 lines above and below.
    *   **Failure Mode**: Often cut off the top of a function (the `def` line) or the start of a class. Without the function signature, the LLM cannot verify if a variable name follows naming conventions or if a default parameter is mutable.
*   **Strategy B: Unified Patch Only**
    *   **Thought Process**: Only provide the `+` and `-` lines from the git diff.
    *   **Failure Mode**: Complete lack of semantic context. The LLM has no idea which class the modified method belongs to, making "Project Guideline" checks impossible.

### 2.2 Final Implementation: Structural AST-Aware Chunking (AST/ATS)
To solve the "missing context" problem, we implemented a parser utilizing **Tree-sitter**.
*   **The AST (Abstract Syntax Tree) Pipeline**:
    *   **1. Parse**: Generate a full concrete syntax tree of the Python file.
    *   **2. Traverse**: Use Depth-First Search (DFS) to find the deepest node that fully encompasses the line where the violation occurred.
    *   **3. Expand**: If the violation is inside a method, the chunker automatically grabs the entire `function_definition`. If the violation is at the class level (e.g., an invalid class attribute name), it grabs the `class_definition`.
*   **Fallback Strategy**:
    *   If the file contains syntax errors (common in old PRs) and the AST cannot be built, the system reverts to a **±10 line sliding window** to ensure no data is lost.
*   **Result**: Every sample in the final dataset contains a **semantically complete code block**, ensuring the LLM has all the information a human reviewer would have.

### 2.4 Final Dataset Refinement
*   **Script**: `filter_valid_violations.py`
*   **Logic**: 
    *   Even with AST chunking and linter labeling, some samples remain "Unlabeled" if the linter doesn't find a match (e.g., the comment was about logic, not style).
    *   We programmatically prune the dataset to **only** include samples where the linter successfully mapped the violation to one of our 5 core categories.
*   **Outcome**: This ensures the RAG system is evaluated on a "clean" test set where the "Ground Truth" is verified by both a human (the original PR comment) and a machine (the linter).

### 2.5 Retrieval Corpus (Knowledge Base) Chunking
For the static guideline documents (PEP8, repository-specific `.md` guides):
*   **Strategy**: **Rule-Based Semantic Splitting**.
*   **Constraint**: Chunks are limited to **200–400 tokens**.
*   **Reasoning**: Each chunk should ideally represent exactly one style rule. If a chunk is too large, the retriever might bring in irrelevant rules that consume the LLM's prompt space.
*   **Metadata Integration**: Each chunk is indexed with its source filename and a unique "rule ID" to allow the LLM to cite its sources during the review process (e.g., "According to PEP8, variable names should be snake_case...").
pt.
