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
| `indentation` | E101, E111–E133, W191 | pycodestyle |
| `naming_convention` | N801–N818 | pep8-naming |
| `unused_import` | F401 | pyflakes |
| `mutable_default` | B006, B008 | flake8-bugbear |
| `documentation_formatting` | D100–D499 | flake8-docstrings (pydocstyle) |

### 2.2 Pylint Code Mapping

| Category | Pylint Codes / Symbols |
|----------|----------------------|
| `indentation` | W0311 (`bad-indentation`) |
| `naming_convention` | C0103 (`invalid-name`), C0104, C0105, C0132, C2401, W3201 |
| `unused_import` | W0611 (`unused-import`), W0614, W0404, W0406 |
| `mutable_default` | W0102 (`dangerous-default-value`) |
| `documentation_formatting` | C0114–C0116 (`missing-*-docstring`), C0112 (`empty-docstring`), C0199 |

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

### 3.1 `mutable_default` — Full Coverage (100%)

Both flake8-bugbear (`B006`) and pylint (`W0102`) reliably detect `=[]`, `={}`, and `=set()` in function signatures. Every ground-truth mutable default violation is caught with an exact file + category + line match. **No gaps**.

### 3.2 `naming_convention` — Strong Coverage (94.9%)

Flake8 `pep8-naming` catches camelCase function names, arguments, and variables. Pylint `C0103` adds coverage for shorter names and class attributes. The 5.1% miss comes from:

- **Variable assignments** inside function bodies where `camelCase` is used but the variable is not a function-level name (some tools only flag definitions, not assignments).
- **Attribute names** on instances that neither tool flags reliably.

Category-level matching (same file, same category, different line) recovers 7 additional matches, bringing effective match rate to ~95%.

### 3.3 `unused_import` — Good Coverage (86.0%)

Pyflakes `F401` and pylint `W0611` detect most unused imports. The 14% miss comes from:

- **Framework-level imports with side effects** (e.g., Django signal handlers or Flask extensions where the import is unused in the local file but loads a module).
- **Wildcard re-exports** where flake8/pylint cannot confirm usage across modules.
- **Conditional or `TYPE_CHECKING`-guarded imports** that confuse static analysis.

### 3.4 `indentation` — Moderate Coverage (76.1%)

Flake8 pycodestyle `E1xx` and pylint `W0311` detect non-4-space indentation and mixed tabs/spaces. The 23.9% miss comes from:

- **Syntax-breaking indentation** — some injected violations produce unparseable files. When `compile()` fails, flake8/pylint refuse to run at all, producing zero detections for the entire file.
- **Continuation-line indentation** that the tools accept as valid alignment style even when the ground truth considers it a violation.
- **2-space or 6-space indentation applied consistently** — some linter configurations accept non-4-space indentation if it is internally consistent.

### 3.5 `documentation_formatting` — Weak Coverage (31.7%)

This is the largest gap. Flake8 `pydocstyle` (D-codes) and pylint `C011x` detect missing docstrings and some formatting issues, but they cannot detect:

- **Docstring indentation mismatches** — the GT frequently flags "Docstring indentation doesn't match block," which no standard tool checks.
- **Framework-specific docstring conventions** — Django test preamble conventions ("Tests that..." is discouraged), pandas NumPy-style parameter formatting, sklearn docstring standards.
- **Semantic docstring quality** — whether a docstring accurately describes the function, uses the correct section headers, or follows Google vs NumPy style.
- **Split one-line docstrings** — malformed multi-line versions of what should be a single-line docstring.

---

## 4. Extensions to Fill the Gaps

The pipeline does **not** attempt to add more static tools to fill the `documentation_formatting` gap. Instead, the system relies on:

1. **RAG retrieval** — the retrieval corpus contains both formal docstring guidelines (PEP 257, framework-specific conventions) and synthetic review comments about docstring issues. The LLM can use retrieved context to generate review comments about docstring problems that no static tool would flag.

2. **LLM inference** — the final code review model receives the code and retrieved context, and can detect semantic docstring issues (wrong style, missing sections, preamble usage) that are inherently beyond the scope of rule-based tools.

3. **Heuristic category prediction** — the `predict_categories()` function in `retrieve.py` uses regex-based heuristics to detect potential `documentation_formatting` issues (missing docstrings, indentation mismatches, split one-liners) and boosts retrieval budget for that category accordingly.

This is a deliberate design choice: static tools provide a high-confidence baseline for the four "structural" categories, while the RAG + LLM pipeline handles the "semantic" documentation category where tools fail.

---

## 5. Ground Truth Comparison Strategy

### 5.1 Three-Tier Matching

The comparison between static tool detections and evaluation ground truth uses a three-tier matching strategy, applied in order of decreasing strictness:

**Tier 1 — Exact Match (file + category + line)**

A static detection matches a GT review if both share the same filename, violation category, and line number. This is the strictest and most reliable match.

**Tier 2 — Semantic Match (documentation_formatting only)**

For `documentation_formatting` violations that fail exact match, the system uses embedding-based semantic similarity. Both the GT `review_comment` and every static tool `message` in the same file (with category `documentation_formatting`) are encoded with the `BAAI/bge-large-en-v1.5` model. The best cosine similarity between the GT text and any static message is computed. If it exceeds the threshold, the pair is considered matched.

This tier exists because documentation violations often appear at different lines (a static tool might flag line 1 for a module-level docstring issue, while the GT flags line 23 for indentation inside the same docstring) but describe the same underlying problem.

**Tier 3 — Category Match (same file + same category, any line)**

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

- At 0.80, only 2/77 pairs match — this means the semantic tier is essentially inactive, and the comparison is dominated by exact and category-level matching.
- The distribution clusters around 0.75–0.79 (median 0.79), meaning most GT–static pairs are semantically related but fall just below the strict threshold.
- The reasoning: a lower threshold (e.g., 0.65) would match more pairs but risks conflating genuinely different issues (e.g., "missing docstring" vs. "docstring indentation mismatch"). In the evaluation context, it is better to honestly report what static tools miss rather than inflate their coverage through loose matching.

The key takeway is that **documentation_formatting is the category where static tools fundamentally fall short**, and the semantic matching analysis confirms this quantitatively rather than just asserting it.

---

## 7. Key Takeaways

1. **Static tools cover 80.3% of GT violations overall** — strong for 4/5 categories.
2. **`documentation_formatting` is the clear weak point** at 31.7% — this is where RAG + LLM adds the most value.
3. **`mutable_default` is fully solved** by existing tools (100% match rate).
4. **False positives are high** (728 extra detections) — static tools are noisy. The pipeline's job is not just to detect violations but to generate contextual, human-like review comments, which static tools cannot do.
5. **The three-tier matching strategy** (exact → semantic → category) provides a fair comparison that accounts for line-number disagreements without inflating accuracy.
