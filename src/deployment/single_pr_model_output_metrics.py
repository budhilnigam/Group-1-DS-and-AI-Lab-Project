from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from groq import Groq
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

TARGET_CATEGORIES = {
    "naming_convention",
    "unused_import",
    "indentation",
    "mutable_default",
    "documentation_formatting",
}

PYLINT_ENABLE = ",".join(
    [
        "unused-import",
        "invalid-name",
        "bad-indentation",
        "dangerous-default-value",
        "missing-module-docstring",
        "missing-class-docstring",
        "missing-function-docstring",
    ]
)

MODEL = "openai/gpt-oss-20b"
DEFAULT_COLLECTION_NAME = "guideline_embeddings"
DEFAULT_EMBED_MODEL = "BAAI/bge-large-en-v1.5"
DEFAULT_TOP_N_CANDIDATES = 25
DEFAULT_TOP_K_FINAL = 7
LEXICAL_WEIGHT = 0.35
CATEGORY_BONUS = 0.15
RANK_PENALTY = 0.01
MAX_PER_CATEGORY = 2


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_prompt_v1(root: Path, explicit_path: str | None = None) -> str:
    if explicit_path:
        prompt_path = Path(explicit_path)
    else:
        prompt_path = root / "src" / "rag_model" / "prompts" / "v1.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8").strip()


def _normalize_pr_text(pr_file_path: Path) -> str:
    text = pr_file_path.read_text(encoding="utf-8", errors="ignore")
    if text.lstrip().startswith("diff --git") or "@@ " in text:
        return _extract_added_lines_from_diff(text)
    return text


def _extract_added_lines_from_diff(diff_text: str) -> str:
    added = []
    for line in diff_text.splitlines():
        if line.startswith("+++"):
            continue
        if line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
    if not added:
        return diff_text
    return "\n".join(added)


def _guess_repo_from_gt(gt_json_path: Path, pr_file_path: Path) -> str | None:
    try:
        data = json.loads(gt_json_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return None

    pr_name = pr_file_path.name
    pr_full = str(pr_file_path).replace("\\", "/")
    for item in data:
        if not isinstance(item, dict):
            continue
        source_file = str(item.get("source_file", "")).replace("\\", "/")
        if not source_file:
            continue
        if source_file.endswith(pr_name) or source_file == pr_full:
            repo = item.get("repo")
            return str(repo) if repo else None
    return None


def _load_gt_reviews_for_pr(gt_json_path: Path, pr_file_path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(gt_json_path.read_text(encoding="utf-8"))
    except Exception:
        return []

    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return []

    pr_stem = pr_file_path.stem
    pr_name = pr_file_path.name
    pr_full = str(pr_file_path).replace("\\", "/")

    matched = None
    for item in data:
        if not isinstance(item, dict):
            continue
        source_file = str(item.get("source_file", "")).replace("\\", "/")
        item_id = str(item.get("id", ""))

        if item_id and item_id == pr_stem:
            matched = item
            break
        if source_file and (source_file == pr_full or source_file.endswith(pr_name)):
            matched = item
            break

    if not isinstance(matched, dict):
        return []

    reviews = matched.get("ground_truth_reviews")
    if not isinstance(reviews, list):
        return []

    out: list[dict[str, Any]] = []
    for r in reviews:
        if not isinstance(r, dict):
            continue
        cat = r.get("violation_category")
        line = r.get("line_number")
        if cat not in TARGET_CATEGORIES or not isinstance(line, int):
            continue
        out.append(
            {
                "line_number": line,
                "violation_category": cat,
                "review_comment": str(r.get("review_comment", "") or ""),
            }
        )
    return out


def _safe_identifier(name: str) -> bool:
    return re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name or "") is not None


def _signal_naming(tree: ast.AST) -> list[str]:
    findings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if _safe_identifier(node.name) and re.search(r"[A-Z]", node.name):
                findings.append(f"function '{node.name}' should be snake_case")
            for arg in node.args.args:
                if _safe_identifier(arg.arg) and re.search(r"[A-Z]", arg.arg):
                    findings.append(f"parameter '{arg.arg}' should be snake_case")
        if isinstance(node, ast.ClassDef):
            if _safe_identifier(node.name) and "_" in node.name:
                findings.append(f"class '{node.name}' should use PascalCase")
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name = target.id
                    if _safe_identifier(name) and re.search(r"[A-Z]", name) and not name.isupper():
                        findings.append(f"variable '{name}' may violate naming convention")
    return findings


def _signal_mutable_default(tree: ast.AST) -> list[str]:
    findings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            defaults = list(node.args.defaults)
            for d in defaults:
                if isinstance(d, (ast.List, ast.Dict, ast.Set)):
                    findings.append(f"function '{node.name}' has mutable default")
    return findings


def _signal_unused_import(tree: ast.AST) -> list[str]:
    imported = []
    used = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.append(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    imported.append(alias.asname or alias.name)
        elif isinstance(node, ast.Name):
            used.add(node.id)

    findings = []
    for name in imported:
        if name and name not in used:
            findings.append(f"unused import '{name}'")
    return findings


def _signal_indentation(code: str) -> list[str]:
    findings = []
    for idx, line in enumerate(code.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "\t" in line[: len(line) - len(line.lstrip())]:
            findings.append(f"line {idx}: tab indentation")
            continue
        leading = len(line) - len(line.lstrip(" "))
        if leading > 0 and leading % 4 != 0:
            findings.append(f"line {idx}: non-4-space indentation")
    return findings


def _signal_doc_format(code: str) -> list[str]:
    findings = []
    lines = code.splitlines()
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            leading = len(line) - len(line.lstrip(" "))
            if leading % 4 != 0:
                findings.append(f"line {idx}: docstring indentation appears inconsistent")
    return findings


def build_query_text_variant2(pr_code: str) -> str:
    signals = []

    try:
        tree = ast.parse(pr_code)
    except Exception as exc:
        return f"General Python code quality and PEP 8 compliance review. Parse issue: {exc}"

    naming_issues = _signal_naming(tree)
    indent_issues = _signal_indentation(pr_code)
    mutable_issues = _signal_mutable_default(tree)
    doc_issues = _signal_doc_format(pr_code)
    unused_issues = _signal_unused_import(tree)

    if naming_issues:
        signals.append(f"Naming issues detected: {' '.join(naming_issues[:3])}")
    if indent_issues:
        signals.append(f"Indentation problems detected: {' '.join(indent_issues[:3])}")
    if mutable_issues:
        signals.append(f"Mutable default argument issues: {' '.join(mutable_issues[:2])}")
    if doc_issues:
        signals.append(f"Documentation formatting issues: {' '.join(doc_issues[:3])}")
    if unused_issues:
        signals.append(f"Unused import issues: {' '.join(unused_issues[:3])}")

    if not signals:
        signals.append("General Python code quality and PEP 8 compliance review.")

    return " ".join(signals)


def _extract_predicted_categories_from_query(query_text: str) -> list[str]:
    q = query_text.lower()
    cats = []
    if "unused import" in q or "unused_import" in q:
        cats.append("unused_import")
    if "indentation" in q:
        cats.append("indentation")
    if "naming" in q or "snake_case" in q or "pascalcase" in q:
        cats.append("naming_convention")
    if "mutable default" in q or "mutable_default" in q:
        cats.append("mutable_default")
    if "docstring" in q or "documentation" in q:
        cats.append("documentation_formatting")
    if not cats:
        cats = sorted(TARGET_CATEGORIES)
    return cats


def _build_query_filter(repo_name: str | None):
    source_types = ["pep8", "flake8", "pylint", "ruff", "pep257"]
    should_conditions = [
        models.FieldCondition(key="source_type", match=models.MatchValue(value=s))
        for s in source_types
    ]

    family = None
    if repo_name:
        repo_lower = repo_name.lower()
        for f in ["django", "fastapi", "flask", "pandas", "sklearn", "scikit-learn"]:
            if f in repo_lower:
                family = "scikit-learn" if f == "sklearn" else f
                break

    if family:
        should_conditions.insert(
            0,
            models.FieldCondition(
                key="source_type",
                match=models.MatchValue(value=f"{family}_guidelines"),
            ),
        )
        should_conditions.insert(
            1,
            models.FieldCondition(
                key="source_type",
                match=models.MatchValue(value=f"{family}_review_comment"),
            ),
        )

    return models.Filter(should=should_conditions)


def _payload_text(payload: Any) -> str:
    if payload is None:
        return ""
    if isinstance(payload, dict):
        for key in ["text", "content", "guideline", "review_comment", "review_text", "chunk"]:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return json.dumps(payload, ensure_ascii=False)
    return str(payload)


def _extract_candidate_category(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ["category", "violation_category", "label", "type"]:
        val = payload.get(key)
        if isinstance(val, str):
            v = val.strip().lower()
            if v in TARGET_CATEGORIES:
                return v
    txt = _payload_text(payload).lower()
    for c in TARGET_CATEGORIES:
        if c in txt:
            return c
    return None


def _tokenize_for_overlap(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z_]{3,}", text.lower()))


def retrieve_rag_chunks(
    pr_code: str,
    query_text: str,
    qdrant_url: str,
    repo_name: str | None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    embed_model_name: str = DEFAULT_EMBED_MODEL,
    top_n_candidates: int = DEFAULT_TOP_N_CANDIDATES,
    top_k_final: int = DEFAULT_TOP_K_FINAL,
) -> list[dict[str, Any]]:
    embed_model = SentenceTransformer(embed_model_name)
    client = QdrantClient(url=qdrant_url)
    query_vector = embed_model.encode(query_text).tolist()

    response = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        query_filter=_build_query_filter(repo_name),
        limit=top_n_candidates,
    )

    points = response.points if hasattr(response, "points") else []
    predicted_categories = set(_extract_predicted_categories_from_query(query_text))
    query_tokens = _tokenize_for_overlap(query_text)

    candidates: list[dict[str, Any]] = []
    for idx, p in enumerate(points):
        payload = getattr(p, "payload", None)
        text = _payload_text(payload)
        if not text:
            continue
        category = _extract_candidate_category(payload)

        lexical_tokens = _tokenize_for_overlap(text)
        overlap = 0.0
        if query_tokens:
            overlap = len(query_tokens & lexical_tokens) / max(1, len(query_tokens))

        semantic_score = float(getattr(p, "score", 0.0) or 0.0)
        category_bonus = CATEGORY_BONUS if category in predicted_categories else 0.0
        rerank_score = semantic_score + (LEXICAL_WEIGHT * overlap) + category_bonus - (RANK_PENALTY * idx)

        candidates.append(
            {
                "text": text,
                "score": semantic_score,
                "category": category,
                "lexical_overlap": overlap,
                "rank_idx": idx,
                "rerank_score": rerank_score,
            }
        )

    candidates.sort(key=lambda x: x["rerank_score"], reverse=True)

    final = []
    per_cat_count: dict[str, int] = {}
    for c in candidates:
        cat = c.get("category") or "uncategorized"
        count = per_cat_count.get(cat, 0)
        if cat != "uncategorized" and count >= MAX_PER_CATEGORY:
            continue
        final.append(c)
        per_cat_count[cat] = count + 1
        if len(final) >= top_k_final:
            break

    return final


def build_prompt(prompt_template: str, pr_id: str, pr_code: str, retrieved_chunks: list[str] | None = None) -> str:
    blocks = [prompt_template.strip()]
    if retrieved_chunks is not None:
        chunk_block = "\n\n".join([f"[Chunk {idx + 1}]\n{c}" for idx, c in enumerate(retrieved_chunks)])
        if not chunk_block:
            chunk_block = "[No retrieved payload chunks available]"
        blocks.append(
            f"""RETRIEVED_PAYLOAD_CHUNKS:
{chunk_block}
END

PR:
ID: {pr_id}
CODE:
{pr_code}
"""
        )
    else:
        blocks.append(
            f"""PR:
ID: {pr_id}
CODE:
{pr_code}
"""
        )
    return "\n".join(blocks)


def call_groq_json(client: Groq, prompt: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    content = response.choices[0].message.content
    return content if isinstance(content, str) else str(content)


def _extract_json_block(raw_text: str) -> Any:
    text = raw_text.strip()
    if not text:
        return []

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    start_arr = text.find("[")
    end_arr = text.rfind("]")
    if start_arr != -1 and end_arr != -1 and end_arr > start_arr:
        candidate = text[start_arr : end_arr + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass

    start_obj = text.find("{")
    end_obj = text.rfind("}")
    if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
        candidate = text[start_obj : end_obj + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass

    return []


def _extract_complete_object_snippets(raw_text: str) -> list[str]:
    snippets = []
    depth = 0
    start = -1
    in_str = False
    escape = False

    for idx, ch in enumerate(raw_text):
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue

        if ch == '"':
            in_str = True
            continue

        if ch == "{":
            if depth == 0:
                start = idx
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start != -1:
                    snippets.append(raw_text[start : idx + 1])
                    start = -1

    return snippets


def _salvage_llm_reviews_from_truncated(raw_text: str) -> list[dict[str, Any]]:
    objects = []
    for snippet in _extract_complete_object_snippets(raw_text):
        try:
            obj = json.loads(snippet)
        except Exception:
            continue
        if isinstance(obj, dict):
            objects.append(obj)

    parsed: list[Any] = []
    for obj in objects:
        if isinstance(obj.get("llm_reviews"), list):
            parsed.extend(obj.get("llm_reviews") or [])
        elif {"line_number", "violation_category"}.issubset(set(obj.keys())):
            parsed.append(obj)

    return _normalize_llm_reviews(parsed)


def _normalize_llm_reviews(parsed: Any) -> list[dict[str, Any]]:
    # Guard for parser edge cases where model output may decode into a plain string/list wrapper.
    if isinstance(parsed, str):
        parsed = _extract_json_block(parsed)

    items = []
    if isinstance(parsed, dict):
        parsed = [parsed]

    if isinstance(parsed, list):
        for obj in parsed:
            if not isinstance(obj, dict):
                continue
            if isinstance(obj.get("llm_reviews"), list):
                for r in obj["llm_reviews"]:
                    if isinstance(r, dict):
                        items.append(r)
            elif {"line_number", "violation_category"}.issubset(set(obj.keys())):
                items.append(obj)

    normalized = []
    for r in items:
        category = r.get("violation_category")
        if category not in TARGET_CATEGORIES:
            continue
        line_number = r.get("line_number")
        if isinstance(line_number, str) and line_number.isdigit():
            line_number = int(line_number)
        if not isinstance(line_number, int):
            continue
        normalized.append(
            {
                "line_number": line_number,
                "violation_category": category,
                "review_comment": str(r.get("review_comment", "")).strip(),
            }
        )
    return normalized


def parse_llm_reviews_preserve_partial(raw_text: str) -> list[dict[str, Any]]:
    parsed = _extract_json_block(raw_text)
    normalized = _normalize_llm_reviews(parsed)
    if normalized:
        return normalized

    # If JSON is truncated mid-item, salvage complete objects so valid earlier findings are kept.
    return _salvage_llm_reviews_from_truncated(raw_text)


def map_pylint_to_category(msg: dict[str, Any]) -> str | None:
    symbol = str(msg.get("symbol") or "").strip().lower()
    message_id = str(msg.get("message-id") or "").strip().upper()

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


def map_flake8_to_category(code: str, text: str) -> str | None:
    c = (code or "").strip().upper()
    t = (text or "").lower()

    if c == "F401":
        return "unused_import"
    if c in {"B006", "B008"}:
        return "mutable_default"
    if c in {"N806", "N815", "N802"}:
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


def compute_micro_metrics(
    predictions: list[dict[str, Any]],
    ground_truth: list[dict[str, Any]],
) -> dict[str, float]:
    pred_counter = {}
    gt_counter = {}

    for r in predictions:
        cat = r.get("violation_category")
        if cat in TARGET_CATEGORIES:
            pred_counter[cat] = pred_counter.get(cat, 0) + 1

    for r in ground_truth:
        cat = r.get("violation_category")
        if cat in TARGET_CATEGORIES:
            gt_counter[cat] = gt_counter.get(cat, 0) + 1

    cats = set(pred_counter) | set(gt_counter)
    tp = 0
    fp = 0
    fn = 0
    for c in cats:
        p = pred_counter.get(c, 0)
        g = gt_counter.get(c, 0)
        tp += min(p, g)
        fp += max(0, p - g)
        fn += max(0, g - p)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    denom = tp + fp + fn
    accuracy = tp / denom if denom > 0 else 1.0

    return {
        "Accuracy": round(accuracy, 6),
        "Recall": round(recall, 6),
        "Precision": round(precision, 6),
        "F1": round(f1, 6),
    }


def run_pylint(file_path: Path) -> tuple[list[dict[str, Any]], float]:
    start = time.perf_counter()
    cmd = [
        sys.executable,
        "-m",
        "pylint",
        str(file_path),
        "--output-format=json",
        "--score=n",
        "--disable=all",
        f"--enable={PYLINT_ENABLE}",
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return [], time.perf_counter() - start

    raw = (proc.stdout or "").strip()
    if not raw:
        return [], time.perf_counter() - start

    try:
        payload = json.loads(raw)
    except Exception:
        return [], time.perf_counter() - start

    findings = []
    if not isinstance(payload, list):
        return findings, time.perf_counter() - start

    for msg in payload:
        if not isinstance(msg, dict):
            continue
        category = map_pylint_to_category(msg)
        if category is None:
            continue
        line = msg.get("line")
        if not isinstance(line, int):
            continue
        message = str(msg.get("message", "")).strip()
        symbol = str(msg.get("symbol", "")).strip()
        comment = f"{symbol}: {message}" if message else symbol
        findings.append(
            {
                "line_number": line,
                "violation_category": category,
                "review_comment": comment,
            }
        )

    return findings, time.perf_counter() - start


def run_flake8(file_path: Path) -> tuple[list[dict[str, Any]], float]:
    start = time.perf_counter()
    cmd = [sys.executable, "-m", "flake8", str(file_path), "--format=%(row)d:%(col)d:%(code)s:%(text)s"]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return [], time.perf_counter() - start

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
            continue

        category = map_flake8_to_category(code, text)
        if category is None:
            continue

        comment = f"{code.strip()}: {text.strip()}" if text.strip() else code.strip()
        findings.append(
            {
                "line_number": row,
                "violation_category": category,
                "review_comment": comment,
            }
        )

    return findings, time.perf_counter() - start


def dedupe_static_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    out = []
    for f in findings:
        key = (f.get("line_number"), f.get("violation_category"))
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return sorted(out, key=lambda x: (x.get("line_number") or 0, x.get("violation_category") or ""))


def run_static_tool_on_code(pr_code: str) -> tuple[list[dict[str, Any]], dict[str, float]]:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
        tmp.write(pr_code)
        tmp_path = Path(tmp.name)

    try:
        total_start = time.perf_counter()
        findings = []
        pylint_findings, pylint_secs = run_pylint(tmp_path)
        flake8_findings, flake8_secs = run_flake8(tmp_path)
        findings.extend(pylint_findings)
        findings.extend(flake8_findings)

        total_secs = time.perf_counter() - total_start
        return dedupe_static_findings(findings), {
            "total_seconds": round(total_secs, 6),
            "pylint_seconds": round(pylint_secs, 6),
            "flake8_seconds": round(flake8_secs, 6),
        }
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


def _call_llm_with_retry(client, prompt, max_retries=2):
    """Call LLM and parse; retry up to max_retries times if result is empty."""
    retries = 0
    while True:
        try:
            raw = call_groq_json(client, prompt)
        except Exception:
            raw = ""
        reviews = parse_llm_reviews_preserve_partial(raw)
        if reviews or retries >= max_retries:
            return reviews, retries
        retries += 1


def prepare_rag_prompt(
    pr_code: str,
    pr_id: str,
    qdrant_url: str,
    prompt_path: str,
    repo_name: str | None = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    embed_model_name: str = DEFAULT_EMBED_MODEL,
) -> dict[str, Any]:
    """Do RAG retrieval and build the final prompt without calling the LLM.
    Returns dict with prompt, chunks, model, temperature."""
    prompt_template = _load_prompt_v1(Path("."), explicit_path=prompt_path)

    if pr_code.lstrip().startswith("diff --git") or "@@ " in pr_code:
        pr_code = _extract_added_lines_from_diff(pr_code)

    query_text = build_query_text_variant2(pr_code)

    chunks = retrieve_rag_chunks(
        pr_code=pr_code,
        query_text=query_text,
        qdrant_url=qdrant_url,
        repo_name=repo_name,
        collection_name=collection_name,
        embed_model_name=embed_model_name,
    )

    prompt = build_prompt(
        prompt_template=prompt_template,
        pr_id=pr_id,
        pr_code=pr_code,
        retrieved_chunks=[c["text"] for c in chunks],
    )

    return {
        "prompt": prompt,
        "chunks": chunks,
        "model": MODEL,
        "temperature": 0,
    }


def run_rag_review(
    pr_code: str,
    pr_id: str,
    qdrant_url: str,
    groq_api_key: str,
    prompt_path: str,
    repo_name: str | None = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    embed_model_name: str = DEFAULT_EMBED_MODEL,
    max_retries: int = 2,
) -> dict[str, Any]:
    """Run only the RAG pipeline on raw PR code. Used by the deployment worker."""
    prep = prepare_rag_prompt(
        pr_code=pr_code, pr_id=pr_id, qdrant_url=qdrant_url,
        prompt_path=prompt_path, repo_name=repo_name,
        collection_name=collection_name, embed_model_name=embed_model_name,
    )

    client = Groq(api_key=groq_api_key)
    reviews, retries = _call_llm_with_retry(client, prep["prompt"], max_retries)
    chunks = prep["chunks"]
    return {
        "reviews": reviews,
        "chunks_used": len(chunks),
        "retries": retries,
        "retrieved_chunks": [{"text": c["text"], "score": round(c.get("rerank_score", 0), 4), "category": c.get("category", "")} for c in chunks],
        "prompt_used": prep["prompt"],
    }


def run_eval_on_code(
    pr_code,
    ground_truth,
    qdrant_url,
    groq_api_key,
    prompt_path,
    repo_name=None,
    collection_name=DEFAULT_COLLECTION_NAME,
    embed_model_name=DEFAULT_EMBED_MODEL,
    max_retries=2,
):
    """Run all 3 baselines on raw code + ground truth. Returns reviews, metrics, latency."""
    prompt_template = _load_prompt_v1(Path("."), explicit_path=prompt_path)

    if pr_code.lstrip().startswith("diff --git") or "@@ " in pr_code:
        pr_code = _extract_added_lines_from_diff(pr_code)

    client = Groq(api_key=groq_api_key)
    pr_id = "eval"

    # --- RAG ---
    rag_t0 = time.perf_counter()
    query_text = build_query_text_variant2(pr_code)
    rag_q = time.perf_counter() - rag_t0

    rag_r0 = time.perf_counter()
    rag_candidates = retrieve_rag_chunks(
        pr_code=pr_code, query_text=query_text, qdrant_url=qdrant_url,
        repo_name=repo_name, collection_name=collection_name,
        embed_model_name=embed_model_name,
    )
    rag_r = time.perf_counter() - rag_r0

    rag_prompt = build_prompt(prompt_template, pr_id, pr_code, [c["text"] for c in rag_candidates])
    rag_a0 = time.perf_counter()
    rag_reviews, rag_retries = _call_llm_with_retry(client, rag_prompt, max_retries)
    rag_a = time.perf_counter() - rag_a0
    rag_total = time.perf_counter() - rag_t0

    # --- Naive LLM ---
    naive_t0 = time.perf_counter()
    naive_prompt = build_prompt(prompt_template, pr_id, pr_code, None)
    naive_a0 = time.perf_counter()
    naive_reviews, naive_retries = _call_llm_with_retry(client, naive_prompt, max_retries)
    naive_a = time.perf_counter() - naive_a0
    naive_total = time.perf_counter() - naive_t0

    # --- Static ---
    static_findings, static_latency = run_static_tool_on_code(pr_code)

    # --- Metrics ---
    gt = [{"line_number": g["line_number"], "violation_category": g["violation_category"]} for g in ground_truth]
    metrics = {
        "RAG": compute_micro_metrics(rag_reviews, gt),
        "Naive_LLM": compute_micro_metrics(naive_reviews, gt),
        "Static_tool": compute_micro_metrics(static_findings, gt),
    }
    latency = {
        "RAG": {"total": round(rag_total, 3), "query": round(rag_q, 3), "retrieval": round(rag_r, 3), "api": round(rag_a, 3), "retries": rag_retries},
        "Naive_LLM": {"total": round(naive_total, 3), "api": round(naive_a, 3), "retries": naive_retries},
        "Static_tool": {"total": static_latency.get("total_seconds", 0)},
    }
    rag_chunk_data = [{"text": c["text"], "score": round(c.get("rerank_score", 0), 4), "category": c.get("category", "")} for c in rag_candidates]
    return {
        "RAG": rag_reviews, "Naive_LLM": naive_reviews, "Static_tool": static_findings,
        "Metrics": metrics, "Latency": latency,
        "retrieved_chunks": rag_chunk_data,
        "prompts_used": {"RAG": rag_prompt, "Naive_LLM": naive_prompt},
    }


def run_models_for_pr(
    qdrant_url: str,
    groq_api_key: str,
    pr_file_path: str,
    gt_json_path: str,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    embed_model_name: str = DEFAULT_EMBED_MODEL,
) -> dict[str, Any]:
    root = _project_root()
    prompt_template = _load_prompt_v1(root)

    pr_path = Path(pr_file_path)
    gt_path = Path(gt_json_path)

    if not pr_path.exists():
        raise FileNotFoundError(f"PR file path does not exist: {pr_path}")
    if not gt_path.exists():
        raise FileNotFoundError(f"GT json path does not exist: {gt_path}")

    pr_id = pr_path.stem
    pr_code = _normalize_pr_text(pr_path)
    repo_name = _guess_repo_from_gt(gt_path, pr_path)
    gt_reviews = _load_gt_reviews_for_pr(gt_path, pr_path)

    client = Groq(api_key=groq_api_key)

    rag_total_start = time.perf_counter()
    rag_query_start = time.perf_counter()
    query_text = build_query_text_variant2(pr_code)
    rag_query_secs = time.perf_counter() - rag_query_start

    rag_retrieval_start = time.perf_counter()
    rag_candidates = retrieve_rag_chunks(
        pr_code=pr_code,
        query_text=query_text,
        qdrant_url=qdrant_url,
        repo_name=repo_name,
        collection_name=collection_name,
        embed_model_name=embed_model_name,
    )
    rag_retrieval_secs = time.perf_counter() - rag_retrieval_start
    rag_chunks = [c["text"] for c in rag_candidates]

    rag_prompt = build_prompt(
        prompt_template=prompt_template,
        pr_id=pr_id,
        pr_code=pr_code,
        retrieved_chunks=rag_chunks,
    )

    rag_api_start = time.perf_counter()
    try:
        rag_raw = call_groq_json(client, rag_prompt)
    except Exception:
        rag_raw = ""
    rag_api_secs = time.perf_counter() - rag_api_start

    rag_parse_start = time.perf_counter()
    rag_reviews = parse_llm_reviews_preserve_partial(rag_raw)
    rag_parse_secs = time.perf_counter() - rag_parse_start
    rag_total_secs = time.perf_counter() - rag_total_start

    naive_total_start = time.perf_counter()
    naive_prompt = build_prompt(
        prompt_template=prompt_template,
        pr_id=pr_id,
        pr_code=pr_code,
        retrieved_chunks=None,
    )

    naive_api_start = time.perf_counter()
    try:
        naive_raw = call_groq_json(client, naive_prompt)
    except Exception:
        naive_raw = ""
    naive_api_secs = time.perf_counter() - naive_api_start

    naive_parse_start = time.perf_counter()
    naive_reviews = parse_llm_reviews_preserve_partial(naive_raw)
    naive_parse_secs = time.perf_counter() - naive_parse_start
    naive_total_secs = time.perf_counter() - naive_total_start

    static_findings, static_latency = run_static_tool_on_code(pr_code)

    metrics = {
        "RAG": compute_micro_metrics(rag_reviews, gt_reviews),
        "Naive_LLM": compute_micro_metrics(naive_reviews, gt_reviews),
        "Static_tool": compute_micro_metrics(static_findings, gt_reviews),
    }

    latency = {
        "RAG": {
            "total_seconds": round(rag_total_secs, 6),
            "query_build_seconds": round(rag_query_secs, 6),
            "retrieval_seconds": round(rag_retrieval_secs, 6),
            "api_call_seconds": round(rag_api_secs, 6),
            "parse_seconds": round(rag_parse_secs, 6),
        },
        "Naive_LLM": {
            "total_seconds": round(naive_total_secs, 6),
            "api_call_seconds": round(naive_api_secs, 6),
            "parse_seconds": round(naive_parse_secs, 6),
        },
        "Static_tool": static_latency,
    }

    return {
        "RAG": rag_reviews,
        "Naive_LLM": naive_reviews,
        "Static_tool": static_findings,
        "Metrics": metrics,
        "Latency": latency,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run final RAG, naive LLM, and static tool on a single PR file.")
    parser.add_argument("--qdrant-url", required=True, help="Qdrant URL")
    parser.add_argument("--groq-api-key", required=True, help="Groq API key")
    parser.add_argument("--pr-file-path", required=True, help="Path to PR file or unified diff")
    parser.add_argument("--gt-json-path", required=True, help="Path to evaluation/GT json")
    parser.add_argument(
        "--collection-name",
        default=DEFAULT_COLLECTION_NAME,
        help=f"Qdrant collection name (default: {DEFAULT_COLLECTION_NAME})",
    )
    parser.add_argument(
        "--embed-model-name",
        default=DEFAULT_EMBED_MODEL,
        help=f"SentenceTransformer model (default: {DEFAULT_EMBED_MODEL})",
    )

    args = parser.parse_args()

    result = run_models_for_pr(
        qdrant_url=args.qdrant_url,
        groq_api_key=args.groq_api_key,
        pr_file_path=args.pr_file_path,
        gt_json_path=args.gt_json_path,
        collection_name=args.collection_name,
        embed_model_name=args.embed_model_name,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()


"""
Command example:
python scripts/single_pr_model_compare.py --qdrant-url http://localhost:6333 --groq-api-key YOUR_GROQ_API_KEY --pr-file-path data/processed/evaluation_files/synthetic-django_PR_21_admin.py --gt-json-path data/processed/evaluation.json
"""