from __future__ import annotations

import re
from typing import Any

ALLOWED_CATEGORIES = [
    "indentation",
    "naming_convention",
    "unused_import",
    "mutable_default",
    "documentation_formatting",
]

DEFAULT_PROMPT_VARIANT = "strict_json_v1"


PROMPT_VARIANTS: dict[str, str] = {
    "strict_json_v1": """You are a Python code-review assistant in a RAG system.

Task:
- Review ONLY the provided diff context and retrieved evidence.
- Focus ONLY on these categories: {allowed_categories_csv}.
- Do NOT comment on functionality correctness, security, architecture, or testing strategy.
- If evidence is weak, state uncertainty explicitly in grounded_comment.
- Use predicted_category_hint only as a weak prior, not as a hard constraint.

Context:
- repo: {repo}
- pr_id: {pr_id}
- file_path: {file_path}
- line_number: {line_number}
- predicted_category_hint: {predicted_category_hint}

Diff chunk:
{diff_chunk}

Retrieved evidence (top-k):
{evidence_block}

Output requirements:
- Return EXACTLY one JSON object only.
- Do not include markdown fences, prose, or extra keys.
- category must be one of: {allowed_categories_list}
- cited_chunk_ids must be a JSON array of chunk IDs (or empty array)

Expected JSON schema:
{{
  "category": "<one allowed category>",
  "grounded_comment": "<single actionable sentence grounded in evidence>",
  "cited_chunk_ids": ["chunk_0001", "chunk_0042"]
}}""",
    "concise_review_v1": """You are a strict Python style reviewer.

Rules:
- Use only this taxonomy: {allowed_categories_csv}
- Use only provided diff + retrieved evidence.
- If uncertain, mention uncertainty briefly.

Context:
repo={repo}
pr_id={pr_id}
file_path={file_path}
line_number={line_number}
predicted_hint={predicted_category_hint}

diff:
{diff_chunk}

evidence:
{evidence_block}

Return exactly one JSON object with keys:
category, grounded_comment, cited_chunk_ids""",
    "evidence_first_v1": """You are a RAG auditor for Python review comments.

Step policy:
1) Pick the most supported category from evidence.
2) Write one grounded, actionable comment.
3) Cite only chunk IDs actually used.

Allowed categories: {allowed_categories_csv}
Hint category (weak): {predicted_category_hint}

Metadata:
- repo: {repo}
- pr_id: {pr_id}
- file_path: {file_path}
- line_number: {line_number}

Diff:
{diff_chunk}

Evidence:
{evidence_block}

Output exactly one JSON object:
{{"category":"...","grounded_comment":"...","cited_chunk_ids":["..."]}}""",
}


def list_prompt_variants() -> list[str]:
    return sorted(PROMPT_VARIANTS.keys())


def _build_evidence_block(retrieved: list[dict[str, Any]], max_snippet_chars: int = 300) -> str:
    lines: list[str] = []
    for i, hit in enumerate(retrieved or [], start=1):
        raw_text = str(hit.get("text", ""))
        snippet = re.sub(r"\s+", " ", raw_text)[:max_snippet_chars]
        score = hit.get("score", 0.0)
        try:
            score_str = f"{float(score):.4f}"
        except (TypeError, ValueError):
            score_str = "0.0000"

        lines.append(
            (
                f"[{i}] chunk_id={hit.get('chunk_id')} | "
                f"category={hit.get('category')} | "
                f"source={hit.get('source_type')} | "
                f"score={score_str}\n{snippet}"
            )
        )

    return "\n\n".join(lines) if lines else "No evidence retrieved."


def render_prompt(
    variant_name: str,
    instance: dict[str, Any],
    retrieved: list[dict[str, Any]],
    predicted_category_hint: str,
    allowed_categories: list[str] | None = None,
    diff_max_chars: int = 2500,
) -> str:
    if variant_name not in PROMPT_VARIANTS:
        raise ValueError(
            f"Unknown prompt variant '{variant_name}'. "
            f"Available: {', '.join(list_prompt_variants())}"
        )

    cats = allowed_categories or ALLOWED_CATEGORIES
    values = {
        "repo": instance.get("repo", ""),
        "pr_id": instance.get("pr_id", ""),
        "file_path": instance.get("file_path", ""),
        "line_number": instance.get("line_number", ""),
        "predicted_category_hint": predicted_category_hint,
        "diff_chunk": str(instance.get("query_text", ""))[:diff_max_chars],
        "evidence_block": _build_evidence_block(retrieved),
        "allowed_categories_csv": ", ".join(cats),
        "allowed_categories_list": str(cats),
    }

    return PROMPT_VARIANTS[variant_name].format(**values)
