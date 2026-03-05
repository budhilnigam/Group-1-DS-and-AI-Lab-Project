#          **RAG-Based LLM Code Review Agent**

                                       Data Science and AI Lab Project

                                  **Milestone 2 Report**  
                                          Group 1

| Name | Email |
| :---- | :---- |
| Jeevika S | 21f3001259@ds.study.iitm.ac.in |
| Budhil Nigam | 23f1001585@ds.study.iitm.ac.in |
| Kannan S | 21f3000990@ds.study.iitm.ac.in |
| Omkar | 22f2001265@ds.study.iitm.ac.in  |
| Karunesh | 221001606@ds.study.iitm.ac.in |

# 

**Contents**

[**1\. Objective	3**](#1.-objective)

[**2\. Dataset Overview	4**](#2.-dataset-overview)

[2.1. Dataset Sources	4](#2.1.-dataset-sources)

[2.2 Evaluation Dataset	5](#2.2-evaluation-dataset)

[2.3 Retrieval Corpus	6](#2.3-retrieval-corpus)

[2.4 Static Analysis Input Dataset	7](#2.4-static-analysis-input-dataset)

[**3\. Dataset Construction and Description	8**](#3.-dataset-construction-and-description)

[3.1 GitHub API Data Collection	8](#3.1-github-api-data-collection)

[3.2 Raw Data Sources	9](#3.2-raw-data-sources)

[3.3 Synthetic Data Generation Strategy	10](#3.3-synthetic-data-generation-strategy)

[3.4 Dataset Statistics	11](#3.4-dataset-statistics)

[**4\. Dataset Quality Assessment	12**](#4.-dataset-quality-assessment)

[**5\. Dataset Splitting Strategy	13**](#5.-dataset-splitting-strategy)

[**6\. Retrieval Corpus Preparation	14**](#6.-retrieval-corpus-preparation)

[6.1 Document Collection	14](#6.1-document-collection)

[6.2 Chunking Strategy	15](#6.2-chunking-strategy)

[6.3 Embedding Generation	16](#6.3-embedding-generation)

[6.4 Vector Database	16](#6.4-vector-database)

[**Visualisations	16**](#visualisations)

[**7\. Data Preprocessing Pipeline	18**](#7.-data-preprocessing-pipeline)

[**8\. Proposed Methodology Overview	19**](#8.-proposed-methodology-overview)

[8.1 System Architecture	19](#8.1-system-architecture)

[8.2 Scope Restriction	20](#8.2-scope-restriction)

[8.3 Dataset	21](#8.3-dataset)

[8.4 Evaluation Metrics	21](#8.4-evaluation-metrics)

[**9\. Expected Outcomes	23**](#9.-expected-outcomes)

# 

#   **1\. Objective** {#1.-objective}

The objective of Milestone 2 is to identify, construct, and prepare the datasets required for building a Retrieval-Augmented Code Review Assistant for Python pull requests.

The proposed system analyzes pull request (PR) diffs and automatically detects five categories of coding violations:

* indentation inconsistencies  
* naming convention violations  
* unused imports  
* mutable default arguments  
* documentation and formatting issues  
    
  The system compares three different approaches:  
    
1. Static analysis tools  
2. Large Language Model (LLM) without retrieval  
3. Retrieval Augmented Generation (RAG) based code review  
     
   To support this evaluation, datasets were collected and constructed from GitHub repositories, coding guidelines, and linter rule documentation.  
     
   The data preparation process focuses on:  
     
* identifying reliable data sources  
* constructing structured datasets from raw pull request diffs  
* ensuring dataset quality and consistency  
* preparing retrieval knowledge for the RAG architecture  
* creating evaluation datasets with ground-truth annotations

# 

# 

# 

# **2\. Dataset Overview** {#2.-dataset-overview}

The project generates three primary datasets, each serving a specific purpose in the system pipeline.

| Dataset | Purpose |
| ----- | ----- |
| Evaluation Dataset | Used for evaluating code review models |
| Retrieval Corpus | Knowledge base used by the RAG system |
| Static Analysis Input | Used to run baseline linters |

| Dataset | Entries | Organic | Synthetic |
| :---- | :---- | :---- | :---- |
| Evaluation Dataset | 158 | 128 | 30 |
| Retrieval Corpus | 220 | 220 | 0 |
| Static Analysis Input | 125 | 95 | 30 |

## **2.1. Dataset Sources** {#2.1.-dataset-sources}

The pull request data used for constructing the evaluation dataset was collected from several well-established open-source Python repositories. These repositories were selected because they follow strong coding standards, maintain active development communities, and contain extensive pull request review activity.

The repositories used in this study include:

| Repository | Role |
| :---: | :---: |
| django/django | Training |
| pandas-dev/pandas | Training |
| scikit-learn/scikit-learn | Training |
| pallets/flask | Evaluation |
| fastapi/fastapi | Evaluation |

These repositories provide a diverse set of Python codebases across web development, machine learning, and data processing domains.

## 

## 

## **2.2 Evaluation Dataset** {#2.2-evaluation-dataset}

Source: Public Python repositories on GitHub.

Description:

The evaluation dataset contains pull request diffs extracted from open-source repositories. These diffs represent real code changes submitted by developers during collaborative development.

| Metric | Value |
| :---- | :---- |
| Total entries | 158 |
| Organic entries | 128 |
| Synthetic entries | 30 |
| Total violations | 268 |

**Violation distribution:**

| Category | Count |
| :---- | :---- |
| indentation | 104 |
| documentation\_formatting | 75 |
| naming\_convention | 53 |
| mutable\_default | 21 |
| unused\_import | 15 |

Each pull request diff is segmented into diff chunks, which are annotated with ground truth review comments describing coding violations.

## **2.3 Retrieval Corpus** {#2.3-retrieval-corpus}

The retrieval corpus forms the knowledge base used by the RAG model. Each document is converted into knowledge chunks that contain rule explanations related to code quality.

Sources include 220 knowledge chunks of:

* Python coding guidelines  
* project style guides  
* linter rule explanations  
* historical review comment

| Source | Chunks |
| :---- | :---- |
| Review comments | 84 |
| PEP-8 guidelines | 81 |
| Linter rules | 36 |
| PEP-257 documentation | 17 |
| Project guidelines | 2 |

**Chunk size statistics:**

* min: 9 words  
* max: 421 words  
* mean: 122 words

Chunks were split to remain within **400 tokens**, ensuring efficient retrieval.

Example:

{  
  "chunk\_id": "guideline\_32",  
  "text": "Avoid importing modules that are not used in the file. Unused imports make code harder to read.",  
  "category": "unused\_import",  
  "source\_type": "project\_guideline"  
}

These chunks are embedded and stored in a vector database for semantic retrieval.

## **2.4 Static Analysis Input Dataset** {#2.4-static-analysis-input-dataset}

This dataset is used to run baseline static analysis tools such as:

* Flake8  
* Pylint

Example structure:

{  
  "file\_path": "utils/helpers.py",  
  "diff\_code": "import numpy as np\\nimport math\\n..."  
}

These tools generate rule-based violation reports that serve as a baseline for comparison with LLM-based systems.

Statistics:

| Metric | Value |
| :---- | :---- |
| Files | 125 |
| Organic files | 95 |
| Synthetic files | 30 |
| Lines of code | 39,015 |

# **3\. Dataset Construction and Description** {#3.-dataset-construction-and-description}

The datasets used in this study are constructed through a **multi-stage data collection and transformation pipeline**. The pipeline gathers raw pull request data, code changes, and review comments from open-source repositories and converts them into structured datasets that can be used by the automated code review system.

## **3.1 GitHub API Data Collection** {#3.1-github-api-data-collection}

Data for the evaluation dataset was collected using the GitHub REST API (v3). The collection process systematically retrieved pull request review comments and file change diffs across selected repositories.

The following endpoints were used during data collection:

**PR Review Comments**  
\[GET /repos/{owner}/{repo}/pulls/comments\]  
This endpoint was used to retrieve the most recent review comments from pull requests.

**PR File Changes**  
\[GET /repos/{owner}/{repo}/pulls/{pr}/files\]  
This endpoint was used to extract unified diff patches representing code modifications in each pull request.

To ensure reliable and stable data collection, several strategies were implemented:

* Pagination was used to retrieve large datasets across multiple API responses.  
* A 1-second delay between API requests was introduced to respect GitHub rate limits.  
* Automatic retries were implemented when HTTP 403 rate-limit responses were encountered.  
* All API responses were cached locally in a cache/ directory to ensure experiment reproducibility.

In total, the data collection process retrieved:

* 25,000 pull request review comments  
* 98 pull request file change sets  
* Data spanning five large Python repositories

## **3.2 Raw Data Sources** {#3.2-raw-data-sources}

The raw dataset is constructed from several complementary sources that provide information about code changes and coding standards.

Raw sources include:

* GitHub pull request diffs  
* repository style guidelines  
* Python style rules  
* linter rule documentation

The collected data is processed and transformed into structured JSON datasets used by the system.

The data collection pipeline used the following GitHub API endpoints:

* /repos/{owner}/{repo}/pulls/comments  
* /repos/{owner}/{repo}/pulls/{number}/files  
* /repos/{owner}/{repo}/contents/{path}

Important features in the dataset include:

| Feature | Description |
| :---: | :---: |
| PR ID | Unique identifier assigned to each pull request in the dataset  |
| Repository | Name of the GitHub repository from which the pull request was extracted |
| File Path | The path of the modified file within the repository |
| Diff Chunks | Segmented portions of the pull request diff representing code changes |
| Line Numbers | Line numbers indicating the location of the modification in the file |
| Violation Category | The category of coding issue detected (e.g., unused import, indentation error) |
| Review Comment | Ground truth review comment describing the detected violation |

## **3.3 Synthetic Data Generation Strategy** {#3.3-synthetic-data-generation-strategy}

During the data collection phase, pull request review comments were scraped from several open-source Python repositories using the GitHub API. In total, more than **25,000 review comments** were collected across the selected repositories. However, only a very small fraction of these comments corresponded to **actual coding guideline violations** relevant to the scope of this project.

Most pull request comments typically relate to general development workflow or project coordination, such as suggestions about architecture, requests for additional tests, clarification questions, or general feedback (e.g., “Looks good”, “Please add tests”, “Can you rebase?”). These comments do not correspond to identifiable coding rule violations and therefore, cannot be used as labeled examples for a code review violation detection system.

After filtering and preprocessing, only a limited number of comments could be confidently mapped to the five predefined violation categories used in this project:

* indentation inconsistencies  
* naming convention violations  
* unused imports  
* mutable default arguments  
* documentation or formatting issues

Because of this imbalance, relying solely on the filtered GitHub data would result in **severe category imbalance**, where some violation types appear frequently while others appear only rarely. Such an imbalance negatively affects both retrieval quality and evaluation reliability.

To address this limitation, **synthetic examples were generated selectively** to supplement the real dataset. Synthetic data was created only for categories that were significantly underrepresented in the collected GitHub review comments. The generation process produced realistic examples of:

* code diffs representing a specific violation pattern  
* corresponding review comments describing the violation

These synthetic examples were designed to follow Python coding standards (PEP8 and PEP257) and typical phrasing patterns found in real code review discussions.

To minimize bias introduced by artificial examples, the following constraints were applied:

1. **Real GitHub data remains the dominant portion of the dataset.**  
   The majority of examples originate from actual pull request reviews.  
2. **Synthetic data is used primarily to balance rare categories.**  
   It is introduced only where the collected data lacks sufficient representation.  
3. **The evaluation dataset prioritizes real-world examples.**  
   Synthetic examples are included only in limited numbers to ensure category coverage.

This strategy allows the dataset to maintain a realistic representation of GitHub code review behavior while ensuring that each violation category is sufficiently represented for meaningful experimentation. Future iterations of the dataset can progressively replace synthetic examples with additional real-world data as more labeled examples are collected.

## **3.4 Dataset Statistics** {#3.4-dataset-statistics}

The raw dataset collected during the pipeline consists of:

| Dataset Component | Count |
| :---: | :---: |
| Review Comments | 25000 |
| Pull Request File Changes | 98 |
| Repositories | 5 |
| Linter Rule Explanations | 36 |
| PEP Guideline Sections | Multiple |

These datasets are then transformed into the structured evaluation dataset and retrieval corpus used by the RAG system.

# **4\. Dataset Quality Assessment** {#4.-dataset-quality-assessment}

Dataset quality was evaluated to ensure that the data is suitable for automated code review analysis.

**Comment Classification System**

To identify violation comments from the raw review dataset, a hybrid classification approach was used.

1. LLM Classification: Review comments were classified using GPT-4 based models.

To minimize API cost and token usage:

* Comments were batched (80 per request)  
* Multiple models were load-balanced  
* Classification prompts emphasized precision over recall.  
* Comments that did not clearly match a violation were labeled "none".

2. Regex Fallback Classifier: A regex-based classifier was implemented as a fallback when LLM responses were unavailable or malformed.

* Over 50 keyword patterns were used across the five categories.

3. Cross Validation

* A second model independently re-classified evaluation comments. Disagreements were handled conservatively to ensure label reliability.

**Missing Values**

Potential missing values include:

* missing line numbers  
* incomplete diff chunks  
* absent annotations

These entries were filtered or manually verified to maintain dataset reliability.  
**Duplicate Entries**

Duplicate code diffs can occur when similar code changes appear in multiple pull requests.  
Duplicates were removed to prevent evaluation bias.

**Noise and Inconsistencies**

Noise may arise from:

* formatting artifacts in GitHub patch files  
* unrelated code changes  
* comments or metadata inside diffs

Preprocessing steps normalize indentation and remove irrelevant lines.

# **5\. Dataset Splitting Strategy** {#5.-dataset-splitting-strategy}

Although the project does not train model weights directly, dataset splitting is necessary to avoid data leakage in the retrieval system.

The split strategy is repository-based.  
Training repositories are used to construct the retrieval corpus.  
Evaluation repositories are used exclusively for building the evaluation dataset.  
This separation ensures that the system cannot retrieve ground truth answers during evaluation.

# **6\. Retrieval Corpus Preparation** {#6.-retrieval-corpus-preparation}

The retrieval corpus is designed to provide **contextual knowledge for the Retrieval-Augmented Generation (RAG) model**. This corpus contains coding guidelines, rule explanations, and documentation that help the model understand coding standards when generating review comments.

Documents are processed through several stages including **collection, chunking, embedding generation, and indexing**.

## **6.1 Document Collection** {#6.1-document-collection}

**Style Guide Sources**

The retrieval corpus was constructed from multiple coding guideline sources to ensure **comprehensive coverage of Python coding standards and best practices.**

The corpus integrates both **general Python style documentation and project-specific coding rules**.

Sources include the following categories:

**PEP Documentation**

Official Python Enhancement Proposals (PEPs) provide the primary reference for Python coding conventions.

* PEP 8 – Python coding style guidelines covering indentation, naming conventions, import organization, whitespace usage, and formatting rules.  
* PEP 257 – Docstring conventions describing how documentation strings should be structured and formatted.  
    
  **Project Contribution Guidelines**  
    
  Repository-specific style documentation was also included to capture **real-world coding practices used by large open-source projects**.  
    
  Documentation was extracted from files such as:  
    
* CONTRIBUTING.md  
* STYLE\_GUIDE.md  
* Developer documentation  
    
  These documents were collected from major Python repositories including:  
    
* django/django  
* pandas-dev/pandas  
* scikit-learn/scikit-learn  
    
  These sources provide additional project-specific coding conventions beyond general Python guidelines.  
    
  **Linter Rule Documentation**  
    
  Static analysis rule descriptions were included to represent **automated coding standard checks used in practice**.  
    
  Rule explanations were collected from:  
    
* Pylint rule descriptions  
* Flake8 rule explanations  
    
  A total of **36 rule explanations** covering the five targeted violation categories were included in the corpus.

## **6.2 Chunking Strategy** {#6.2-chunking-strategy}

To improve retrieval efficiency, documents are divided into smaller segments before embedding.

Each document is split into 200–400 token chunks. Smaller chunks allow the embedding model to capture specific coding rules and concepts more precisely, improving semantic retrieval performance.

Example chunk:

*Mutable default arguments should be avoided because*  
*The same object persists across function calls.*

This chunking strategy ensures that each vector represents a focused coding guideline rather than an entire document.

## **6.3 Embedding Generation** {#6.3-embedding-generation}

In future versions of the system, textual guideline chunks may be converted into vector embeddings using models such as **bge-large-en-v1.5.**  
Embeddings represent the semantic meaning of coding rules and allow similarity comparison between code diffs and guideline documents.  
This enables the system to identify relevant coding standards that relate to a specific code change.

## **6.4 Vector Database** {#6.4-vector-database}

The generated embeddings can be stored in a **FAISS** **vector database** to enable efficient semantic search.  
During inference, code diffs could be embedded and used to retrieve the most relevant guideline chunks from the index.  
These retrieved documents would then be provided as context to the RAG model for generating grounded review comments.

# **Visualisations** {#visualisations}

![][image1]  
**Fig 1: Organic vs Synthetic Data distribution in Evaluation, Retrieval and Static Analysis datasets**

![][image2]  
**Fig 2: Violation Categories distribution**

![][image3]  
**Fig 3: Code Repository wise entries distribution**

![][image4]  
**Fig 4: Retrieval Corpus Dataset (Source Type) distribution**

# 

# **7\. Data Preprocessing Pipeline** {#7.-data-preprocessing-pipeline}

The retrieval corpus is designed to provide contextual knowledge for the Retrieval-Augmented Generation **(RAG)** model. This corpus contains coding guidelines, rule explanations, and documentation that help the model understand coding standards when generating review comments.

Documents are processed through several stages including collection, chunking, embedding generation, and indexing.

1. **Fetch**  
     
   Retrieve raw pull request review comments and file diffs using the GitHub API.  
     
2. **Extract**  
     
   Parse JSON responses and extract structured fields including:  
     
* file path  
* line number  
* diff hunk  
* review comment body  
    
    
3. **Classify**  
     
   Each review comment is automatically classified into one of the five violation categories using multiple large language models:  
     
* GPT-4.1  
* GPT-4o  
* GPT-4.1-mini  
  In cases where API limits are reached, a fallback pattern-matching classifier is applied.  
    
4. **Filter**

   Only comments corresponding to actual guideline violations are retained. General discussion comments are discarded.

   

5. **Construct**  
     
   Violations are grouped by:  
   *(repository, pull request, file)*  
   and converted into structured evaluation dataset entries with associated diff chunks.  
     
6. **Validate**

   Quality checks are performed including:

* duplicate removal  
* consistency checks  
* annotation validation

# **8\. Proposed Methodology Overview** {#8.-proposed-methodology-overview}

## **8.1 System Architecture** {#8.1-system-architecture}

The proposed system is designed as a Retrieval-Augmented Generation (RAG) framework for automated review of small Python pull request (PR) diffs. The architecture integrates structured retrieval of project-specific coding guidelines with Large Language Model (LLM)-based review generation to improve correctness, grounding, and contextual alignment.

## **8.2 Scope Restriction** {#8.2-scope-restriction}

The system is strictly limited to detecting the following five guideline violation categories:

1. Indentation inconsistencies  
2. Naming convention violations  
3. Unused imports  
4. Mutable default arguments  
5. Documentation or formatting deviations

   The system explicitly excludes:

* Functional correctness issues  
* Security vulnerabilities  
* Architectural design feedback  
* Performance optimization suggestions  
  This restriction ensures focused evaluation and reduces ambiguity in labeling.

  ## **8.3 Dataset** {#8.3-dataset}


  To prevent memorization effects and ensure fair evaluation, the dataset is divided into separate training (retrieval corpus) and evaluation repositories.


  **Data Sources Included:**


1. Project Documentation  
* CONTRIBUTING.md  
* STYLE\_GUIDE.md  
* Developer documentation

2. Relevant PEP8 Sections  
* Indentation rules  
* Naming conventions  
* Import organization  
* Mutable default argument guidelines  
* Docstring formatting standards  
    
3. Static Analysis Rule Explanations  
* Pylint rule descriptions  
* Flake8 rule descriptions  
* Mapping of rule IDs to violation categories

4. Accepted Style-Related Review Comments  
* Extracted only from training repositories  
* Must correspond to one of the five violation categories  
    
  **Chunking Strategy**  
    
* 200–400 tokens per chunk  
* One rule/principle per chunk  
* Minimal semantic overlap  
* Metadata stored with each chunk:  
  * Category  
  * Source type  
  * Repository origin

  This ensures precise retrieval and controlled grounding.


  ## **8.4 Evaluation Metrics** {#8.4-evaluation-metrics}


  The system is evaluated across multiple dimensions to ensure comprehensive analysis.


  **Issue Detection Accuracy**


  Evaluation is performed at the violation-instance level.


  A prediction is considered correct if the generated comment identifies the same violation category as the corresponding human review comment.


  


  Metrics reported:

* Precision (per category)  
* Recall (per category)  
* F1-score (per category)  
* Macro-averaged F1-score  
    
  **Grounding Rate**  
    
  Grounding measures whether the generated comment explicitly references relevant retrieved knowledge.  
    
  A comment is considered grounded if it:  
* References a retrieved guideline or rule  
* Explicitly cites a project-specific standard  
* Aligns with retrieved documentation content  
    
  Grounding Rate \=  
  (Number of grounded comments / Total generated comments)  
    
  **Hallucination Rate**  
    
  A comment is classified as hallucinated if:  
* It identifies a violation not present in the diff  
* It references irrelevant or unsupported rules  
* It introduces fabricated project policies  
    
  Hallucination Rate \=  
  (Number of hallucinated comments / Total generated comments)  
    
  **Semantic Alignment with Human Reviews**  
    
  To measure alignment with reviewer intent:  
* BERTScore F1 is computed between:  
  * Generated comment  
  * Corresponding human review comment

  If the similarity exceeds a predefined threshold, the generated comment is considered semantically aligned.


  


  


  **Latency Analysis**


  To evaluate practical deployment feasibility:

* Retrieval latency  
* Generation latency  
* Total inference time  
  are recorded and compared between baseline LLM and RAG-based LLM.

# **9\. Expected Outcomes** {#9.-expected-outcomes}

The proposed system is expected to demonstrate measurable improvements over both static analysis tools and a baseline LLM.

**Improved Detection Accuracy**

The RAG-based model is expected to achieve:

* Higher macro F1-score than the baseline LLM  
* Improved recall for documentation and naming-related violations  
    
  **Higher Grounding Rate**  
    
  By incorporating project-specific retrieval, the RAG-based model should:  
* Explicitly reference applicable style rules  
* Demonstrate stronger contextual justification  
    
  **Reduced Hallucination**  
    
  Retrieval-based constraints are expected to:  
* Reduce false-positive style suggestions  
* Minimize unsupported or irrelevant guideline references  
    
  **Project-Aware Comment Generation**  
    
  Generated comments should:  
* Reflect repository-specific conventions  
* Match the tone and structure of human reviewers  
* Provide constructive, localized feedback  
    
    
    
  **Practical Prototype**  
    
  The final deliverable will include:  
* A functional RAG-based code review prototype  
* A structured evaluation dataset  
* Comparative experimental results  
* Quantitative grounding and hallucination analysis  
* Reproducible data collection pipeline

[image1]: <data:image/png;base64,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>

[image2]: <data:image/png;base64,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>

[image3]: <data:image/png;base64,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>

[image4]: <data:image/png;base64,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>