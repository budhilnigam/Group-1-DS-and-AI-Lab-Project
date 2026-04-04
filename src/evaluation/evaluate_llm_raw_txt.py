import argparse
import ast
import json
import re
from collections import Counter
from pathlib import Path


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


def split_batches(raw_text: str):
    pattern = re.compile(r"^Batch\s+(\d+)\s+-\s+PR ids:\s+(\[.*?\])\s*$", re.MULTILINE)
    matches = list(pattern.finditer(raw_text))
    batches = []

    for idx, m in enumerate(matches):
        batch_no = int(m.group(1))
        pr_ids_text = m.group(2)
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(raw_text)
        body = raw_text[start:end].strip()

        repos_line = None
        body_lines = body.splitlines()
        if body_lines and body_lines[0].startswith("repos:"):
            repos_line = body_lines[0]
            body = "\n".join(body_lines[1:]).strip()

        batches.append(
            {
                "batch_no": batch_no,
                "pr_ids_text": pr_ids_text,
                "repos_line": repos_line,
                "response_text": body,
            }
        )

    return batches


def safe_json_loads(text: str):
    if not text:
        return None

    cleaned = text.strip()
    if not cleaned:
        return None

    # Remove trailing commas before closing braces/brackets.
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)

    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Fallback: allow Python-literal style content (single quotes, etc.).
    try:
        return ast.literal_eval(cleaned)
    except Exception:
        return None


def parse_raw_predictions(raw_path: Path):
    raw_text = raw_path.read_text(encoding="utf-8", errors="ignore")
    batches = split_batches(raw_text)

    pred_by_pr = {}
    parse_failures = []
    empty_response_prs = []

    for b in batches:
        pr_ids = safe_json_loads(b["pr_ids_text"])
        if not isinstance(pr_ids, list):
            continue

        payload = safe_json_loads(b["response_text"])

        if payload is None:
            for pr in pr_ids:
                empty_response_prs.append(pr)
            continue

        if not isinstance(payload, list):
            parse_failures.append((b["batch_no"], pr_ids, "Response is not a JSON array"))
            continue

        for obj in payload:
            if not isinstance(obj, dict):
                continue
            pr_id = obj.get("PR_ID")
            llm_reviews = obj.get("llm_reviews")
            if not pr_id or not isinstance(llm_reviews, list):
                continue

            normalized_reviews = []
            for r in llm_reviews:
                if not isinstance(r, dict):
                    continue
                line_number = r.get("line_number")
                adjusted_line = line_number + 1 if isinstance(line_number, int) else line_number
                normalized_reviews.append(
                    {
                        "line_number_raw": line_number,
                        "line_number_adjusted": adjusted_line,
                        "violation_category": r.get("violation_category"),
                        "review_comment": r.get("review_comment"),
                    }
                )

            pred_by_pr[pr_id] = normalized_reviews

    return pred_by_pr, parse_failures, empty_response_prs


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
    total_llm_comments = 0
    total_gt_comments_for_analyzed_prs = 0

    analyzed_prs = []

    for pr_id, pred_reviews in pred_by_pr.items():
        gt_reviews = gt_by_pr.get(pr_id, [])

        # Ignore PRs with no LLM responses.
        if len(pred_reviews) == 0:
            continue

        analyzed_prs.append(pr_id)

        gt_len = len(gt_reviews)
        pred_len = len(pred_reviews)

        total_gt_comments_for_analyzed_prs += gt_len
        total_llm_comments += pred_len

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

        # Line-number match tracking per predicted review.
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
        "total_llm_comments": total_llm_comments,
        "total_gt_comments_for_analyzed_prs": total_gt_comments_for_analyzed_prs,
        "line_match_total": line_match_total,
        "line_mismatch_total": line_mismatch_total,
        "analyzed_pr_count": len(analyzed_prs),
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate LLM raw txt responses against evaluation.json")
    parser.add_argument(
        "--raw",
        type=Path,
        default=Path("outputs/llm_raw_responses.txt"),
        help="Path to raw response txt file",
    )
    parser.add_argument(
        "--evaluation",
        type=Path,
        default=Path("data/processed/evaluation.json"),
        help="Path to evaluation.json",
    )
    args = parser.parse_args()

    gt_by_pr = load_evaluation_map(args.evaluation)
    pred_by_pr, parse_failures, empty_response_prs = parse_raw_predictions(args.raw)

    results = compute_metrics(gt_by_pr, pred_by_pr)

    print("=== Parsed Input Summary ===")
    print(f"Ground-truth PRs: {len(gt_by_pr)}")
    print(f"Predicted PRs with parsed JSON: {len(pred_by_pr)}")
    print(f"PRs ignored due to empty/non-JSON batch response: {len(empty_response_prs)}")
    if parse_failures:
        print(f"Parse failures: {len(parse_failures)}")

    print("\n=== Violation Count Comparison ===")
    print(f"analyzed_pr_count: {results['analyzed_pr_count']}")
    print(f"llm_comments_total_for_analyzed_prs: {results['total_llm_comments']}")
    print(
        "ground_truth_comments_total_for_analyzed_prs: "
        f"{results['total_gt_comments_for_analyzed_prs']}"
    )
    print(f"missed_violations: {results['missed_violations']}")
    print(f"extra_violations: {results['extra_violations']}")
    print(f"equal_violations_prs: {results['equal_violations']}")

    print("\n=== Line Match Tracking (using llm_line + 1) ===")
    print(f"line_match_total: {results['line_match_total']}")
    print(f"line_mismatch_total: {results['line_mismatch_total']}")

    print("\n=== Category-wise Metrics ===")
    header = f"{'category':<28} {'precision':>10} {'recall':>10} {'f1':>10} {'tp':>6} {'fp':>6} {'fn':>6} {'line_ok':>8} {'line_bad':>9}"
    print(header)
    print("-" * len(header))
    for row in results["metrics_rows"]:
        print(
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


if __name__ == "__main__":
    main()


"""
python scripts/evaluate_llm_raw_txt.py --raw outputs/llm_raw_responses.txt --evaluation data/processed/evaluation.json
"""