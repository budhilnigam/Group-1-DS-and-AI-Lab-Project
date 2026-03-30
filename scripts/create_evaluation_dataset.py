#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import random
import re
import sys
import time
import difflib
from collections import Counter

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

GITHUB_API = "https://api.github.com"
MODELS_API = "https://models.github.ai/inference/chat/completions"

FRAMEWORKS = ["flask", "fastapi", "pandas", "sklearn", "django"]

VIOLATION_CATEGORIES = [
    "unused_import",
    "indentation",
    "naming_convention",
    "documentation_formatting",
    "mutable_default",
]

MODEL_CASCADE = [
    "openai/gpt-4.1",
    "openai/gpt-4o",
    "deepseek/DeepSeek-V3-0324",
    "openai/gpt-4.1-mini",
    "deepseek/deepseek-r1",
    "openai/gpt-4o-mini",
    "meta/llama-4-scout-17b-16e-instruct",
    "openai/gpt-4.1-nano",
    "microsoft/phi-4",
]

REPO_PREFIX = "synthetic"

EVAL_FILE_LISTS = {
    "flask": [
        ("routes/index.py", "Flask route handlers for home, search, and error pages"),
        ("services/email.py", "Email sending service using Flask-Mail with templates"),
        ("services/cache.py", "Redis caching wrapper for Flask views and API responses"),
        ("models/comment.py", "SQLAlchemy Comment model with user FK, post FK, timestamps"),
        ("models/tag.py", "SQLAlchemy Tag model with many-to-many relationship to Post"),
        ("utils/pagination.py", "Custom pagination helper for Flask SQLAlchemy queries"),
        ("utils/decorators.py", "Custom decorators: rate_limit, admin_required, json_response"),
        ("blueprints/api_v2.py", "REST API v2 blueprint with versioned endpoints and auth"),
        ("tasks/background.py", "Background task runner using threading for email and reports"),
        ("tests/test_api.py", "Pytest tests for API endpoints: CRUD, auth, error handling"),
    ],
    "fastapi": [
        ("routers/health.py", "Health check and readiness probe endpoints"),
        ("routers/admin.py", "Admin routes for user management and system stats"),
        ("services/notification.py", "Notification service with email and webhook support"),
        ("services/storage.py", "File storage service with local and S3 backends"),
        ("models/order.py", "SQLAlchemy Order model with status enum, total, user FK"),
        ("models/product.py", "SQLAlchemy Product model with price, inventory, category"),
        ("schemas/order.py", "Pydantic schemas for Order CRUD with status validation"),
        ("utils/rate_limiter.py", "Rate limiting utility using sliding window counter"),
        ("crud/order.py", "CRUD operations for Order with status transitions"),
        ("tests/test_orders.py", "Pytest tests for order endpoints with async client"),
    ],
    "django": [
        ("api/views.py", "DRF ViewSets for Article and Category with filtering"),
        ("api/permissions.py", "Custom DRF permissions: IsOwner, IsStaffOrReadOnly"),
        ("api/filters.py", "Django-filter FilterSets for Article search and date range"),
        ("services/search.py", "Full-text search service using Django ORM Q objects"),
        ("services/export.py", "Data export service generating CSV and PDF reports"),
        ("models/profile.py", "User profile model with bio, avatar, social links"),
        ("models/notification.py", "Notification model with read status and type choices"),
        ("utils/cache.py", "Django cache utilities with key generation and invalidation"),
        ("tasks/cleanup.py", "Management command for cleaning expired sessions and tokens"),
        ("tests/test_api.py", "DRF APITestCase for ViewSets with auth and permissions"),
    ],
    "pandas": [
        ("etl/extract.py", "Data extraction from multiple sources: API, database, files"),
        ("etl/transform.py", "Data transformation pipeline with chained operations"),
        ("etl/load.py", "Data loading functions for database and file outputs"),
        ("analysis/correlation.py", "Correlation analysis with heatmap generation"),
        ("analysis/outliers.py", "Outlier detection using IQR, Z-score, and isolation forest"),
        ("cleaning/text_cleaner.py", "Text data cleaning: normalize, strip HTML, fix encoding"),
        ("cleaning/date_parser.py", "Date parsing utility handling multiple formats"),
        ("reporting/summary.py", "Summary report generator with descriptive statistics"),
        ("utils/profiler.py", "DataFrame profiler reporting dtypes, nulls, memory usage"),
        ("tests/test_etl.py", "Pytest tests for ETL pipeline with sample CSV fixtures"),
    ],
    "sklearn": [
        ("models/classifier.py", "Multi-classifier trainer: SVM, KNN, DecisionTree with metrics"),
        ("models/regressor.py", "Multi-regressor trainer: SVR, KernelRidge with CV scoring"),
        ("preprocessing/encoder.py", "Feature encoding: ordinal, target, binary encoding"),
        ("preprocessing/scaler.py", "Custom scaling: robust, quantile, power transform"),
        ("evaluation/explainer.py", "Model explanation with feature importance and SHAP values"),
        ("evaluation/comparator.py", "Model comparison utility with statistical tests"),
        ("pipelines/text_pipeline.py", "Text ML pipeline: vectorize, select, classify"),
        ("pipelines/image_pipeline.py", "Image feature pipeline: extract, reduce, cluster"),
        ("utils/experiment.py", "Experiment tracker with param logging and result storage"),
        ("tests/test_classifiers.py", "Pytest tests for classifiers with iris and digits datasets"),
    ],
}

VIOLATION_COMBOS = [
    ["unused_import"],
    ["naming_convention"],
    ["unused_import", "indentation"],
    ["naming_convention", "mutable_default"],
    ["unused_import", "documentation_formatting"],
    ["indentation", "naming_convention"],
    ["mutable_default", "documentation_formatting"],
    ["unused_import", "mutable_default"],
    ["unused_import", "indentation", "naming_convention"],
    ["naming_convention", "mutable_default", "documentation_formatting"],
]


class LLMClient:
    def __init__(self, tokens: list[str]):
        if isinstance(tokens, str):
            tokens = [tokens]
        self.tokens = tokens
        self.token_idx = 0
        self.models = list(MODEL_CASCADE)
        self.current_idx = 0

    @property
    def _current_token(self) -> str:
        return self.tokens[self.token_idx]

    @property
    def _current_model(self) -> str:
        return self.models[self.current_idx]

    def _rotate_model(self):
        old = self._current_model
        self.current_idx = (self.current_idx + 1) % len(self.models)
        print(f"  [LLM] Rotating: {old} -> {self._current_model}")

    def _rotate_token(self) -> bool:
        old_idx = self.token_idx
        self.token_idx = (self.token_idx + 1) % len(self.tokens)
        if self.token_idx == old_idx:
            return False
        print(f"  [LLM] Rotating token: #{old_idx + 1} -> #{self.token_idx + 1}")
        self.current_idx = 0
        return True

    def generate(self, system_prompt: str, user_prompt: str,
                 temperature: float = 0.7, max_tokens: int = 4000) -> str:
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        for cycle in range(2):
            tokens_tried = 0
            while tokens_tried < len(self.tokens):
                headers = {"Authorization": f"Bearer {self._current_token}",
                           "Content-Type": "application/json"}
                models_tried = 0
                while models_tried < len(self.models):
                    payload["model"] = self._current_model
                    try:
                        resp = requests.post(MODELS_API, headers=headers,
                                             json=payload, timeout=120)
                        if resp.status_code == 429:
                            print(f"  [LLM] Rate limited on {self._current_model}")
                            self._rotate_model()
                            models_tried += 1
                            time.sleep(2)
                            continue
                        if resp.status_code == 403:
                            print(f"  [LLM] 403 Forbidden on {self._current_model}, rotating")
                            self._rotate_model()
                            models_tried += 1
                            time.sleep(1)
                            continue
                        resp.raise_for_status()
                        return resp.json()["choices"][0]["message"]["content"]
                    except requests.exceptions.HTTPError:
                        if resp.status_code >= 500:
                            time.sleep(3)
                            models_tried += 1
                            continue
                        raise
                if not self._rotate_token():
                    break
                tokens_tried += 1
            if cycle == 0:
                print("  [LLM] All rate-limited. Waiting 90s...")
                time.sleep(90)
        raise RuntimeError("All LLM tokens/models exhausted.")

    @staticmethod
    def extract_code(text: str) -> str:
        m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
        return m.group(1).strip() if m else text.strip()


def gh_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"}


def gh_get(token: str, path: str, params: dict | None = None) -> requests.Response:
    return requests.get(f"{GITHUB_API}{path}", headers=gh_headers(token),
                        params=params, timeout=30)


def gh_post(token: str, path: str, payload: dict) -> requests.Response:
    return requests.post(f"{GITHUB_API}{path}", headers=gh_headers(token),
                         json=payload, timeout=30)


def get_authenticated_user(token: str) -> str:
    resp = gh_get(token, "/user")
    resp.raise_for_status()
    return resp.json()["login"]


def check_repo_exists(token: str, owner: str, repo: str) -> bool:
    return gh_get(token, f"/repos/{owner}/{repo}").status_code == 200


def create_repo(token: str, name: str, description: str) -> dict:
    resp = gh_post(token, "/user/repos",
                   {"name": name, "description": description,
                    "private": False, "auto_init": True})
    resp.raise_for_status()
    return resp.json()


def get_default_branch_sha(token: str, owner: str, repo: str) -> str:
    resp = gh_get(token, f"/repos/{owner}/{repo}/git/ref/heads/main")
    resp.raise_for_status()
    return resp.json()["object"]["sha"]


def commit_files(token: str, owner: str, repo: str, branch: str,
                 files: dict[str, str], message: str,
                 parent_sha: str | None = None) -> str:
    hdrs = gh_headers(token)
    base = f"{GITHUB_API}/repos/{owner}/{repo}"

    tree_items = []
    for path, content in files.items():
        blob = requests.post(f"{base}/git/blobs", headers=hdrs,
                             json={"content": content, "encoding": "utf-8"}, timeout=30)
        blob.raise_for_status()
        tree_items.append({"path": path, "mode": "100644", "type": "blob",
                           "sha": blob.json()["sha"]})

    tree_payload: dict = {"tree": tree_items}
    if parent_sha:
        pc = requests.get(f"{base}/git/commits/{parent_sha}", headers=hdrs, timeout=30)
        pc.raise_for_status()
        tree_payload["base_tree"] = pc.json()["tree"]["sha"]

    tree_resp = requests.post(f"{base}/git/trees", headers=hdrs,
                              json=tree_payload, timeout=30)
    tree_resp.raise_for_status()

    commit_payload: dict = {"message": message, "tree": tree_resp.json()["sha"]}
    if parent_sha:
        commit_payload["parents"] = [parent_sha]
    commit_resp = requests.post(f"{base}/git/commits", headers=hdrs,
                                json=commit_payload, timeout=30)
    commit_resp.raise_for_status()
    commit_sha = commit_resp.json()["sha"]

    ref_resp = requests.get(f"{base}/git/ref/heads/{branch}", headers=hdrs, timeout=30)
    if ref_resp.status_code == 200:
        requests.patch(f"{base}/git/refs/heads/{branch}", headers=hdrs,
                       json={"sha": commit_sha}, timeout=30).raise_for_status()
    else:
        requests.post(f"{base}/git/refs", headers=hdrs,
                      json={"ref": f"refs/heads/{branch}", "sha": commit_sha},
                      timeout=30).raise_for_status()
    return commit_sha


def create_branch(token: str, owner: str, repo: str, branch: str, sha: str):
    resp = gh_post(token, f"/repos/{owner}/{repo}/git/refs",
                   {"ref": f"refs/heads/{branch}", "sha": sha})
    if resp.status_code == 422:
        requests.patch(f"{GITHUB_API}/repos/{owner}/{repo}/git/refs/heads/{branch}",
                       headers=gh_headers(token),
                       json={"sha": sha, "force": True}, timeout=30).raise_for_status()
        return
    resp.raise_for_status()


def create_pull_request(token: str, owner: str, repo: str,
                        title: str, body: str, head: str) -> dict:
    resp = gh_post(token, f"/repos/{owner}/{repo}/pulls",
                   {"title": title, "body": body, "head": head, "base": "main"})
    resp.raise_for_status()
    return resp.json()


def count_all_prs(token: str, owner: str, repo: str) -> int:
    count, page = 0, 1
    while True:
        resp = gh_get(token, f"/repos/{owner}/{repo}/pulls",
                      {"state": "all", "per_page": 100, "page": page})
        resp.raise_for_status()
        items = resp.json()
        count += len(items)
        if len(items) < 100:
            break
        page += 1
    return count


def count_eval_prs(token: str, owner: str, repo: str) -> int:
    count, page = 0, 1
    while True:
        resp = gh_get(token, f"/repos/{owner}/{repo}/pulls",
                      {"state": "all", "per_page": 100, "page": page})
        resp.raise_for_status()
        items = resp.json()
        for pr in items:
            if pr["head"]["ref"].startswith("eval/"):
                count += 1
        if len(items) < 100:
            break
        page += 1
    return count


def get_file_content(token: str, owner: str, repo: str,
                     path: str, ref: str = "main") -> str:
    resp = gh_get(token, f"/repos/{owner}/{repo}/contents/{path}", {"ref": ref})
    resp.raise_for_status()
    return base64.b64decode(resp.json()["content"]).decode("utf-8")


def get_repo_file_list(token: str, owner: str, repo: str) -> list[str]:
    resp = gh_get(token, f"/repos/{owner}/{repo}/git/trees/main",
                  {"recursive": "1"})
    resp.raise_for_status()
    return [i["path"] for i in resp.json()["tree"]
            if i["type"] == "blob" and i["path"].endswith(".py")]


def generate_clean_file(llm: LLMClient, framework: str,
                        file_path: str, description: str) -> str:
    system = (
        f"You are an expert {framework} developer. Write clean, production-quality "
        "Python code. Strict PEP 8: 4-space indent, snake_case, organized imports, "
        "proper docstrings. Output ONLY Python code."
    )
    user = (
        f"Write a Python module '{file_path}' for a {framework} project.\n"
        f"Purpose: {description}\n"
        "Requirements: 50-120 lines, valid syntax, realistic names, type hints, "
        "module docstring. Output ONLY Python code."
    )
    raw = llm.generate(system, user, temperature=0.5)
    code = llm.extract_code(raw)
    try:
        compile(code, "<gen>", "exec")
        return code
    except SyntaxError:
        return (f'"""{file_path} - {description}"""\n\n'
                f"# stub for {framework}\n")


INJECTION_INSTRUCTIONS = {
    "unused_import": "Add 2-3 unused imports (e.g. os, sys, re) at the top that are never referenced.",
    "indentation": "Change 2-3 blocks from 4-space to 2-space or 6-space indentation.",
    "naming_convention": "Rename 2-3 functions/variables from snake_case to camelCase.",
    "documentation_formatting": "Break 2-3 docstrings: remove them, or split single-line to malformed multi-line.",
    "mutable_default": "Change 2-3 function defaults from None to [] or {} (mutable defaults).",
}


def inject_multi_violations(llm: LLMClient, clean_code: str, file_path: str,
                            violations: list[str]) -> tuple[str, list[dict]]:
    instructions = "\n".join(
        f"- {v}: {INJECTION_INSTRUCTIONS[v]}" for v in violations
    )
    system = (
        "You modify Python code to introduce specific coding violations for testing. "
        "Apply ALL requested violation types. Output the COMPLETE modified code, "
        "then after a line '---VIOLATIONS---', output a JSON array where each item "
        "has 'line' (int), 'category' (str), and 'description' (str)."
    )
    user = (
        f"File: {file_path}\n```python\n{clean_code}\n```\n\n"
        f"Inject these violations:\n{instructions}\n\n"
        "Output the COMPLETE modified file, then the violations JSON."
    )

    try:
        raw = llm.generate(system, user, temperature=0.3)
    except RuntimeError:
        return _fallback_multi_inject(clean_code, violations)

    parts = raw.split("---VIOLATIONS---")
    code = LLMClient.extract_code(parts[0])

    violation_list = []
    if len(parts) > 1:
        try:
            jm = re.search(r"\[.*\]", parts[1], re.DOTALL)
            if jm:
                violation_list = json.loads(jm.group())
        except (json.JSONDecodeError, AttributeError):
            pass

    has_indentation = "indentation" in violations
    if not has_indentation:
        try:
            compile(code, "<inj>", "exec")
        except SyntaxError:
            return _fallback_multi_inject(clean_code, violations)

    if not violation_list:
        violation_list = _diff_violations(clean_code, code, violations)

    return code, violation_list


def _fallback_multi_inject(clean_code: str, violations: list[str]) -> tuple[str, list[dict]]:
    lines = clean_code.splitlines()
    result_violations = []

    if "unused_import" in violations:
        for i, imp in enumerate(["import os", "import sys", "import re"]):
            lines.insert(i, imp)
            result_violations.append(
                {"line": i + 1, "category": "unused_import",
                 "description": f"Added unused: {imp}"})

    if "naming_convention" in violations:
        count = 0
        for i, line in enumerate(lines):
            m = re.match(r"^(def )([a-z]+_[a-z]\w*)\(", line)
            if m and count < 3:
                old = m.group(2)
                parts = old.split("_")
                camel = parts[0] + "".join(w.capitalize() for w in parts[1:])
                lines[i] = line.replace(old, camel, 1)
                result_violations.append(
                    {"line": i + 1, "category": "naming_convention",
                     "description": f"Renamed {old} -> {camel}"})
                count += 1

    if "mutable_default" in violations:
        count = 0
        for i, line in enumerate(lines):
            if "=None" in line.replace(" ", "") and "def " in line and count < 3:
                lines[i] = line.replace("=None", "=[]", 1)
                result_violations.append(
                    {"line": i + 1, "category": "mutable_default",
                     "description": "Changed default None -> mutable []"})
                count += 1

    if "documentation_formatting" in violations:
        count = 0
        in_func = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("def ") or stripped.startswith("class "):
                in_func = True
                continue
            if in_func and '"""' in stripped and stripped.count('"""') == 2 and count < 3:
                indent = len(line) - len(line.lstrip())
                content = stripped.replace('"""', "").strip()
                lines[i] = " " * indent + '"""' + content
                lines.insert(i + 1, " " * indent + '"""')
                result_violations.append(
                    {"line": i + 1, "category": "documentation_formatting",
                     "description": "Broke docstring formatting"})
                count += 1
                in_func = False
            else:
                in_func = False

    if "indentation" in violations:
        count = 0
        for i, line in enumerate(lines):
            if line.startswith("    ") and count < 3:
                lines[i] = "  " + line.lstrip()
                result_violations.append(
                    {"line": i + 1, "category": "indentation",
                     "description": "Changed to 2-space indentation"})
                count += 1

    return "\n".join(lines), result_violations


def _diff_violations(clean: str, modified: str,
                     categories: list[str]) -> list[dict]:
    orig = clean.splitlines()
    mod = modified.splitlines()
    violations = []
    cat_cycle = iter(categories * 5)
    for i, mod_line in enumerate(mod):
        if i < len(orig) and orig[i] != mod_line:
            try:
                cat = next(cat_cycle)
            except StopIteration:
                cat = categories[0]
            violations.append({"line": i + 1, "category": cat,
                               "description": f"{cat} violation"})
    return violations[:8]


EVAL_REVIEW_PROMPTS = {
    "unused_import": "The import '{detail}' is present but never used in this file.",
    "indentation": "Inconsistent indentation at this line - expected 4 spaces per PEP 8.",
    "naming_convention": "This name uses camelCase instead of snake_case (PEP 8).",
    "documentation_formatting": "Docstring formatting is incorrect per PEP 257.",
    "mutable_default": "Mutable default argument detected - use None and initialize inside the function.",
}


def generate_review_comment(llm: LLMClient, file_path: str,
                            violated_code: str, violation: dict) -> str:
    line_num = violation.get("line", 1)
    category = violation.get("category", "")
    desc = violation.get("description", "")
    code_lines = violated_code.splitlines()
    start = max(0, line_num - 3)
    end = min(len(code_lines), line_num + 2)
    context = "\n".join(f"{j+1}: {code_lines[j]}"
                        for j in range(start, end) if j < len(code_lines))

    system = (
        "You are a code reviewer. Write a short, specific review comment about "
        "a coding issue. Be direct and reference the code. 1-2 sentences. "
        "Output ONLY the comment text."
    )
    user = (
        f"File: {file_path}, line {line_num}\n"
        f"Category: {category}\n"
        f"Context:\n{context}\n"
        f"Issue: {desc}\n"
        "Write the review comment."
    )
    try:
        comment = llm.generate(system, user, temperature=0.7, max_tokens=200)
        return comment.strip().strip('"').strip("'")
    except RuntimeError:
        return EVAL_REVIEW_PROMPTS.get(category, f"Issue: {desc}")


def make_unified_diff(clean_code: str, violated_code: str, file_path: str) -> str:
    clean_lines = clean_code.splitlines(keepends=True)
    violated_lines = violated_code.splitlines(keepends=True)
    diff = difflib.unified_diff(clean_lines, violated_lines,
                                fromfile=f"a/{file_path}",
                                tofile=f"b/{file_path}")
    return "".join(diff)


def create_eval_repo(token: str, owner: str, framework: str,
                     llm: LLMClient) -> str:
    repo_name = f"{REPO_PREFIX}-{framework}"

    if not check_repo_exists(token, owner, repo_name):
        print(f"[Error] {owner}/{repo_name} does not exist. "
              "Run create_synthetic_repos.py first.")
        sys.exit(1)

    print(f"[Repo] Using existing {owner}/{repo_name}")
    return repo_name


def create_eval_prs(token: str, owner: str, repo_name: str,
                    framework: str, llm: LLMClient,
                    target_prs: int) -> list[dict]:
    existing_eval = count_eval_prs(token, owner, repo_name)
    remaining = target_prs - existing_eval

    if remaining <= 0:
        print(f"[PR] {owner}/{repo_name} already has {existing_eval} eval PRs "
              f"(target: {target_prs}), skipping creation.")
        return []

    total_prs = count_all_prs(token, owner, repo_name)
    print(f"[PR] {owner}/{repo_name}: {total_prs} total PRs, {existing_eval} eval PRs, "
          f"creating {remaining} more eval PRs.")

    py_files = get_repo_file_list(token, owner, repo_name)
    if not py_files:
        print("  [PR] No Python files found, skipping.")
        return []

    main_sha = get_default_branch_sha(token, owner, repo_name)
    eval_entries = []

    for i in range(existing_eval, target_prs):
        combo = VIOLATION_COMBOS[i % len(VIOLATION_COMBOS)]
        target_file = py_files[i % len(py_files)]
        pr_num = i + 1
        combo_slug = "-".join(sorted(set(c.replace("_", "-") for c in combo)))
        branch_name = f"eval/{combo_slug}-{pr_num}"

        print(f"  [PR {pr_num}/{target_prs}] {combo} in {target_file}")

        try:
            clean_code = get_file_content(token, owner, repo_name, target_file)
            violated_code, violation_details = inject_multi_violations(
                llm, clean_code, target_file, combo)

            create_branch(token, owner, repo_name, branch_name, main_sha)
            commit_files(
                token, owner, repo_name, branch_name,
                {target_file: violated_code},
                f"Introduce {combo_slug} violations in {target_file}",
                parent_sha=main_sha)

            pr_title = f"Eval: {', '.join(combo)} in {os.path.basename(target_file)}"
            pr_body = f"Evaluation PR modifying `{target_file}` with violations."
            pr_data = create_pull_request(
                token, owner, repo_name, pr_title, pr_body, branch_name)
            print(f"    Created PR #{pr_data['number']}")

            reviews = []
            for v in violation_details[:5]:
                comment = generate_review_comment(
                    llm, target_file, violated_code, v)
                reviews.append({
                    "line_number": v.get("line", 1),
                    "violation_category": v.get("category", combo[0]),
                    "review_comment": comment,
                })
                time.sleep(0.5)

            eval_entries.append({
                "id": f"{repo_name}_PR_{pr_data['number']}",
                "repo": f"{owner}/{repo_name}",
                "source_path": target_file,
                "source_file": violated_code,
                "ground_truth_reviews": reviews,
            })

        except Exception as exc:
            print(f"    [Error] PR {pr_num}: {exc}")
            continue

        time.sleep(2)

    return eval_entries


def _parse_categories_from_slug(slug: str) -> list[str]:
    cat_slugs = sorted(
        [c.replace("_", "-") for c in VIOLATION_CATEGORIES],
        key=lambda s: -len(s),
    )
    found = []
    remaining = slug
    while remaining:
        matched = False
        for cs in cat_slugs:
            if remaining.startswith(cs):
                found.append(cs.replace("-", "_"))
                remaining = remaining[len(cs):]
                if remaining.startswith("-"):
                    remaining = remaining[1:]
                matched = True
                break
        if not matched:
            break
    return found


_UNITTEST_CAMEL = frozenset({
    "setUp", "tearDown", "setUpClass", "tearDownClass",
    "setUpModule", "tearDownModule", "addCleanup",
    "skipTest", "subTest",
})


def _split_params(params_str: str) -> list[str]:
    """Split function parameters respecting nested brackets."""
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in params_str:
        if ch in "([{":
            depth += 1
            current.append(ch)
        elif ch in ")]}":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current))
    return parts


def detect_violations(code: str, categories: list[str]) -> list[dict]:
    lines = code.splitlines()
    results = []

    # ── unused_import ────────────────────────────────────────────────
    if "unused_import" in categories:
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "__future__" in stripped:
                continue

            names_to_check = []
            # Strip inline comments before parsing
            code_part = stripped.split("#")[0].strip()
            if (code_part.startswith("import ")
                    and not code_part.startswith("import typing")):
                after_import = code_part[len("import "):].strip()
                for item in after_import.split(","):
                    item = item.strip()
                    if not item:
                        continue
                    if " as " in item:
                        alias = item.split(" as ")[-1].strip()
                        names_to_check.append((alias, item))
                    else:
                        mod = item.split(".")[0].strip()
                        names_to_check.append((mod, item))
            elif code_part.startswith("from ") and "import" in code_part:
                after_import = code_part.split("import", 1)[-1].strip()
                if after_import.strip() == "*":
                    continue
                for item in after_import.split(","):
                    item = item.strip()
                    if not item:
                        continue
                    if " as " in item:
                        alias = item.split(" as ")[-1].strip()
                        names_to_check.append((alias, alias))
                    else:
                        names_to_check.append((item, item))

            if not names_to_check:
                continue

            rest = "\n".join(lines[j] for j in range(len(lines)) if j != i)
            for name, desc in names_to_check:
                if not name:
                    continue
                if not re.search(r"\b" + re.escape(name) + r"\b", rest):
                    results.append({
                        "line": i + 1, "category": "unused_import",
                        "description": f"Unused import: {desc}"})

    # ── naming_convention ────────────────────────────────────────────
    if "naming_convention" in categories:
        i = 0
        while i < len(lines):
            stripped = lines[i].strip()

            fn_match = re.match(
                r"(?:async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", stripped)
            if fn_match:
                name = fn_match.group(1)
                if (re.search(r"[a-z][A-Z]", name)
                        and not name.startswith("__")
                        and name not in _UNITTEST_CAMEL):
                    results.append({
                        "line": i + 1, "category": "naming_convention",
                        "description": f"camelCase function name: {name}"})

                sig = lines[i]
                j = i
                while ")" not in sig and j + 1 < len(lines):
                    j += 1
                    sig += " " + lines[j]

                try:
                    ps = sig.index("(")
                    pe = sig.rindex(")")
                    params_str = sig[ps + 1:pe]
                except ValueError:
                    i = j + 1
                    continue

                for param_text in _split_params(params_str):
                    pname = (param_text.strip().lstrip("*")
                             .split(":")[0].split("=")[0].strip())
                    if (pname and pname.isidentifier()
                            and pname not in ("self", "cls", "", "/")):
                        if re.search(r"[a-z][A-Z]", pname):
                            for k in range(i, j + 1):
                                if pname in lines[k]:
                                    results.append({
                                        "line": k + 1,
                                        "category": "naming_convention",
                                        "description":
                                            f"camelCase parameter: {pname}"})
                                    break
                i = j + 1
                continue

            self_match = re.match(
                r"self\.([a-z][a-zA-Z0-9_]*)\s*[:=]", stripped)
            if self_match:
                attr_name = self_match.group(1)
                if re.search(r"[a-z][A-Z]", attr_name):
                    results.append({
                        "line": i + 1, "category": "naming_convention",
                        "description":
                            f"camelCase attribute: self.{attr_name}"})

            if not stripped.startswith((
                    "def ", "class ", "for ", "if ", "elif ", "while ",
                    "return ", "from ", "import ", "with ", "except ",
                    "assert ", "yield ", "raise ", "#", "async ")):
                var_match = re.match(r"([a-z][a-zA-Z0-9]*)\s*[:=]", stripped)
                if var_match:
                    vname = var_match.group(1)
                    if re.search(r"[a-z][A-Z]", vname):
                        results.append({
                            "line": i + 1, "category": "naming_convention",
                            "description":
                                f"camelCase variable: {vname}"})

            i += 1

    # ── indentation ──────────────────────────────────────────────────
    if "indentation" in categories:
        paren_depth = 0
        in_multiline_str = False
        seen_indents = {0}
        prev_nonblank_indent = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue

            triple_count = line.count('"""') + line.count("'''")
            if in_multiline_str:
                if triple_count % 2 == 1:
                    in_multiline_str = False
                continue
            if triple_count % 2 == 1:
                in_multiline_str = True

            old_depth = paren_depth
            paren_depth += line.count("(") + line.count("[") + line.count("{")
            paren_depth -= line.count(")") + line.count("]") + line.count("}")
            paren_depth = max(0, paren_depth)

            if old_depth > 0:
                continue

            indent = len(line) - len(line.lstrip())

            if indent < prev_nonblank_indent and indent in seen_indents:
                seen_indents = {l for l in seen_indents if l <= indent}

            if indent in seen_indents:
                prev_nonblank_indent = indent
                continue

            if indent > prev_nonblank_indent:
                diff = indent - prev_nonblank_indent
            else:
                parent = max(
                    (l for l in seen_indents if l < indent), default=0)
                diff = indent - parent

            if diff % 4 != 0:
                results.append({
                    "line": i + 1, "category": "indentation",
                    "description": f"Non-4-space indent ({indent} spaces)"})

            seen_indents.add(indent)
            prev_nonblank_indent = indent

    # ── mutable_default ──────────────────────────────────────────────
    if "mutable_default" in categories:
        sig_depth = 0
        in_sig = False
        for i, line in enumerate(lines):
            if re.match(r"\s*(?:async\s+)?def\s+", line):
                in_sig = True
                sig_depth = 0
            if in_sig:
                sig_depth += line.count("(") - line.count(")")
                for m in re.finditer(
                        r"=\s*(\[\]|\{\}|\[[^\]]+\]|\{[^\}]+\})", line):
                    val = m.group(1)
                    before = line[:m.start()].rstrip()
                    pname_match = re.search(r"(\w+)\s*(?::.*)?$", before)
                    if pname_match:
                        pname = pname_match.group(1)
                        if pname not in ("self", "cls", "def", "async",
                                         "return", "class", "if", "else"):
                            results.append({
                                "line": i + 1,
                                "category": "mutable_default",
                                "description":
                                    f"Mutable default {val} for "
                                    f"param '{pname}'"})
                if sig_depth <= 0:
                    in_sig = False

    # ── documentation_formatting ─────────────────────────────────────
    if "documentation_formatting" in categories:
        for i, line in enumerate(lines):
            stripped = line.strip()
            if i > 0:
                prev_stripped = lines[i - 1].strip()
                if (prev_stripped.startswith(("import ", "from "))
                        and stripped.startswith(('"""', "'''"))):
                    if not any(
                            lines[j].strip().startswith(("def ", "class "))
                            for j in range(max(0, i - 3), i)):
                        results.append({
                            "line": i + 1,
                            "category": "documentation_formatting",
                            "description":
                                "Module docstring placed after imports"})
            if (stripped.startswith(('"""', "'''"))
                    and (stripped.count('"""') + stripped.count("'''")) == 1):
                if i + 1 < len(lines):
                    next_s = lines[i + 1].strip()
                    if next_s in ('"""', "'''"):
                        results.append({
                            "line": i + 1,
                            "category": "documentation_formatting",
                            "description":
                                "Single-line docstring split across lines"})
            if ('"""' in stripped or "'''" in stripped) and (
                    stripped.endswith('"""') or stripped.endswith("'''")):
                indent = len(line) - len(line.lstrip())
                expected_indent = None
                for j in range(i - 1, max(i - 5, -1), -1):
                    pline = lines[j].strip()
                    if pline.startswith(("def ", "class ", "async def ")):
                        expected_indent = (
                            len(lines[j]) - len(lines[j].lstrip())) + 4
                        break
                if expected_indent is not None and indent != expected_indent:
                    results.append({
                        "line": i + 1,
                        "category": "documentation_formatting",
                        "description":
                            "Docstring indentation doesn't match block"})

    return results


def fetch_existing_eval_data(token: str, owner: str,
                             repo_name: str, framework: str,
                             llm: LLMClient) -> list[dict]:
    print(f"  [Fetch] Rebuilding eval data from existing PRs in {owner}/{repo_name}...")
    entries = []
    page = 1
    while True:
        resp = gh_get(token, f"/repos/{owner}/{repo_name}/pulls",
                      {"state": "all", "per_page": 100, "page": page})
        resp.raise_for_status()
        prs = resp.json()
        if not prs:
            break

        for pr in prs:
            branch = pr["head"]["ref"]
            if not branch.startswith("eval/"):
                continue

            pr_number = pr["number"]
            files_resp = gh_get(
                token, f"/repos/{owner}/{repo_name}/pulls/{pr_number}/files")
            files_resp.raise_for_status()
            pr_files = files_resp.json()
            if not pr_files:
                continue

            for pf in pr_files:
                file_path = pf["filename"]

                try:
                    file_content = get_file_content(
                        token, owner, repo_name, file_path,
                        ref=branch)
                except Exception:
                    file_content = pf.get("patch", "")

                file_content = _strip_giveaway_comments(file_content)

                reviews = []
                detected = detect_violations(
                    file_content, VIOLATION_CATEGORIES)
                for hit in detected:
                    reviews.append({
                        "line_number": hit["line"],
                        "violation_category": hit["category"],
                        "review_comment": hit["description"],
                    })

                entries.append({
                    "id": f"{repo_name}_PR_{pr_number}",
                    "repo": f"{owner}/{repo_name}",
                    "source_path": file_path,
                    "source_file": file_content,
                    "ground_truth_reviews": reviews,
                })
            time.sleep(0.3)

        if len(prs) < 100:
            break
        page += 1

    return entries


GIVEAWAY_RE = re.compile(
    r"("
    r"#\s*[Uu]nused[\s_]import.*$|"
    r"#\s*unused$|"
    r"#\s*[Mm]utable[\s_]default.*$|"
    r"#\s*[Rr]enamed.*$|"
    r"#\s*[Cc]hanged\s+from.*$|"
    r"#\s*camelCase.*$|"
    r"#\s*naming[_\s]convention.*$|"
    r"#\s*unused_import.*$|"
    r"#\s*indentation.*$|"
    r"#\s*[Dd]ocstring.*$|"
    r"#\s*[Bb]roke.*$|"
    r"#\s*[Ss]tub\s+for.*$|"
    r"#\s*[Vv]iolation.*$"
    r")", re.IGNORECASE)


def _strip_giveaway_comments(code: str) -> str:
    return "\n".join(
        GIVEAWAY_RE.sub("", line).rstrip()
        for line in code.split("\n")
    )


def save_source_file(output_dir: str, entry_id: str, source_path: str,
                     content: str) -> str:
    content = _strip_giveaway_comments(content)
    ext = os.path.splitext(source_path)[1] or ".py"
    safe_name = source_path.replace("/", "_").replace("\\", "_")
    filename = f"{entry_id}_{safe_name}"
    if not filename.endswith(ext):
        filename += ext
    files_dir = os.path.join(output_dir, "evaluation_files")
    os.makedirs(files_dir, exist_ok=True)
    filepath = os.path.join(files_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return f"evaluation_files/{filename}"


def main():
    parser = argparse.ArgumentParser(
        description="Create evaluation dataset with multi-violation PRs.")
    parser.add_argument("--repo-token", default=None)
    parser.add_argument("--llm-token", default=None)
    parser.add_argument("--repos", nargs="+", default=FRAMEWORKS, choices=FRAMEWORKS)
    parser.add_argument("--num-prs", type=int, default=20)
    parser.add_argument("--output", default="data/processed/evaluation.json")
    args = parser.parse_args()

    repo_token = args.repo_token or os.environ.get("GITHUB_REPO")
    if not repo_token:
        print("[Error] No repo token. Pass --repo-token or set GITHUB_REPO.")
        sys.exit(1)

    raw_llm = args.llm_token or os.environ.get("GITHUB_LLM_TOKEN", "")
    raw_llm = raw_llm.strip().strip("[]")
    llm_tokens = [t.strip() for t in raw_llm.split(",") if t.strip()]
    if not llm_tokens:
        print("[Error] No LLM tokens. Pass --llm-token or set GITHUB_LLM_TOKEN.")
        sys.exit(1)

    print("[Auth] Verifying repo token ...")
    owner = get_authenticated_user(repo_token)
    print(f"[Auth] Authenticated as: {owner}")

    llm = LLMClient(llm_tokens)
    print(f"[Auth] LLM client with {len(llm_tokens)} token(s).\n")

    all_entries = []

    for framework in args.repos:
        print(f"{'='*60}")
        print(f"Processing: {framework}")
        print(f"{'='*60}")

        repo_name = create_eval_repo(token=repo_token, owner=owner,
                                     framework=framework, llm=llm)

        new_entries = create_eval_prs(
            token=repo_token, owner=owner, repo_name=repo_name,
            framework=framework, llm=llm, target_prs=args.num_prs)

        if not new_entries:
            existing = fetch_existing_eval_data(
                token=repo_token, owner=owner, repo_name=repo_name,
                framework=framework, llm=llm)
            all_entries.extend(existing)
        else:
            all_entries.extend(new_entries)

        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(sorted(all_entries, key=lambda e: (e["repo"], e["id"])),
                      f, indent=2, ensure_ascii=False)
        print(f"  [Save] {len(all_entries)} entries saved so far.")

    all_entries.sort(key=lambda e: (e["repo"], e["id"]))

    output_dir = os.path.dirname(args.output)
    os.makedirs(output_dir, exist_ok=True)
    for entry in all_entries:
        content = entry["source_file"]
        rel_path = save_source_file(output_dir, entry["id"],
                                    entry["source_path"], content)
        entry["source_file"] = rel_path

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(all_entries, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"Saved {len(all_entries)} evaluation entries to {args.output}")

    by_repo = Counter(e["repo"] for e in all_entries)
    by_cat = Counter()
    for e in all_entries:
        for r in e["ground_truth_reviews"]:
            by_cat[r["violation_category"]] += 1

    print(f"\nBy repo:")
    for k, v in sorted(by_repo.items()):
        print(f"  {k}: {v}")
    print(f"\nBy violation category:")
    for k, v in sorted(by_cat.items()):
        print(f"  {k}: {v}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
