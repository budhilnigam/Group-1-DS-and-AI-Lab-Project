"""Build (or incrementally update) a FAISS vector index from the retrieval corpus."""

from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
CORPUS_PATH = ROOT / "data" / "processed" / "retrival_corpus.json"
INDEX_PATH = ROOT / "data" / "processed" / "faiss_index.bin"
META_PATH = ROOT / "data" / "processed" / "faiss_metadata.json"

EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"
BATCH_SIZE = 32


def load_corpus() -> list[dict]:
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_existing() -> tuple[faiss.Index | None, list[dict]]:
    if INDEX_PATH.exists() and META_PATH.exists():
        index = faiss.read_index(str(INDEX_PATH))
        with open(META_PATH, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        return index, metadata
    return None, []


def save(index: faiss.Index, metadata: list[dict]) -> None:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH))
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def main() -> None:
    # 1. Load corpus and existing state
    corpus = load_corpus()
    index, metadata = load_existing()
    existing_ids: set[str] = {m["chunk_id"] for m in metadata}

    print(f"Corpus chunks : {len(corpus)}")
    print(f"Already indexed: {len(existing_ids)}")

    # 2. Find new chunks
    new_entries = [e for e in corpus if e["chunk_id"] not in existing_ids]

    if not new_entries:
        print("No new chunks to embed. Index is up-to-date.")
        return

    print(f"New chunks     : {len(new_entries)}")

    # 3. Embed new chunks
    model = SentenceTransformer(EMBEDDING_MODEL)
    texts = [e["text"] for e in new_entries]

    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype(np.float32)

    # 4. Create or update FAISS index
    dim = embeddings.shape[1]
    if index is None:
        index = faiss.IndexFlatIP(dim)

    index.add(embeddings)

    # 5. Append new metadata
    for entry in new_entries:
        metadata.append(
            {
                "chunk_id": entry["chunk_id"],
                "category": entry["category"],
                "source_type": entry["source_type"],
                "source_path": entry["source_path"],
                "text": entry["text"],
            }
        )

    # 6. Save
    save(index, metadata)

    print(f"\nEmbedded {len(new_entries)} new chunks.")
    print(f"Total vectors  : {index.ntotal}")
    print(f"Index saved    : {INDEX_PATH}")
    print(f"Metadata saved : {META_PATH}")


if __name__ == "__main__":
    main()
