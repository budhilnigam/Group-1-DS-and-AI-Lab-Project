"""Evaluate all prompt configurations on evaluation data.

Runs (strategy × detection × mode × hint-combo) × models, scores with
both exact-match and category-F1, and reports a leaderboard with top-3.

Usage:
  python scripts/evaluate_prompts.py                   # first eval entry, all models
  python scripts/evaluate_prompts.py --max-entries 5   # first 5 entries
  python scripts/evaluate_prompts.py --detection multi # multi-issue only
  python scripts/evaluate_prompts.py --models qwen2.5-coder:14b,phi4:14b
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from llm_inference import (
    LOCAL_MODELS,
    API_MODELS,
    infer_one,
    save_cache,
    _cache_key,
)
from retrieve import retrieve_with_context

# ═══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

EVAL_PATH = ROOT / "data" / "processed" / "evaluation.json"
EVAL_DIR = ROOT / "data" / "processed" / "evaluation_files"

TEMPERATURE = 0.0
MAX_TOKENS = 1024
RAG_TOP_K = 10

CATEGORIES = [
    "unused_import", "indentation", "naming_convention",
    "documentation_formatting", "mutable_default",
]
CATEGORIES_STR = ", ".join(CATEGORIES)
LINE_RANGE_VARIANTS = [1, 2, 3]

# ═══════════════════════════════════════════════════════════════════════════════
#  ROLE & OUTPUT FORMATS
# ═══════════════════════════════════════════════════════════════════════════════

ROLE = (
    "You are an expert Python code reviewer. "
    "Your task is to detect code violations in the given code."
)

SINGLE_OUTPUT_FMT = """\
Respond with ONLY a JSON object in this exact format (no markdown, no extra text):
{
  "line_number": <int>,
  "violation_category": "<one of: unused_import, indentation, naming_convention, documentation_formatting, mutable_default>",
  "review_comment": "<brief explanation of the violation>"
}"""

MULTI_OUTPUT_FMT = """\
Respond with ONLY a JSON array of objects in this exact format (no markdown, no extra text):
[
  {
    "line_number": <int>,
    "violation_category": "<one of: unused_import, indentation, naming_convention, documentation_formatting, mutable_default>",
    "review_comment": "<brief explanation of the violation>"
  }
]"""

SINGLE_OUTPUT_FMT_RAG = """\
Respond with ONLY a JSON object in this exact format (no markdown, no extra text):
{
  "line_number": <int>,
  "violation_category": "<one of: unused_import, indentation, naming_convention, documentation_formatting, mutable_default>",
  "review_comment": "<brief explanation of the violation>",
  "guideline_chunks_used": ["<chunk_id_1>", "<chunk_id_2>"]
}"""

MULTI_OUTPUT_FMT_RAG = """\
Respond with ONLY a JSON array of objects in this exact format (no markdown, no extra text):
[
  {
    "line_number": <int>,
    "violation_category": "<one of: unused_import, indentation, naming_convention, documentation_formatting, mutable_default>",
    "review_comment": "<brief explanation of the violation>",
    "guideline_chunks_used": ["<chunk_id_1>", "<chunk_id_2>"]
  }
]"""

# ═══════════════════════════════════════════════════════════════════════════════
#  COT STEPS
# ═══════════════════════════════════════════════════════════════════════════════

COT_STEPS_SINGLE = """\
Follow these steps carefully:
Step 1: Read the code line by line and understand its structure.
Step 2: For each line, check if it violates any of the violation categories listed below.
Step 3: Identify the single most prominent violation.
Step 4: Determine the exact line number where the violation occurs.
Step 5: Write a concise review comment explaining the issue.
Step 6: Output ONLY the final JSON — no reasoning text."""

COT_STEPS_MULTI = """\
Follow these steps carefully:
Step 1: Read the code line by line and understand its structure.
Step 2: For each line, check if it violates any of the violation categories listed below.
Step 3: Collect ALL violations found across the entire file.
Step 4: For each violation, determine the exact line number and category.
Step 5: Write a concise review comment for each violation.
Step 6: Output ONLY the final JSON array — no reasoning text."""

COT_STEPS_SINGLE_RAG = """\
Follow these steps carefully:
Step 1: Read the retrieved coding guidelines and understand the rules.
Step 2: Read the code line by line and understand its structure.
Step 3: For each line, check if it violates any of the violation categories or guidelines.
Step 4: Identify the single most prominent violation.
Step 5: Determine the exact line number where the violation occurs.
Step 6: Note which guideline chunks supported your finding.
Step 7: Write a concise review comment explaining the issue.
Step 8: Output ONLY the final JSON — no reasoning text."""

COT_STEPS_MULTI_RAG = """\
Follow these steps carefully:
Step 1: Read the retrieved coding guidelines and understand the rules.
Step 2: Read the code line by line and understand its structure.
Step 3: For each line, check if it violates any of the violation categories or guidelines.
Step 4: Collect ALL violations found across the entire file.
Step 5: For each violation, determine the exact line number and category.
Step 6: Note which guideline chunks supported each finding.
Step 7: Write a concise review comment for each violation.
Step 8: Output ONLY the final JSON array — no reasoning text."""

# ═══════════════════════════════════════════════════════════════════════════════
#  HINT FRAGMENTS
# ═══════════════════════════════════════════════════════════════════════════════


def _exact_line_hint_single(line: int) -> str:
    return f"\nHint: Focus on line {line}."


def _exact_line_hint_multi(lines: list) -> str:
    return f"\nHint: Focus on lines {', '.join(str(l) for l in lines)}."


def _line_range_hint_single(line: int, margin: int) -> str:
    return f"\nHint: The violation is between lines {max(1, line - margin)} and {line + margin}."


def _line_range_hint_multi(lines: list, margin: int) -> str:
    ranges = [f"{max(1, l - margin)}-{l + margin}" for l in lines]
    return f"\nHint: Look at these line ranges: {', '.join(ranges)}."


def _ground_truth_hint_single(comment: str) -> str:
    return f'\nHint: A reviewer noted — "{comment}"'


def _ground_truth_hint_multi(comments: list) -> str:
    bullets = "\n".join(f'  - "{c}"' for c in comments)
    return f"\nHint: A reviewer noted the following issues:\n{bullets}"


def _rag_guidelines_block(guidelines: str) -> str:
    return (
        f"\n\nRelevant coding guidelines (retrieved from project documentation):\n"
        f"---\n{guidelines}\n---\n"
        "Use these guidelines to support your analysis. "
        "In your response, also include a \"guideline_chunks_used\" field listing "
        "the chunk IDs that contributed to finding each violation."
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  PROMPT BUILDERS (8 functions)
# ═══════════════════════════════════════════════════════════════════════════════

def build_minimal_single_llm(code, hints, line=None, gt_comment=None, **_):
    parts = [ROLE]
    parts.append(f"\nAnalyse the following Python code for violations.\n\n```python\n{code}\n```")
    if hints["exact_line"] and line is not None:
        parts.append(_exact_line_hint_single(line))
    if hints["line_range"] and line is not None:
        parts.append(_line_range_hint_single(line, hints["line_range"]))
    if hints["ground_truth"] and gt_comment is not None:
        parts.append(_ground_truth_hint_single(gt_comment))
    parts.append(f"\nViolation categories to check: {CATEGORIES_STR}.")
    parts.append(f"\n{SINGLE_OUTPUT_FMT}")
    return "\n".join(parts)


def build_minimal_multi_llm(code, hints, lines=None, gt_comments=None, **_):
    parts = [ROLE]
    parts.append(f"\nAnalyse the following Python code for ALL violations.\n\n```python\n{code}\n```")
    if hints["exact_line"] and lines:
        parts.append(_exact_line_hint_multi(lines))
    if hints["line_range"] and lines:
        parts.append(_line_range_hint_multi(lines, hints["line_range"]))
    if hints["ground_truth"] and gt_comments:
        parts.append(_ground_truth_hint_multi(gt_comments))
    parts.append(f"\nViolation categories to check: {CATEGORIES_STR}.")
    parts.append(f"\n{MULTI_OUTPUT_FMT}")
    return "\n".join(parts)


def build_minimal_single_rag(code, hints, guidelines="", line=None, gt_comment=None, **_):
    parts = [ROLE]
    parts.append(_rag_guidelines_block(guidelines))
    parts.append(f"\nAnalyse the following Python code for violations.\n\n```python\n{code}\n```")
    if hints["exact_line"] and line is not None:
        parts.append(_exact_line_hint_single(line))
    if hints["line_range"] and line is not None:
        parts.append(_line_range_hint_single(line, hints["line_range"]))
    if hints["ground_truth"] and gt_comment is not None:
        parts.append(_ground_truth_hint_single(gt_comment))
    parts.append(f"\nViolation categories to check: {CATEGORIES_STR}.")
    parts.append(f"\n{SINGLE_OUTPUT_FMT_RAG}")
    return "\n".join(parts)


def build_minimal_multi_rag(code, hints, guidelines="", lines=None, gt_comments=None, **_):
    parts = [ROLE]
    parts.append(_rag_guidelines_block(guidelines))
    parts.append(f"\nAnalyse the following Python code for ALL violations.\n\n```python\n{code}\n```")
    if hints["exact_line"] and lines:
        parts.append(_exact_line_hint_multi(lines))
    if hints["line_range"] and lines:
        parts.append(_line_range_hint_multi(lines, hints["line_range"]))
    if hints["ground_truth"] and gt_comments:
        parts.append(_ground_truth_hint_multi(gt_comments))
    parts.append(f"\nViolation categories to check: {CATEGORIES_STR}.")
    parts.append(f"\n{MULTI_OUTPUT_FMT_RAG}")
    return "\n".join(parts)


def build_cot_single_llm(code, hints, line=None, gt_comment=None, **_):
    parts = [ROLE, f"\n{COT_STEPS_SINGLE}", f"\n```python\n{code}\n```"]
    if hints["exact_line"] and line is not None:
        parts.append(_exact_line_hint_single(line))
    if hints["line_range"] and line is not None:
        parts.append(_line_range_hint_single(line, hints["line_range"]))
    if hints["ground_truth"] and gt_comment is not None:
        parts.append(_ground_truth_hint_single(gt_comment))
    parts.append(f"\nViolation categories to check: {CATEGORIES_STR}.")
    parts.append(f"\n{SINGLE_OUTPUT_FMT}")
    return "\n".join(parts)


def build_cot_multi_llm(code, hints, lines=None, gt_comments=None, **_):
    parts = [ROLE, f"\n{COT_STEPS_MULTI}", f"\n```python\n{code}\n```"]
    if hints["exact_line"] and lines:
        parts.append(_exact_line_hint_multi(lines))
    if hints["line_range"] and lines:
        parts.append(_line_range_hint_multi(lines, hints["line_range"]))
    if hints["ground_truth"] and gt_comments:
        parts.append(_ground_truth_hint_multi(gt_comments))
    parts.append(f"\nViolation categories to check: {CATEGORIES_STR}.")
    parts.append(f"\n{MULTI_OUTPUT_FMT}")
    return "\n".join(parts)


def build_cot_single_rag(code, hints, guidelines="", line=None, gt_comment=None, **_):
    parts = [ROLE, _rag_guidelines_block(guidelines), f"\n{COT_STEPS_SINGLE_RAG}",
             f"\n```python\n{code}\n```"]
    if hints["exact_line"] and line is not None:
        parts.append(_exact_line_hint_single(line))
    if hints["line_range"] and line is not None:
        parts.append(_line_range_hint_single(line, hints["line_range"]))
    if hints["ground_truth"] and gt_comment is not None:
        parts.append(_ground_truth_hint_single(gt_comment))
    parts.append(f"\nViolation categories to check: {CATEGORIES_STR}.")
    parts.append(f"\n{SINGLE_OUTPUT_FMT_RAG}")
    return "\n".join(parts)


def build_cot_multi_rag(code, hints, guidelines="", lines=None, gt_comments=None, **_):
    parts = [ROLE, _rag_guidelines_block(guidelines), f"\n{COT_STEPS_MULTI_RAG}",
             f"\n```python\n{code}\n```"]
    if hints["exact_line"] and lines:
        parts.append(_exact_line_hint_multi(lines))
    if hints["line_range"] and lines:
        parts.append(_line_range_hint_multi(lines, hints["line_range"]))
    if hints["ground_truth"] and gt_comments:
        parts.append(_ground_truth_hint_multi(gt_comments))
    parts.append(f"\nViolation categories to check: {CATEGORIES_STR}.")
    parts.append(f"\n{MULTI_OUTPUT_FMT_RAG}")
    return "\n".join(parts)


BUILDERS = {
    ("minimal", "single", "llm"): build_minimal_single_llm,
    ("minimal", "multi",  "llm"): build_minimal_multi_llm,
    ("minimal", "single", "rag"): build_minimal_single_rag,
    ("minimal", "multi",  "rag"): build_minimal_multi_rag,
    ("cot",     "single", "llm"): build_cot_single_llm,
    ("cot",     "multi",  "llm"): build_cot_multi_llm,
    ("cot",     "single", "rag"): build_cot_single_rag,
    ("cot",     "multi",  "rag"): build_cot_multi_rag,
}

# ═══════════════════════════════════════════════════════════════════════════════
#  HINT COMBINATIONS & CONFIG ENUMERATION
# ═══════════════════════════════════════════════════════════════════════════════

OPTIONAL_HINTS = ["exact_line", "line_range", "ground_truth"]


def _all_hint_combos() -> List[Dict[str, Any]]:
    combos: list[dict] = []
    for r in range(len(OPTIONAL_HINTS) + 1):
        for subset in combinations(OPTIONAL_HINTS, r):
            if "line_range" in subset:
                for n in LINE_RANGE_VARIANTS:
                    combos.append({
                        "exact_line": "exact_line" in subset,
                        "line_range": n,
                        "ground_truth": "ground_truth" in subset,
                    })
            else:
                combos.append({
                    "exact_line": "exact_line" in subset,
                    "line_range": None,
                    "ground_truth": "ground_truth" in subset,
                })
    return combos


ALL_HINT_COMBOS = _all_hint_combos()

# Multi-issue: NO line hints — only no_hints and ground_truth
MULTI_HINT_COMBOS = [
    h for h in ALL_HINT_COMBOS
    if not h["exact_line"] and not h["line_range"]
]


def _hint_tag(hints: dict) -> str:
    parts = []
    if hints["exact_line"]:   parts.append("exact_line")
    if hints["line_range"]:   parts.append(f"line_range_±{hints['line_range']}")
    if hints["ground_truth"]: parts.append("ground_truth")
    return "+".join(parts) if parts else "no_hints"


def build_all_configs(
    strategy_filter: str | None = None,
    detection_filter: str | None = None,
    mode_filter: str | None = None,
) -> List[Dict[str, Any]]:
    configs: list[dict] = []
    for strategy in ["minimal", "cot"]:
        if strategy_filter and strategy != strategy_filter:
            continue
        for detection in ["single", "multi"]:
            if detection_filter and detection != detection_filter:
                continue
            hint_pool = ALL_HINT_COMBOS if detection == "single" else MULTI_HINT_COMBOS
            for mode in ["llm", "rag"]:
                if mode_filter and mode != mode_filter:
                    continue
                for hints in hint_pool:
                    config_id = f"{strategy}_{detection}_{mode}_{_hint_tag(hints)}"
                    configs.append({
                        "config_id": config_id,
                        "strategy": strategy,
                        "detection": detection,
                        "mode": mode,
                        "hints": hints,
                        "builder_fn": BUILDERS[(strategy, detection, mode)],
                    })
    return configs


# ═══════════════════════════════════════════════════════════════════════════════
#  JSON PARSING
# ═══════════════════════════════════════════════════════════════════════════════

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```")


def _parse_json(text: str):
    text = text.strip()
    m = _JSON_FENCE_RE.search(text)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
#  RAG HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _format_rag_chunks(chunks: list[dict]) -> tuple[str, dict]:
    """Format retrieved chunks as prompt text + metadata dict."""
    text_parts = []
    chunks_dict = {}
    for c in chunks:
        cid = c["chunk_id"]
        text_parts.append(f"[chunk_id: {cid}] (score={c['score']:.3f})\n{c['text']}")
        chunks_dict[cid] = {"score": c["score"], "text": c["text"]}
    return "\n\n".join(text_parts), chunks_dict


# ═══════════════════════════════════════════════════════════════════════════════
#  SCORING
# ═══════════════════════════════════════════════════════════════════════════════

def _score_one(parsed, gt_reviews: list[dict]) -> dict:
    """Score a single parsed LLM response against ground truth."""
    if isinstance(parsed, list):
        preds = parsed
    elif isinstance(parsed, dict) and "line_number" in parsed:
        preds = [parsed]
    else:
        return {"valid_json": False, "n_found": 0, "exact_hits": 0,
                "precision": 0.0, "recall": 0.0, "f1": 0.0}

    gt_set = {(r["line_number"], r["violation_category"]) for r in gt_reviews}
    gt_cats = Counter(r["violation_category"] for r in gt_reviews)

    # Exact match: (line_number, violation_category)
    exact_hits = sum(
        1 for p in preds
        if (p.get("line_number"), p.get("violation_category")) in gt_set
    )

    # Category-level: precision, recall, F1
    pred_cats = [p.get("violation_category") for p in preds
                 if p.get("violation_category") in set(CATEGORIES)]

    # For recall: how many GT categories are matched (counting multiplicity)
    gt_cat_remaining = dict(gt_cats)
    cat_tp = 0
    for pc in pred_cats:
        if gt_cat_remaining.get(pc, 0) > 0:
            gt_cat_remaining[pc] -= 1
            cat_tp += 1

    precision = cat_tp / len(pred_cats) if pred_cats else 0.0
    recall = cat_tp / len(gt_reviews) if gt_reviews else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "valid_json": True,
        "n_found": len(preds),
        "exact_hits": exact_hits,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

def run_evaluation(
    entries: list[dict],
    models: list[str],
    configs: list[dict],
) -> list[dict]:
    """Run all configs × models × entries and return scored results."""

    total = len(configs) * len(models) * len(entries)
    print(f"Running {len(configs)} configs × {len(models)} models × "
          f"{len(entries)} entries = {total} inference calls\n")

    results = []
    done = 0

    for entry in entries:
        # Load code
        code_path = EVAL_DIR / entry["source_file"].replace("evaluation_files/", "")
        code_text = code_path.read_text()
        code_numbered = "\n".join(
            f"{i+1}: {l}" for i, l in enumerate(code_text.splitlines())
        )

        gt_reviews = entry["ground_truth_reviews"]
        gt_lines = [r["line_number"] for r in gt_reviews]
        gt_comments = [r["review_comment"] for r in gt_reviews]

        # RAG: use S15 production retrieval
        rag_chunks = None
        rag_guidelines = ""
        rag_chunks_dict: dict = {}
        rag_needed = any(c["mode"] == "rag" for c in configs)
        if rag_needed:
            rag_chunks = retrieve_with_context(code_text, top_k=RAG_TOP_K)
            rag_guidelines, rag_chunks_dict = _format_rag_chunks(rag_chunks)

        for cfg in configs:
            hints = cfg["hints"]
            builder = cfg["builder_fn"]
            detection = cfg["detection"]
            mode = cfg["mode"]
            hints_tag = _hint_tag(hints)

            # Build prompt
            kwargs: dict[str, Any] = {"code": code_numbered, "hints": hints}

            if mode == "rag":
                kwargs["guidelines"] = rag_guidelines

            if detection == "single":
                kwargs["line"] = gt_lines[0] if gt_lines else None
                kwargs["gt_comment"] = gt_comments[0] if gt_comments else None
            else:
                # Multi-issue: NO line hints (lines not passed)
                kwargs["gt_comments"] = gt_comments if gt_comments else None

            prompt = builder(**kwargs)

            is_rag = mode == "rag"

            for model in models:
                done += 1

                resp = infer_one(
                    prompt, model, temperature=TEMPERATURE,
                    prompt_configuration=cfg["config_id"],
                    baseline="RAG" if is_rag else "LLM",
                    retrieval_chunks=rag_chunks_dict if is_rag else None,
                    topk_retrieval=RAG_TOP_K if is_rag else None,
                    hints=hints_tag,
                    raw_retrieval_query="" if not is_rag else code_text[:500],
                )

                is_cached = resp.get("cached", False)
                raw = resp.get("response", "")
                parsed = _parse_json(raw)

                # Back-patch parsed into cache
                if parsed is not None and resp.get("parsed_response") is None:
                    resp["parsed_response"] = parsed
                    key = _cache_key(prompt, "", model, TEMPERATURE)
                    save_cache(key, resp)

                scores = _score_one(parsed, gt_reviews)

                results.append({
                    "entry_id": entry["id"],
                    "config_id": cfg["config_id"],
                    "strategy": cfg["strategy"],
                    "detection": detection,
                    "mode": mode,
                    "hints_tag": hints_tag,
                    "model": model,
                    "cached": is_cached,
                    "latency_ms": resp.get("latency_ms", 0),
                    **scores,
                })

                if done % 10 == 0 or done == total:
                    tag = "cached" if is_cached else f"{resp.get('latency_ms', 0):.0f}ms"
                    print(f"  [{done}/{total}] {cfg['config_id']} × "
                          f"{model.split(':')[0]}  ({tag})  "
                          f"exact={scores['exact_hits']} f1={scores['f1']:.2f}")

    return results


# ═══════════════════════════════════════════════════════════════════════════════
#  LEADERBOARD & REPORTING
# ═══════════════════════════════════════════════════════════════════════════════

def report(results: list[dict]) -> None:
    """Print leaderboard and top-3 highlights."""

    # Group by config_id and average across models + entries
    by_config: dict[str, list[dict]] = {}
    for r in results:
        by_config.setdefault(r["config_id"], []).append(r)

    rows = []
    for cid, group in by_config.items():
        n = len(group)
        rows.append({
            "config_id": cid,
            "strategy": group[0]["strategy"],
            "detection": group[0]["detection"],
            "mode": group[0]["mode"],
            "hints_tag": group[0]["hints_tag"],
            "avg_exact": sum(r["exact_hits"] for r in group) / n,
            "avg_precision": sum(r["precision"] for r in group) / n,
            "avg_recall": sum(r["recall"] for r in group) / n,
            "avg_f1": sum(r["f1"] for r in group) / n,
            "valid_json_pct": sum(1 for r in group if r["valid_json"]) / n * 100,
            "n_runs": n,
        })

    # Sort by F1 primary, exact match secondary
    rows.sort(key=lambda x: (x["avg_f1"], x["avg_exact"]), reverse=True)

    # ── Full leaderboard ──
    print(f"\n{'='*110}")
    print(f"{'Rank':>4}  {'Config':<45} {'Det':<6} {'Mode':<4} "
          f"{'Exact':>6} {'Prec':>6} {'Rec':>6} {'F1':>6} {'JSON%':>6}")
    print("-" * 110)
    for i, row in enumerate(rows, 1):
        print(f"{i:>4}  {row['config_id']:<45} {row['detection']:<6} {row['mode']:<4} "
              f"{row['avg_exact']:>6.2f} {row['avg_precision']:>5.1%} "
              f"{row['avg_recall']:>5.1%} {row['avg_f1']:>6.3f} "
              f"{row['valid_json_pct']:>5.1f}%")

    # ── Top 3 ──
    single_rows = [r for r in rows if r["detection"] == "single"]
    multi_rows = [r for r in rows if r["detection"] == "multi"]

    top3 = []
    if single_rows:
        top3.append(("BEST SINGLE-ISSUE", single_rows[0]))
    if multi_rows:
        top3.append(("BEST MULTI-ISSUE", multi_rows[0]))

    # Runner-up: 2nd best from whichever type had higher F1
    if len(single_rows) > 1 and len(multi_rows) > 1:
        if single_rows[0]["avg_f1"] >= multi_rows[0]["avg_f1"]:
            top3.append(("RUNNER-UP (single)", single_rows[1]))
        else:
            top3.append(("RUNNER-UP (multi)", multi_rows[1]))
    elif len(single_rows) > 1:
        top3.append(("RUNNER-UP (single)", single_rows[1]))
    elif len(multi_rows) > 1:
        top3.append(("RUNNER-UP (multi)", multi_rows[1]))

    print(f"\n{'='*110}")
    print("TOP 3 PROMPT CONFIGURATIONS")
    print(f"{'='*110}")

    for label, row in top3:
        cid = row["config_id"]
        print(f"\n  ★ {label}: {cid}")
        print(f"    F1={row['avg_f1']:.3f}  Precision={row['avg_precision']:.1%}  "
              f"Recall={row['avg_recall']:.1%}  Exact={row['avg_exact']:.2f}  "
              f"ValidJSON={row['valid_json_pct']:.0f}%")

        # Per-model breakdown
        group = by_config[cid]
        models_seen: dict[str, list[dict]] = {}
        for r in group:
            models_seen.setdefault(r["model"], []).append(r)

        print(f"    {'Model':<30} {'Exact':>6} {'F1':>6} {'Prec':>6} {'Rec':>6}")
        for model, runs in sorted(models_seen.items()):
            n = len(runs)
            print(f"    {model:<30} "
                  f"{sum(r['exact_hits'] for r in runs)/n:>6.2f} "
                  f"{sum(r['f1'] for r in runs)/n:>6.3f} "
                  f"{sum(r['precision'] for r in runs)/n:>5.1%} "
                  f"{sum(r['recall'] for r in runs)/n:>5.1%}")

    # ── Summary counts ──
    n_single = len(single_rows)
    n_multi = len(multi_rows)
    print(f"\n{'='*110}")
    print(f"Total configs evaluated: {len(rows)} ({n_single} single + {n_multi} multi)")
    print(f"Total inference calls : {len(results)}")
    print(f"Cached calls          : {sum(1 for r in results if r['cached'])}")
    print(f"Valid JSON rate        : {sum(1 for r in results if r['valid_json'])/len(results)*100:.1f}%")


# ═══════════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate all prompt configurations on evaluation data")
    parser.add_argument("--max-entries", type=int, default=1,
                        help="Number of eval entries to process (default: 1)")
    parser.add_argument("--models", type=str, default=None,
                        help="Comma-separated model names (default: all)")
    parser.add_argument("--detection", choices=["single", "multi"],
                        help="Filter to single or multi detection only")
    parser.add_argument("--strategy", choices=["minimal", "cot"],
                        help="Filter to minimal or cot strategy only")
    parser.add_argument("--mode", choices=["llm", "rag"],
                        help="Filter to llm or rag mode only")
    args = parser.parse_args()

    # Load eval data
    with open(EVAL_PATH) as f:
        eval_data = json.load(f)
    entries = [e for e in eval_data if e.get("ground_truth_reviews")]
    entries = entries[:args.max_entries]

    # Models
    if args.models:
        models = [m.strip() for m in args.models.split(",")]
    else:
        models = list(LOCAL_MODELS) + list(API_MODELS)

    # Build configs
    configs = build_all_configs(
        strategy_filter=args.strategy,
        detection_filter=args.detection,
        mode_filter=args.mode,
    )

    print(f"Eval entries : {len(entries)}")
    print(f"Models       : {len(models)} — {', '.join(m.split(':')[0] for m in models)}")
    print(f"Prompt configs: {len(configs)}")
    n_single = sum(1 for c in configs if c["detection"] == "single")
    n_multi = sum(1 for c in configs if c["detection"] == "multi")
    print(f"  Single-issue: {n_single} (16 hint combos × filtered strategies/modes)")
    print(f"  Multi-issue : {n_multi} (2 hint combos, no line hints)")
    print()

    results = run_evaluation(entries, models, configs)
    report(results)


if __name__ == "__main__":
    main()
