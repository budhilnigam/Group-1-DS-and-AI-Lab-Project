import json
import os
import random
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "dataset_v1"
EMBED_DIR = ROOT / "data" / "processed" / "embedding"
PROCESSED_DIR = ROOT / "data" / "processed" / "milestone3"

EVAL_PATH = RAW_DIR / "evaluation_dataset.json"
CORPUS_PATH = RAW_DIR / "retrieval_corpus.json"
INDEX_PATH = EMBED_DIR / "faiss_index_ip.bin"
META_PATH = EMBED_DIR / "faiss_metadata.json"

OUT_PREDICTIONS = PROCESSED_DIR / "smoke_test_predictions.json"
OUT_METRICS = PROCESSED_DIR / "smoke_test_metrics.json"
OUT_SAMPLES = PROCESSED_DIR / "smoke_test_examples.json"

TOP_K = int(os.getenv("SMOKE_TOP_K", "5"))
SUBSET_SIZE = int(os.getenv("SMOKE_SUBSET_SIZE", "60"))
SEED = int(os.getenv("SMOKE_SEED", "42"))

# auto|faiss|lexical
RETRIEVAL_BACKEND = os.getenv("SMOKE_RETRIEVAL_BACKEND", "auto").lower()
# template|groq
GENERATION_BACKEND = os.getenv("SMOKE_GENERATION_BACKEND", "template").lower()

# Groq settings: keep default RPM at 30 to avoid 429 during tests.
GROQ_MODEL = os.getenv("SMOKE_GROQ_MODEL", "openai/gpt-oss-20b")
GROQ_RPM_LIMIT = int(os.getenv("SMOKE_GROQ_RPM_LIMIT", "30"))
GROQ_MAX_RETRIES = int(os.getenv("SMOKE_GROQ_MAX_RETRIES", "3"))
SMOKE_NUM_LLM_SAMPLES = int(os.getenv("SMOKE_NUM_LLM_SAMPLES", "0"))

CATEGORY_NAMES = [
    "indentation",
    "naming_convention",
    "unused_import",
    "mutable_default",
    "documentation_formatting",
]

STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "for",
    "in",
    "is",
    "on",
    "with",
    "this",
    "that",
    "it",
    "as",
    "be",
    "by",
    "are",
    "from",
    "at",
    "if",
    "not",
    "use",
    "using",
    "line",
    "lines",
}

CATEGORY_HINTS = {
    "indentation": ["indent", "spaces", "tabs", "whitespace", "align", "wrapped", "line-length"],
    "naming_convention": ["snake_case", "camelcase", "pascalcase", "naming", "rename", "variable-name", "class-name"],
    "unused_import": ["import", "unused", "remove-import", "redundant-import", "f401"],
    "mutable_default": ["default", "mutable", "list", "dict", "set", "none", "sentinel", "w0102", "b006"],
    "documentation_formatting": ["docstring", "documentation", "comment", "pep257", "format", "triple-quotes"],
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def tokenize(text: str):
    tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_\-]*", text.lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


def normalize_diff_line(line: str):
    if not line:
        return ""
    if line[0] in "+- ":
        return line[1:]
    return line


def extract_chunk_text(entry: dict, target_line: int):
    selected = None
    for chunk in entry.get("diff_chunks", []):
        start = int(chunk.get("start_line", 0))
        end = int(chunk.get("end_line", 0))
        if start <= target_line <= end:
            selected = chunk
            break

    if selected is None and entry.get("diff_chunks"):
        selected = entry["diff_chunks"][0]

    if selected is None:
        return ""

    lines = [normalize_diff_line(l) for l in selected.get("diff_lines", [])]
    return "\n".join(lines)


def add_hint_tokens(tokens):
    expanded = set(tokens)
    token_set = set(tokens)
    for category, hints in CATEGORY_HINTS.items():
        for hint in hints:
            if hint in token_set:
                expanded.add(category)
    return expanded


def score_overlap(query_tokens, doc_tokens):
    if not query_tokens or not doc_tokens:
        return 0.0
    inter = len(query_tokens & doc_tokens)
    if inter == 0:
        return 0.0
    return inter / (len(query_tokens) ** 0.5 * len(doc_tokens) ** 0.5)


def build_lexical_corpus(corpus):
    indexed = []
    for c in corpus:
        text = c.get("text", "")
        tokens = add_hint_tokens(set(tokenize(text)))
        indexed.append(
            {
                "chunk_id": c.get("chunk_id"),
                "category": c.get("category"),
                "source_type": c.get("source_type"),
                "text": text,
                "tokens": tokens,
            }
        )
    return indexed


def retrieve_top_k_lexical(query_text, indexed_corpus, top_k=TOP_K):
    query_tokens = add_hint_tokens(set(tokenize(query_text)))
    scored = []
    for item in indexed_corpus:
        s = score_overlap(query_tokens, item["tokens"])
        if s > 0:
            scored.append((s, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]
    return [
        {
            "chunk_id": x[1]["chunk_id"],
            "category": x[1]["category"],
            "source_type": x[1]["source_type"],
            "text": x[1]["text"],
            "score": round(float(x[0]), 4),
        }
        for x in top
    ]


def try_load_faiss_backend():
    if not INDEX_PATH.exists() or not META_PATH.exists():
        return None

    try:
        import faiss
        from sentence_transformers import SentenceTransformer
    except Exception:
        return None

    try:
        metadata = load_json(META_PATH)
        index = faiss.read_index(str(INDEX_PATH))
        model = SentenceTransformer("BAAI/bge-large-en-v1.5")
        return {
            "index": index,
            "metadata": metadata,
            "model": model,
        }
    except Exception:
        return None


def retrieve_top_k_faiss(query_text, faiss_backend, top_k=TOP_K):
    import numpy as np

    model = faiss_backend["model"]
    index = faiss_backend["index"]
    metadata = faiss_backend["metadata"]

    q_emb = model.encode([query_text], normalize_embeddings=True, convert_to_numpy=True).astype(np.float32)
    scores, idxs = index.search(q_emb, top_k)

    hits = []
    for score, idx in zip(scores[0], idxs[0]):
        if idx < 0 or idx >= len(metadata):
            continue
        doc = metadata[idx]
        hits.append(
            {
                "chunk_id": doc.get("chunk_id"),
                "category": doc.get("category"),
                "source_type": doc.get("source_type"),
                "text": doc.get("text", ""),
                "score": round(float(score), 4),
            }
        )
    return hits


def predict_category(retrieved):
    if not retrieved:
        return "documentation_formatting"
    votes = Counter(x["category"] for x in retrieved if x.get("category") in CATEGORY_NAMES)
    if not votes:
        return "documentation_formatting"
    return votes.most_common(1)[0][0]


def build_template_comment(pred_category, retrieved):
    if retrieved:
        evidence = retrieved[0]["text"].strip().replace("\n", " ")[:180]
        source = retrieved[0]["source_type"]
    else:
        evidence = "No direct guideline chunk retrieved."
        source = "none"

    return (
        f"Potential {pred_category.replace('_', ' ')} issue detected. "
        f"Suggested review: align this change with project style guidance and update the code accordingly. "
        f"Evidence source ({source}): {evidence}"
    )


def build_prompt(instance: dict, retrieved: list[dict], predicted_category: str) -> str:
    evidence_lines = []
    for i, hit in enumerate(retrieved, start=1):
        snippet = re.sub(r"\s+", " ", hit.get("text", ""))[:300]
        evidence_lines.append(
            f"[{i}] chunk_id={hit.get('chunk_id')} | category={hit.get('category')} | source={hit.get('source_type')} | score={hit.get('score', 0):.4f}\n{snippet}"
        )

    evidence_block = "\n\n".join(evidence_lines) if evidence_lines else "No evidence retrieved."

    return f"""You are a Python code-review assistant in a RAG system.

Task:
- Review ONLY the provided diff context and retrieved evidence.
- Focus ONLY on these categories: {', '.join(CATEGORY_NAMES)}.
- Do NOT comment on functionality correctness, security, architecture, or testing strategy.
- If evidence is weak, state uncertainty explicitly in grounded_comment.
- Use predicted_category_hint only as a weak prior, not as a hard constraint.

Context:
- repo: {instance.get('repo')}
- pr_id: {instance.get('pr_id')}
- file_path: {instance.get('file_path')}
- line_number: {instance.get('line_number')}
- predicted_category_hint: {predicted_category}

Diff chunk:
{instance.get('query_text', '')[:2500]}

Retrieved evidence (top-k):
{evidence_block}

Output requirements:
- Return EXACTLY one JSON object only.
- Do not include markdown fences, prose, or extra keys.
- category must be one of: {CATEGORY_NAMES}
- cited_chunk_ids must be a JSON array of chunk IDs (or empty array)

Expected JSON schema:
{{
  "category": "<one allowed category>",
  "grounded_comment": "<single actionable sentence grounded in evidence>",
  "cited_chunk_ids": ["chunk_0001", "chunk_0042"]
}}
"""


def parse_llm_output(response: str) -> dict:
    result = {
        "category": "documentation_formatting",
        "grounded_comment": "Unable to parse response; review required.",
        "cited_chunk_ids": [],
        "is_valid": False,
        "parse_status": "unparsed",
    }

    if not response or not response.strip():
        result["parse_status"] = "empty_response"
        return result

    cleaned = response.strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    try:
        payload = json.loads(cleaned)

        # Handle nested JSON string/list outputs from model generations.
        if isinstance(payload, str):
            payload = json.loads(payload)
        if isinstance(payload, list):
            payload = payload[0] if payload else {}

        if isinstance(payload, dict):
            cat = str(payload.get("category", "")).strip()
            comment = str(payload.get("grounded_comment", "")).strip()
            ids = payload.get("cited_chunk_ids", [])

            if isinstance(ids, str):
                ids = [x.strip() for x in ids.split(",") if x.strip()]
            elif not isinstance(ids, list):
                ids = []

            ids = [str(x).strip() for x in ids if str(x).strip()]

            if cat in CATEGORY_NAMES and comment:
                result.update(
                    {
                        "category": cat,
                        "grounded_comment": comment,
                        "cited_chunk_ids": ids,
                        "is_valid": True,
                        "parse_status": "json_ok",
                    }
                )
                return result

            result["parse_status"] = "json_missing_fields"
            return result

        result["parse_status"] = "json_not_object"
        return result
    except Exception:
        result["parse_status"] = "json_parse_failed"
        return result


class GroqRateLimiter:
    def __init__(self, rpm_limit: int):
        self.min_interval = 60.0 / max(1, rpm_limit)
        self.last_request_ts = 0.0

    def wait(self):
        now = time.time()
        elapsed = now - self.last_request_ts
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_ts = time.time()


def call_groq_api(client, limiter, prompt: str, max_tokens: int = 512, temperature: float = 0.1):
    last_error = None

    for attempt in range(1, GROQ_MAX_RETRIES + 2):
        try:
            limiter.wait()
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "Return exactly one JSON object and nothing else."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )

            if not response.choices:
                if attempt <= GROQ_MAX_RETRIES:
                    continue
                return ""

            msg = response.choices[0].message
            return msg.content if msg and msg.content else ""
        except Exception as e:
            last_error = e
            err_text = str(e)
            if "429" in err_text:
                # Conservative wait on rate limit errors.
                backoff = min(30.0, (2 ** attempt) * limiter.min_interval)
                time.sleep(backoff)
            elif attempt <= GROQ_MAX_RETRIES:
                time.sleep(1.0)

    if last_error is not None:
        print(f"LLM call failed after retries: {type(last_error).__name__}: {last_error}")
    return ""


def build_instances(eval_dataset):
    instances = []
    for entry in eval_dataset:
        for review in entry.get("ground_truth_reviews", []):
            target_line = int(review.get("line_number", 0))
            chunk_text = extract_chunk_text(entry, target_line)
            query_text = f"{entry.get('file_path', '')}\n{chunk_text}"
            instances.append(
                {
                    "pr_id": entry.get("pr_id"),
                    "repo": entry.get("repo"),
                    "file_path": entry.get("file_path"),
                    "line_number": target_line,
                    "query_text": query_text,
                    "gold_category": review.get("violation_category"),
                    "gold_comment": review.get("review_comment", ""),
                }
            )
    return instances


def stratified_subset(instances, n=SUBSET_SIZE, seed=SEED):
    random.seed(seed)
    grouped = defaultdict(list)
    for ins in instances:
        grouped[ins["gold_category"]].append(ins)

    per_cat = max(1, n // max(1, len(grouped)))
    subset = []

    for cat in CATEGORY_NAMES:
        pool = grouped.get(cat, [])
        random.shuffle(pool)
        subset.extend(pool[:per_cat])

    remaining = [x for x in instances if x not in subset]
    random.shuffle(remaining)
    subset.extend(remaining[: max(0, n - len(subset))])
    random.shuffle(subset)
    return subset[:n]


def split_train_val_test(subset):
    n = len(subset)
    n_train = int(0.6 * n)
    n_val = int(0.2 * n)
    train = subset[:n_train]
    val = subset[n_train : n_train + n_val]
    test = subset[n_train + n_val :]
    return train, val, test


def compute_metrics(gold, pred):
    labels = sorted(set(gold) | set(pred))

    tp = Counter()
    fp = Counter()
    fn = Counter()

    for g, p in zip(gold, pred):
        if g == p:
            tp[g] += 1
        else:
            fp[p] += 1
            fn[g] += 1

    per_class = {}
    for c in labels:
        p = tp[c] / (tp[c] + fp[c]) if (tp[c] + fp[c]) else 0.0
        r = tp[c] / (tp[c] + fn[c]) if (tp[c] + fn[c]) else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) else 0.0
        per_class[c] = {
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f1, 4),
            "support": int(sum(1 for x in gold if x == c)),
        }

    accuracy = sum(1 for g, p in zip(gold, pred) if g == p) / len(gold) if gold else 0.0
    macro_f1 = sum(v["f1"] for v in per_class.values()) / len(per_class) if per_class else 0.0

    return {
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "num_samples": len(gold),
        "per_class": per_class,
    }


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    eval_dataset = load_json(EVAL_PATH)
    corpus = load_json(CORPUS_PATH)

    lexical_corpus = build_lexical_corpus(corpus)
    faiss_backend = try_load_faiss_backend()

    if RETRIEVAL_BACKEND == "faiss":
        retrieval_backend = "faiss" if faiss_backend else "lexical"
    elif RETRIEVAL_BACKEND == "lexical":
        retrieval_backend = "lexical"
    else:
        retrieval_backend = "faiss" if faiss_backend else "lexical"

    groq_enabled = False
    groq_client = None
    groq_limiter = None
    llm_budget = SMOKE_NUM_LLM_SAMPLES

    if GENERATION_BACKEND == "groq":
        try:
            from groq import Groq

            api_key = os.getenv("GROQ_API_KEY", "").strip()
            if api_key:
                groq_client = Groq(api_key=api_key)
                groq_limiter = GroqRateLimiter(GROQ_RPM_LIMIT)
                groq_enabled = True
            else:
                print("GROQ_API_KEY not found. Falling back to template generation.")
        except Exception:
            print("groq client is unavailable. Falling back to template generation.")

    instances = build_instances(eval_dataset)
    subset = stratified_subset(instances, n=SUBSET_SIZE)
    train, val, test = split_train_val_test(subset)

    predictions = []
    parse_status_counter = Counter()

    for idx, ins in enumerate(test, start=1):
        if retrieval_backend == "faiss":
            retrieved = retrieve_top_k_faiss(ins["query_text"], faiss_backend, top_k=TOP_K)
        else:
            retrieved = retrieve_top_k_lexical(ins["query_text"], lexical_corpus, top_k=TOP_K)

        pred_cat = predict_category(retrieved)

        generated_comment = build_template_comment(pred_cat, retrieved)
        generation_backend = "template"
        parse_status = "not_applicable"
        cited_chunks = []
        llm_parse_valid = False

        should_call_llm = groq_enabled and (llm_budget <= 0 or idx <= llm_budget)
        if should_call_llm:
            prompt = build_prompt(ins, retrieved, pred_cat)
            raw = call_groq_api(groq_client, groq_limiter, prompt)
            parsed = parse_llm_output(raw)
            generated_comment = parsed["grounded_comment"]
            pred_cat = parsed["category"]
            cited_chunks = parsed["cited_chunk_ids"]
            parse_status = parsed["parse_status"]
            llm_parse_valid = parsed["is_valid"]
            generation_backend = "groq_llm"
            parse_status_counter[parse_status] += 1

        predictions.append(
            {
                "pr_id": ins["pr_id"],
                "repo": ins["repo"],
                "file_path": ins["file_path"],
                "line_number": ins["line_number"],
                "gold_category": ins["gold_category"],
                "predicted_category": pred_cat,
                "generated_comment": generated_comment,
                "retrieval_backend": retrieval_backend,
                "generation_backend": generation_backend,
                "llm_parse_valid": llm_parse_valid,
                "llm_parse_status": parse_status,
                "cited_chunk_ids": cited_chunks,
                "retrieved_chunks": [
                    {
                        "chunk_id": x["chunk_id"],
                        "category": x["category"],
                        "source_type": x["source_type"],
                        "score": x["score"],
                    }
                    for x in retrieved
                ],
            }
        )

    gold = [p["gold_category"] for p in predictions]
    pred = [p["predicted_category"] for p in predictions]
    metrics = compute_metrics(gold, pred)

    split_meta = {
        "subset_size": len(subset),
        "train_size": len(train),
        "val_size": len(val),
        "test_size": len(test),
        "seed": SEED,
        "top_k": TOP_K,
        "note": "Milestone 3 smoke test split used for end-to-end verification",
    }

    capability_meta = {
        "implemented": {
            "preprocessing": True,
            "query_construction": True,
            "retrieval": retrieval_backend,
            "category_prediction": True,
            "comment_generation": "template_and_optional_llm",
        },
        "optional_in_this_run": {
            "llm_provider": "groq" if groq_enabled else "not_enabled",
            "llm_samples_requested": llm_budget,
            "groq_model": GROQ_MODEL if groq_enabled else None,
            "groq_rpm_limit": GROQ_RPM_LIMIT if groq_enabled else None,
        },
        "planned_or_external": {
            "static_analysis_baseline": "outside this smoke pipeline script",
        },
    }

    payload = {
        "split": split_meta,
        "metrics": metrics,
        "pipeline_capabilities": capability_meta,
        "llm_parse_status_counts": dict(parse_status_counter),
    }

    with OUT_PREDICTIONS.open("w", encoding="utf-8") as f:
        json.dump(predictions, f, indent=2)

    with OUT_METRICS.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    with OUT_SAMPLES.open("w", encoding="utf-8") as f:
        json.dump(predictions[:5], f, indent=2)

    print("Smoke test pipeline completed.")
    print(f"Train/Val/Test: {len(train)}/{len(val)}/{len(test)}")
    print(f"Retrieval backend used: {retrieval_backend}")
    print(f"Groq enabled: {groq_enabled}")
    print(f"Accuracy: {metrics['accuracy']}")
    print(f"Macro F1: {metrics['macro_f1']}")
    print(f"Saved: {OUT_PREDICTIONS}")
    print(f"Saved: {OUT_METRICS}")
    print(f"Saved: {OUT_SAMPLES}")


if __name__ == "__main__":
    main()
