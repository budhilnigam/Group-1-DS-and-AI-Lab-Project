try:
    from .retrieve import retrieve, predict_categories
except ImportError:  # pragma: no cover - fallback when run as a script
    from retrieve import retrieve, predict_categories  # type: ignore

def _dedup_merge(hits_list, top_k):
    results, seen = [], set()
    for hits in hits_list:
        for h in hits:
            if h["chunk_id"] not in seen:
                seen.add(h["chunk_id"])
                results.append(h)
    return results[:top_k]

def _rerank(candidates, preds, boosts, top_k):
    for c in candidates:
        c["rerank_score"] = c["score"] + boosts.get(preds.get(c["category"], 0), 0)
    candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
    return candidates[:top_k]

REFINED_QUERIES = {
    "unused_import": "unused import module not used remove F401 W0611",
    "indentation": "indentation whitespace spaces tabs alignment PEP8 E1 W1",
    "naming_convention": "naming convention snake_case CamelCase PEP8 variable function class name",
    "documentation_formatting": "docstring formatting summary description numpy google style pep257 D100 D200",
    "mutable_default": "mutable default argument list dict set function parameter B006 W0102",
}

def s15_adapt_rerank_refined(code, repo_hint, top_k=10):
    preds = predict_categories(code)
    budget = {cat: {3: 4, 2: 3, 1: 2, 0: 1}[conf] for cat, conf in preds.items()}
    candidates = _dedup_merge(
        [retrieve(REFINED_QUERIES[cat], top_k=k) for cat, k in budget.items()], top_k * 3)
    return _rerank(candidates, preds, {3: 0.12, 2: 0.06, 1: 0.02, 0: -0.03}, top_k)