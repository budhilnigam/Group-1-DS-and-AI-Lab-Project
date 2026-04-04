"""Evaluate all 16 retrieval strategies on the full evaluation dataset.

Measures precision, category recall, MRR, and F1 for each strategy.
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from retrieve import retrieve, predict_categories

ROOT = Path(__file__).resolve().parent.parent

with open(ROOT / "data/processed/evaluation.json") as f:
    eval_data = json.load(f)

CATEGORIES = [
    "unused_import", "indentation", "naming_convention",
    "documentation_formatting", "mutable_default",
]

REFINED_QUERIES = {
    "unused_import": "unused import module not used remove F401 W0611",
    "indentation": "indentation whitespace spaces tabs alignment PEP8 E1 W1",
    "naming_convention": "naming convention snake_case CamelCase PEP8 variable function class name",
    "documentation_formatting": "docstring formatting summary description numpy google style pep257 D100 D200",
    "mutable_default": "mutable default argument list dict set function parameter B006 W0102",
}


def _dedup_merge(hits_list, top_k):
    results, seen = [], set()
    for hits in hits_list:
        for h in hits:
            if h["chunk_id"] not in seen:
                seen.add(h["chunk_id"])
                results.append(h)
    return results[:top_k]


def _per_cat_retrieve(categories, query_fn, top_k, per_cat_k=None):
    if per_cat_k is None:
        per_cat_k = max(2, top_k // len(categories))
    return _dedup_merge(
        [retrieve(query_fn(cat), top_k=per_cat_k) for cat in categories],
        top_k,
    )


def _rerank(candidates, preds, boosts, top_k):
    for c in candidates:
        c["rerank_score"] = c["score"] + boosts.get(preds.get(c["category"], 0), 0)
    candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
    return candidates[:top_k]


def extract_repo_hint(entry):
    repo = entry.get("repo", "") + entry.get("id", "")
    for fw in ["django", "flask", "fastapi", "pandas", "sklearn"]:
        if fw in repo.lower():
            return fw
    return "python"


# ── Strategies ──

def s1_code_only(code, repo_hint, top_k=10):
    return retrieve(code[:500], top_k=top_k)


def s2_per_category(code, repo_hint, top_k=10):
    return _per_cat_retrieve(CATEGORIES, lambda c: "{} violation in Python code".format(c), top_k)


def s3_code_plus_category(code, repo_hint, top_k=10):
    prefix = code[:200].replace("\n", " ")
    return _per_cat_retrieve(CATEGORIES, lambda c: "Code review for {} violation: {}".format(c, prefix), top_k)


def s4_repo_category(code, repo_hint, top_k=10):
    return _per_cat_retrieve(
        CATEGORIES, lambda c: "{} {} code review guidelines and best practices".format(repo_hint, c), top_k)


def s5_hybrid(code, repo_hint, top_k=10):
    code_k = top_k // 2
    cat_hits = [retrieve("{} {} code review guidelines and best practices".format(repo_hint, c),
                         top_k=max(2, (top_k - code_k) // 5)) for c in CATEGORIES]
    return _dedup_merge([retrieve(code[:500], top_k=code_k)] + cat_hits, top_k)


def s6_code_repo_category(code, repo_hint, top_k=10):
    lines = code.split("\n")
    imports = [l.strip() for l in lines[:20] if l.strip().startswith(("import ", "from "))]
    code_hint = " ".join(imports[:5]) if imports else code[:150]
    queries = {
        "unused_import": "{} unused import detection. Code has imports: {}".format(repo_hint, code_hint[:200]),
        "documentation_formatting": "{} docstring formatting rules structure indentation numpy google style".format(repo_hint),
        "naming_convention": "{} naming convention snake_case CamelCase PEP8 function class variable names".format(repo_hint),
        "indentation": "{} indentation 4 spaces tabs consistent code formatting".format(repo_hint),
        "mutable_default": "{} mutable default argument list dict set function parameter".format(repo_hint),
    }
    return _per_cat_retrieve(CATEGORIES, lambda c: queries[c], top_k)


def s7_heuristic_filter(code, repo_hint, top_k=10):
    active = [c for c, s in predict_categories(code).items() if s >= 1] or CATEGORIES[:]
    return _per_cat_retrieve(active, lambda c: "{} violation in Python code".format(c), top_k)


def s8_adaptive_budget(code, repo_hint, top_k=10):
    budget = {cat: {3: 3, 2: 2, 1: 1, 0: 0}[conf] for cat, conf in predict_categories(code).items()}
    if sum(budget.values()) == 0:
        budget = {c: 2 for c in CATEGORIES}
    return _dedup_merge(
        [retrieve("{} violation in Python code".format(cat), top_k=k) for cat, k in budget.items() if k > 0],
        top_k)


def s9_two_phase(code, repo_hint, top_k=10):
    phase1 = retrieve(code[:500], top_k=5)
    detected = set(h["category"] for h in phase1)
    for cat, conf in predict_categories(code).items():
        if conf >= 2:
            detected.add(cat)
    detected = detected or set(CATEGORIES)
    cat_hits = [retrieve("{} violation in Python code".format(c), top_k=max(2, top_k // len(detected)))
                for c in detected]
    return _dedup_merge([phase1] + cat_hits, top_k)


def s10_refined_queries(code, repo_hint, top_k=10):
    return _per_cat_retrieve(CATEGORIES, lambda c: REFINED_QUERIES[c], top_k)


def s11_refined_heuristic(code, repo_hint, top_k=10):
    active = [c for c, s in predict_categories(code).items() if s >= 1] or CATEGORIES[:]
    return _per_cat_retrieve(active, lambda c: REFINED_QUERIES[c], top_k)


def s12_score_rerank(code, repo_hint, top_k=10):
    preds = predict_categories(code)
    per_cat_k = max(3, (top_k * 2) // 5)
    candidates = _dedup_merge(
        [retrieve("{} violation in Python code".format(c), top_k=per_cat_k) for c in CATEGORIES], top_k * 3)
    return _rerank(candidates, preds, {3: 0.10, 2: 0.05, 1: 0.02, 0: -0.05}, top_k)


def s13_adapt_refined_repo(code, repo_hint, top_k=10):
    active = [c for c, s in predict_categories(code).items() if s >= 1] or CATEGORIES[:]
    queries = {
        "unused_import": "{} unused import module not used remove cleanup".format(repo_hint),
        "documentation_formatting": "{} docstring formatting summary blank line closing triple quote pep257".format(repo_hint),
        "naming_convention": "{} naming convention snake_case CamelCase PEP8 function class variable".format(repo_hint),
        "indentation": "{} indentation whitespace spaces tabs consistent alignment".format(repo_hint),
        "mutable_default": "{} mutable default argument list dict set function parameter".format(repo_hint),
    }
    return _per_cat_retrieve(active, lambda c: queries.get(c, "{} {} violation".format(repo_hint, c)), top_k)


def s14_adapt_rerank(code, repo_hint, top_k=10):
    preds = predict_categories(code)
    budget = {cat: {3: 4, 2: 3, 1: 2, 0: 1}[conf] for cat, conf in preds.items()}
    candidates = _dedup_merge(
        [retrieve("{} violation in Python code".format(cat), top_k=k) for cat, k in budget.items()], top_k * 3)
    return _rerank(candidates, preds, {3: 0.12, 2: 0.06, 1: 0.02, 0: -0.03}, top_k)


def s15_adapt_rerank_refined(code, repo_hint, top_k=10):
    preds = predict_categories(code)
    budget = {cat: {3: 4, 2: 3, 1: 2, 0: 1}[conf] for cat, conf in preds.items()}
    candidates = _dedup_merge(
        [retrieve(REFINED_QUERIES[cat], top_k=k) for cat, k in budget.items()], top_k * 3)
    return _rerank(candidates, preds, {3: 0.12, 2: 0.06, 1: 0.02, 0: -0.03}, top_k)


def s16_rerank_guarantee(code, repo_hint, top_k=10):
    preds = predict_categories(code)
    per_cat_k = max(3, (top_k * 2) // 5)
    best_per_cat = {}
    all_hits = []
    for cat in CATEGORIES:
        hits = retrieve("{} violation in Python code".format(cat), top_k=per_cat_k)
        all_hits.append(hits)
        if hits:
            best_per_cat[cat] = hits[0]
    candidates = _dedup_merge(all_hits, top_k * 3)
    candidates = _rerank(candidates, preds, {3: 0.10, 2: 0.05, 1: 0.02, 0: -0.05}, top_k * 3)

    guaranteed_ids = set()
    results = []
    for cat in CATEGORIES:
        if cat in best_per_cat:
            results.append(best_per_cat[cat])
            guaranteed_ids.add(best_per_cat[cat]["chunk_id"])
    for c in candidates:
        if len(results) >= top_k:
            break
        if c["chunk_id"] not in guaranteed_ids:
            results.append(c)
    return results[:top_k]


STRATEGIES = {
    "S1_code_only":             s1_code_only,
    "S2_per_category":          s2_per_category,
    "S3_code_plus_category":    s3_code_plus_category,
    "S4_repo_category":         s4_repo_category,
    "S5_hybrid":                s5_hybrid,
    "S6_code_repo_category":    s6_code_repo_category,
    "S7_heuristic_filter":      s7_heuristic_filter,
    "S8_adaptive_budget":       s8_adaptive_budget,
    "S9_two_phase":             s9_two_phase,
    "S10_refined_queries":      s10_refined_queries,
    "S11_refined_heuristic":    s11_refined_heuristic,
    "S12_score_rerank":         s12_score_rerank,
    "S13_adapt_refined_repo":   s13_adapt_refined_repo,
    "S14_adapt_rerank":         s14_adapt_rerank,
    "S15_adapt_rerank_refined": s15_adapt_rerank_refined,
    "S16_rerank_guarantee":     s16_rerank_guarantee,
}


# ── Evaluation ──

def evaluate_strategy(strategy_fn, entries, top_k=10):
    total_retrieved, total_relevant = 0, 0
    category_covered, category_total = Counter(), Counter()
    per_file_precision, reciprocal_ranks = [], []

    for entry in entries:
        gt_cats = set(r["violation_category"] for r in entry["ground_truth_reviews"])
        if not gt_cats:
            continue
        code_path = ROOT / "data/processed/evaluation_files" / entry["source_file"].replace("evaluation_files/", "")
        code = code_path.read_text()
        results = strategy_fn(code, extract_repo_hint(entry), top_k=top_k)

        relevant = sum(1 for r in results if r["category"] in gt_cats)
        retrieved_cats = set(r["category"] for r in results)
        total_retrieved += len(results)
        total_relevant += relevant
        per_file_precision.append(relevant / len(results) if results else 0)

        for cat in gt_cats:
            category_total[cat] += 1
            if cat in retrieved_cats:
                category_covered[cat] += 1
            rank = next((i + 1 for i, r in enumerate(results) if r["category"] == cat), 0)
            reciprocal_ranks.append(1.0 / rank if rank > 0 else 0.0)

    precision = total_relevant / total_retrieved if total_retrieved else 0
    cat_recall = {cat: category_covered[cat] / category_total[cat] if category_total[cat] > 0 else 0.0
                  for cat in CATEGORIES}
    return {
        "precision": precision,
        "avg_category_recall": sum(cat_recall.values()) / len(cat_recall),
        "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0,
        "category_recall": cat_recall,
        "avg_file_precision": sum(per_file_precision) / len(per_file_precision) if per_file_precision else 0,
    }


if __name__ == "__main__":
    entries = [e for e in eval_data if e.get("ground_truth_reviews")]
    print("Evaluating {} strategies on {} eval entries\n".format(len(STRATEGIES), len(entries)))

    results_summary = {}
    for name, fn in STRATEGIES.items():
        print("Running {} ...".format(name), end=" ", flush=True)
        res = evaluate_strategy(fn, entries, top_k=10)
        results_summary[name] = res
        print("P={:.1%} R={:.1%} MRR={:.3f}".format(res["precision"], res["avg_category_recall"], res["mrr"]))

    print("\n" + "=" * 90)
    print("{:<28} {:>10} {:>10} {:>8} {:>8}".format("Strategy", "Precision", "Recall", "MRR", "F1"))
    print("-" * 90)
    for name in STRATEGIES:
        r = results_summary[name]
        p, rec = r["precision"], r["avg_category_recall"]
        f1 = 2 * p * rec / (p + rec) if (p + rec) > 0 else 0
        print("{:<28} {:>9.1%} {:>9.1%} {:>8.3f} {:>8.3f}".format(name, p, rec, r["mrr"], f1))

    print("\n" + "=" * 90)
    print("Per-category recall:")
    header = "{:<28}".format("Strategy")
    for cat in CATEGORIES:
        header += " {:>12}".format(cat[:12])
    print(header)
    print("-" * 90)
    for name in STRATEGIES:
        r = results_summary[name]
        line = "{:<28}".format(name)
        for cat in CATEGORIES:
            line += " {:>11.1%}".format(r["category_recall"].get(cat, 0))
        print(line)
