"""Run LLM inference across local (Ollama) and API (Groq) models with caching."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

LOCAL_MODELS: list[str] = [
    "qwen2.5-coder:14b",
    "llama3.1:8b",
    "deepseek-coder:6.7b",
    "mistral:7b-instruct",
    "codellama:7b-instruct",
    "phi4:14b",
    "gemma4:latest",
]

API_MODELS: list[str] = []  # Groq-hosted models, e.g. ["openai/gpt-oss-20b"]

GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
GITHUB_LLM_TOKEN: str = os.environ.get("GITHUB_LLM_TOKEN", "")

TEMPERATURES: list[float] = [0.0]
MAX_TOKENS: int = 1024
MAX_RETRIES: int = 4

OLLAMA_URL: str = "http://localhost:11434/api/chat"
GROQ_URL: str = "https://api.groq.com/openai/v1/chat/completions"

CACHE_DIR: Path = ROOT / "data" / "llm_cache"



def _cache_key(prompt: str, code: str, model: str, temperature: float) -> str:
    raw = f"{prompt}\n---\n{code}\n---\n{model}\n---\n{temperature}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def load_cache(key: str) -> dict | None:
    p = _cache_path(key)
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_cache(key: str, entry: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(_cache_path(key), "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=2, ensure_ascii=False)


def _is_valid_json_response(text: str) -> bool:
    text = text.strip()
    if not text:
        return False
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False



def infer_ollama(
    messages: list[dict], model: str, temperature: float, max_tokens: int
) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=300)
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def infer_groq(
    messages: list[dict], model: str, temperature: float, max_tokens: int
) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set – cannot call Groq API.")
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]



def run_inference(prompt: str, code: str) -> list[dict]:
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": code},
    ]

    all_models: list[tuple[str, str]] = []  # (model, backend)
    for m in LOCAL_MODELS:
        all_models.append((m, "ollama"))
    for m in API_MODELS:
        all_models.append((m, "groq"))

    if not all_models:
        print("No models configured. Add entries to LOCAL_MODELS or API_MODELS.")
        return []

    results: list[dict] = []

    for model, backend in all_models:
        for temp in TEMPERATURES:
            key = _cache_key(prompt, code, model, temp)
            cached = load_cache(key)
            if cached is not None:
                cached["cached"] = True
                results.append(cached)
                _print_row(cached)
                continue

            infer_fn = infer_ollama if backend == "ollama" else infer_groq
            response: str = ""
            latency_ms: float = 0.0
            success = False

            for attempt in range(1, MAX_RETRIES + 1):
                t0 = time.perf_counter()
                try:
                    response = infer_fn(messages, model, temp, MAX_TOKENS)
                    latency_ms = (time.perf_counter() - t0) * 1000
                except Exception as exc:
                    latency_ms = (time.perf_counter() - t0) * 1000
                    print(
                        f"  [{model} T={temp}] attempt {attempt}/{MAX_RETRIES} "
                        f"error: {exc}"
                    )
                    if attempt < MAX_RETRIES:
                        time.sleep(2)
                    continue

                if _is_valid_json_response(response):
                    success = True
                    break

                print(
                    f"  [{model} T={temp}] attempt {attempt}/{MAX_RETRIES} "
                    f"invalid/empty JSON – retrying"
                )
                if attempt < MAX_RETRIES:
                    time.sleep(1)

            entry = {
                "prompt": prompt,
                "code": code,
                "model": model,
                "temperature": temp,
                "response": response,
                "latency_ms": round(latency_ms, 1),
                "cached": False,
            }
            if not success:
                entry["error"] = "invalid_json_after_retries"

            save_cache(key, entry)
            results.append(entry)
            _print_row(entry)

    return results


def infer_one(
    full_prompt: str,
    model: str,
    temperature: float = 0.0,
    max_tokens: int = MAX_TOKENS,
    *,
    prompt_configuration: str = "",
    baseline: str = "LLM",
    parsed_response: object = None,
    retrieval_chunks: dict | None = None,
    topk_retrieval: int | None = None,
    hints: str = "",
    raw_retrieval_query: str = "",
) -> dict:
    """Run inference for a single (prompt, model) pair with caching.

    The full_prompt is a self-contained prompt (role + code + hints etc.).

    Optional keyword arguments are stored alongside the response for
    downstream analysis but do NOT affect the cache key (so the same
    prompt+model pair is never re-inferred just because metadata changed).
    """
    backend = "groq" if model in API_MODELS else "ollama"
    key = _cache_key(full_prompt, "", model, temperature)
    cached = load_cache(key)
    if cached is not None:
        cached["cached"] = True
        # patch in metadata that may have been missing in the original cache
        cached.setdefault("prompt_configuration", prompt_configuration)
        cached.setdefault("baseline", baseline)
        cached.setdefault("parsed_response", parsed_response)
        cached.setdefault("retrieval_chunks", retrieval_chunks)
        cached.setdefault("topk_retrieval", topk_retrieval)
        cached.setdefault("hints", hints)
        cached.setdefault("raw_retrieval_query", raw_retrieval_query)
        return cached

    messages = [{"role": "user", "content": full_prompt}]
    infer_fn = infer_ollama if backend == "ollama" else infer_groq
    response: str = ""
    latency_ms: float = 0.0
    success = False

    for attempt in range(1, MAX_RETRIES + 1):
        t0 = time.perf_counter()
        try:
            response = infer_fn(messages, model, temperature, max_tokens)
            latency_ms = (time.perf_counter() - t0) * 1000
        except Exception as exc:
            latency_ms = (time.perf_counter() - t0) * 1000
            if attempt < MAX_RETRIES:
                time.sleep(2)
                continue
            response = f"ERROR: {exc}"
            break

        if _is_valid_json_response(response):
            success = True
            break

        if attempt < MAX_RETRIES:
            time.sleep(1)

    entry = {
        "prompt_configuration": prompt_configuration,
        "baseline": baseline,
        "prompt": full_prompt,
        "model": model,
        "temperature": temperature,
        "response": response,
        "parsed_response": parsed_response,
        "latency_ms": round(latency_ms, 1),
        "cached": False,
        "retrieval_chunks": retrieval_chunks,
        "topk_retrieval": topk_retrieval,
        "hints": hints,
        "raw_retrieval_query": raw_retrieval_query,
    }
    if not success:
        entry["error"] = "invalid_json_after_retries"

    save_cache(key, entry)
    return entry




_HEADER_PRINTED = False


def _print_row(entry: dict) -> None:
    global _HEADER_PRINTED
    if not _HEADER_PRINTED:
        print(
            f"{'Model':<30} {'Temp':>5} {'Latency':>10} {'Cached':>7} "
            f"{'Status':>8}  Response preview"
        )
        print("-" * 110)
        _HEADER_PRINTED = True

    preview = (entry.get("response") or "")[:80].replace("\n", " ")
    status = "OK" if "error" not in entry else entry["error"][:16]
    cached = "yes" if entry.get("cached") else "no"
    print(
        f"{entry['model']:<30} {entry['temperature']:>5.1f} "
        f"{entry['latency_ms']:>8.0f}ms {cached:>7} {status:>8}  {preview}"
    )



def main() -> None:
    parser = argparse.ArgumentParser(description="Run LLM inference with caching")
    g1 = parser.add_mutually_exclusive_group(required=True)
    g1.add_argument("--prompt", help="Prompt text (system message)")
    g1.add_argument("--prompt-file", help="Path to file containing prompt")

    g2 = parser.add_mutually_exclusive_group(required=True)
    g2.add_argument("--code", help="Code text (user message)")
    g2.add_argument("--code-file", help="Path to file containing code")

    args = parser.parse_args()

    prompt = args.prompt or Path(args.prompt_file).read_text(encoding="utf-8")
    code = args.code or Path(args.code_file).read_text(encoding="utf-8")

    results = run_inference(prompt, code)
    print(f"\nTotal results: {len(results)}")


if __name__ == "__main__":
    main()
