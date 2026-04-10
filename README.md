# RAG-Based LLM Code Review Agent

## Overview

This project investigates whether incorporating project-specific knowledge through a **Retrieval-Augmented Generation (RAG)** framework improves the accuracy and usefulness of automated code review comments compared to non-retrieval baselines.

### What is This Project?

The system analyzes **single-file Python pull request (PR) diffs** with up to 200 modified lines and generates localized review comments limited to five predefined guideline violation categories:
- Indentation inconsistencies
- Naming convention violations
- Unused imports
- Mutable default arguments
- Documentation or formatting deviations

### Key Features

- **RAG-Based Architecture**: Retrieves relevant project-specific guidelines, documentation, and prior accepted review discussions at the diff-chunk level
- **Grounded Feedback**: Generated comments explicitly reference retrieved guidelines rather than being purely generative
- **Comprehensive Evaluation**: Compares RAG system with:
  - Baseline LLM (without retrieval)
  - Static analysis tools (Pylint, Flake8)
- **Vector Database Integration**: Uses **Qdrant** as the vector database for efficient similarity-based retrieval


## Project Structure

### 📁 Directory Overview

```
├── app/                          # Main application files
│   └── app.py                    # Entry point for the application
├── notebooks/                    # Jupyter notebooks for development and experimentation
│   ├── data_preparation_pipeline_v*.ipynb
│   ├── embedding_generation.ipynb
│   ├── rag_llm.ipynb
│   ├── naive_llm.ipynb
│   ├── retrieval_query_strategy*.ipynb
│   ├── reranking_simple_comparison.ipynb
│   └── results/                  # Output results from notebook experiments
├── src/                          # Source code modules
│   ├── data_processing/          # Data processing utilities
│   ├── evaluation/               # Evaluation metrics and scripts
│   └── rag_model/                # RAG model implementation
├── data/                         # Data directory
│   ├── raw/                      # Raw datasets
│   └── processed/                # Processed/cleaned datasets
├── outputs/                      # LLM and RAG evaluation outputs
│   ├── llm_raw_responses_*.txt
│   ├── rag_llm_raw_responses_*.txt
│   ├── static_tool_results_*.txt
│   ├── zero_response_PRs_*.txt
│   └── *.json                    # Cached results
├── results/                      # Experiment results
│   ├── experiment_results_v*/
│   ├── rag-llm_output/
│   └── retrieval_query_strategy_results_v*/
├── docs/                         # Documentation
│   ├── objectives.md
│   ├── problem_statement.md
│   ├── chunking_report.md
│   ├── Milestone 1-5/            # Milestone reports
│   └── ...
├── scripts/                      # Utility scripts
│   ├── create_evaluation_dataset.py
│   ├── create_synthetic_repos.py
│   ├── fetch_review_comments.py
│   └── ...
├── archive/                      # Previous versions and experimental work
│   ├── *.ipynb                   # Old notebooks
│   ├── clean_v1/                 # Previous milestone versions
│   ├── data_processing_old/
│   └── dataset_v*/
├── temp/                         # Temporary files
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variables template
├── README.md                     # This file
└── CHANGELOG.md                  # Project changes and versions
```

### 📋 Key Folders Explained

| Folder | Contents |
|--------|----------|
| **notebooks/** | All Jupyter notebooks used for data preparation, embedding generation, RAG pipeline testing, and retrieval strategy development |
| **outputs/** | Text files containing raw responses from LLM evaluations, RAG+LLM evaluations, and static tool outputs for comparison |
| **results/** | Structured experiment results including performance metrics, retrieval strategy results, and RAG output analysis |
| **src/** | Core source code for data processing pipelines, evaluation metrics, and RAG model implementation |
| **data/** | Training and evaluation datasets (raw and processed versions) |
| **docs/** | Project documentation including problem statement, objectives, technical reports, and milestone deliverables |
| **scripts/** | Standalone Python scripts for dataset creation, synthetic repository generation, and data fetching |
| **archive/** | Historical versions of notebooks and previous experimental approaches (for reference only) |


## Prerequisites

Before setting up the project, ensure you have:

- **Python 3.10+** installed
- **pip** (Python package manager)
- **Qdrant** server running (see [Qdrant Setup](#qdrant-setup) section below)
- **Git** (for version control)


## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/budhilnigam/Group-1-DS-and-AI-Lab-Project.git
cd Group-1-DS-and-AI-Lab-Project
```

### 2. Virtual Environment Setup

It is **strongly recommended** to use a Python virtual environment to isolate project dependencies.

#### Create Virtual Environment

```bash
# On Windows
python -m venv .venv

# On macOS/Linux
python3 -m venv .venv
```

#### Activate Virtual Environment

```bash
# On Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# On Windows (Command Prompt)
.venv\Scripts\activate.bat

# On macOS/Linux
source .venv/bin/activate
```

### 3. Install Dependencies

With the virtual environment activated, install all required packages:

```bash
pip install -r requirements.txt
```

**Key Libraries Installed:**
- `qdrant-client==1.17.1` - Qdrant vector database client for semantic retrieval
- `sentence-transformers==5.3.0` - BAAI/bge-large-en-v1.5 embeddings generation
- `groq==1.1.1` - Groq LLM API client for comment generation
- `python-dotenv==1.2.2` - Environment variable management
- `pandas`, `numpy`, `scikit-learn` - Data processing and evaluation metrics
- `jupyter` - Interactive notebook support
- `flake8`, `pylint` - Static analysis tools (baseline)
- `requests` - GitHub API client for dataset generation


## Environment Variables Setup

### Create `.env` File

The project uses environment variables for configuration. Create a `.env` file **in the project root directory** (same level as this README):

```bash
cp .env.example .env
```

### Configure `.env`

Open the `.env` file in the project root and populate it with the following essential variables. All scripts and notebooks load `.env` from the project root:

```env
# Qdrant Vector Database Configuration
QDRANT_URL=http://localhost:6333
RAG_COLLECTION_NAME=guideline_embeddings

# LLM API Keys (Required for RAG and baseline systems)
GROQ_API_KEY=your_groq_api_key_here
GROQ_API_KEY_V2=your_groq_api_key_v2_here
GROQ_API_URL=https://api.groq.com

# Optional: GitHub Token (for dataset generation)
GITHUB_TOKEN=your_github_token_here
```

Refer to `.env.example` for all available options including embedding model, RAG settings, and LLM parameters.


## Datasets

### Dataset Location

Final processed datasets are located in the `data/` folder:

```
data/processed/
├── evaluation.json              # Main evaluation dataset with PR diffs and ground truth reviews
├── evaluation_files/            # Individual Python source files used in evaluation
│   └── synthetic-<framework>_PR_<id>_*.py
├── retrieval_corpus.json        # Coding guidelines and best practices for retrieval
└── new/                         # Alternative dataset versions
```

### Dataset Composition

- **evaluation.json**: 97 PR samples with manually annotated violation categories
  - Fields: `id`, `source_file`, `diff`, `ground_truth_reviews`
  - Review fields: `line_number`, `violation_category`, `review_comment`
  - 5 violation categories: indentation, naming_convention, unused_import, mutable_default, documentation_formatting

- **retrieval_corpus.json**: 505+ guideline chunks for semantic retrieval
  - Used to build embeddings in Qdrant
  - Chunks cover Python best practices and coding standards

### Dataset Generation

**Note**: The scripts and code used to generate these datasets from GitHub repositories are stored in a separate branch (not available locally). The finalized, processed datasets in `data/processed/` are ready to use for training and evaluation.

To regenerate datasets:
1. Checkout the appropriate branch containing dataset generation scripts
2. Use `scripts/create_evaluation_dataset.py` and `scripts/create_synthetic_repos.py`
3. Follow documentation in that branch for GitHub API setup


## Qdrant Vector Database Setup

### What is Qdrant?

**Qdrant** is a production-grade vector database for similarity search on high-dimensional embeddings. In this project, it stores code embeddings and coding guidelines for efficient semantic retrieval during RAG-based code review generation. Unlike FAISS (used in earlier experimental phases), Qdrant provides metadata filtering, native persistence, and REST/gRPC APIs.

### Installation and Setup

#### Option 1: Docker (Recommended)

Install Docker, then run:

```bash
docker run -p 6333:6333 \
  -e QDRANT_API_KEY=your_api_key \
  qdrant/qdrant:latest
```

This starts a Qdrant server on `localhost:6333`.

#### Option 2: Standalone Installation

1. Download Qdrant from [https://qdrant.tech/](https://qdrant.tech/)
2. Extract and run the executable
3. Access the dashboard at `http://localhost:6333/dashboard`

#### Option 3: Qdrant Cloud

Use Qdrant's managed cloud service:
1. Sign up at [https://cloud.qdrant.io/](https://cloud.qdrant.io/)
2. Create a cluster
3. Update `.env` with your cloud credentials:
   ```env
   QDRANT_URL=https://your-cluster-url.qdrant.io
   QDRANT_API_KEY=your_qdrant_api_key
   ```

### Using Qdrant in the Project

#### 1. Connect to Qdrant

```python
from qdrant_client import QdrantClient
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize client from .env configuration
client = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"))

# Or for cloud with API key:
# client = QdrantClient(
#     url=os.getenv("QDRANT_URL"),
#     api_key=os.getenv("QDRANT_API_KEY")
# )
```

#### 2. Create a Collection

```python
# Create a collection for code guidelines with 1024-dimensional vectors
client.create_collection(
    collection_name="guideline_embeddings",
    vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
)
```

#### 3. Store Embeddings

```python
from sentence_transformers import SentenceTransformer

# Initialize embedding model (1024-dimensional)
model = SentenceTransformer('BAAI/bge-large-en-v1.5')

# Create embeddings for guidelines/code snippets
guidelines = ["Use meaningful variable names", "Add docstrings to functions"]
embeddings = model.encode(guidelines)

# Store in Qdrant
for i, (guideline, embedding) in enumerate(zip(guidelines, embeddings)):
    client.upsert(
        collection_name="guideline_embeddings",
        points=[{
            "id": i,
            "vector": embedding.tolist(),
            "payload": {
                "text": guideline,
                "category": "documentation_formatting",
                "source_type": "guideline"
            }
        }]
    )
```

**Embedding Details:**
- Model: `BAAI/bge-large-en-v1.5` (from SentenceTransformers)
- Dimension: 1024
- Normalization: L2-normalized for cosine similarity
- Distance metric: Cosine (inner product on normalized vectors)

#### 4. Retrieve Similar Items

```python
# Query for similar guidelines
query = "What about variable naming conventions?"
query_embedding = model.encode(query)

results = client.search(
    collection_name="code_guidelines",
    query_vector=query_embedding.tolist(),
    limit=5  # Return top 5 results
)

for result in results:
    print(f"Score: {result.score}, Guideline: {result.payload['text']}")
```

### Qdrant Monitoring

Access the Qdrant dashboard at `http://localhost:6333/dashboard` to:
- View collections and their statistics
- Monitor vector storage
- Check collection health


## Running the Project

### Jupyter Notebooks

To run the experimental notebooks:

```bash
# Activate your virtual environment if not already active
.venv\Scripts\Activate.ps1  # Windows
# or
source .venv/bin/activate  # macOS/Linux

# Start Jupyter
jupyter notebook
```

Navigate to the `notebooks/` folder and open the desired notebook.

**Key Notebooks:**
- `data_preparation_pipeline_v*.ipynb` - Data processing
- `embedding_generation.ipynb` - Generate embeddings
- `rag_llm.ipynb` - RAG-based code review generation
- `naive_llm.ipynb` - Baseline LLM without retrieval
- `retrieval_query_strategy.ipynb` - Query optimization for retrieval

### Running Scripts

```bash
# Create evaluation dataset
python scripts/create_evaluation_dataset.py

# Create synthetic repositories
python scripts/create_synthetic_repos.py

# Fetch review comments
python scripts/fetch_review_comments.py
```

### Main Application

To run the main application (when implemented):

```bash
python app/app.py
```


## Project Workflow

### 1. **Data Preparation**
   - Collect Python PR diffs and human review comments
   - Preprocess and clean data
   - Split into training and evaluation sets

### 2. **Embedding Generation**
   - Generate embeddings for code snippets and guidelines using `sentence-transformers`
   - Store embeddings in Qdrant

### 3. **RAG Pipeline**
   - For each PR diff, retrieve relevant guidelines from Qdrant
   - Pass diff + retrieved context to LLM
   - Generate review comments

### 4. **Evaluation**
   - Compare RAG-based output with:
     - Baseline LLM (no retrieval)
     - Static analysis tools
   - Measure: accuracy, grounding rate, semantic similarity
   - Analyze hallucination rate

### 5. **Analysis & Reporting**
   - Generate experiment results and visualizations
   - Document findings in milestone reports


## Key Features

### ✅ Code Review Categories

The system detects and reviews:
- Indentation inconsistencies
- Naming convention violations
- Unused imports
- Mutable default arguments
- Documentation/formatting deviations

### ✅ Evaluation Metrics

- **Violation Detection Accuracy**: Does the system correctly identify violations present in human reviews?
- **Grounding Rate**: Does the system reference retrieved guidelines?
- **Semantic Similarity**: How similar are generated comments to human reviews (BERTScore)?
- **Hallucination Rate**: How many invalid violations are flagged?
- **Latency**: What is the retrieval overhead?

### ✅ Integration Support

- Works with popular Python linters (Pylint, Flake8) for static analysis baseline
- Groq LLM API for fast, efficient comment generation
- Qdrant vector database for efficient semantic retrieval of coding guidelines
- SentenceTransformers (BAAI/bge-large-en-v1.5) for 1024-dimensional embeddings


## Troubleshooting

### Virtual Environment Issues

```bash
# Deactivate and reactivate
deactivate
.venv\Scripts\Activate.ps1

# Reinstall dependencies if corrupted
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### Qdrant Connection Issues

```bash
# Verify Qdrant is running
curl http://localhost:6333/health

# Check Qdrant logs
docker logs <container_id>  # If using Docker
```


## Team Members

| Name | Email |
|------|-------|
| Jeevika S | 21f3001259@ds.study.iitm.ac.in |
| Budhil Nigam | 23f1001585@ds.study.iitm.ac.in |
| Kannan S | 21f3000990@ds.study.iitm.ac.in |
| Karunesh | 22f1001606@ds.study.iitm.ac.in |


## Documentation


### Milestone Reports (overview)

- [Milestone 1 Report](docs/Milestone%201/Milestone-1.md) - Defines the problem, project objectives, and a literature review comparing RAG and existing automated code-review approaches.
- [Milestone 2 Report](docs/Milestone%202/Milestone-2.md) - Describes dataset collection and construction, retrieval corpus preparation, chunking strategy, and dataset quality assessment.
- [Milestone 3 Report](docs/Milestone%203/Milestone%203.md) - Details data preprocessing, embedding/FAISS index construction, retrieval and context formation, and the system's model architecture.
- [Milestone 4 Report](docs/Milestone%204/Milestone%204.md) - Covers scalable data preparation, 'linter-in-the-loop' automated labeling, advanced chunking strategies, and pipeline refinements.
- [Milestone 5 Report](docs/Milestone%205/Milestone-5.md) - Presents final evaluation, quantitative and qualitative results, error analysis, and conclusions with next-step priorities.


## License

This project is part of the IITM Data Science and AI Lab curriculum.


## References

- Lewis, P., et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. arXiv:2005.11401
- Li, Z., et al. (2022). *CodeReviewer: Pre-Training for Automatic Code Review*. arXiv:2203.09095
- McIntosh, S., et al. (2016). *A Large-Scale Study of Modern Code Review*. ACM MSR
- Markovtsev, V., et al. (2019). *Style-Analyzer: Fixing Code Style Inconsistencies with Unsupervised Learning*. arXiv:1908.02737
- Siow, J., et al. (2022). *AUGER: Automated Code Review Comment Generation*. arXiv:2208.08014
- Tufano, M., et al. (2018). *Automatic Code Review by Learning the Revision of Source Code*. arXiv:1812.08693
- Chen, M., et al. (2021). *Evaluating Large Language Models Trained on Code*. arXiv:2107.03374
- Papineni, K., et al. (2002). *BLEU: A Method for Automatic Evaluation of Machine Translation*. ACL
- Zhang, T., et al. (2019). *BERTScore: Evaluating Text Generation with BERT*. arXiv:1904.09675
- SmartDoc (2025). *SmartDoc*. arXiv:2511.00450