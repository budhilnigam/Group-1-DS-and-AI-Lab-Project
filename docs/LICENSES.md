# License

## MIT License

Copyright (c) 2026 Group 1 DSAI Lab Project Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## Third-Party Licenses

### Dependencies

The project uses the following open-source libraries and models under their respective licenses:

**Python Runtime & Web Framework**:
- FastAPI, Uvicorn (BSD 3-Clause License)
- Jinja2 (BSD 3-Clause License)
- Celery (BSD License)

**Data Processing & Analysis**:
- pandas, numpy, scikit-learn (BSD 3-Clause License)
- Tree-sitter (MIT License)

**Vector Search & Embeddings**:
- Qdrant (AGPL-3.0 License)
- SentenceTransformers / sentence-transformers (Apache 2.0 License)
- FAISS (MIT License)
- BAAI/bge-large-en-v1.5 embedding model (MIT License)

**Code Analysis**:
- Pylint (GPL-2.0 License)
- Flake8 (MIT License)
- Ruff (MIT License)

**LLM Inference**:
- Groq API access for `openai/gpt-oss-20b` (see Groq Terms of Service)

**GitHub Integration**:
- PyGithub (BSD 3-Clause License)

### Data and Models

**Evaluation Dataset**:
- `data/processed/evaluation.json`: Original project data assembled from synthetic repositories and GitHub PR comments
- Ground-truth annotations created via linter-in-the-loop methodology (Flake8, Pylint)

**Retrieval Corpus**:
- `src/deployment/corpus/retrival_corpus.json`: Curated guideline chunks from:
  - PEP 8 and PEP 257 (Python Enhancement Proposals, public domain)
  - Framework documentation (Django, Flask, FastAPI, pandas, scikit-learn)
  - Linter tool documentation (Ruff, Flake8, Pylint)
  - Synthetic review comments from generated PR discussions

**GitHub-Derived Data**:
- Any PR comments or diffs sourced from external GitHub repositories remain subject to the terms of the original repositories and GitHub's terms of service.
- For use in your own work, ensure compliance with the source repository licenses.

---

## Citation and Attribution

If you use this project in academic work or publications, please cite it as:

```bibtex
@misc{dsai_group1_code_review_2026,
  title={Retrieval-Augmented Code Review System for Python Pull Requests},
  author={Group 1 DSAI Lab Project},
  year={2026},
  note={Available at: https://github.com/budhilnigam/Group-1-DS-and-AI-Lab-Project}
}
```

When referencing the embedding model or LLM, cite the respective sources:
- BAAI/bge-large-en-v1.5: [BAAI/bge repository](https://github.com/FlagOpen/FlagEmbedding)
- openai/gpt-oss-20b: Accessed via [Groq API](https://groq.com/)