"""Retrieve top-k chunks from Qdrant with optional deduplication.

Supports two modes:
  1. retrieve(query, top_k) — basic single-query retrieval.
  2. retrieve_with_context(code, top_k) — production strategy (S15):
     adaptive budget + refined queries + heuristic reranking.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

import numpy as np
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Paths & defaults
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_COLLECTION_NAME = os.getenv("RAG_COLLECTION_NAME", "guideline_embeddings")
DEFAULT_QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"
DEFAULT_TOP_K = 10
DEDUP_SIMILARITY_THRESHOLD = 0.85  # chunks above this cosine sim are considered duplicates
OVERFETCH_MULTIPLIER = 3           # fetch this many x top_k to have room for filtering


# -- loading ----------------------------------------------------------------

_model_cache: SentenceTransformer | None = None
_client_cache: QdrantClient | None = None


def _get_model() -> SentenceTransformer:
    global _model_cache
    if _model_cache is None:
        _model_cache = SentenceTransformer(EMBEDDING_MODEL)
    return _model_cache


def _get_client() -> QdrantClient:
    global _client_cache
    if _client_cache is None:
        _client_cache = QdrantClient(url=DEFAULT_QDRANT_URL)
    return _client_cache


def load_index() -> tuple[QdrantClient, str]:
    """Compatibility helper retained from the original module."""
    client = _get_client()
    try:
        client.get_collection(DEFAULT_COLLECTION_NAME)
    except Exception as exc:
        raise FileNotFoundError(
            f"Qdrant collection not found. Start Qdrant and build embeddings first.\n"
            f"  Expected collection: {DEFAULT_COLLECTION_NAME}\n  Qdrant URL: {DEFAULT_QDRANT_URL}"
        ) from exc
    return client, DEFAULT_COLLECTION_NAME


# -- deduplication ----------------------------------------------------------

def _deduplicate(
    chunks: list[dict],
    embeddings: np.ndarray,
    top_k: int,
    threshold: float,
) -> list[dict]:
    """Keep up to top_k chunks, greedily removing near-duplicates.

    Walk the ranked list; for each candidate check cosine similarity against
    all already-accepted chunks. Drop if it exceeds threshold with any.
    """
    if len(chunks) == 0:
        return []

    accepted_idx: list[int] = []

    for i in range(len(chunks)):
        if len(accepted_idx) >= top_k:
            break

        is_duplicate = False
        for j in accepted_idx:
            sim = float(np.dot(embeddings[i], embeddings[j]))
            if sim >= threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            accepted_idx.append(i)

    return [chunks[i] for i in accepted_idx]


# -- core retrieval ---------------------------------------------------------

def _point_to_doc(point: Any) -> dict[str, Any]:
    payload = getattr(point, "payload", None)
    if isinstance(payload, dict):
        doc = dict(payload)
    else:
        doc = {"text": str(payload) if payload is not None else ""}
    doc["score"] = round(float(getattr(point, "score", 0.0)), 4)
    if "chunk_id" not in doc and getattr(point, "id", None) is not None:
        doc["chunk_id"] = getattr(point, "id")
    return doc


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    deduplicate: bool = False,
    threshold: float = DEDUP_SIMILARITY_THRESHOLD,
) -> list[dict]:
    """Return up to top_k relevant chunks for the query.

    Parameters
    ----------
    query : str
        Natural-language search query.
    top_k : int
        Number of chunks to return.
    deduplicate : bool
        When True, over-fetch and greedily filter out near-duplicate chunks
        so the final list contains top_k semantically distinct results.
    threshold : float
        Cosine similarity threshold above which two chunks are considered
        duplicates (only used when deduplicate is True).
    """
    model = _get_model()
    client, collection_name = load_index()

    q_emb = model.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype(np.float32)

    fetch_k = min(
        top_k * OVERFETCH_MULTIPLIER if deduplicate else top_k,
        top_k * OVERFETCH_MULTIPLIER if deduplicate else top_k,
    )

    response = client.query_points(
        collection_name=collection_name,
        query=q_emb[0].tolist(),
        limit=fetch_k,
        with_payload=True,
        with_vectors=deduplicate,
    )

    candidates: list[dict[str, Any]] = []
    candidate_embs: list[np.ndarray] = []

    for point in response.points:
        doc = _point_to_doc(point)
        candidates.append(doc)

        if deduplicate:
            vector = getattr(point, "vector", None)
            if isinstance(vector, dict):
                vector = next(iter(vector.values()), None)
            if vector is not None:
                candidate_embs.append(np.asarray(vector, dtype=np.float32))

    if deduplicate and candidates and len(candidate_embs) == len(candidates):
        emb_matrix = np.stack(candidate_embs)
        candidates = _deduplicate(candidates, emb_matrix, top_k, threshold)
    else:
        candidates = candidates[:top_k]

    return candidates


# ---------------------------------------------------------------------------
# Category prediction heuristics (S15 component)
# ---------------------------------------------------------------------------

CATEGORIES = [
    "unused_import",
    "indentation",
    "naming_convention",
    "documentation_formatting",
    "mutable_default",
]

# Keyword-rich queries tuned to avoid cross-category confusion
# (e.g., doc_formatting ↔ indentation bleed eliminated by using linter codes)
REFINED_QUERIES = {
    "unused_import": "unused import module not used remove F401 W0611",
    "indentation": "indentation whitespace spaces tabs alignment PEP8 E1 W1",
    "naming_convention": "naming convention snake_case CamelCase PEP8 variable function class name",
    "documentation_formatting": "docstring formatting summary description numpy google style pep257 D100 D200",
    "mutable_default": "mutable default argument list dict set function parameter B006 W0102",
}

# Reranking boosts indexed by heuristic confidence level (0-3)
_RERANK_BOOSTS = {3: 0.12, 2: 0.06, 1: 0.02, 0: -0.03}


def predict_categories(code: str) -> dict[str, int]:
    """Predict which violation categories are likely present in *code*.

    Returns ``{category: confidence}`` where confidence is 0–3.
    Biased towards high recall (better to over-predict than miss).
    """
    lines = code.split("\n")
    scores: dict[str, int] = {}

    # ── unused_import ──
    import_lines = [l for l in lines[:40] if l.strip().startswith(("import ", "from "))]
    if import_lines:
        body = "\n".join(lines[len(import_lines):])
        unused_count = 0
        for imp_line in import_lines:
            parts = imp_line.strip().split()
            if "as" in parts:
                name = parts[parts.index("as") + 1].rstrip(",")
            elif parts[0] == "import":
                name = parts[-1].rstrip(",").split(".")[-1]
            elif "import" in parts:
                name = parts[-1].rstrip(",")
            else:
                name = parts[-1].rstrip(",")
            if name and name not in body:
                unused_count += 1
        if unused_count > 0:
            scores["unused_import"] = 3
        elif len(import_lines) > 3:
            scores["unused_import"] = 2
        else:
            scores["unused_import"] = 1
    else:
        scores["unused_import"] = 0

    # ── naming_convention ──
    nc_score = 0
    func_names = re.findall(r"def\s+(\w+)\s*\(", code)
    class_names = re.findall(r"class\s+(\w+)", code)
    var_assigns = re.findall(r"^(\s*)(\w+)\s*=", code, re.MULTILINE)
    for fn in func_names:
        if fn != fn.lower() and not fn.startswith("_"):
            nc_score += 2
        if len(fn) == 1:
            nc_score += 1
    for cn in class_names:
        if cn == cn.lower():
            nc_score += 2
    for _, vn in var_assigns:
        if re.search(r"[a-z][A-Z]", vn) and vn != vn.lower():
            nc_score += 1
    scores["naming_convention"] = min(3, nc_score) if nc_score else (1 if func_names or class_names else 0)

    # ── indentation ──
    indent_levels: set[int] = set()
    has_tab = False
    has_space = False
    for l in lines:
        if l and l[0] in (" ", "\t"):
            leading = l[:len(l) - len(l.lstrip())]
            if "\t" in leading:
                has_tab = True
            if " " in leading:
                has_space = True
                indent_levels.add(len(leading))
    mixed = has_tab and has_space
    odd_indents = sum(1 for i in indent_levels if i % 4 != 0)
    if mixed:
        scores["indentation"] = 3
    elif odd_indents > 2:
        scores["indentation"] = 2
    elif len(indent_levels) > 0:
        scores["indentation"] = 1
    else:
        scores["indentation"] = 0

    # ── documentation_formatting ──
    has_docstring = '"""' in code or "'''" in code
    has_def = bool(func_names) or bool(class_names)
    if has_docstring:
        doc_issues = 0
        if re.search(r'"""[^\n]+\n\s*\S', code):
            doc_issues += 1
        if re.search(r'\S"""', code):
            doc_issues += 1
        scores["documentation_formatting"] = min(3, 1 + doc_issues)
    elif has_def:
        scores["documentation_formatting"] = 1
    else:
        scores["documentation_formatting"] = 0

    # ── mutable_default ──
    md_score = 0
    for match in re.finditer(r"def\s+\w+\s*\(([^)]*)\)", code, re.DOTALL):
        params = match.group(1)
        if re.search(r"=\s*\[\s*\]", params):
            md_score += 2
        if re.search(r"=\s*\{\s*\}", params):
            md_score += 2
        if re.search(r"=\s*set\s*\(", params):
            md_score += 2
        if re.search(r"=\s*list\s*\(", params):
            md_score += 1
        if re.search(r"=\s*dict\s*\(", params):
            md_score += 1
    scores["mutable_default"] = min(3, md_score)

    return scores


# ---------------------------------------------------------------------------
# Strategy S15 — Adaptive Budget + Refined Queries + Heuristic Reranking
# ---------------------------------------------------------------------------

def retrieve_with_context(
    code: str,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict]:
    """Production retrieval strategy (S15).

    Three-stage pipeline:
      1. **Predict** which violation categories are likely present in *code*
         using lightweight regex heuristics (confidence 0-3 per category).
      2. **Adaptive budget**: allocate retrieval slots per category
         proportionally to confidence (high=4, med=3, low=2, none=1).
      3. **Rerank**: boost search scores for chunks whose category matches
         high-confidence predictions; demote low-confidence ones.

    This achieves 59.6% precision, 96.3% recall, 0.625 MRR, 0.736 F1
    across 102 evaluation files — the best balanced strategy we tested.

    Parameters
    ----------
    code : str
        The full source code (or diff) to review.
    top_k : int
        Maximum number of chunks to return.

    Returns
    -------
    list[dict]
        Ranked list of retrieval chunks, each with keys:
        chunk_id, text, category, source_type, score, rerank_score.
    """
    preds = predict_categories(code)

    # Adaptive budget allocation
    budget: dict[str, int] = {}
    for cat, conf in preds.items():
        if conf >= 3:
            budget[cat] = 4
        elif conf >= 2:
            budget[cat] = 3
        elif conf >= 1:
            budget[cat] = 2
        else:
            budget[cat] = 1  # minimum 1 for recall safety

    # Retrieve with refined queries per category
    candidates: list[dict] = []
    seen_ids: set[str] = set()
    for cat, k in budget.items():
        q = REFINED_QUERIES[cat]
        hits = retrieve(q, top_k=k)
        for h in hits:
            if h["chunk_id"] not in seen_ids:
                seen_ids.add(h["chunk_id"])
                candidates.append(h)

    # Heuristic reranking
    for c in candidates:
        conf = preds.get(c["category"], 0)
        boost = _RERANK_BOOSTS.get(conf, 0)
        c["rerank_score"] = c["score"] + boost

    candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
    return candidates[:top_k]


# -- CLI --------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieve chunks from Qdrant")
    sub = parser.add_subparsers(dest="mode")

    # --- basic query mode ---
    q_parser = sub.add_parser("query", help="Single-query retrieval")
    q_parser.add_argument("text", help="Search query text")
    q_parser.add_argument("-k", "--top-k", type=int, default=DEFAULT_TOP_K,
                          help=f"Number of chunks to return (default: {DEFAULT_TOP_K})")
    q_parser.add_argument("--deduplicate", action="store_true",
                          help="Filter near-duplicate chunks from results")
    q_parser.add_argument("--threshold", type=float, default=DEDUP_SIMILARITY_THRESHOLD,
                          help=f"Cosine similarity threshold for dedup (default: {DEDUP_SIMILARITY_THRESHOLD})")
    q_parser.add_argument("--json", action="store_true", dest="json_out",
                          help="Output raw JSON instead of formatted table")

    # --- S15 code-context mode ---
    c_parser = sub.add_parser("code", help="S15 production strategy — retrieve by code context")
    c_parser.add_argument("file", help="Path to the Python source file")
    c_parser.add_argument("-k", "--top-k", type=int, default=DEFAULT_TOP_K,
                          help=f"Number of chunks to return (default: {DEFAULT_TOP_K})")
    c_parser.add_argument("--json", action="store_true", dest="json_out",
                          help="Output raw JSON instead of formatted table")

    args = parser.parse_args()

    if args.mode == "code":
        code = Path(args.file).read_text(encoding="utf-8")
        preds = predict_categories(code)
        results = retrieve_with_context(code, top_k=args.top_k)

        if args.json_out:
            print(json.dumps(results, indent=2, ensure_ascii=False))
            return

        print(f"\nFile: {args.file}")
        print(f"Predicted categories: {preds}")
        print(f"Results: {len(results)}  (strategy=S15)\n")
        print(f"{'#':<4} {'Score':>6} {'Rerank':>7}  {'Category':<26} {'Source':<24} Text")
        print("-" * 120)
        for i, r in enumerate(results, 1):
            text_preview = r["text"][:55].replace("\n", " ")
            print(
                f"{i:<4} {r['score']:>6.4f} {r.get('rerank_score', r['score']):>7.4f}  "
                f"{r['category']:<26} {r['source_type']:<24} {text_preview}"
            )
    else:
        # Default / query mode (backward compatible)
        if args.mode is None:
            parser.print_help()
            return
        results = retrieve(
            query=args.text,
            top_k=args.top_k,
            deduplicate=args.deduplicate,
            threshold=args.threshold,
        )

        if args.json_out:
            print(json.dumps(results, indent=2, ensure_ascii=False))
            return

        print(f"\nQuery: {args.text}")
        print(f"Results: {len(results)}  (deduplicate={'on' if args.deduplicate else 'off'})\n")
        print(f"{'#':<4} {'Score':>6}  {'Category':<26} {'Source':<24} {'Chunk ID':<12} Text")
        print("-" * 120)
        for i, r in enumerate(results, 1):
            text_preview = r["text"][:60].replace("\n", " ")
            print(
                f"{i:<4} {r['score']:>6.4f}  {r['category']:<26} "
                f"{r['source_type']:<24} {r['chunk_id']:<12} {text_preview}"
            )


if __name__ == "__main__":
    main()
