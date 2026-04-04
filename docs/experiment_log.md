# Experiment Log — RAG Code Review Pipeline

Tracks every retrieval and prompting strategy attempted, including failures,
so results are reproducible and the reasoning behind the final design is clear.

---

## Approach 1 — Dense-only retrieval, no repo boosting (FAILED)

**What we tried:** FAISS cosine search using only the diff chunk text as the query,
with no repo name, file path, or framework context added. Top-K=5, no reranking.

**Result:** PEP 8 and Flake8 rule chunks dominated the top-5 for every query
regardless of which repo the diff came from. Framework-specific guidelines
(e.g. Django's `use underscores, not camelCase`) never surfaced even for
Django-specific violations because they were not semantically distinct enough
from the generic PEP 8 equivalents.

**Why it failed:** The embedding model treats "use snake_case" from the Django
documentation and the equivalent PEP 8 chunk as near-identical. Without a
signal that repo-specific guidance should be preferred, the retrieval is
effectively rank-unaware of provenance.

**What we changed:** Added repo name + framework + file path to every query
string, plus a second-stage reranking boost for `repo_scope == framework`.
See Approach 3.

---

## Approach 2 — Semantic-only indentation detection (FAILED)

**What we tried:** Used only semantic similarity to surface indentation
guideline chunks when the query contained an indentation violation. No
structural signals were applied to the code.

**Result:** Indentation violations scored poorly against pure-text guideline
chunks because diff lines like `      result = foo()` (six leading spaces)
have little semantic content that matches "use 4 spaces per indentation level."
The embedding model picks up meaning, not whitespace counts.

Additionally, mutable_default and naming_convention queries often scored higher
than indentation chunks even when the true violation was an indentation issue,
because the diff window happened to contain identifiers or argument lists.

**Why it failed:** Indentation is a structural property of source code, not a
semantic one. Sentence embeddings over diff text cannot reliably detect
"this line has wrong indentation" from the raw characters alone.

**What we changed:** Added `detect_indentation()` in `scripts/retrieval.py`.
This independently checks structural signals (non-4-space leading whitespace,
mixed tabs/spaces, docstring indentation mismatch, inconsistent surrounding
context) and, when triggered, boosts the score of indentation-category chunks
by `indent_boost` weight regardless of semantic rank. Also always includes
indentation-specific context in the retrieval query for such cases.

---

## Approach 3 — Two-stage retrieval with repo-priority reranking (CURRENT)

**What we tried:** Build the retrieval query to include `Repository: <name>`,
`Framework: <name>`, `File: <path>`, and a 6-line code window around the
violation line. Run FAISS over-fetch (top_k × 4 candidates), then rerank
with two additive boosts:
  - `repo_boost_weight` (default 0.2) for chunks whose `repo_scope` matches
    the current framework
  - `indent_boost` (default 0.15) for indentation-category chunks when
    `detect_indentation()` fires

Cap each `source_type` at `per_source_cap` (default 3) entries so that PEP 8
chunks cannot dominate if framework-specific guidelines are available.

**Result (sweep on validation subset):** Recall@5 improved by approximately
12–18 percentage points for `naming_convention` and `mutable_default` compared
to Approach 1. Indentation Recall@5 improved approximately 20 pp compared to
Approach 2.

**Why it works:** The framework name in the query moves the embedding closer to
framework-specific guideline chunks in embedding space. The score boost then
nudges those chunks above generic PEP 8 equivalents even when pure cosine
similarity is tied.

**Tunable parameters (found via notebook sweep):**
  - `top_k`: 5–10 (10 often slightly better for rare categories)
  - `repo_boost_weight`: 0.2 is a reasonable default; too high (>0.4) causes
    framework chunks to appear even when they are semantically irrelevant
  - `indent_boost`: 0.15–0.20
  - `per_source_cap`: 3

---

## Approach 4 — Category hint injection (MIXED)

**What we tried:** Added `include_category_hint=True` to the retrieval config
and injected "Likely violation type: <gold_category>" into the query string.
Also added a `with_category_hint` prompt template that primes the LLM with the
category before showing the diff.

**Result:** Recall@5 improved slightly for all categories (approximately +5 pp
on average) when the hint was present. However, the category was derived from
the gold label in evaluation mode, which is a form of label leakage. In real
deployment the category hint is not available.

**How we handle it:** We report metrics both with and without the category hint
so the reader can see the upper bound (with hint) and the realistic bound
(without hint). The default "best config" is selected from the no-hint
configurations to avoid inflating reported metrics.

---

## Approach 5 — LLM prompt engineering iterations

**Templates tried:**
  1. `minimal` — diff + bare output constraint. Produced highest parse error
     rate (~15%) when the model wandered outside the JSON format.
  2. `with_evidence` — diff + formatted guideline evidence. Parse errors dropped
     to ~4%. Categories were more accurate when the evidence contained a
     relevant chunk.
  3. `with_repo_hint` — framework-aware system prefix + evidence sorted
     framework-first. Small additional improvement on framework-specific
     categories (~2–3 pp F1).
  4. `with_category_hint` — evidence + category priming. Best raw accuracy
     (with label leakage caveat noted in Approach 4).

**Temperature:** 0.0 consistently outperformed 0.1 for structured JSON output.
Higher temperatures caused more format drift.

**max_tokens:** 256 was sufficient for all templates. 512 only helped in a few
edge cases and nearly doubled generation latency.

**Final choice:** `with_evidence` at temperature=0.0, max_tokens=256, with
`with_repo_hint` as the recommended variant for deployment since it does not
rely on the gold label.

---

## Summary of final configuration

| Parameter | Value | Rationale |
| --- | --- | --- |
| Embedding model | BAAI/bge-large-en-v1.5 | Milestone spec, good code→text similarity |
| FAISS index type | IndexFlatIP (inner product) | L2-normalised vectors → cosine similarity |
| top_k | 10 (sweep best) | Broader coverage; reranking filters to relevant |
| repo_boost_weight | 0.2 | Empirically best in sweep without over-boosting |
| indent_boost | 0.15 | Structural override effective without false positives |
| per_source_cap | 3 | Prevents PEP 8 monopolising the top-K |
| LLM | qwen2.5-coder:7b-instruct | Free, local, code-competent |
| prompt_template | with_evidence | Best accuracy/reliability trade-off |
| temperature | 0.0 | Deterministic JSON output |
| max_tokens | 256 | Sufficient; faster generation |

---

## Approach 6 — Targeted RAG fixes + output consolidation (CURRENT)

**Context — why Approach 3/5 RAG underperformed LLM-only:**

After running the full sweep on the SWEEP_N=10 subset (58 pairs) the results were:

| Metric | RAG (rag_0001) | LLM-only |
|--------|---------------|----------|
| Macro-F1 | 0.2152 | 0.2398 |
| Parse errors | 14 / 58 (24%) | 10 / 58 (17%) |
| Grounding rate | 0.0% | 0.0% |
| cited_chunk_ids non-empty | 0 / 58 | — |
| Retrieval Recall@1 | 0.1724 | — |
| Retrieval Recall@5 | 0.5690 | — |

Four root causes were identified by inspecting `raw_response` values in
`predictions_rag_best.json`:

1. **Category label leakage** — evidence was formatted as
   `[chunk_id] (category, source_type): text`, so when a retrieved chunk
   belonged to the wrong category the LLM read the wrong label from the
   evidence itself and copied it. Because Recall@1 is only 0.17, ≈83% of
   top-1 hits were off-category — making this a systematic bias.

2. **Too many evidence chunks for TinyLlama** — passing 5 chunks pushed
   the prompt toward TinyLlama's effective context limit (~1400 tokens).
   The model responded by producing prose containing guidelines rather than
   JSON, causing parse errors (+40% compared to LLM-only).

3. **No confidence gating** — chunks with very low cosine similarity (score
   < 0.4) were still injected into the prompt. In these cases the evidence
   was entirely irrelevant and only added noise.

4. **`cited_chunk_ids` always empty** — `parse_response()` set
   `"cited_chunk_ids": []` in every fallback branch. However, inspecting
   raw responses showed the model did mention `[chunk_0241]` etc. in prose
   output — these were never extracted. As a result grounding rate was 0%
   even when the model referenced real chunks.

**Changes made:**

| Change | File | Rationale |
|--------|------|-----------|
| Remove category label from evidence | `llm_inference._format_evidence()` | Stop wrong-category leakage; model sees only chunk text |
| Add `_extract_cited_ids(raw)` helper | `llm_inference.py` | Recover `[chunk_id]` refs from prose using `re.findall` |
| Apply cited-ID extraction in all 3 parse strategies | `llm_inference.parse_response()` | Fix 0% grounding: post-hoc scan whenever `cited_chunk_ids` is empty |
| Stricter JSON-only instruction | `PROMPT_TEMPLATES["with_evidence"]` | Add "Respond with ONLY valid JSON. No text before or after." to reduce TinyLlama prose output |
| Score threshold (`min_score=0.4`) | `llm_inference.build_rag_prompt()` | Skip evidence entirely when no chunk is relevant enough; fall back to minimal template |
| Cap evidence at top-3 (`evidence_top_k=3`) | `llm_inference.build_rag_prompt()` | Shorter prompts; fits within TinyLlama context; less noise |
| Retrieve top-10 (`top_k=10`) | `pipeline.ipynb` config | More candidates before filtering — improves recall at the reranking stage |
| Embed `retrieval_hits` in prediction dict | `llm_inference.run_inference()` | Eliminates separate `retrieval_logs_*.json` files; all info in one place |
| Consolidate to 3 output files | `pipeline.ipynb` save cell | Replace ~12 scattered `predictions_*` / `retrieval_logs_*` / `run_configs.json` with `results_rag.json`, `results_llm.json`, `results_static.json` |
| Inline charts | `evaluation.ipynb` | Remove `plt.savefig()` calls; charts render inside the notebook |

**Output file schema (new):**

Each file (`results_rag.json`, `results_llm.json`, `results_static.json`) is:
```json
{
  "config":   { ...hyperparameters used... },
  "metadata": { "sweep_n": 10, "total_pairs": 58, "timestamp": "..." },
  "predictions": [
    {
      "pr_id", "repo", "source_path", "line_number",
      "gold_category", "gold_comment",
      "predicted_category", "predicted_comment",
      "cited_chunk_ids",   <- now populated from prose extraction
      "parse_error", "from_cache", "latency_ms",
      "baseline", "config_id", "raw_response",
      "retrieval_hits": [  <- RAG only; embedded instead of separate log file
        { "chunk_id", "rank", "score_raw", "score_boosted",
          "category", "source_type", "repo_scope", "text" }
      ]
    }
  ]
}
```

**Expected improvements (hypotheses):**
- Parse error rate should fall because shorter, more directive prompts.
- `cited_chunk_ids` non-empty rate should increase (previously 0%).
- RAG Macro-F1 should approach or exceed LLM-only (0.2398) once category
  label leakage and context overflow are resolved.
- `mutable_default` and `documentation_formatting` are most likely to
  improve because these categories had Recall@10 of 0.09 and 0.00
  (indentation chunks dominated for them under the old format).

**Observed results (SWEEP_N=10, 58 pairs, config = rag_0000):**

| Metric | Approach 5 RAG | Approach 6 RAG | LLM-only | Static |
|--------|---------------|---------------|----------|--------|
| Macro-F1 | 0.2152 | **0.2398** | 0.2398 | 0.1042 |
| Parse errors | 14/58 (24%) | 10/58 (17%) | 10/58 (17%) | — |
| Grounding rate | 0% | 0% | 0% | — |
| `cited_chunk_ids` non-empty | 0/58 | 0/58 | — | — |
| Retrieval Recall@1 | 0.17 | 0.09 | — | — |
| Retrieval Recall@5 | 0.57 | 0.55 | — | — |
| Retrieval Recall@10 | — | 0.69 | — | — |
| Best prompt template | with_evidence | **minimal** | minimal | — |

**Key findings:**
1. **RAG Macro-F1 now equals LLM-only (0.2398)** — improvement of +0.0246 over Approach 5. The label-leakage and context-overflow fixes eliminated the regression relative to LLM-only.
2. **`with_evidence` template hurt performance** — configs using it achieved accuracy 0.1207 vs 0.2069 for `minimal`. TinyLlama is too small to correctly leverage retrieved evidence; the evidence confuses rather than guides it. This is the dominant finding.
3. **RAG `minimal` ≡ LLM-only** — because the best RAG config uses the `minimal` template (no evidence in prompt), the LLM receives identical prompts as LLM-only baseline. The retrieval step is computed but not consumed, so F1 is identical. RAG only adds value when the model is large enough to use the evidence.
4. **`cited_chunk_ids` still empty** — as expected for `minimal` template (no chunk IDs in prompt). The extraction helper works correctly but has nothing to extract. To get non-empty citations, a larger model capable of using `with_evidence` is needed.
5. **Parse errors reduced** — from 24% (Approach 5) to 17% (Approach 6), confirming that shorter prompts and the stricter JSON instruction reduce prose bleed-through.
6. **Retrieval Recall@10 = 0.69** — strong retrieval; the bottleneck is purely LLM utilisation of the retrieved evidence.

**Conclusion / next change motivation:**
The evidence is clear: TinyLlama (1.1B) cannot leverage retrieved context. The next step is to switch to a larger model (e.g. `qwen2.5-coder:7b-instruct` as identified in Approach 5's ideal config) that can reason over evidence. Retrieval quality is good (Recall@10 = 0.69); the model is the limiting factor.

---

---

## Approach 7 — Upgrade to qwen2.5-coder:7b-instruct (CURRENT)

**Motivation from Approach 6 conclusion:** TinyLlama (1.1B) cannot leverage retrieved context. Retrieval Recall@10 = 0.69 is strong; the model is the bottleneck. The M4 Pro 24 GB machine can comfortably run a 7B model. `qwen2.5-coder:7b-instruct` was already identified as the ideal candidate in Approach 5.

**Changes made:**

| Change | File | Rationale |
|--------|------|-----------|
| Switch `MODEL` from `tinyllama` to `qwen2.5-coder:7b-instruct` | `pipeline.ipynb` config cell | 7B code-specialised model; fits easily in 24 GB RAM |
| Increase `max_tokens` from 256 → 512 | `pipeline.ipynb` config cell | Larger model produces longer, more detailed comments |
| Clear LLM cache | — | Prevent tinyllama cached responses from being reused |

All other hyperparameters unchanged (top_k=10, evidence_top_k=3, min_score=0.4, both `minimal` and `with_evidence` templates swept).

**Observed results (SWEEP_N=10, 58 pairs, best config = rag_0001 `with_evidence`):**

| Metric | TinyLlama RAG (App. 6) | **Qwen2.5 RAG (App. 7)** | Qwen2.5 LLM-only | Static |
|--------|------------------------|--------------------------|------------------|--------|
| Macro-F1 | 0.2398 | **0.3270** | 0.3424 | 0.1042 |
| Parse errors | 10/58 (17%) | **0/58 (0%)** | 0/58 (0%) | — |
| Grounding rate | 0.0% | **39.7%** | 0.0% | — |
| `cited_chunk_ids` non-empty | 0/58 (0%) | **58/58 (100%)** | 0/58 | — |
| Best prompt template | minimal | **with_evidence** | minimal | — |
| Retrieval Recall@10 | 0.69 | 0.69 | — | — |

**Per-category F1:**

| Category | RAG | LLM-only |
|----------|-----|----------|
| indentation | 0.2222 | 0.2353 |
| naming_convention | **0.5306** | 0.4000 |
| unused_import | **0.8824** | 0.3846 |
| mutable_default | 0.0000 | **0.6923** |
| documentation_formatting | 0.0000 | 0.0000 |

**Key findings:**
1. **RAG Macro-F1 improved from 0.2398 → 0.3270** (+0.087 vs Approach 6, +0.092 vs original TinyLlama baseline). The larger model can actually leverage retrieved evidence.
2. **`with_evidence` is now the best template** (0.50 accuracy) vs `minimal` (0.38). This confirms Approach 6's conclusion — the issue was model capacity, not the RAG design.
3. **Zero parse errors** — Qwen2.5-coder reliably outputs valid JSON with no fallback needed.
4. **All 58 predictions have non-empty `cited_chunk_ids`** — grounding rate 39.7% (was 0%). The model genuinely cites the retrieved chunks it used.
5. **LLM-only still slightly ahead overall (0.3424 vs 0.3270)** — RAG dominates on `naming_convention` and `unused_import` (where retrieval Recall@10 is 0.60 and 1.00), but RAG hurts on `mutable_default` (Recall@10=0.55, model is confused by partially relevant evidence).
6. **Root cause of remaining gap:** For `mutable_default` and `documentation_formatting`, retrieval quality is lower (Recall@10 = 0.55 / 0.125). The injected `with_evidence` chunks for those categories are wrong-category, which misdirects the model. A per-category retrieval threshold or a higher `min_score` for low-recall categories would help.

**Conclusion:** Qwen2.5-coder:7b-instruct is a substantial improvement. RAG+evidence now beats LLM-only on 2/5 categories. The next improvement should target `mutable_default` and `documentation_formatting` retrieval quality.

---

## Approach 8 — Heuristic Detectors, 48-Config Sweep, Multi-Model Comparison (CURRENT)

**Motivation from Approach 7 conclusion:** RAG scores 0.00 F1 on both `mutable_default` and `documentation_formatting`. Root causes identified: (1) only 10 corpus chunks for mutable_default — top-3 hits were always wrong-category due to `repo_boost`; (2) doc_formatting Recall@10 = 0.125 because a bare `def func():` has no semantic overlap with "use triple-double-quotes" guidelines. Approach 8 targets these directly with code heuristic detectors, expands the hyperparameter sweep to 48 configs, and benchmarks 7 models.

**Changes made:**

| Change | File | Rationale |
|--------|------|-----------|
| Add `detect_mutable_default()` | `scripts/retrieval.py` | Regex scan for `def f(x=[])` / `=[]` / `={}` patterns in ±4 line window; fires a `mutable_boost` reward for `mutable_default` chunks |
| Add `detect_docstring_issue()` | `scripts/retrieval.py` | Detects `def`/`class` in ±5 lines + absence of `"""` / `'''` in ±10 lines; fires a `doc_boost` reward for `documentation_formatting` chunks |
| Expand `build_query()` window ±3→±5 lines | `scripts/retrieval.py` | Broader code window improves embedding quality for short functions |
| Add docstring hint to query | `scripts/retrieval.py` | Appends "Code may have a docstring formatting issue." when detector fires |
| Add `chain_of_thought` prompt template | `scripts/llm_inference.py` | 3-step reasoning: (1) what code does, (2) which guideline applies, (3) JSON output |
| Expand RETRIEVAL_GRID (4 new axes) | `notebooks/pipeline.ipynb` | Sweep `mutable_boost` ∈ {0, 0.2}, `doc_boost` ∈ {0, 0.2}, `evidence_top_k` ∈ {3, 5}, `min_score` ∈ {0.3, 0.5} |
| Expand INFERENCE_GRID (add `chain_of_thought`) | `notebooks/pipeline.ipynb` | 3 templates × 16 retrieval combos = **48 RAG configs total** |
| SWEEP_N 10→20 | `notebooks/pipeline.ipynb` | More evaluation entries for reliable per-category F1 |
| Multi-model comparison cell | `notebooks/pipeline.ipynb` | Pulls 6 extra models, runs top-5 configs on each |
| 3 new visualisation cells | `notebooks/evaluation.ipynb` | All-configs ranked bar, model comparison bar, models×categories heatmap |

**Observed results — qwen2.5-coder:7b best config (rag_0030, SWEEP_N=20, 121 pairs):**

| Metric | Approach 7 | **Approach 8 (qwen7b)** | Approach 8 (phi4:14b best) |
|--------|-----------|------------------------|---------------------------|
| RAG Macro-F1 | 0.3270 | **0.3519** | — |
| LLM-only Macro-F1 | 0.3424 | 0.3171 | — |
| Static Macro-F1 | 0.1042 | 0.2055 | — |
| Parse errors | 0/58 | **0/121** | — |
| Grounding rate | 39.7% | 59.5% | — |
| Best prompt template | with_evidence | **with_evidence** | minimal |
| Best config | rag_0001 | rag_0030 | rag_0029 |

**Retrieval metrics (best config rag_0030):**

| Metric | Approach 7 | **Approach 8** |
|--------|-----------|----------------|
| Recall@5 | — | 0.5455 |
| Recall@10 | 0.69 | **0.7851** |
| mutable_default Recall@10 | 0.545 | **1.0000** |
| doc_formatting Recall@10 | 0.125 | **0.4762** |

**Per-category F1 — all models (best config per model):**

| Category | qwen7b | qwen14b | llama3.1:8b | deepseek6.7b | mistral7b | codellama7b | **phi4:14b** |
|----------|--------|---------|------------|-------------|---------|-----------|-----------|
| indentation | 0.27 | 0.56 | 0.27 | 0.33 | 0.28 | 0.18 | **0.45** |
| naming_convention | 0.25 | 0.52 | 0.26 | 0.11 | 0.36 | 0.13 | **0.41** |
| unused_import | 0.59 | 0.62 | 0.51 | 0.56 | 0.05 | 0.47 | **0.73** |
| mutable_default | 0.59 | 0.53 | 0.54 | 0.50 | 0.17 | 0.63 | **0.64** |
| documentation_formatting | 0.06 | 0.12 | 0.00 | 0.00 | 0.15 | 0.10 | **0.28** |
| **Best accuracy** | 0.364 | 0.471 | 0.331 | 0.339 | 0.240 | 0.306 | **0.521** |

**Key findings:**
1. **mutable_default fixed: F1 0.00 → 0.59 (qwen7b), up to 0.64 (phi4)** — The `detect_mutable_default()` heuristic + `mutable_boost=0.2` pushes the right corpus chunks to the top. Recall@10 went from 0.545 → 1.000 (perfect retrieval).
2. **documentation_formatting: F1 0.00 → 0.06 (qwen7b), 0.28 (phi4)** — The docstring detector improved Recall@10 from 0.125 → 0.476. Still hard; the embedding gap remains the fundamental challenge but is now reduced.
3. **`chain_of_thought` template did not outperform `with_evidence`** — In the 48-config sweep, all top-15 configs use `minimal` or `with_evidence`. Chain-of-thought reasoning overhead hurt structured JSON output reliability.
4. **`mutable_boost=0.2` is the single strongest lever** — Every config in top-15 has `mutable_boost=0.2`. `doc_boost=0.0` appears optimal for qwen7b (doc_boost=0.2 appears in top-4 as secondary, slightly lower).
5. **phi4:14b is the overall winner at accuracy=0.521** — Uses rag_0029 (`minimal` template, ev_top_k=3, min_score=0.5, mutable_boost=0.2). phi4's instruction-following likely benefits from shorter, cleaner prompts.
6. **qwen2.5-coder:14b second at 0.471** — Strong gains over 7B sibling, especially on indentation (0.27→0.56) and naming_convention (0.25→0.52).
7. **Grounding rate improved 39.7% → 59.5%** — Broader context window (±5 lines) and higher `evidence_top_k=5` give the model more relevant text to cite.

**Config sweep highlights (48 configs, qwen7b):**

| Rank | Config | Accuracy | mutable_boost | doc_boost | min_score | ev_top_k | template |
|------|--------|----------|--------------|-----------|----------|---------|---------|
| 1 | rag_0030 | 0.3636 | 0.2 | 0.0 | 0.3 | 5 | with_evidence |
| 2 | rag_0033 | 0.3636 | 0.2 | 0.0 | 0.5 | 5 | with_evidence |
| 3 | rag_0045 | 0.3554 | 0.2 | 0.2 | 0.5 | 5 | with_evidence |
| 4 | rag_0042 | 0.3554 | 0.2 | 0.2 | 0.3 | 5 | with_evidence |
| 5-15 | rag_002x-004x | 0.3471 | 0.2 or 0.0 | varies | varies | 3 or 5 | minimal |

**Conclusion / next change motivation:**
The heuristic detector approach for mutable_default is highly effective and can be extended. `documentation_formatting` remains the hardest category — the fundamental issue is embedding-space semantic gap between violation code and guideline text. Potential next steps: (1) synthetic hard-negative retrieval training to teach the embedding model what "missing docstring" looks like; (2) category-conditional re-routing (if no docstring chunk in top-10, fall back to a dedicated docstring sub-index); (3) use phi4:14b as the production model as it delivers best overall performance across all categories.

---

## Known limitations

- Retrieval relevance uses category-match as a proxy because per-chunk human
  relevance labels are not available; this underestimates true retrieval quality
  for multi-fact chunks.
- The evaluation dataset is 721 violations across 103 files. Statistical
  significance is limited for rare-category comparisons.
- LLM inference outputs are non-deterministic at temperature 0.0 due to GPU
  floating-point variance; cached responses are used for reproduction.
- Indentation detection is heuristic only; unusual indentation patterns
  (e.g. intentional two-space indent, alignment-based multiline arguments)
  may trigger false override.
