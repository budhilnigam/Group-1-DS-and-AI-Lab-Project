from __future__ import annotations

import ast
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

from data_processing.documentation_signal import check_documentation_formatting_errors
from data_processing.indent_signal import check_indent_errors
from data_processing.mutable_default_signal import check_mutable_default_errors
from data_processing.naming_signal import check_naming_convention_errors
from data_processing.unused_import_signal import check_unused_import_errors

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_ROOT = ROOT
DEFAULT_EVALUATION_FILES_DIR = ROOT / "data" / "processed" / "evaluation_files"
DEFAULT_COLLECTION_NAME = os.getenv("RAG_COLLECTION_NAME", "guideline_embeddings")
DEFAULT_EMBED_MODEL_NAME = os.getenv("RAG_EMBED_MODEL_NAME", "BAAI/bge-large-en-v1.5")
DEFAULT_QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
DEFAULT_MAX_CHARS_PER_CHUNK = int(os.getenv("RAG_MAX_CHARS_PER_CHUNK", "700"))
DEFAULT_MAX_TOTAL_RETRIEVAL_CHARS = int(os.getenv("RAG_MAX_TOTAL_RETRIEVAL_CHARS", "2800"))
COMMON_SOURCE_TYPES = ["pep8", "flake8", "pylint", "ruff", "pep257"]
REPO_FAMILIES = ["django", "fastapi", "flask", "pandas", "sklearn", "scikit-learn"]


@lru_cache(maxsize=1)
def get_qdrant_client(url: str = DEFAULT_QDRANT_URL) -> QdrantClient:
    return QdrantClient(url=url)


@lru_cache(maxsize=1)
def get_embed_model(model_name: str = DEFAULT_EMBED_MODEL_NAME) -> SentenceTransformer:
    return SentenceTransformer(model_name)


def repo_family(repo_name: str | None) -> str | None:
    repo_lower = (repo_name or "").lower()
    for family in REPO_FAMILIES:
        if family in repo_lower:
            return "scikit-learn" if family == "sklearn" else family
    return None


def build_query_filter(repo_name: str | None):
    family = repo_family(repo_name)
    should_conditions = [
        models.FieldCondition(key="source_type", match=models.MatchValue(value=source_type))
        for source_type in COMMON_SOURCE_TYPES
    ]
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


def resolve_source_path(
    source_file: str,
    source_root: Path | None = None,
    evaluation_files_dir: Path | None = None,
) -> Path:
    source_root = source_root or DEFAULT_SOURCE_ROOT
    evaluation_files_dir = evaluation_files_dir or DEFAULT_EVALUATION_FILES_DIR

    candidate = Path(source_file)
    if candidate.is_absolute() and candidate.exists():
        return candidate

    candidate = source_root / source_file
    if candidate.exists():
        return candidate

    candidate = evaluation_files_dir / source_file
    if candidate.exists():
        return candidate

    candidate = evaluation_files_dir / Path(source_file).name
    return candidate


def payload_to_text(payload: Any) -> str:
    if payload is None:
        return ""
    if isinstance(payload, dict):
        for key in ["text", "content", "guideline", "review_comment", "review_text", "chunk"]:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return str(payload)
    return str(payload)


def entry_source_text(entry: dict) -> str:
    """Return the source text for an evaluation entry.

    The notebook passes evaluation metadata that usually contains `source_file`
    but not the full file contents. The regex-based query builders need the
    source text to detect categories such as mutable_default reliably, so this
    helper loads the file on demand when `file_text` is absent.
    """
    text = entry.get("file_text", "")
    if isinstance(text, str) and text.strip():
        return text

    source_file = entry.get("source_file") or entry.get("source_path")
    if not source_file:
        return ""

    source_path = resolve_source_path(str(source_file))
    try:
        return source_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _is_mutable_default_node(node: ast.AST) -> bool:
    if isinstance(node, (ast.List, ast.Dict, ast.Set)):
        return True
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name) and func.id in {"list", "dict", "set", "defaultdict"}:
            return True
        if isinstance(func, ast.Attribute) and func.attr in {"list", "dict", "set", "defaultdict"}:
            return True
    return False


def detect_mutable_default_issues(entry: dict, text: str) -> list[str]:
    """Detect mutable default argument issues with file-first, AST-fallback logic."""
    issues: list[str] = []

    source_file = entry.get("source_file") or entry.get("source_path")
    if source_file:
        try:
            source_path = resolve_source_path(str(source_file))
            file_issues = check_mutable_default_errors(str(source_path))
            issues.extend([msg for msg in file_issues if "mutable default" in msg.lower()])
        except Exception:
            pass

    if issues:
        return issues

    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        positional_args = list(fn.args.posonlyargs) + list(fn.args.args)
        positional_defaults = list(fn.args.defaults)
        if positional_defaults:
            start = len(positional_args) - len(positional_defaults)
            for arg, default in zip(positional_args[start:], positional_defaults):
                if _is_mutable_default_node(default):
                    issues.append(
                        f"Line {getattr(default, 'lineno', fn.lineno)}: Function '{fn.name}' uses mutable default for argument '{arg.arg}'."
                    )

        for kw_arg, kw_default in zip(fn.args.kwonlyargs, fn.args.kw_defaults):
            if kw_default is not None and _is_mutable_default_node(kw_default):
                issues.append(
                    f"Line {getattr(kw_default, 'lineno', fn.lineno)}: Function '{fn.name}' uses mutable default for keyword-only argument '{kw_arg.arg}'."
                )

    return issues


def retrieve_guidelines(
    query_text: str,
    repo_name: str | None,
    top_k: int = DEFAULT_TOP_K,
    client: QdrantClient | None = None,
    embed_model: SentenceTransformer | None = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
):
    client = client or get_qdrant_client()
    embed_model = embed_model or get_embed_model()
    query_vector = embed_model.encode(query_text).tolist()
    response = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        query_filter=build_query_filter(repo_name),
        limit=top_k,
    )
    return response.points


def build_query_text(entry: dict, source_file: Path) -> str:
        # STRATEGY 2 VARIANT 2: Helper-function based (signal-based approach)
    indent_issues = check_indent_errors(str(source_file))
    mutable_default_issues = check_mutable_default_errors(str(source_file))
    naming_issues = check_naming_convention_errors(str(source_file))
    documentation_issues = check_documentation_formatting_errors(str(source_file))
    unused_import_issues = check_unused_import_errors(str(source_file))

    signals = []
    if naming_issues:
        signals.append(f"Naming issues detected: {' '.join(naming_issues[:3])}")
    if indent_issues:
        signals.append(f"Indentation problems detected: {' '.join(indent_issues[:3])}")
    if mutable_default_issues:
        signals.append(f"Mutable default argument issues: {' '.join(mutable_default_issues[:2])}")
    if documentation_issues:
        signals.append(f"Documentation formatting issues: {' '.join(documentation_issues[:3])}")
    if unused_import_issues:
        signals.append(f"Unused import issues: {' '.join(unused_import_issues[:3])}")

    if not signals:
        signals.append("General Python code quality and PEP 8 compliance review.")

    return " ".join(signals)


# ============================================================================
# STRATEGY 2 - VARIANT 1: Regex/String-based Intelligent Query Generation
# ============================================================================
def query_strategy_regex_intelligent(entry: dict) -> str:
    """
    Strategy 2, Variant 1: Regex/string-based intelligent query generation.

    This variant detects violations using direct regex pattern matching on file text,
    rather than AST-based analysis. It's faster but potentially less accurate.

    Args:
        entry (dict): Entry dict with 'file_text' (full source code) and 'repo' keys.
    
    Returns:
        str: Query text combining multiple signal types joined with " ; " separator.
    """
    text = entry_source_text(entry)
    if not text:
        return "General Python code quality review"

    lines = text.splitlines()

    # Extract imports using regex
    imports = [ln.strip() for ln in lines if re.match(r"^\s*(import|from)\s+", ln)]

    # Detect camelCase identifiers (potential naming convention violations)
    camel_case_identifiers = set(re.findall(r"\b[a-z]+[A-Z][A-Za-z0-9_]*\b", text))

    # Detect mutable defaults with AST-backed fallback for better recall.
    mutable_default_issues = detect_mutable_default_issues(entry, text)
    mutable_default_count = len(mutable_default_issues)
    if not mutable_default_count:
        mutable_defaults = re.findall(
            r"def\s+\w+\([^)]*=\s*(\[\]|\{\}|dict\(|list\(|set\(|defaultdict\()",
            text,
        )
        mutable_default_count = len(mutable_defaults)

    # Check indentation issues via manual line inspection
    indent_issues = 0
    for ln in lines:
        stripped = ln.lstrip(" ")
        if not stripped or ln.startswith("#"):
            continue
        leading_spaces = len(ln) - len(stripped)
        if leading_spaces > 0 and leading_spaces % 4 != 0:
            indent_issues += 1

    # Count docstring markers
    docstring_markers = len(re.findall(r"'''|\"\"\"", text))

    # Build signals with " ; " separator (different from helper-based variant)
    signals = [
        f"repo family: {repo_family(entry.get('repo'))}",
        f"import statements count: {len(imports)}",
        f"camelCase identifiers: {', '.join(sorted(list(camel_case_identifiers))[:8]) or 'none'}",
        f"mutable-default patterns: {mutable_default_count}",
        f"non-4-space indentation lines: {indent_issues}",
        f"docstring markers count: {docstring_markers}",
        "focus on naming_convention, unused_import, indentation, mutable_default, documentation_formatting"
    ]

    if mutable_default_count:
        signals.append("mutable_default priority terms: B006 W0102 dangerous-default-value none sentinel pattern")

    return " ; ".join(signals)


def query_strategy_regex_intelligent_v2(entry: dict) -> str:
    """
    Strategy 2, Variant 1.2: regex-based query text with category-aware hints.

    This keeps the fast regex approach but adds explicit keywords for categories
    that are often confused during retrieval/reranking.
    """
    text = entry_source_text(entry)
    if not text:
        return "General Python code quality review ; focus naming_convention unused_import indentation mutable_default documentation_formatting"

    lines = text.splitlines()
    imports = [ln.strip() for ln in lines if re.match(r"^\s*(import|from)\s+", ln)]
    camel_case_identifiers = set(re.findall(r"\b[a-z]+[A-Z][A-Za-z0-9_]*\b", text))
    mutable_default_issues = detect_mutable_default_issues(entry, text)
    mutable_default_count = len(mutable_default_issues)
    if not mutable_default_count:
        mutable_defaults = re.findall(
            r"def\s+\w+\([^)]*=\s*(\[\]|\{\}|dict\(|list\(|set\(|defaultdict\()",
            text,
        )
        mutable_default_count = len(mutable_defaults)
    indent_issues = sum(
        1
        for ln in lines
        if ln.strip()
        and not ln.lstrip().startswith("#")
        and (len(ln) - len(ln.lstrip(" ")) > 0)
        and ((len(ln) - len(ln.lstrip(" "))) % 4 != 0)
    )
    docstring_markers = len(re.findall(r"'''|\"\"\"", text))

    hints = []
    if camel_case_identifiers:
        hints.append("naming_convention snake_case PascalCase")
    if imports:
        hints.append("unused_import import cleanup dead import")
    if indent_issues:
        hints.append("indentation 4-space tabs spaces")
    if mutable_default_count:
        hints.append(
            "mutable_default B006 W0102 dangerous-default-value mutable argument default list dict set defaultdict none sentinel"
        )
    if docstring_markers:
        hints.append("documentation_formatting docstring summary style")
    if not hints:
        hints.append("naming_convention unused_import indentation mutable_default documentation_formatting")

    signals = [
        f"repo family: {repo_family(entry.get('repo'))}",
        f"import statements count: {len(imports)}",
        f"camelCase identifiers: {', '.join(sorted(list(camel_case_identifiers))[:8]) or 'none'}",
        f"mutable-default patterns: {mutable_default_count}",
        f"non-4-space indentation lines: {indent_issues}",
        f"docstring markers count: {docstring_markers}",
        f"category hints: {' | '.join(hints)}",
    ]

    if mutable_default_issues:
        signals.append(f"mutable-default evidence: {' | '.join(mutable_default_issues[:2])}")

    return " ; ".join(signals)


# ============================================================================
# STRATEGY 2 - VARIANT 2: Helper Function / Signal-based variant
# ============================================================================
def build_query_text_signal_based(entry: dict, source_file: Path) -> str:
    """
    Strategy 2, Variant 2: Helper function / signal-based intelligent query generation.

    This variant detects violations using AST-based helper functions that perform
    sophisticated static analysis. It's more accurate but slower than regex variant.

    Args:
        entry (dict): Entry dict (currently unused, kept for API consistency).
        source_file (Path): Path to the Python source file to analyze.
    
    Returns:
        str: Query text combining multiple signal types joined with " " separator.
    """
    indent_issues = check_indent_errors(str(source_file))
    mutable_default_issues = check_mutable_default_errors(str(source_file))
    naming_issues = check_naming_convention_errors(str(source_file))
    documentation_issues = check_documentation_formatting_errors(str(source_file))
    unused_import_issues = check_unused_import_errors(str(source_file))

    signals = []
    if naming_issues:
        signals.append(f"Naming issues detected: {' '.join(naming_issues[:3])}")
    if indent_issues:
        signals.append(f"Indentation problems detected: {' '.join(indent_issues[:3])}")
    if mutable_default_issues:
        signals.append(f"Mutable default argument issues: {' '.join(mutable_default_issues[:2])}")
    if documentation_issues:
        signals.append(f"Documentation formatting issues: {' '.join(documentation_issues[:3])}")
    if unused_import_issues:
        signals.append(f"Unused import issues: {' '.join(unused_import_issues[:3])}")

    if not signals:
        signals.append("General Python code quality and PEP 8 compliance review.")

    return " ".join(signals)


# ============================================================================
# ALTERNATIVE SIGNAL CHECKING FUNCTIONS FOR EXPERIMENTATION
# ============================================================================
def check_indent_errors_lenient(file: str) -> list[str]:
    """
    Lenient indentation checking variant (fewer false positives).
    Only flags clear violations: tabs mixed with spaces, or indents not divisible by 4.
    """
    errors = []
    try:
        with open(file, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except Exception as exc:
        return [f"File read error: {exc}"]

    for i, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip('\n\r')
        stripped_line = line.lstrip(' \t')
    
        if not stripped_line or stripped_line.startswith('#'):
            continue
        
        leading = line[:len(line) - len(stripped_line)]
    
        if '\t' in leading and ' ' in leading:
            errors.append(f"Line {i}: Mixed tabs and spaces.")
        elif '\t' in leading:
            errors.append(f"Line {i}: Tab indentation found (use spaces).")
        elif ' ' in leading and len(leading) % 4 != 0:
            errors.append(f"Line {i}: Indentation not multiple of 4 ({len(leading)} spaces).")

    return errors


def check_naming_convention_errors_strict(file: str) -> list[str]:
    """
    Strict naming convention checking variant (includes edge cases and constant checking).
    """
    import ast
    try:
        with open(file, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
    except Exception as exc:
        return [f"File read error: {exc}"]

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"Syntax error at line {exc.lineno}: {exc.msg}"]

    errors = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Function names must be snake_case
            if not node.name.startswith("_") and re.match(r"^[A-Z]|[a-z0-9][A-Z]", node.name):
                errors.append(f"Line {node.lineno}: Function '{node.name}' not in snake_case.")
    
        if isinstance(node, ast.ClassDef):
            # Class names must be PascalCase
            if not re.match(r"^[A-Z][A-Za-z0-9]*$", node.name):
                errors.append(f"Line {node.lineno}: Class '{node.name}' not in PascalCase.")

    return errors


def check_unused_import_errors_conservative(file: str) -> list[str]:
    """
    Conservative unused import checking variant (fewer false positives).
    Ignores imports starting with _, and typing imports which may be for type hints.
    """
    import ast
    try:
        with open(file, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
    except Exception as exc:
        return [f"File read error: {exc}"]

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"Syntax error at line {exc.lineno}: {exc.msg}"]

    imported = {}
    used = set()
    typing_imports = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound = alias.asname if alias.asname else alias.name.split(".")[0]
                if not bound.startswith("_"):
                    imported[bound] = node.lineno
                    if "typing" in alias.name:
                        typing_imports.add(bound)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    continue
                bound = alias.asname if alias.asname else alias.name
                if not bound.startswith("_"):
                    imported[bound] = node.lineno
                    if node.module and "typing" in node.module:
                        typing_imports.add(bound)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used.add(node.id)

    errors = []
    for name, lineno in imported.items():
        if name not in used and name not in typing_imports:
            errors.append(f"Line {lineno}: Imported '{name}' may be unused.")

    return errors


def query_strategy(
    entry: dict,
    top_k: int = DEFAULT_TOP_K,
    client: QdrantClient | None = None,
    embed_model: SentenceTransformer | None = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    source_root: Path | None = None,
    evaluation_files_dir: Path | None = None,
    max_chars_per_chunk: int = DEFAULT_MAX_CHARS_PER_CHUNK,
    max_total_retrieval_chars: int = DEFAULT_MAX_TOTAL_RETRIEVAL_CHARS,
):
    source_file = entry.get("source_file")
    if not source_file:
        raise ValueError("entry must include source_file")

    source_path = resolve_source_path(source_file, source_root=source_root, evaluation_files_dir=evaluation_files_dir)
    query_text = build_query_text(entry, source_path)
    points = retrieve_guidelines(
        query_text=query_text,
        repo_name=entry.get("repo"),
        top_k=top_k,
        client=client,
        embed_model=embed_model,
        collection_name=collection_name,
    )

    retrieved_chunks = []

    total_chars = 0
    for point in points:
        payload = getattr(point, "payload", None)
        chunk = payload_to_text(payload)
        if not chunk:
            continue
        chunk = chunk[:max_chars_per_chunk].strip()
        if not chunk:
            continue
        if total_chars + len(chunk) > max_total_retrieval_chars:
            break
        retrieved_chunks.append(chunk)
        total_chars += len(chunk)

    return {
        "query_text": query_text,
        "retrieved_chunks": retrieved_chunks,
        "retrieved_count": len(retrieved_chunks),
        "source_path": str(source_path),
        "family": repo_family(entry.get("repo")),
    }
