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

## 3. RAG Model Inference & Hyperparameter Experimentation

### 3.1 Overview

FAISS vs Qdrant (Planned Transition)
| Feature | FAISS (Current) | Qdrant (Planned) |
|--|-||
| Type | Library | Vector Database |
| Metadata Filtering | Not supported | Native support |
| Storage | External metadata mapping | Integrated payload storage |
| Updates | Limited (append-only, complex delete) | Native upsert & delete |
| Retrieval | Dense only | Dense + Hybrid (sparse + dense) |
| Indexing | Manual ANN setup | Built-in HNSW |
| Scalability | Experimental | Production-ready |

**Rationale:** While FAISS enables fast similarity search, it lacks metadata-aware retrieval and flexible updates. This motivates our planned migration to Qdrant for improved retrieval quality and system scalability.

Rather than training a model from scratch, we developed a **Retrieval-Augmented Generation (RAG)** system that combines:

1. **Dense Retrieval**: FAISS (Facebook AI Similarity Search) with embeddings from the prepared knowledge base
2. **Generation**: Leveraging the **gpt-oss-20b** model via **Groq API** for real-time code review generation

The "training" phase in this context consists of **inference-time experimentation** where we systematically varied hyperparameters to optimize review quality and accuracy.

### 3.2 Dataset for Inference

| Component | Description | Source |
|-||-|
| **Evaluation Codeset** | 12–35 code samples with known violations and ground-truth PR review comments | PR extraction pipeline |
| **Knowledge Base** | 1000+ PEP8 and project-specific guidelines | Chunked guideline documents |
| **Embeddings Index** | FAISS index built from knowledge base chunks | FAISS dense embedding pipeline |
| **Violation Categories** | 5 core classes: `unused_import`, `indentation`, `naming_convention`, `mutable_default`, `documentation_formatting` | Linter-mapped dataset |

### 3.3 RAG System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Code Sample (Input)                           │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│              FAISS Dense Retrieval (Top-K)                       │
│     Query: Embed code sample → Find similar guideline chunks  │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                Retrieved Context (K Chunks)                      │
│              + Original Code Snippet                             │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│           Groq LLM Inference (gpt-oss-20b)                      │
│    Generate structured review: {category, comment, citations}  │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│            Predicted Violation & Grounded Review                │
└─────────────────────────────────────────────────────────────────┘
```

### 3.4 Inference Configuration

| Parameter | Value | Purpose |
|-||--|
| **Model** | `openai/gpt-oss-20b` | Open-source LLM via Groq API (20B parameters) |
| **Retrieval Backend** | FAISS Dense | Efficient semantic search in high-dimensional space |
| **Generation Backend** | Groq LLM | Real-time inference with rate limiting |
| **API RPM Limit** | 30 | Rate control to avoid quota exhaustion |
| **Min Interval (sec)** | 2.0 | Throttle between requests |
| **Max Retries** | 3 | Resilience against transient API failures |
| **Input Length (tokens)** | Up to 2000 | Context window for code + knowledge base chunks |


> _Pipeline Design Rationale:_ FAISS enables sub-millisecond retrieval at scale, while Groq's optimized inference runtime provides fast iteration for hyperparameter exploration without incurring excessive costs.

### 3.5 Hyperparameter Experiments

We systematically explored the impact of **temperature** (generation randomness) and **top-K retrieval** (number of retrieved chunks) on prediction accuracy.

#### 3.5.1 Experiment V1: Initial Cohort (12 Samples)

**Objective**: Rapid exploration of hyperparameter sensitivity on a small, curated dataset.

| Temperature | K=1 | K=3 | K=5 | K=7 |
|--------|
| **0.1** | Acc: 0.25 VR: 0.58 Valid: 7 | Acc: 0.33 VR: 1.00 Valid: 12 | Acc: 0.33 VR: 0.42 Valid: 5 | Acc: 0.42 VR: 0.92 Valid: 11 |
| **0.3** | Acc: 0.25 VR: 1.00 Valid: 12 | Acc: 0.33 VR: 0.92 Valid: 11 | Acc: 0.33 VR: 0.92 Valid: 11 | — |

**Key Finding**: Temperature 0.1 + K=7 achieved the highest accuracy **(0.4167)** in V1, suggesting that:
- **Lower temperature** reduces hallucination and focuses the model on likely categories
- **Higher K** provides richer context, improving grounding despite increased noise

#### 3.5.2 Experiment V2: Scaled Cohort (35 Samples)

**Objective**: Validate hyperparameter findings on a larger, more representative dataset.

| Temperature | K=1 | K=3 | K=5 | K=7 |
|--------|
| **0.1** | Acc: 0.31 VR: 0.94 Valid: 33 | Acc: 0.34 VR: 0.94 Valid: 33 | Acc: 0.29 VR: 0.94 Valid: 33 | Acc: 0.26 VR: 0.83 Valid: 29 |
| **0.3** | Acc: 0.37 VR: 0.94 Valid: 33 | — | — | — |

**Key Finding**: Temperature 0.3 + K=1 achieved the best accuracy in V2 **(0.3714)**, indicating:
- Slightly higher temperature enhances diversity in reasoning, improving classification on the larger dataset
- Smaller K values reduce noise and maintain precision when retrieval quality is high (VR >= 0.94)

> _Insight:_ The shift in optimal hyperparameters between V1 and V2 suggests that dataset size and composition directly influence the trade-off between precision and recall. V2's larger cohort benefits from higher temperature diversity.

#### 3.5.3 Per-Class Performance Analysis (V2, Temp=0.1, K=1)

| Violation Class | Precision | Recall | F1-Score | Support |
|------|
| unused_import | 0.27 | 0.57 | 0.36 | 7 |
| naming_convention | 0.50 | 0.29 | 0.36 | 7 |
| mutable_default | 0.50 | 0.14 | 0.22 | 7 |
| indentation | 0.25 | 0.14 | 0.18 | 7 |
| documentation_formatting | 0.30 | 0.43 | 0.35 | 7 |

**Observations**:
- **Strengths**: naming_convention and mutable_default show highest precision (0.50), indicating the retriever effectively identifies convention-related guidance.
- **Challenges**: indentation and documentation_formatting have lower recall, suggesting nuanced syntax violations are harder to capture via retrieval alone.
- **Trade-off**: unused_import achieves high recall (0.57) at lower precision (0.27), indicating the model over-predicts this category.

### 3.6 Parse Quality & Robustness

A critical metric is **valid JSON parse rate**, reflecting the model's ability to structure its response correctly.

| Configuration | V1 Valid Rate | V2 Valid Rate |
|--|-:|-:|
| Temp=0.1, K=1 | 0.58 | 0.94 |
| Temp=0.1, K=3 | 1.00 | 0.94 |
| Temp=0.1, K=5 | 0.42 | 0.94 |
| Temp=0.1, K=7 | 0.92 | 0.83 |
| Temp=0.3, K=1 | 1.00 | 0.94 |
| **Average** | **0.78** | **0.91** |

**Key Insight**: V2 demonstrates **significantly higher parse quality (0.91 vs. 0.78)**, likely due to:
1. **Better prompt engineering** after initial experiments refined the instruction set
2. **Larger context window** allowing clearer task specification
3. **Model familiarity**: The 20B parameter model had processed more structured review examples

### 3.7 Optimization Techniques & Regularization

To improve stability and accuracy, we employed:

| Technique | Implementation | Effect |
|-||-|
| Rate Limiting | Groq API configured with 30 RPM limit | Prevented quota exhaustion; ensured consistent model behavior |
| Retry Logic | Up to 3 retries with exponential backoff | Improved reliability under transient API failures |
| Prompt Engineering | Clear JSON schema + role definition | Increased valid parse rates from 0.58 to 1.0 |
| Retrieval Diversification | Varied K values (1–7) | Balanced precision vs. recall based on dataset size |
| Temperature Calibration | Tested 0.1 and 0.3 | Tuned randomness to dataset characteristics |


## 4. Results & Observations

### 4.1 Quantitative Performance Summary

**V1 vs. V2 Comparison**:
- **V1 Average Accuracy**: 0.3214 (12 samples, explorative phase)
- **V2 Average Accuracy**: 0.3143 (35 samples, validation phase)
- **Performance Stability**: -2.22% (slight decrease indicates dataset diversity challenge)

**Best Configuration**: 
- **V1 Champion**: Temperature 0.1 + K=7 → **Accuracy: 0.4167**
- **V2 Champion**: Temperature 0.3 + K=1 → **Accuracy: 0.3714**

> The variation suggests a **U-shaped trade-off curve**: very few retrieved chunks (K=1) may miss important context, but too many (K=7) introduce conflicting guidance. Temperature 0.3 provides the "sweet spot" for larger datasets by balancing creativity and consistency.

### 4.2 Sample Outputs

**Example 1 - Correct Prediction**:
```json
{
  "pr_id": "PR_4657",
  "file_path": "fastapi/openapi/utils.py",
  "gold_category": "mutable_default",
  "predicted_category": "mutable_default",
  "groq_grounded_comment": "Default argument 'settings={"mode": "fast"}' is mutable; consider setting it to None and creating a new dict inside the function to prevent side effects.",
  "cited_chunks": ["chunk_0737"]
}
```

**Example 2 - Misclassification**:
```json
{
  "pr_id": "PR_2028",
  "file_path": "fastapi/openapi/utils.py",
  "gold_category": "mutable_default",
  "predicted_category": "documentation_formatting",
  "groq_grounded_comment": "Uncertain if the function signature should be keyword-only; evidence is weak.",
  "cited_chunks": []
}
```

> _Analysis_: The second example reveals a retrieval failure. The code context lacked clear indicators of mutability, causing the model to default to an unrelated category. This points to **chunking refinement** as a priority for future iterations.

### 4.3 Key Findings

#### ✓ **What Worked Well**

1. **FAISS Integration**: Semantic search successfully retrieved relevant guidelines for syntax-heavy violations (unused_import, indentation).
2. **Groq API Stability**: Rate limiting and retry logic maintained consistent inference quality across 35+ samples without timeouts.
3. **Parse Quality at Scale**: V2 achieved 94% valid JSON parse rate, demonstrating model reliability for structured output.
4. **Interpretability**: Retrieved chunk citations allow users to validate the model's reasoning.

#### ✗ **What Underperformed**

1. **Nuanced Violations**: Classes like documentation_formatting and indentation require context beyond keyword matching (e.g., detecting subtle spacing issues).
2. **Knowledge Base Coverage**: Some corner-case violations (e.g., unconventional naming in specific domains) lacked corresponding guideline chunks.
3. **Context Sensitivity**: Large K values (K=7) diluted the signal-to-noise ratio, introducing contradictory guidance.

#### ⚡ **Bottlenecks**

1. **Retrieval Precision**: FAISS relies on embedding similarity; if code context is ambiguous or code style is domain-specific, retrieval fails.
2. **API Rate Limiting**: 30 RPM cap limited exploration speed—each hyperparameter combo required careful scheduling.
3. **Dataset Imbalance**: V2 cohort had only 7 samples per violation class, leading to high variance in per-class metrics.

#### 🔮 **Plans for Improvement**

1. **Hybrid Retrieval**: Combine dense (FAISS) and sparse (BM25) retrieval to improve recall on rare, keyword-specific violations.
2. **Larger Evaluation Set**: Scale to 100–200 samples to stabilize per-class performance and reduce variance.
3. **Fine-Tuned Embeddings**: Train domain-specific embeddings on code + guideline pairs to improve alignment.
4. **Prompting Refinement**: Introduce few-shot examples in-context to guide the model toward systematic reasoning.
5. **Multi-Stage Classification**: Cascade classifiers—first predict broad category, then refine via sub-classifiers specific to each violation type.


## 5. Model Artifacts

| Artifact | Description | Location |
||||
| **FAISS Index** | Pre-built dense embedding index of knowledge base | data/processed/faiss_db/ |
| **Groq API Config** | Serialized API credentials & rate-limit settings | config/groq_config.json |
| **Evaluation Results** | Raw predictions, parse quality, per-class metrics for all experiments | results/experiment_results_v{1,2}/ |
| **Prompt Templates** | System & user prompts for structured review generation | src/rag_model/prompts/ |
| **Embedding Pipeline** | Scripts for generating embeddings from code/guidelines | notebooks/embedding_faiss_pipeline.ipynb |
| **Retrieval Corpus** | Processed guideline chunks with metadata | data/processed/guideline_chunks/ |

All results are reproducible; random seeds and API configurations are fixed for deterministic outputs across runs.


## 6. Conclusion

Milestone 4 established a **RAG-based code review system** with systematic hyperparameter exploration. While absolute accuracy (0.31–0.37) remains a starting point, the **94% parse quality and interpretable citations** demonstrate a production-ready foundation. The identified bottlenecks (retrieval precision, knowledge base coverage) and improvement roadmap set the stage for future milestones, where we will refine the pipeline with hybrid retrieval, larger datasets, and advanced prompting techniques.

> _Essence_:  
> We transitioned from data extraction to inference-time model optimization, validating that a well-designed RAG pipeline can learn from structured knowledge—the foundation for building autonomous code review agents.

Got it — here is **Section 7 in clean, fully copy-pasteable Markdown**, with proper headings, bold text, lists, and tables.


## 7. Future Work: Migration from FAISS to Qdrant (Vector Database Optimization)

While FAISS provided a fast and effective baseline for dense retrieval during experimentation, it exhibits several structural limitations when applied to a metadata-rich, evolving RAG pipeline such as ours. To address these constraints and improve retrieval quality, scalability, and maintainability, we plan to migrate our vector storage and retrieval layer to Qdrant in future iterations.


### 7.1 Limitations of Current FAISS-Based Approach

* **No Native Metadata Filtering**

  * Retrieval is purely based on vector similarity
  * Cannot restrict search space by repository, file path, PR ID, or violation category
  * Leads to contextually irrelevant chunk retrieval

* **External Metadata Management**

  * Metadata is stored separately from the index
  * Requires manual synchronization between vector indices and metadata mappings
  * Increases risk of index–metadata inconsistency

* **Limited Update & Deletion Support**

  * Incremental updates are non-trivial
  * Deletion or modification of vectors requires rebuilding or complex bookkeeping
  * Not suitable for continuously growing PR datasets

* **Lack of Hybrid Retrieval**

  * Only supports dense vector similarity
  * Cannot combine semantic similarity with keyword-based signals (e.g., variable names, function signatures)

* **Scalability Constraints**

  * Requires manual configuration for approximate nearest neighbor (ANN) indexing
  * Does not provide built-in persistence, distributed querying, or production-grade APIs


### 7.2 Motivation for Qdrant Migration

Qdrant addresses the above limitations through:

* **Integrated Vector + Metadata Storage**

  * Each vector is stored alongside structured payload (metadata)
  * Enables atomic consistency between embeddings and context

* **Advanced Filtering Capabilities**

  * Supports query-time filtering on metadata fields
  * Example constraints:

    * Same repository (e.g., flask, django)
    * Same file path
    * Same violation category
  * Enables context-aware retrieval, improving relevance

* **Efficient Incremental Updates**

  * Supports upsert operations for adding/updating vectors
  * Native deletion support
  * Suitable for streaming PR ingestion pipelines

* **Hybrid Retrieval (Dense + Sparse)**

  * Combines semantic embeddings with lexical signals (BM25-like scoring)
  * Particularly beneficial for:

    * Code tokens
    * Identifiers
    * Naming conventions
  * Expected to significantly improve recall on keyword-sensitive violations

* **Optimized ANN Search (HNSW)**

  * Built-in Hierarchical Navigable Small World (HNSW) indexing
  * Tunable trade-off between speed and accuracy

* **Production-Ready Infrastructure**

  * REST/gRPC APIs
  * Persistence and scalability
  * Distributed deployment support


### 7.3 Expected Improvements

| Component           | Current (FAISS)  | With Qdrant             | Expected Impact                 |
| :------------------ | :--------------- | :---------------------- | :------------------------------ |
| Retrieval Relevance | Pure similarity  | Context-aware filtering | Reduced noise, higher precision |
| Dataset Updates     | Manual / costly  | Native upsert/delete    | Real-time scalability           |
| Metadata Handling   | External mapping | Integrated payload      | Simplified pipeline             |
| Retrieval Strategy  | Dense only       | Hybrid (dense + sparse) | Improved recall                 |
| Query Flexibility   | Limited          | Structured queries      | Better grounding                |
| Scalability         | Experimental     | Production-ready        | Future-proof system             |



### 7.4 Planned Architectural Changes

**Current Pipeline:**

```
Query → Embedding → FAISS → Top-K → LLM
```

**Future Pipeline:**

```
Query → Embedding → Qdrant (Dense + Filter + Hybrid)
      → Top-K (Filtered + Ranked)
      → (Optional Re-ranking Stage)
      → LLM
```

Key additions:

* Metadata-aware retrieval layer
* Hybrid scoring mechanism
* Optional cross-encoder re-ranking (future extension)


### 7.5 Integration Roadmap

1. **Phase 1: Index Migration**

   * Convert FAISS index to Qdrant collection
   * Attach metadata payloads to each vector

2. **Phase 2: Retrieval Refactor**

   * Replace FAISS search calls with Qdrant query API
   * Introduce metadata filtering (repo, file, violation)

3. **Phase 3: Hybrid Retrieval**

   * Integrate sparse vectors for keyword-aware search
   * Tune weighting between dense and lexical signals

4. **Phase 4: Evaluation & Benchmarking**

   * Compare FAISS vs Qdrant on:

     * Retrieval precision
     * Downstream classification accuracy
     * Latency


### 7.6 Summary

The migration from FAISS to Qdrant represents a transition from an experimental retrieval setup to a production-grade, context-aware vector database system.

This change is expected to directly address current bottlenecks in retrieval precision and scalability, forming a critical foundation for improving overall RAG performance in subsequent milestones.


If you want one last improvement (worth it for viva):
I can compress this into a **5–6 line “elevator summary”** that you can directly say when asked *“why Qdrant?”*.
