"""Evaluate static analysis tools against evaluation ground truth.

Combines all static analysis evaluation steps:
  1. Run flake8 + pylint on evaluation files, map to five categories
  2. Compare detections against GT with 3-tier matching (exact/semantic/category)
  3. Threshold sweep for doc-formatting semantic matching
  4. Inspect doc-formatting text patterns

Usage:
  python scripts/evaluate_static_analysis.py              # run all
  python scripts/evaluate_static_analysis.py scan         # step 1 only
  python scripts/evaluate_static_analysis.py compare      # step 2 only
  python scripts/evaluate_static_analysis.py sweep        # step 3 only
  python scripts/evaluate_static_analysis.py inspect      # step 4 only
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = ROOT / "data" / "processed" / "evaluation_files"
EVAL_PATH = ROOT / "data" / "processed" / "evaluation.json"
STATIC_PATH = ROOT / "data" / "processed" / "static_analysis_results.json"

DOC_SIM_THRESHOLD = 0.80
EMBED_MODEL = "BAAI/bge-large-en-v1.5"

# ── Flake8 code → category mapping ──

FLAKE8_MAP: dict[str, str] = {}

for _code in [
    "E101", "E111", "E112", "E113", "E114", "E115", "E116", "E117",
    "E121", "E122", "E123", "E124", "E125", "E126", "E127", "E128",
    "E129", "E131", "E133",
]:
    FLAKE8_MAP[_code] = "indentation"
FLAKE8_MAP["W191"] = "indentation"

for _code in [
    "N801", "N802", "N803", "N804", "N805", "N806", "N807",
    "N811", "N812", "N813", "N814", "N815", "N816", "N817", "N818",
]:
    FLAKE8_MAP[_code] = "naming_convention"

FLAKE8_MAP["F401"] = "unused_import"
FLAKE8_MAP["B006"] = "mutable_default"
FLAKE8_MAP["B008"] = "mutable_default"

for _prefix in ["D1", "D2", "D3", "D4"]:
    for _i in range(100):
        FLAKE8_MAP[f"D{_prefix[1]}{_i:02d}"] = "documentation_formatting"

# ── Pylint code → category mapping ──

PYLINT_MAP: dict[str, str] = {
    "W0311": "indentation", "bad-indentation": "indentation",
    "C0103": "naming_convention", "invalid-name": "naming_convention",
    "C0104": "naming_convention", "disallowed-name": "naming_convention",
    "C0105": "naming_convention", "typevar-name-incorrect-variance": "naming_convention",
    "C0132": "naming_convention", "typevar-name-mismatch": "naming_convention",
    "C2401": "naming_convention", "non-ascii-name": "naming_convention",
    "W3201": "naming_convention", "bad-dunder-name": "naming_convention",
    "W0611": "unused_import", "unused-import": "unused_import",
    "W0614": "unused_import", "unused-wildcard-import": "unused_import",
    "W0404": "unused_import", "reimported": "unused_import",
    "W0406": "unused_import", "import-self": "unused_import",
    "W0102": "mutable_default", "dangerous-default-value": "mutable_default",
    "C0114": "documentation_formatting", "missing-module-docstring": "documentation_formatting",
    "C0115": "documentation_formatting", "missing-class-docstring": "documentation_formatting",
    "C0116": "documentation_formatting", "missing-function-docstring": "documentation_formatting",
    "C0112": "documentation_formatting", "empty-docstring": "documentation_formatting",
    "C0199": "documentation_formatting", "docstring-first-line-empty": "documentation_formatting",
}

_strip_code_re = re.compile(r"^\[?[A-Z]\d{3,4}\]?\s*")


def _clean(text: str) -> str:
    return _strip_code_re.sub("", text).strip()


def _match_flake8_code(code: str) -> str | None:
    if code in FLAKE8_MAP:
        return FLAKE8_MAP[code]
    for prefix_len in [4, 3, 2]:
        prefix = code[:prefix_len]
        if prefix in FLAKE8_MAP:
            return FLAKE8_MAP[prefix]
    return None


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


# ═══════════════════════════════════════════════════════════════════════════════
# Step 1: Scan — run flake8 + pylint on evaluation files
# ═══════════════════════════════════════════════════════════════════════════════

def run_flake8(filepath: Path) -> list[dict]:
    cmd = [
        sys.executable, "-m", "flake8",
        "--select", "E1,W191,F401,N8,B006,B008,D",
        "--max-line-length", "999",
        "--format", "%(path)s:%(row)d:%(col)d: %(code)s %(text)s",
        str(filepath),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    violations: list[dict] = []
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        try:
            parts = line.split(":", 3)
            row = int(parts[1])
            rest = parts[3].strip()
            code = rest.split()[0]
            message = rest[len(code):].strip()
        except (IndexError, ValueError):
            continue
        category = _match_flake8_code(code)
        if category:
            violations.append({"tool": "flake8", "code": code, "category": category,
                               "line": row, "message": message})
    return violations


def run_pylint(filepath: Path) -> list[dict]:
    cmd = [
        sys.executable, "-m", "pylint",
        "--disable=all",
        "--enable="
        "W0311,C0103,C0104,C0105,C0132,C2401,W3201,"
        "W0611,W0614,W0404,W0406,"
        "W0102,"
        "C0114,C0115,C0116,C0112,C0199",
        "--output-format=json",
        "--max-line-length=999",
        str(filepath),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    violations: list[dict] = []
    if not result.stdout.strip():
        return violations
    try:
        messages = json.loads(result.stdout)
    except json.JSONDecodeError:
        return violations
    for msg in messages:
        code = msg.get("message-id", "")
        symbol = msg.get("symbol", "")
        category = PYLINT_MAP.get(code) or PYLINT_MAP.get(symbol)
        if category:
            violations.append({"tool": "pylint", "code": code, "symbol": symbol,
                               "category": category, "line": msg.get("line", 0),
                               "message": msg.get("message", "")})
    return violations


def cmd_scan() -> None:
    """Run flake8 + pylint on all evaluation files."""
    py_files = sorted(EVAL_DIR.glob("*.py"))
    if not py_files:
        print(f"No .py files found in {EVAL_DIR}")
        return

    print(f"Scanning {len(py_files)} files in {EVAL_DIR}\n")
    all_results: list[dict] = []
    total_violations = 0

    for filepath in py_files:
        fname = filepath.name
        print(f"  {fname} ... ", end="", flush=True)
        flake8_v = run_flake8(filepath)
        pylint_v = run_pylint(filepath)

        seen: set[tuple[str, int]] = set()
        merged: list[dict] = []
        for v in flake8_v + pylint_v:
            key = (v["category"], v["line"])
            if key not in seen:
                seen.add(key)
                merged.append(v)
        merged.sort(key=lambda v: (v["category"], v["line"]))

        all_results.append({"file": fname, "violations": merged})
        count = len(merged)
        total_violations += count
        cats: dict[str, int] = {}
        for v in merged:
            cats[v["category"]] = cats.get(v["category"], 0) + 1
        summary = ", ".join(f"{c}:{n}" for c, n in sorted(cats.items()))
        print(f"{count} violations  ({summary})" if count else "clean")

    STATIC_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATIC_PATH, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    cat_totals: dict[str, int] = {}
    for entry in all_results:
        for v in entry["violations"]:
            cat_totals[v["category"]] = cat_totals.get(v["category"], 0) + 1

    print(f"\n{'='*60}")
    print(f"Total files     : {len(py_files)}")
    print(f"Total violations: {total_violations}")
    print(f"\nBy category:")
    for cat, count in sorted(cat_totals.items()):
        print(f"  {cat:<28} {count}")
    print(f"\nSaved to: {STATIC_PATH}")


# ═══════════════════════════════════════════════════════════════════════════════
# Step 2: Compare — static detections vs evaluation ground truth
# ═══════════════════════════════════════════════════════════════════════════════

def _load_embed_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBED_MODEL)


def cmd_compare() -> None:
    """Compare static analysis results against evaluation GT."""
    with open(EVAL_PATH) as f:
        eval_data = json.load(f)
    with open(STATIC_PATH) as f:
        static_data = json.load(f)

    static_lookup: dict[str, set[tuple[str, int]]] = {}
    static_violations: dict[str, list[dict]] = {}
    for entry in static_data:
        static_lookup[entry["file"]] = {(v["category"], v["line"]) for v in entry["violations"]}
        static_violations[entry["file"]] = entry["violations"]

    # Precompute doc-formatting embeddings
    print("Loading embedding model for doc-formatting semantic match ...")
    model = _load_embed_model()

    gt_doc_texts: set[str] = set()
    for entry in eval_data:
        for r in entry.get("ground_truth_reviews", []):
            if r["violation_category"] == "documentation_formatting":
                gt_doc_texts.add(r["review_comment"])
    st_doc_texts: set[str] = set()
    for vlist in static_violations.values():
        for v in vlist:
            if v["category"] == "documentation_formatting":
                st_doc_texts.add(v["message"])
    all_texts = sorted(gt_doc_texts | st_doc_texts)
    text_to_idx = {t: i for i, t in enumerate(all_texts)}
    embeddings = model.encode([_clean(t) for t in all_texts],
                              normalize_embeddings=True, show_progress_bar=False)
    print(f"Embedded {len(all_texts)} unique doc-formatting texts.\n")

    def best_sim(gt_text: str, st_messages: list[str]) -> tuple[float, str]:
        if not st_messages:
            return 0.0, ""
        gt_vec = embeddings[text_to_idx[gt_text]]
        sims = [(_cosine(gt_vec, embeddings[text_to_idx[m]]), m) for m in st_messages]
        best = max(sims, key=lambda x: x[0])
        return best[0], best[1]

    # Main comparison
    tp = tp_cat = tp_sem = fn = fp = gt_total = 0
    cat_tp: Counter[str] = Counter()
    cat_tp_cat: Counter[str] = Counter()
    cat_tp_sem: Counter[str] = Counter()
    cat_fn: Counter[str] = Counter()
    cat_gt: Counter[str] = Counter()
    matched: list[tuple] = []
    missed: list[tuple] = []
    sem_matched: list[tuple] = []
    sem_missed: list[tuple] = []

    for entry in eval_data:
        fname = entry["source_file"].replace("evaluation_files/", "")
        gt_set: set[tuple[str, int]] = set()

        for r in entry.get("ground_truth_reviews", []):
            gt_total += 1
            cat = r["violation_category"]
            line = r["line_number"]
            cat_gt[cat] += 1
            gt_set.add((cat, line))
            svs = static_lookup.get(fname, set())

            if (cat, line) in svs:
                tp += 1
                cat_tp[cat] += 1
                matched.append((fname, cat, line, "exact"))
            elif cat == "documentation_formatting":
                st_msgs = [v["message"] for v in static_violations.get(fname, [])
                           if v["category"] == "documentation_formatting"]
                sim, best_st_msg = best_sim(r["review_comment"], st_msgs)
                if sim >= DOC_SIM_THRESHOLD:
                    tp_sem += 1
                    cat_tp_sem[cat] += 1
                    matched.append((fname, cat, line, f"semantic({sim:.2f})"))
                    sem_matched.append((fname, line, sim, r["review_comment"], best_st_msg))
                else:
                    fn += 1
                    cat_fn[cat] += 1
                    missed.append((fname, cat, line, r["review_comment"][:60]))
                    sem_missed.append((fname, line, sim, r["review_comment"], best_st_msg))
            else:
                cat_lines = sorted(l for (c, l) in svs if c == cat)
                if cat_lines:
                    tp_cat += 1
                    cat_tp_cat[cat] += 1
                    matched.append((fname, cat, line, f"cat_match @{cat_lines[:5]}"))
                else:
                    fn += 1
                    cat_fn[cat] += 1
                    missed.append((fname, cat, line, r["review_comment"][:60]))

        for (cat, line) in static_lookup.get(fname, set()):
            if (cat, line) not in gt_set:
                fp += 1

    total_matched = tp + tp_cat + tp_sem
    print(f"Ground truth reviews       : {gt_total}")
    print(f"Exact match (file+cat+line): {tp}  ({tp / gt_total * 100:.1f}%)")
    print(f"Semantic match (doc-fmt)   : {tp_sem}  ({tp_sem / gt_total * 100:.1f}%)")
    print(f"Category match (diff line) : {tp_cat}  ({tp_cat / gt_total * 100:.1f}%)")
    print(f"Missed (false negative)    : {fn}  ({fn / gt_total * 100:.1f}%)")
    print(f"Extra  (false positive)    : {fp}")
    print(f"\nTotal matched              : {total_matched}  ({total_matched / gt_total * 100:.1f}%)")

    print(f"\n{'Category':<28} {'GT':>4} {'Exact':>6} {'Sem':>5} {'CatM':>5} {'Miss':>5} {'MatchRate':>10}")
    print("-" * 70)
    for cat in sorted(cat_gt):
        gt = cat_gt[cat]
        ex = cat_tp[cat]
        sm = cat_tp_sem.get(cat, 0)
        cm = cat_tp_cat[cat]
        ms = cat_fn[cat]
        rate = (ex + sm + cm) / gt * 100 if gt else 0
        print(f"{cat:<28} {gt:>4} {ex:>6} {sm:>5} {cm:>5} {ms:>5} {rate:>9.1f}%")

    print(f"\n--- Sample exact matches (first 10) ---")
    count = 0
    for f, c, l, s in matched:
        if s == "exact":
            print(f"  {f}:{l}  {c}")
            count += 1
            if count >= 10:
                break

    print(f"\n--- Sample semantic matches (first 10) ---")
    count = 0
    for f, c, l, s in matched:
        if s.startswith("semantic"):
            print(f"  {f}:{l}  {c}  {s}")
            count += 1
            if count >= 10:
                break

    print(f"\n--- Sample misses (first 15) ---")
    for f, c, l, m in missed[:15]:
        print(f"  {f}:{l}  {c}  \"{m}\"")

    print(f"\n{'='*80}")
    print(f"SEMANTIC MATCH DETAIL (threshold={DOC_SIM_THRESHOLD})  —  doc-formatting only")
    print(f"{'='*80}")

    print(f"\n--- MATCHED (sim >= {DOC_SIM_THRESHOLD}) : {len(sem_matched)} pairs ---")
    for fname, line, sim, gt_t, st_t in sorted(sem_matched, key=lambda x: -x[2]):
        print(f"  sim={sim:.4f}  {fname}:{line}")
        print(f"    GT : {gt_t}")
        print(f"    ST : {st_t}")
        print()

    print(f"--- NOT MATCHED (sim < {DOC_SIM_THRESHOLD}) : {len(sem_missed)} pairs ---")
    for fname, line, sim, gt_t, st_t in sorted(sem_missed, key=lambda x: -x[2]):
        print(f"  sim={sim:.4f}  {fname}:{line}")
        print(f"    GT : {gt_t}")
        print(f"    ST : {st_t if st_t else '(no static doc violations in file)'}")
        print()


# ═══════════════════════════════════════════════════════════════════════════════
# Step 3: Sweep — find best similarity threshold for doc-formatting
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_sweep() -> None:
    """Threshold sweep for doc-formatting semantic matching."""
    with open(EVAL_PATH) as f:
        eval_data = json.load(f)
    with open(STATIC_PATH) as f:
        static_data = json.load(f)

    static_lookup: dict[str, list[dict]] = {}
    for entry in static_data:
        static_lookup[entry["file"]] = entry["violations"]

    pairs: list[dict] = []
    for e in eval_data:
        fname = e["source_file"].replace("evaluation_files/", "")
        st_docs = [v for v in static_lookup.get(fname, [])
                   if v["category"] == "documentation_formatting"]
        if not st_docs:
            continue
        for r in e.get("ground_truth_reviews", []):
            if r["violation_category"] != "documentation_formatting":
                continue
            pairs.append({
                "file": fname,
                "gt_line": r["line_number"],
                "gt_comment": r["review_comment"],
                "st_candidates": [{"line": v["line"], "message": v["message"], "code": v["code"]}
                                  for v in st_docs],
            })

    print(f"Doc-formatting GT violations with static candidates: {len(pairs)}")
    if not pairs:
        print("No pairs to test.")
        return

    model = _load_embed_model()
    all_gt_texts = list({p["gt_comment"] for p in pairs})
    all_st_texts = list({c["message"] for p in pairs for c in p["st_candidates"]})
    print(f"Unique GT texts: {len(all_gt_texts)}")
    print(f"Unique ST texts: {len(all_st_texts)}")

    gt_embs = model.encode(all_gt_texts, normalize_embeddings=True, convert_to_numpy=True)
    st_embs = model.encode(all_st_texts, normalize_embeddings=True, convert_to_numpy=True)
    gt_emb_map = {t: gt_embs[i] for i, t in enumerate(all_gt_texts)}
    st_emb_map = {t: st_embs[i] for i, t in enumerate(all_st_texts)}

    print("\n=== Per-pair best similarities ===")
    best_sims: list[float] = []
    pair_details: list[tuple] = []

    for p in pairs:
        gt_vec = gt_emb_map[p["gt_comment"]]
        best_sim_val = -1.0
        best_st = None
        for c in p["st_candidates"]:
            st_vec = st_emb_map[c["message"]]
            sim = float(np.dot(gt_vec, st_vec))
            if sim > best_sim_val:
                best_sim_val = sim
                best_st = c
        best_sims.append(best_sim_val)
        pair_details.append((p["file"], p["gt_line"], p["gt_comment"][:50],
                             best_st["line"] if best_st else -1,
                             best_st["message"][:50] if best_st else "",
                             best_sim_val))

    pair_details.sort(key=lambda x: x[5], reverse=True)
    for fname, gt_line, gt_txt, st_line, st_txt, sim in pair_details[:20]:
        tag = "LINE_MATCH" if gt_line == st_line else f"line_diff({gt_line}vs{st_line})"
        print(f"  sim={sim:.4f} {tag:20s} GT=\"{gt_txt}\"  ST=\"{st_txt}\"")
    print("\n...")
    for fname, gt_line, gt_txt, st_line, st_txt, sim in pair_details[-10:]:
        tag = "LINE_MATCH" if gt_line == st_line else f"line_diff({gt_line}vs{st_line})"
        print(f"  sim={sim:.4f} {tag:20s} GT=\"{gt_txt}\"  ST=\"{st_txt}\"")

    print(f"\n=== Threshold sweep ===")
    print(f"{'Threshold':>10} {'Matched':>8} {'Missed':>7} {'Total':>6} {'Rate':>7}")
    print("-" * 45)
    total = len(best_sims)
    for thresh in [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]:
        n_matched = sum(1 for s in best_sims if s >= thresh)
        print(f"{thresh:>10.2f} {n_matched:>8} {total - n_matched:>7} {total:>6} "
              f"{n_matched / total * 100:>6.1f}%")

    arr = np.array(best_sims)
    print(f"\n=== Similarity distribution ===")
    for pctl in [0, 10, 25, 50, 75, 90, 100]:
        print(f"  p{pctl:>3}: {np.percentile(arr, pctl):.4f}")
    print(f"  mean: {arr.mean():.4f}")
    print(f"  std:  {arr.std():.4f}")


# ═══════════════════════════════════════════════════════════════════════════════
# Step 4: Inspect — doc-formatting text patterns
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_inspect() -> None:
    """Inspect doc-formatting text patterns: GT review_comments vs static tool messages."""
    with open(EVAL_PATH) as f:
        eval_data = json.load(f)
    with open(STATIC_PATH) as f:
        static_data = json.load(f)

    static_lookup: dict[str, list[dict]] = {}
    for entry in static_data:
        static_lookup[entry["file"]] = entry["violations"]

    gt_texts: set[str] = set()
    for e in eval_data:
        for r in e.get("ground_truth_reviews", []):
            if r["violation_category"] == "documentation_formatting":
                gt_texts.add(r["review_comment"])

    print("=== Unique GT review_comments (documentation_formatting) ===")
    for t in sorted(gt_texts):
        print(f"  {t}")

    static_texts: set[str] = set()
    for entry in static_data:
        for v in entry["violations"]:
            if v["category"] == "documentation_formatting":
                static_texts.add(f"[{v['tool']}:{v['code']}] {v['message']}")

    print(f"\n=== Unique static messages (documentation_formatting) ===")
    for t in sorted(static_texts):
        print(f"  {t}")

    print(f"\n=== PAIRED EXAMPLES (first 5 files) ===")
    count = 0
    for e in eval_data:
        fname = e["source_file"].replace("evaluation_files/", "")
        gt_docs = [(r["line_number"], r["review_comment"])
                   for r in e.get("ground_truth_reviews", [])
                   if r["violation_category"] == "documentation_formatting"]
        if not gt_docs:
            continue
        st_docs = [(v["line"], v["message"], v["code"])
                   for v in static_lookup.get(fname, [])
                   if v["category"] == "documentation_formatting"]
        print(f"\n  File: {fname}")
        for line, comment in gt_docs:
            print(f"    GT  line {line}: {comment}")
        for line, msg, code in st_docs:
            print(f"    ST  line {line}: [{code}] {msg}")
        count += 1
        if count >= 5:
            break


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

COMMANDS = {
    "scan": cmd_scan,
    "compare": cmd_compare,
    "sweep": cmd_sweep,
    "inspect": cmd_inspect,
}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd not in COMMANDS:
            print(f"Unknown command: {cmd}")
            print(f"Available: {', '.join(COMMANDS)}")
            sys.exit(1)
        COMMANDS[cmd]()
    else:
        # Run all steps
        print("=" * 80)
        print("STEP 1: Scan evaluation files with flake8 + pylint")
        print("=" * 80)
        cmd_scan()
        print("\n\n")
        print("=" * 80)
        print("STEP 2: Compare static detections vs ground truth")
        print("=" * 80)
        cmd_compare()
        print("\n\n")
        print("=" * 80)
        print("STEP 3: Threshold sweep for doc-formatting semantic matching")
        print("=" * 80)
        cmd_sweep()
        print("\n\n")
        print("=" * 80)
        print("STEP 4: Inspect doc-formatting text patterns")
        print("=" * 80)
        cmd_inspect()
