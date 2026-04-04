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

GUIDELINES_MAP = {
    "django": "django_chunks.json",
    "fastapi": "fastapi_chunks.json",
    "pandas": "pandas_chunks.json",
    "sklearn": "scikit-learn_chunks.json",
}

FILE_LISTS = {
    "flask": [
        ("app.py", "Flask application factory with create_app function, register blueprints, config loading"),
        ("config.py", "Flask configuration classes (Development, Production, Testing) with settings like SECRET_KEY, DATABASE_URI"),
        ("extensions.py", "Flask extension initialization (SQLAlchemy, Migrate, Login, Mail) without app binding"),
        ("models/user.py", "SQLAlchemy User model with fields: id, username, email, password_hash, created_at, methods for password hashing"),
        ("models/post.py", "SQLAlchemy Post model with fields: id, title, body, timestamp, author_id foreign key, relationships"),
        ("views/auth.py", "Flask blueprint for auth routes: login, logout, register with form validation and flash messages"),
        ("views/main.py", "Flask blueprint for main routes: index, about, dashboard with login_required decorator"),
        ("views/api.py", "Flask blueprint for REST API endpoints: GET/POST /api/posts, GET /api/users with jsonify responses"),
        ("forms/auth.py", "WTForms classes: LoginForm, RegistrationForm with validators (DataRequired, Email, EqualTo)"),
        ("forms/post.py", "WTForms PostForm and CommentForm with TextAreaField, StringField, validators"),
        ("utils/helpers.py", "Utility functions: format_datetime, slugify, paginate_query, send_email helper"),
        ("utils/validators.py", "Custom validators: validate_username, validate_email_domain, validate_file_extension"),
        ("middleware.py", "Flask before_request and after_request handlers for logging, CORS headers, request timing"),
        ("blueprints/admin.py", "Admin blueprint with routes for user management, dashboard stats, content moderation"),
        ("blueprints/blog.py", "Blog blueprint with routes for listing posts, single post view, create/edit/delete post"),
        ("tests/test_auth.py", "Pytest tests for auth routes: test_login, test_logout, test_register, test_invalid_login"),
        ("tests/test_main.py", "Pytest tests for main routes: test_index, test_dashboard_requires_login, test_about_page"),
        ("tests/test_models.py", "Pytest tests for models: test_user_creation, test_password_hashing, test_post_relationship"),
        ("tests/conftest.py", "Pytest fixtures: app, client, db, sample_user, sample_post using Flask test config"),
        ("cli.py", "Flask CLI commands using click: init-db, seed-data, create-admin, run-tests"),
    ],
    "fastapi": [
        ("main.py", "FastAPI app creation with lifespan, include routers, CORS middleware, root health endpoint"),
        ("config.py", "Pydantic BaseSettings for configuration: DATABASE_URL, SECRET_KEY, DEBUG, from environment/.env"),
        ("database.py", "SQLAlchemy async setup: engine, sessionmaker, Base, get_db dependency generator"),
        ("models/user.py", "SQLAlchemy User model: id, username, email, hashed_password, is_active, created_at columns"),
        ("models/item.py", "SQLAlchemy Item model: id, title, description, price, owner_id FK, relationship to User"),
        ("schemas/user.py", "Pydantic schemas: UserCreate, UserUpdate, UserResponse, UserInDB with email validation"),
        ("schemas/item.py", "Pydantic schemas: ItemCreate, ItemUpdate, ItemResponse with Field validators and examples"),
        ("routers/users.py", "APIRouter for users: GET /users, GET /users/{id}, POST /users, PUT /users/{id}, DELETE"),
        ("routers/items.py", "APIRouter for items: CRUD endpoints with query params for pagination and filtering"),
        ("routers/auth.py", "APIRouter for auth: POST /token (OAuth2 password flow), POST /refresh, GET /me"),
        ("dependencies.py", "Dependency functions: get_current_user, get_db_session, pagination_params, require_admin"),
        ("middleware.py", "Custom middleware: RequestTimingMiddleware, LoggingMiddleware with structured logging"),
        ("utils/security.py", "Security utilities: hash_password, verify_password, create_access_token, decode_token using jose"),
        ("utils/helpers.py", "Helper functions: generate_slug, format_response, calculate_offset, sanitize_input"),
        ("crud/user.py", "CRUD operations for User: get_user, get_users, create_user, update_user, delete_user using async session"),
        ("crud/item.py", "CRUD operations for Item: get_item, get_items, create_item, update_item with owner filtering"),
        ("tests/test_users.py", "Pytest tests for user endpoints: test_create_user, test_get_user, test_update_user, test_list_users"),
        ("tests/test_items.py", "Pytest tests for item endpoints: test_create_item, test_get_items, test_filter_items"),
        ("tests/conftest.py", "Pytest fixtures: async_client, test_db, sample_user, auth_headers using httpx.AsyncClient"),
        ("exceptions.py", "Custom exception classes and handlers: NotFoundError, ForbiddenError, ValidationError with handler registration"),
    ],
    "django": [
        ("settings.py", "Django settings module: INSTALLED_APPS, MIDDLEWARE, DATABASES, AUTH_PASSWORD_VALIDATORS, TEMPLATES config"),
        ("urls.py", "Root URL configuration: admin, api, auth paths with include() and app_name namespaces"),
        ("wsgi.py", "WSGI application entry point with get_wsgi_application and os.environ default settings"),
        ("models.py", "Django models: Article, Category, Tag with fields, Meta class, __str__, get_absolute_url"),
        ("views.py", "Class-based views: ArticleListView, ArticleDetailView, ArticleCreateView with mixins"),
        ("forms.py", "Django ModelForms: ArticleForm, CategoryForm with custom clean methods and widgets"),
        ("admin.py", "ModelAdmin classes: ArticleAdmin with list_display, search_fields, list_filter, prepopulated_fields"),
        ("serializers.py", "DRF serializers: ArticleSerializer, CategorySerializer with nested relations and validation"),
        ("managers.py", "Custom QuerySet and Manager: PublishedManager, ArticleQuerySet with chainable filter methods"),
        ("signals.py", "Django signals: post_save for Article slug generation, pre_delete for cleanup, m2m_changed handler"),
        ("middleware.py", "Custom middleware classes: TimingMiddleware, RequestLoggingMiddleware with __init__, __call__"),
        ("templatetags/custom_tags.py", "Custom template tags and filters: markdown_to_html, time_since, truncate_words, active_link"),
        ("utils/helpers.py", "Utility functions: generate_unique_slug, get_client_ip, send_notification_email"),
        ("utils/validators.py", "Custom validators: validate_image_size, validate_slug_format, validate_no_profanity"),
        ("tests/test_models.py", "TestCase for models: test_article_creation, test_slug_generation, test_category_relationship"),
        ("tests/test_views.py", "TestCase for views: test_article_list, test_article_detail, test_create_requires_login"),
        ("tests/test_forms.py", "TestCase for forms: test_valid_form, test_empty_form, test_duplicate_title_validation"),
        ("tests/conftest.py", "Pytest fixtures with django.test: create_user, create_article, create_category, client setup"),
        ("management/commands/seed_data.py", "Custom management command: seed_data with handle() creating sample articles, categories, users"),
        ("permissions.py", "DRF permissions: IsAuthorOrReadOnly, IsAdminOrReadOnly with has_object_permission"),
    ],
    "pandas": [
        ("data_loader.py", "Functions to load data from CSV, Excel, JSON, SQL with pandas read_ functions, dtype specification, error handling"),
        ("data_cleaner.py", "Data cleaning functions: remove_duplicates, standardize_columns, fix_dtypes, handle_outliers using IQR"),
        ("feature_engineering.py", "Feature creation: polynomial_features, date_features, interaction_terms, binning using pd.cut/qcut"),
        ("data_transformer.py", "DataFrame transformations: melt, pivot, stack/unstack, transpose with proper index handling"),
        ("aggregations.py", "Aggregation functions: summary_stats, grouped_agg, custom_agg with named aggregation syntax"),
        ("time_series.py", "Time series operations: resample, rolling_mean, shift, pct_change with DatetimeIndex handling"),
        ("merge_operations.py", "DataFrame merge/join functions: inner_merge, left_join, concat_frames, merge_asof with validation"),
        ("pivot_operations.py", "Pivot table operations: create_pivot, cross_tabulation, pivot_and_fill with margins support"),
        ("string_operations.py", "String accessor operations: clean_text, extract_patterns, split_columns using .str methods"),
        ("missing_data.py", "Missing data handlers: detect_missing, fill_strategies, interpolate_values, drop_incomplete rows/cols"),
        ("data_validator.py", "Validation functions: check_schema, validate_ranges, assert_no_nulls, check_unique_columns"),
        ("io_operations.py", "I/O functions: to_parquet, to_excel_formatted, to_sql_chunked, read_chunked_csv with progress"),
        ("visualization.py", "DataFrame plotting helpers: plot_distribution, plot_correlation_matrix, plot_time_series using matplotlib"),
        ("statistical_analysis.py", "Stats functions: descriptive_stats, correlation_analysis, hypothesis_test using scipy.stats"),
        ("groupby_operations.py", "GroupBy operations: group_and_transform, group_filter, apply_custom_func, group_ranking"),
        ("window_functions.py", "Window functions: rolling_statistics, expanding_mean, ewm_smoothing with min_periods"),
        ("categorical_data.py", "Categorical operations: encode_categories, ordered_categories, memory_optimize_categories"),
        ("multi_index.py", "MultiIndex operations: create_multi_index, cross_section, level_operations, reset_and_set_index"),
        ("performance_utils.py", "Performance utilities: optimize_dtypes, chunked_processing, memory_usage_report, vectorized_ops"),
        ("tests/test_pipeline.py", "Pytest tests for the data pipeline: test_load, test_clean, test_transform, test_aggregate with sample DataFrames"),
    ],
    "sklearn": [
        ("preprocessing.py", "Preprocessing functions: scale_features, encode_labels, impute_missing using StandardScaler, LabelEncoder, SimpleImputer"),
        ("feature_selection.py", "Feature selection: select_k_best, recursive_elimination, variance_threshold using sklearn selectors"),
        ("model_training.py", "Model training functions: train_classifier, train_regressor with fit, parameter logging"),
        ("model_evaluation.py", "Evaluation functions: evaluate_classifier, evaluate_regressor returning metrics dict with accuracy, precision, recall, MAE"),
        ("pipeline.py", "sklearn Pipeline construction: build_preprocessing_pipeline, build_full_pipeline with ColumnTransformer"),
        ("custom_transformer.py", "Custom sklearn transformer: OutlierRemover(BaseEstimator, TransformerMixin) with fit, transform"),
        ("cross_validation.py", "Cross-validation functions: stratified_kfold_cv, leave_one_out_cv, time_series_split returning scores"),
        ("hyperparameter_tuning.py", "Hyperparameter tuning: grid_search, random_search, bayesian_optimize with param_grid definitions"),
        ("ensemble_models.py", "Ensemble model functions: build_random_forest, build_gradient_boosting, build_voting_classifier"),
        ("clustering.py", "Clustering functions: kmeans_cluster, dbscan_cluster, silhouette_analysis with elbow method"),
        ("dimensionality_reduction.py", "Dim reduction: apply_pca, apply_tsne, apply_umap with explained_variance tracking"),
        ("text_classification.py", "Text classification: tfidf_vectorize, train_text_classifier using TfidfVectorizer and MultinomialNB"),
        ("regression_models.py", "Regression: train_linear, train_ridge, train_lasso, train_elastic_net with alpha parameters"),
        ("metrics_utils.py", "Metrics utilities: classification_report_dict, plot_confusion_matrix, plot_roc_curve helpers"),
        ("data_splitter.py", "Data splitting: train_test_val_split, stratified_split, time_based_split returning X_train, X_test, y_train, y_test"),
        ("model_persistence.py", "Model save/load: save_model, load_model, export_onnx using joblib and pickle with versioning"),
        ("feature_extraction.py", "Feature extraction: extract_text_features, extract_image_features using sklearn extractors"),
        ("anomaly_detection.py", "Anomaly detection: isolation_forest_detect, local_outlier_factor, one_class_svm for outlier detection"),
        ("utils/helpers.py", "Utility functions: set_seed, log_experiment, format_results, timer_decorator for reproducibility"),
        ("tests/test_models.py", "Pytest tests: test_preprocessing, test_train_classifier, test_pipeline, test_evaluation with iris/boston datasets"),
    ],
}


class LLMClient:
    def __init__(self, tokens: list[str]):
        if isinstance(tokens, str):
            tokens = [tokens]
        self.tokens = tokens
        self.token_idx = 0
        self.models = list(MODEL_CASCADE)
        self.current_idx = 0
        self._request_counts: dict[str, int] = {m: 0 for m in self.models}

    @property
    def _current_token(self) -> str:
        return self.tokens[self.token_idx]

    @property
    def _current_model(self) -> str:
        return self.models[self.current_idx]

    def _rotate_model(self):
        old = self._current_model
        self.current_idx = (self.current_idx + 1) % len(self.models)
        print(f"  [LLM] Rotating model: {old} -> {self._current_model}")

    def _rotate_token(self) -> bool:
        old_idx = self.token_idx
        self.token_idx = (self.token_idx + 1) % len(self.tokens)
        if self.token_idx == old_idx:
            return False
        print(f"  [LLM] Rotating token: #{old_idx + 1} -> #{self.token_idx + 1}")
        self.current_idx = 0
        return True

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> str:
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        max_full_cycles = 2
        for cycle in range(max_full_cycles):
            start_token = self.token_idx
            tokens_tried = 0
            while tokens_tried < len(self.tokens):
                headers = {
                    "Authorization": f"Bearer {self._current_token}",
                    "Content-Type": "application/json",
                }
                models_tried = 0
                while models_tried < len(self.models):
                    payload["model"] = self._current_model
                    try:
                        resp = requests.post(
                            MODELS_API, headers=headers, json=payload, timeout=120
                        )
                        if resp.status_code == 429:
                            print(f"  [LLM] Rate limited on {self._current_model} (token #{self.token_idx + 1})")
                            self._rotate_model()
                            models_tried += 1
                            time.sleep(2)
                            continue
                        resp.raise_for_status()
                        self._request_counts[self._current_model] += 1
                        data = resp.json()
                        return data["choices"][0]["message"]["content"]
                    except requests.exceptions.HTTPError:
                        if resp.status_code >= 500:
                            print(f"  [LLM] Server error {resp.status_code}, retrying...")
                            time.sleep(3)
                            models_tried += 1
                            continue
                        raise
                if not self._rotate_token():
                    break
                tokens_tried += 1
            if cycle < max_full_cycles - 1:
                wait = 90 * (cycle + 1)
                print(f"  [LLM] All tokens/models rate-limited. Waiting {wait}s before retry (cycle {cycle + 1}/{max_full_cycles})...")
                time.sleep(wait)
        raise RuntimeError("All LLM tokens and models exhausted or rate-limited.")

    @staticmethod
    def extract_code(text: str) -> str:
        match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()


def validate_python_code(code: str, max_lines: int = 200) -> tuple[bool, str]:
    lines = code.splitlines()
    if len(lines) > max_lines:
        return False, f"Code has {len(lines)} lines, exceeds {max_lines}"
    try:
        compile(code, "<generated>", "exec")
    except SyntaxError as exc:
        return False, f"SyntaxError: {exc}"
    return True, code


def gh_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def gh_get(token: str, path: str, params: dict | None = None) -> requests.Response:
    resp = requests.get(
        f"{GITHUB_API}{path}", headers=gh_headers(token), params=params, timeout=30
    )
    return resp


def gh_post(token: str, path: str, payload: dict) -> requests.Response:
    resp = requests.post(
        f"{GITHUB_API}{path}", headers=gh_headers(token), json=payload, timeout=30
    )
    return resp


def get_authenticated_user(token: str) -> str:
    resp = gh_get(token, "/user")
    resp.raise_for_status()
    return resp.json()["login"]


def check_repo_exists(token: str, owner: str, repo: str) -> bool:
    resp = gh_get(token, f"/repos/{owner}/{repo}")
    return resp.status_code == 200


def create_repo(token: str, name: str, description: str) -> dict:
    payload = {
        "name": name,
        "description": description,
        "private": False,
        "auto_init": True,
    }
    resp = gh_post(token, "/user/repos", payload)
    resp.raise_for_status()
    return resp.json()


def commit_files(
    token: str,
    owner: str,
    repo: str,
    branch: str,
    files: dict[str, str],
    message: str,
    parent_sha: str | None = None,
) -> str:
    hdrs = gh_headers(token)
    base = f"{GITHUB_API}/repos/{owner}/{repo}"

    tree_items = []
    for path, content in files.items():
        blob_resp = requests.post(
            f"{base}/git/blobs",
            headers=hdrs,
            json={"content": content, "encoding": "utf-8"},
            timeout=30,
        )
        blob_resp.raise_for_status()
        tree_items.append(
            {
                "path": path,
                "mode": "100644",
                "type": "blob",
                "sha": blob_resp.json()["sha"],
            }
        )

    tree_payload: dict = {"tree": tree_items}
    if parent_sha:
        parent_commit = requests.get(
            f"{base}/git/commits/{parent_sha}", headers=hdrs, timeout=30
        )
        parent_commit.raise_for_status()
        tree_payload["base_tree"] = parent_commit.json()["tree"]["sha"]
    tree_resp = requests.post(
        f"{base}/git/trees", headers=hdrs, json=tree_payload, timeout=30
    )
    tree_resp.raise_for_status()
    tree_sha = tree_resp.json()["sha"]

    commit_payload: dict = {"message": message, "tree": tree_sha}
    if parent_sha:
        commit_payload["parents"] = [parent_sha]
    commit_resp = requests.post(
        f"{base}/git/commits", headers=hdrs, json=commit_payload, timeout=30
    )
    commit_resp.raise_for_status()
    commit_sha = commit_resp.json()["sha"]

    ref_resp = requests.get(
        f"{base}/git/ref/heads/{branch}", headers=hdrs, timeout=30
    )
    if ref_resp.status_code == 200:
        requests.patch(
            f"{base}/git/refs/heads/{branch}",
            headers=hdrs,
            json={"sha": commit_sha},
            timeout=30,
        ).raise_for_status()
    else:
        requests.post(
            f"{base}/git/refs",
            headers=hdrs,
            json={"ref": f"refs/heads/{branch}", "sha": commit_sha},
            timeout=30,
        ).raise_for_status()

    return commit_sha


def get_default_branch_sha(token: str, owner: str, repo: str) -> str:
    resp = gh_get(token, f"/repos/{owner}/{repo}/git/ref/heads/main")
    resp.raise_for_status()
    return resp.json()["object"]["sha"]


def create_branch(token: str, owner: str, repo: str, branch: str, sha: str):
    payload = {"ref": f"refs/heads/{branch}", "sha": sha}
    resp = gh_post(token, f"/repos/{owner}/{repo}/git/refs", payload)
    if resp.status_code == 422:
        resp2 = requests.patch(
            f"{GITHUB_API}/repos/{owner}/{repo}/git/refs/heads/{branch}",
            headers=gh_headers(token),
            json={"sha": sha, "force": True},
            timeout=30,
        )
        resp2.raise_for_status()
        return
    resp.raise_for_status()


def create_pull_request(
    token: str,
    owner: str,
    repo: str,
    title: str,
    body: str,
    head: str,
    base: str = "main",
) -> dict:
    payload = {"title": title, "body": body, "head": head, "base": base}
    resp = gh_post(token, f"/repos/{owner}/{repo}/pulls", payload)
    resp.raise_for_status()
    return resp.json()


def count_all_prs(token: str, owner: str, repo: str) -> int:
    count = 0
    page = 1
    while True:
        resp = gh_get(
            token,
            f"/repos/{owner}/{repo}/pulls",
            params={"state": "all", "per_page": 100, "page": page},
        )
        resp.raise_for_status()
        items = resp.json()
        count += len(items)
        if len(items) < 100:
            break
        page += 1
    return count


def get_file_content(
    token: str, owner: str, repo: str, path: str, ref: str = "main"
) -> str:
    resp = gh_get(
        token, f"/repos/{owner}/{repo}/contents/{path}", params={"ref": ref}
    )
    resp.raise_for_status()
    content_b64 = resp.json()["content"]
    return base64.b64decode(content_b64).decode("utf-8")


def post_pr_review(
    token: str,
    owner: str,
    repo: str,
    pr_number: int,
    comments: list[dict],
):
    payload = {"event": "COMMENT", "comments": comments}
    resp = gh_post(
        token, f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews", payload
    )
    resp.raise_for_status()


def get_repo_file_list(token: str, owner: str, repo: str) -> list[str]:
    resp = gh_get(
        token,
        f"/repos/{owner}/{repo}/git/trees/main",
        params={"recursive": "1"},
    )
    resp.raise_for_status()
    return [
        item["path"]
        for item in resp.json()["tree"]
        if item["type"] == "blob" and item["path"].endswith(".py")
    ]


def build_guidelines_md(
    framework: str, guidelines_dir: str, llm: LLMClient
) -> str:
    json_file = GUIDELINES_MAP.get(framework)
    if json_file:
        json_path = os.path.join(guidelines_dir, json_file)
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as fh:
                chunks = json.load(fh)
            sections: list[str] = []
            seen_titles: set[str] = set()
            for chunk in chunks:
                title = chunk.get("source_title", "General")
                text = chunk.get("text", "")
                if title not in seen_titles:
                    sections.append(f"## {title}\n")
                    seen_titles.add(title)
                sections.append(text + "\n")
            header = f"# {framework.title()} Coding Guidelines\n\n"
            return header + "\n".join(sections)

    # Fallback: LLM-generated
    system = (
        "You are a senior Python developer. Write concise coding guidelines "
        f"for a {framework} project. Cover: PEP 8 style, imports, naming, "
        "docstrings, mutable defaults, indentation rules. Output Markdown."
    )
    user = (
        f"Generate a guidelines.md document for a {framework} Python project. "
        "Include sections for: Code Style, Import Organization, Naming Conventions, "
        "Documentation, Common Pitfalls (mutable defaults). Keep it practical, ~100 lines."
    )
    return llm.generate(system, user, temperature=0.4)


def generate_python_file(
    llm: LLMClient,
    framework: str,
    file_path: str,
    description: str,
) -> str:
    system = (
        f"You are a senior Python developer specializing in {framework}. "
        "Generate clean, idiomatic Python code. Follow PEP 8 strictly: "
        "4-space indentation, snake_case naming, organized imports "
        "(stdlib → third-party → local). Include proper docstrings. "
        "Output ONLY the Python code, no explanations or markdown fences."
    )
    user = (
        f"Generate a Python module at '{file_path}' for a {framework} project.\n"
        f"Purpose: {description}\n"
        "Requirements:\n"
        "- Between 40 and 150 lines (strict maximum 200 lines)\n"
        "- Must be syntactically valid Python\n"
        "- Use realistic variable and function names\n"
        "- Include module-level docstring\n"
        "- Include type hints where appropriate\n"
        "Output ONLY Python code, nothing else."
    )

    raw = llm.generate(system, user)
    code = llm.extract_code(raw)
    ok, result = validate_python_code(code)
    if ok:
        return result

    print(f"    [Validate] Failed for {file_path}: {result}, retrying...")
    retry_user = (
        f"The previous code had an error: {result}\n"
        f"Please fix and regenerate the module for '{file_path}'.\n"
        f"Purpose: {description}\n"
        "Output ONLY valid Python code, max 200 lines."
    )
    raw2 = llm.generate(system, retry_user)
    code2 = llm.extract_code(raw2)
    ok2, result2 = validate_python_code(code2)
    if ok2:
        return result2

    print(f"    [Validate] Retry also failed for {file_path}, using stub")
    return (
        f'"""{file_path} - {description}"""\n\n'
        f"# Auto-generated stub for {framework}\n"
        "# LLM generation failed validation\n"
    )


VIOLATION_PROMPTS = {
    "unused_import": (
        "Add 3 import statements at the top of the file that are never used "
        "anywhere in the code. Use common stdlib modules like os, sys, re, json, "
        "collections, typing, pathlib. The imports should look plausible but "
        "none of them should be referenced in the code body."
    ),
    "indentation": (
        "Introduce 3 indentation violations: change some 4-space indented blocks "
        "to use 2 spaces, 6 spaces, or mix tabs with spaces. Make the indentation "
        "inconsistent across different functions or blocks. The code may have "
        "syntax issues — that is intentional."
    ),
    "naming_convention": (
        "Rename 3 functions or variables to use camelCase instead of snake_case. "
        "For example, change 'get_user_data' to 'getUserData' or 'user_name' to "
        "'userName'. Make the naming inconsistent with PEP 8."
    ),
    "documentation_formatting": (
        "Break 3 docstrings in the file: convert single-line docstrings to badly "
        "formatted multi-line ones (missing blank line after summary, or closing "
        "quotes on wrong line), or remove docstrings entirely from functions that "
        "had them. Make the documentation inconsistent."
    ),
    "mutable_default": (
        "Change 3 function signatures to use mutable default arguments. "
        "Replace 'None' defaults with '[]', '{}', or 'set()'. For example, "
        "change 'def func(items=None):' to 'def func(items=[]):'. If a function "
        "doesn't have such a parameter, add one with a mutable default."
    ),
}


def inject_violations(
    llm: LLMClient,
    original_code: str,
    violation_type: str,
    file_path: str,
) -> tuple[str, list[dict]]:
    instruction = VIOLATION_PROMPTS[violation_type]
    system = (
        "You are modifying Python code to introduce specific coding violations "
        "for testing a code review system. Follow the instructions precisely. "
        "Output format:\n"
        "1. First output the COMPLETE modified Python code\n"
        "2. Then after a line containing only '---VIOLATIONS---', output a JSON "
        "array of violation details, each with 'line' (line number) and "
        "'description' (what was changed).\n"
        "Example:\n"
        "```python\nimport os  # unused\n...\n```\n"
        "---VIOLATIONS---\n"
        '[{"line": 1, "description": "Added unused import os"}]'
    )
    user = (
        f"Original file ({file_path}):\n"
        f"```python\n{original_code}\n```\n\n"
        f"Violation type: {violation_type}\n"
        f"Instructions: {instruction}\n\n"
        "Output the COMPLETE modified code (not a diff), then the violations JSON."
    )

    try:
        raw = llm.generate(system, user, temperature=0.3)
    except RuntimeError:
        print(f"    [Violation] LLM unavailable, using deterministic injection")
        return _fallback_inject(original_code, violation_type)

    parts = raw.split("---VIOLATIONS---")
    code_part = parts[0]
    code = LLMClient.extract_code(code_part)

    violations = []
    if len(parts) > 1:
        try:
            json_match = re.search(r"\[.*\]", parts[1], re.DOTALL)
            if json_match:
                violations = json.loads(json_match.group())
        except (json.JSONDecodeError, AttributeError):
            pass

    # Validate (skip compile for indentation since it's intentionally broken)
    if violation_type != "indentation":
        ok, msg = validate_python_code(code)
        if not ok:
            print(f"    [Violation] Validation failed: {msg}, using simple injection")
            code, violations = _fallback_inject(original_code, violation_type)

    if not violations:
        violations = _guess_violations(original_code, code, violation_type)

    return code, violations


def _fallback_inject(original_code: str, violation_type: str) -> tuple[str, list[dict]]:
    lines = original_code.splitlines()
    violations = []

    if violation_type == "unused_import":
        imports = ["import os", "import sys", "from collections import OrderedDict"]
        for i, imp in enumerate(imports):
            lines.insert(i, imp)
            violations.append({"line": i + 1, "description": f"Added unused: {imp}"})
    elif violation_type == "naming_convention":
        for i, line in enumerate(lines):
            match = re.match(r"^(def )([a-z]+_[a-z]\w*)\(", line)
            if match and len(violations) < 3:
                old_name = match.group(2)
                parts_list = old_name.split("_")
                camel = parts_list[0] + "".join(w.capitalize() for w in parts_list[1:])
                lines[i] = line.replace(old_name, camel, 1)
                violations.append(
                    {"line": i + 1, "description": f"Renamed {old_name} -> {camel}"}
                )
    elif violation_type == "mutable_default":
        for i, line in enumerate(lines):
            if "=None" in line.replace(" ", "") and "def " in line and len(violations) < 3:
                lines[i] = line.replace("=None", "=[]", 1)
                violations.append(
                    {"line": i + 1, "description": "Changed default None to mutable []"}
                )
    elif violation_type == "documentation_formatting":
        in_func = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("def ") or stripped.startswith("class "):
                in_func = True
                continue
            if in_func and '"""' in stripped and stripped.count('"""') == 2 and len(violations) < 3:
                indent = len(line) - len(line.lstrip())
                content = stripped.replace('"""', "").strip()
                lines[i] = " " * indent + '"""' + content
                lines.insert(i + 1, " " * indent + "some extra line")
                lines.insert(i + 2, " " * indent + '"""')
                violations.append(
                    {"line": i + 1, "description": "Broke single-line docstring formatting"}
                )
                in_func = False
            else:
                in_func = False
    elif violation_type == "indentation":
        count = 0
        for i, line in enumerate(lines):
            if line.startswith("    ") and count < 3:
                lines[i] = "  " + line.lstrip()  # 2-space instead of 4
                violations.append(
                    {"line": i + 1, "description": "Changed to 2-space indentation"}
                )
                count += 1

    return "\n".join(lines), violations


def _guess_violations(
    original: str, modified: str, violation_type: str
) -> list[dict]:
    orig_lines = original.splitlines()
    mod_lines = modified.splitlines()
    violations = []
    for i, mod_line in enumerate(mod_lines):
        if i < len(orig_lines):
            if orig_lines[i] != mod_line:
                violations.append(
                    {"line": i + 1, "description": f"{violation_type} violation introduced"}
                )
        else:
            violations.append(
                {"line": i + 1, "description": f"{violation_type} violation (new line)"}
            )
    return violations[:4]


_FALLBACK_COMMENTS = {
    "unused_import": [
        "This import doesn't seem to be used anywhere in this file. Consider removing it to keep the imports clean.",
        "Looks like this import was added but never referenced. Unused imports add clutter — let's remove it.",
        "I don't see this module being used below. Mind cleaning up the unused import?",
    ],
    "indentation": [
        "The indentation here looks inconsistent with the rest of the file. We should stick to 4-space indentation per PEP 8.",
        "This block is using mixed indentation. Let's standardize to 4 spaces throughout.",
        "Indentation mismatch — this line doesn't align with its surrounding block.",
    ],
    "naming_convention": [
        "This name doesn't follow PEP 8 snake_case convention for functions/variables. Consider renaming.",
        "Looks like camelCase was used here instead of snake_case — let's keep naming consistent per PEP 8.",
        "The naming here deviates from the project's snake_case convention.",
    ],
    "documentation_formatting": [
        "The docstring formatting looks off here. Single-line docstrings should stay on one line per PEP 257.",
        "This docstring doesn't follow standard formatting. Consider cleaning up the whitespace and structure.",
        "Docstring style is inconsistent with the rest of the codebase. Let's fix the formatting.",
    ],
    "mutable_default": [
        "Using a mutable default argument (like `[]` or `{}`) is a common Python gotcha. Use `None` and initialize inside the function instead.",
        "Heads up: mutable default arguments are shared across calls. This can cause subtle bugs — default to `None` instead.",
        "This default argument is mutable, which can lead to unexpected behavior between function calls.",
    ],
}


def _fallback_review_comment(desc: str, violation_type: str) -> str:
    pool = _FALLBACK_COMMENTS.get(violation_type, [f"Issue found: {desc}"])
    return random.choice(pool)


def generate_review_comments(
    llm: LLMClient,
    file_path: str,
    violated_code: str,
    violations: list[dict],
    violation_type: str,
) -> list[dict]:
    comments = []
    code_lines = violated_code.splitlines()

    for v in violations[:4]:  # Cap at 4 comments per PR
        line_num = v.get("line", 1)
        desc = v.get("description", violation_type)

        # Get surrounding context
        start = max(0, line_num - 2)
        end = min(len(code_lines), line_num + 2)
        context = "\n".join(
            f"{i+1}: {code_lines[i]}" for i in range(start, end) if i < len(code_lines)
        )

        system = (
            "You are an experienced code reviewer on a Python open-source project. "
            "Write a concise, constructive, human-sounding review comment about a "
            "specific coding issue you found. Be direct but helpful, like a senior "
            "developer would comment on a PR. Do NOT mention 'violation category', "
            "'violation type', or sound automated. Reference the specific code. "
            "Keep it 1-3 sentences. Output ONLY the review comment text."
        )
        user = (
            f"File: {file_path}\n"
            f"Code context around line {line_num}:\n{context}\n\n"
            f"Issue: {desc}\n"
            "Write a single review comment for this line."
        )

        try:
            comment_text = llm.generate(system, user, temperature=0.8, max_tokens=300)
            comment_text = comment_text.strip().strip('"').strip("'")
        except RuntimeError:
            comment_text = _fallback_review_comment(desc, violation_type)
        comments.append(
            {"path": file_path, "line": line_num, "body": comment_text}
        )

    return comments


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def create_repo_with_files(
    token: str,
    owner: str,
    framework: str,
    llm: LLMClient,
    guidelines_dir: str,
):
    """Phase 1: Create repo with 20 clean Python files + guidelines.md."""
    repo_name = f"synthetic-{framework}"

    if check_repo_exists(token, owner, repo_name):
        print(f"[Repo] {owner}/{repo_name} already exists, skipping creation.")
        return repo_name

    print(f"[Repo] Creating {owner}/{repo_name} ...")
    create_repo(
        token,
        repo_name,
        f"Synthetic {framework.title()} repository for code review evaluation",
    )
    # Wait for GitHub to initialize
    time.sleep(3)

    files: dict[str, str] = {}

    files["README.md"] = (
        f"# synthetic-{framework}\n\n"
        f"Synthetic {framework.title()} repository for code review evaluation.\n\n"
        "This repository contains auto-generated Python code following "
        f"{framework.title()} best practices and coding guidelines.\n"
    )

    print(f"  [Guidelines] Building guidelines.md for {framework}...")
    files["guidelines.md"] = build_guidelines_md(framework, guidelines_dir, llm)

    file_list = FILE_LISTS[framework]
    for i, (fpath, desc) in enumerate(file_list, 1):
        print(f"  [Gen] ({i}/{len(file_list)}) {fpath}")
        code = generate_python_file(llm, framework, fpath, desc)
        files[fpath] = code
        time.sleep(1)

    print(f"  [Commit] Pushing {len(files)} files to main ...")
    parent_sha = get_default_branch_sha(token, owner, repo_name)
    commit_files(
        token, owner, repo_name, "main", files,
        "Add project files",
        parent_sha=parent_sha,
    )
    print(f"  [Done] {owner}/{repo_name} created with {len(files)} files.")
    return repo_name


def create_prs_with_violations(
    token: str,
    owner: str,
    repo_name: str,
    framework: str,
    llm: LLMClient,
    target_prs: int,
):
    existing_prs = count_all_prs(token, owner, repo_name)
    remaining = target_prs - existing_prs

    if remaining <= 0:
        print(
            f"[PR] {owner}/{repo_name} already has {existing_prs} PRs "
            f"(target: {target_prs}), skipping."
        )
        return

    print(
        f"[PR] {owner}/{repo_name}: {existing_prs} existing, "
        f"creating {remaining} more to reach {target_prs}."
    )

    py_files = get_repo_file_list(token, owner, repo_name)
    if not py_files:
        print("  [PR] No Python files in repo, skipping PR creation.")
        return

    main_sha = get_default_branch_sha(token, owner, repo_name)

    for i in range(existing_prs, target_prs):
        violation_type = VIOLATION_CATEGORIES[i % len(VIOLATION_CATEGORIES)]
        target_file = random.choice(py_files)
        pr_num = i + 1
        branch_name = f"violation/{violation_type.replace('_', '-')}-{pr_num}"

        print(
            f"  [PR {pr_num}/{target_prs}] {violation_type} in {target_file} "
            f"-> branch: {branch_name}"
        )

        try:
            clean_code = get_file_content(token, owner, repo_name, target_file)

            violated_code, violations = inject_violations(
                llm, clean_code, violation_type, target_file
            )

            create_branch(token, owner, repo_name, branch_name, main_sha)

            commit_files(
                token,
                owner,
                repo_name,
                branch_name,
                {target_file: violated_code},
                f"Introduce {violation_type.replace('_', ' ')} in {target_file}",
                parent_sha=main_sha,
            )

            pr_title = (
                f"Update {os.path.basename(target_file)}: "
                f"{violation_type.replace('_', ' ')} changes"
            )
            pr_body = (
                f"This PR modifies `{target_file}` with code style changes.\n\n"
                "Please review for any coding standard issues."
            )
            pr_data = create_pull_request(
                token, owner, repo_name, pr_title, pr_body, branch_name
            )
            pr_number = pr_data["number"]
            print(f"    Created PR #{pr_number}")

            review_comments = generate_review_comments(
                llm, target_file, violated_code, violations, violation_type
            )
            if review_comments:
                try:
                    post_pr_review(
                        token, owner, repo_name, pr_number, review_comments
                    )
                    print(
                        f"    Posted {len(review_comments)} review comments on PR #{pr_number}"
                    )
                except requests.exceptions.HTTPError as exc:
                    print(f"    [Warn] Failed to post review: {exc}")
                    _post_fallback_review(
                        token, owner, repo_name, pr_number, review_comments
                    )

        except Exception as exc:
            print(f"    [Error] PR {pr_num} failed: {exc}")
            continue

        time.sleep(2)


def _post_fallback_review(
    token: str,
    owner: str,
    repo: str,
    pr_number: int,
    comments: list[dict],
):
    body_parts = ["**Code Review Comments:**\n"]
    for c in comments:
        body_parts.append(f"- **{c['path']}** (line {c['line']}): {c['body']}")
    body = "\n".join(body_parts)
    resp = requests.post(
        f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments",
        headers=gh_headers(token),
        json={"body": body},
        timeout=30,
    )
    if resp.ok:
        print(f"    Posted fallback review comment on PR #{pr_number}")


def main():
    parser = argparse.ArgumentParser(description="Create synthetic repos with violations and review comments.")
    parser.add_argument("--repo-token", default=None)
    parser.add_argument("--llm-token", default=None)
    parser.add_argument("--repos", nargs="+", default=FRAMEWORKS, choices=FRAMEWORKS)
    parser.add_argument("--num-prs", type=int, default=20)
    parser.add_argument("--guidelines-dir", default="data/raw/guidelines_raw")
    args = parser.parse_args()

    repo_token = args.repo_token or os.environ.get("GITHUB_REPO")
    if not repo_token:
        print("[Error] No repo token. Pass --repo-token or set GITHUB_REPO in .env")
        sys.exit(1)

    raw_llm = args.llm_token or os.environ.get("GITHUB_LLM_TOKEN", "")
    raw_llm = raw_llm.strip().strip("[]")
    llm_tokens = [t.strip() for t in raw_llm.split(",") if t.strip()]
    if not llm_tokens:
        print("[Error] No LLM tokens. Pass --llm-token or set GITHUB_LLM_TOKEN in .env")
        sys.exit(1)

    print("[Auth] Verifying repo token ...")
    owner = get_authenticated_user(repo_token)
    print(f"[Auth] Authenticated as: {owner}")

    llm = LLMClient(llm_tokens)
    print(f"[Auth] LLM client initialized with {len(llm_tokens)} token(s).")

    for framework in args.repos:
        print(f"\n{'='*60}")
        print(f"Processing: {framework}")
        print(f"{'='*60}")

        repo_name = create_repo_with_files(
            repo_token, owner, framework, llm, args.guidelines_dir
        )

        create_prs_with_violations(
            repo_token, owner, repo_name, framework, llm, args.num_prs
        )

    print(f"\n{'='*60}")
    print("All done!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
