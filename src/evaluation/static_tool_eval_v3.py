import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path


TARGET_CATEGORIES = {
    "naming_convention",
    "unused_import",
    "indentation",
    "mutable_default",
    "documentation_formatting",
}


def load_evaluation_map(evaluation_path: Path):
    data = json.loads(evaluation_path.read_text(encoding="utf-8"))
    pr_map = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        pr_id = item.get("id")
        if not pr_id:
            continue
        reviews = item.get("ground_truth_reviews") or []
        normalized = []
        for r in reviews:
            if not isinstance(r, dict):
                continue
            normalized.append(
                {
                    "line_number": r.get("line_number"),
                    "violation_category": r.get("violation_category"),
                    "review_comment": r.get("review_comment"),
                }
            )
        pr_map[pr_id] = normalized
    return pr_map


def map_pylint_to_category(msg: dict):
    symbol = (msg.get("symbol") or "").strip().lower()
    message_id = (msg.get("message-id") or "").strip().upper()

    if symbol == "unused-import" or message_id == "W0611":
        return "unused_import"
    if symbol == "invalid-name" or message_id == "C0103":
        return "naming_convention"
    if symbol == "bad-indentation" or message_id == "W0311":
        return "indentation"
    if symbol == "dangerous-default-value" or message_id == "W0102":
        return "mutable_default"

    doc_symbols = {"missing-module-docstring", "missing-class-docstring", "missing-function-docstring"}
    doc_ids = {"C0114", "C0115", "C0116"}
    if symbol in doc_symbols or message_id in doc_ids:
        return "documentation_formatting"

    return None


def map_flake8_to_category(code: str, text: str):
    c = (code or "").strip().upper()
    t = (text or "").lower()

    if c == "F401":
        return "unused_import"
    if c in {"B006", "B008"}:
        return "mutable_default"
    if c.startswith("N"):
        return "naming_convention"

    indentation_codes = {
        "E111",
        "E112",
        "E113",
        "E114",
        "E115",
        "E116",
        "E117",
        "E121",
        "E122",
        "E123",
        "E124",
        "E125",
        "E126",
        "E127",
        "E128",
        "E129",
        "E131",
        "W191",
    }
    if c in indentation_codes:
        return "indentation"

    if c.startswith("D") or "docstring" in t:
        return "documentation_formatting"

    return None


def run_pylint(file_path: Path):
    cmd = [sys.executable, "-m", "pylint", str(file_path), "--output-format=json", "--score=n"]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    raw = (proc.stdout or "").strip()
    if not raw:
        return [], None
    try:
        payload = json.loads(raw)
    except Exception:
        return [], None

    findings = []
    if not isinstance(payload, list):
        return findings, None

    for msg in payload:
        if not isinstance(msg, dict):
            continue
        category = map_pylint_to_category(msg)
        if category is None:
            continue
        line = msg.get("line")
        findings.append(
            {
                "tool": "pylint",
                "line_number_raw": line,
                "line_number_adjusted": line if isinstance(line, int) else line,
                "violation_category": category,
                "review_comment": f"pylint[{msg.get('symbol') or msg.get('message-id')}]: {msg.get('message', '')}",
            }
        )

    return findings, None


def run_flake8(file_path: Path):
    cmd = [sys.executable, "-m", "flake8", str(file_path), "--format=%(row)d:%(col)d:%(code)s:%(text)s"]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    lines = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]

    findings = []
    for ln in lines:
        parts = ln.split(":", 3)
        if len(parts) != 4:
            continue
        row_text, _col_text, code, text = parts
        try:
            row = int(row_text)
        except Exception:
            row = None

        category = map_flake8_to_category(code, text)
        if category is None:
            continue

        findings.append(
            {
                "tool": "flake8",
                "line_number_raw": row,
                "line_number_adjusted": row if isinstance(row, int) else row,
                "violation_category": category,
                "code": code,
                "review_comment": f"flake8[{code}]: {text}",
            }
        )

    return findings, None


def dedupe_reviews(reviews: list[dict]):
    seen = set()
    deduped = []
    for r in reviews:
        key = (r.get("line_number_adjusted"), r.get("violation_category"), r.get("review_comment"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    return deduped


def merge_close_findings(reviews: list[dict], window: int = 1):
    ints = [r for r in reviews if isinstance(r.get("line_number_adjusted"), int)]
    others = [r for r in reviews if not isinstance(r.get("line_number_adjusted"), int)]

    ints_sorted = sorted(ints, key=lambda x: (x["violation_category"], x["line_number_adjusted"]))
    merged = []
    i = 0
    while i < len(ints_sorted):
        cur = ints_sorted[i]
        cat = cur["violation_category"]
        line_group = [cur]
        j = i + 1
        while j < len(ints_sorted):
            nxt = ints_sorted[j]
            if nxt["violation_category"] != cat:
                break
            if nxt["line_number_adjusted"] - line_group[-1]["line_number_adjusted"] <= window:
                line_group.append(nxt)
                j += 1
            else:
                break
        rep = dict(line_group[0])
        rep["line_number_adjusted"] = min(r["line_number_adjusted"] for r in line_group)
        rep["review_comment"] = " | ".join([r.get("review_comment", "") for r in line_group])
        merged.append(rep)
        i = j

    merged.extend(others)
    return merged


def consolidate_findings(pylint_rev: list[dict], flake8_rev: list[dict]):
    # Prioritize high-confidence codes and require corroboration for indentation
    preds = []

    # Index by category -> list of lines per tool
    pylint_by_cat_line = {}
    flake8_by_cat_line = {}

    for r in pylint_rev:
        cat = r.get("violation_category")
        ln = r.get("line_number_adjusted")
        pylint_by_cat_line.setdefault(cat, []).append(ln)

    for r in flake8_rev:
        cat = r.get("violation_category")
        ln = r.get("line_number_adjusted")
        flake8_by_cat_line.setdefault(cat, []).append(ln)

    # Unused import and mutable_default: accept if either tool reports
    for cat in ("unused_import", "mutable_default"):
        lines = set((pylint_by_cat_line.get(cat) or []) + (flake8_by_cat_line.get(cat) or []))
        for ln in sorted([l for l in lines if isinstance(l, int)]):
            preds.append({"line_number_adjusted": ln, "violation_category": cat, "review_comment": f"consolidated:{cat}"})

    # Naming conventions: accept pylint invalid-name or flake8 N codes; require tool report (either)
    for ln in set((pylint_by_cat_line.get("naming_convention") or []) + (flake8_by_cat_line.get("naming_convention") or [])):
        if isinstance(ln, int):
            preds.append({"line_number_adjusted": ln, "violation_category": "naming_convention", "review_comment": "consolidated:naming_convention"})

    # Indentation: require both tools to agree on nearby line to reduce FP
    pyl_lines = set([l for l in (pylint_by_cat_line.get("indentation") or []) if isinstance(l, int)])
    flk_lines = set([l for l in (flake8_by_cat_line.get("indentation") or []) if isinstance(l, int)])
    for pl in pyl_lines:
        # accept if any flake8 line within ±1
        if any(abs(pl - fl) <= 1 for fl in flk_lines):
            preds.append({"line_number_adjusted": pl, "violation_category": "indentation", "review_comment": "consolidated:indentation"})

    # Documentation formatting: keep both tools' findings (we'll ignore/conservative evaluation later)
    doc_lines = set((pylint_by_cat_line.get("documentation_formatting") or []) + (flake8_by_cat_line.get("documentation_formatting") or []))
    for ln in sorted([l for l in doc_lines if isinstance(l, int)]):
        preds.append({"line_number_adjusted": ln, "violation_category": "documentation_formatting", "review_comment": "consolidated:documentation_formatting"})

    preds = merge_close_findings(preds, window=1)
    preds = dedupe_reviews(preds)
    return preds


def run_static_predictions(evaluation_path: Path):
    entries = load_evaluation_entries(evaluation_path)

    pred_by_pr = {}
    parse_failures = []
    empty_response_prs = []

    for entry in entries:
        pr_id = entry.get("id")
        if not pr_id:
            continue

        file_path = resolve_source_file(entry, evaluation_path)
        if file_path is None or not file_path.exists():
            parse_failures.append((pr_id, "source_file_missing"))
            continue

        pylint_reviews, pylint_error = run_pylint(file_path)
        flake8_reviews, flake8_error = run_flake8(file_path)

        if pylint_error and flake8_error:
            parse_failures.append((pr_id, f"{pylint_error}; {flake8_error}"))

        preds = consolidate_findings(pylint_reviews, flake8_reviews)
        preds = [r for r in preds if r.get("violation_category") in TARGET_CATEGORIES]

        pred_by_pr[pr_id] = preds

        if len(preds) == 0:
            empty_response_prs.append(pr_id)

    return pred_by_pr, parse_failures, empty_response_prs


def load_evaluation_entries(evaluation_path: Path):
    data = json.loads(evaluation_path.read_text(encoding="utf-8"))
    entries = []
    for item in data:
        if isinstance(item, dict) and item.get("id"):
            entries.append(item)
    return entries


def resolve_source_file(entry: dict, evaluation_path: Path) -> Path | None:
    source_file = entry.get("source_file")
    if not source_file:
        return None

    source_path = Path(source_file)
    if source_path.is_absolute():
        return source_path

    base_dir = evaluation_path.parent
    candidate = base_dir / source_path
    if candidate.exists():
        return candidate

    fallback = base_dir / "evaluation_files" / source_path.name
    if fallback.exists():
        return fallback

    return candidate


def compute_metrics(gt_by_pr, pred_by_pr):
    category_tp = Counter()
    category_fp = Counter()
    category_fn = Counter()

    line_match_total = 0
    line_mismatch_total = 0
    line_match_by_category = Counter()
    line_mismatch_by_category = Counter()

    missed_violations = 0
    extra_violations = 0
    equal_violations = 0

    analyzed_prs = []

    for pr_id, pred_reviews in pred_by_pr.items():
        gt_reviews = gt_by_pr.get(pr_id, [])

        if len(pred_reviews) == 0:
            continue

        analyzed_prs.append(pr_id)

        gt_len = len(gt_reviews)
        pred_len = len(pred_reviews)

        if pred_len < gt_len:
            missed_violations += gt_len - pred_len
        elif pred_len > gt_len:
            extra_violations += pred_len - gt_len
        else:
            equal_violations += 1

        gt_cat_counter = Counter([r.get("violation_category") for r in gt_reviews if r.get("violation_category")])
        pred_cat_counter = Counter([r.get("violation_category") for r in pred_reviews if r.get("violation_category")])

        all_cats = set(gt_cat_counter) | set(pred_cat_counter)
        for cat in all_cats:
            tp = min(gt_cat_counter.get(cat, 0), pred_cat_counter.get(cat, 0))
            fp = max(0, pred_cat_counter.get(cat, 0) - gt_cat_counter.get(cat, 0))
            fn = max(0, gt_cat_counter.get(cat, 0) - pred_cat_counter.get(cat, 0))
            category_tp[cat] += tp
            category_fp[cat] += fp
            category_fn[cat] += fn

        gt_pairs = set()
        for g in gt_reviews:
            c = g.get("violation_category")
            ln = g.get("line_number")
            if c is not None and isinstance(ln, int):
                gt_pairs.add((c, ln))

        for p in pred_reviews:
            c = p.get("violation_category")
            ln = p.get("line_number_adjusted")
            if c is None:
                continue
            if isinstance(ln, int) and (c, ln) in gt_pairs:
                line_match_total += 1
                line_match_by_category[c] += 1
            else:
                line_mismatch_total += 1
                line_mismatch_by_category[c] += 1

    cats_sorted = sorted(set(category_tp) | set(category_fp) | set(category_fn))
    metrics_rows = []
    for cat in cats_sorted:
        tp = category_tp[cat]
        fp = category_fp[cat]
        fn = category_fn[cat]

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        metrics_rows.append(
            {
                "category": cat,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "line_match": line_match_by_category.get(cat, 0),
                "line_mismatch": line_mismatch_by_category.get(cat, 0),
            }
        )

    return {
        "metrics_rows": metrics_rows,
        "missed_violations": missed_violations,
        "extra_violations": extra_violations,
        "equal_violations": equal_violations,
        "line_match_total": line_match_total,
        "line_mismatch_total": line_mismatch_total,
        "analyzed_pr_count": len(analyzed_prs),
    }


def build_report_text(gt_by_pr, pred_by_pr, parse_failures, empty_response_prs, results):
    lines = []
    lines.append("=== Parsed Input Summary ===")
    lines.append(f"Ground-truth PRs: {len(gt_by_pr)}")
    lines.append(f"Predicted PRs with static findings: {len(pred_by_pr)}")
    lines.append(f"PRs ignored due to empty/static-no-match response: {len(empty_response_prs)}")
    if parse_failures:
        lines.append(f"Parse failures: {len(parse_failures)}")

    lines.append("")
    lines.append("=== Violation Count Comparison ===")
    lines.append(f"analyzed_pr_count: {results['analyzed_pr_count']}")
    lines.append(f"missed_violations: {results['missed_violations']}")
    lines.append(f"extra_violations: {results['extra_violations']}")
    lines.append(f"equal_violations_prs: {results['equal_violations']}")

    lines.append("")
    lines.append("=== Line Match Tracking (using static line number) ===")
    lines.append(f"line_match_total: {results['line_match_total']}")
    lines.append(f"line_mismatch_total: {results['line_mismatch_total']}")

    lines.append("")
    lines.append("=== Category-wise Metrics ===")
    header = (
        f"{'category':<28} {'precision':>10} {'recall':>10} {'f1':>10} "
        f"{'tp':>6} {'fp':>6} {'fn':>6} {'line_ok':>8} {'line_bad':>9}"
    )
    lines.append(header)
    lines.append("-" * len(header))
    for row in results["metrics_rows"]:
        lines.append(
            f"{row['category']:<28} "
            f"{row['precision']:>10.4f} "
            f"{row['recall']:>10.4f} "
            f"{row['f1']:>10.4f} "
            f"{row['tp']:>6d} "
            f"{row['fp']:>6d} "
            f"{row['fn']:>6d} "
            f"{row['line_match']:>8d} "
            f"{row['line_mismatch']:>9d}"
        )

    if parse_failures:
        lines.append("")
        lines.append("=== Parse/Tool Failures (first 20) ===")
        for item in parse_failures[:20]:
            lines.append(str(item))

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Evaluate static-tool findings against evaluation.json (v3)")
    parser.add_argument(
        "--evaluation",
        type=Path,
        default=Path("data/processed/evaluation.json"),
        help="Path to evaluation.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/static_tool_results_v3.txt"),
        help="Path to save evaluation summary text",
    )
    args = parser.parse_args()

    gt_by_pr = load_evaluation_map(args.evaluation)
    pred_by_pr, parse_failures, empty_response_prs = run_static_predictions(args.evaluation)

    results = compute_metrics(gt_by_pr, pred_by_pr)
    report_text = build_report_text(gt_by_pr, pred_by_pr, parse_failures, empty_response_prs, results)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report_text, encoding="utf-8")

    print(report_text, end="")
    print(f"\nSaved static tool evaluation report to: {args.output}")


if __name__ == "__main__":
    main()
