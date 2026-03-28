# Guideline Chunking Report

Date: 2026-03-28

## Summary

- Input folder: `data/raw/guidelines_raw`
- Output folder: `data/processed/guideline_chunks`
- Embedding model (recorded in each chunk): `BAAI/bge-large-en-v1.5`
- Per-repo chunk counts (generated):
  - `pandas`: 31 chunks
  - `scikit-learn`: 10 chunks
  - `fastapi`: 18 chunks
  - `django`: 16 chunks

## Key parameters

- Document-first max words per chunk: **180 words**
- Overlap when splitting/merging segments: **40 words**

Reasoning (short): these values prioritize preserving semantic units (full guideline blocks, lists, code examples) while keeping chunks small enough for reliable embeddings and retrieval. A 180-word cap balances context with embedding cost; a 40-word overlap preserves continuity across split boundaries.

## Step-by-step process

1. Discover all raw guideline files matching `*_guidelines_raw.md` under `data/raw/guidelines_raw`.
2. For each file, parse strict blocks delimited by `BEGIN_GUIDELINE_BLOCK` / `END_GUIDELINE_BLOCK`.
   - Extract metadata fields present between the block start and `BEGIN_TEXT` (e.g., `source_id`, `source_url`, `source_title`, `section_hint`).
   - Extract the block text between `BEGIN_TEXT` and `END_TEXT` and HTML-unescape it.
3. Document-first chunking rule:
   - If a block's text is <= 180 words, emit it as a single chunk (preserving metadata).
   - If > 180 words, segment the block into coherent segments:
     - Preserve fenced code blocks as-is.
     - Group contiguous list items (so list entries stay together).
     - Split non-code regions into paragraphs (double-newline separation) and list groups.
4. Merge segments into chunk windows:
   - Iterate segments in order, concatenating segments until adding the next would exceed 180 words.
   - When starting a new chunk, carry up to 40 tail words from the previous buffer to serve as overlap/context.
5. Final safety split: if any produced chunk still exceeds 180 words (rare), split by sentence boundaries into ~180-word windows, keeping the 40-word overlap.
6. For each chunk, write an object containing: unique `id`, `chunk_id` (source_id + index), `repo`, `source_file`, `source_id`, `source_url`, `source_title`, `section_hint`, `text`, `word_count`, and `embedding_model`.
7. Write per-repo JSON files named `<repo>_chunks.json` into `data/processed/guideline_chunks` and a `summary.json`.

## Why this design

- Document-first: raw guideline files are already organized into small, meaningful blocks (lists + examples). Keeping blocks intact maintains semantic clarity for retrieval and reduces noise when embedding.
- Paragraph/list-aware splitting: naive fixed-size or sentence-level splitting risks separating an example from its explanation. Grouping list items and preserving code blocks avoids that.
- 180-word cap: embeddings tend to be more effective when chunks are concise; 180 words gives enough context while limiting vector size and cost.
- 40-word overlap: provides context across boundaries to improve retrieval continuity and reduce missed matches near split points.

## Verification performed

- Ran the pipeline and generated the per-repo chunk files. Summary produced at `data/processed/guideline_chunks/summary.json` (counts above).
- Manually sampled chunks for `pandas` and `scikit-learn` to verify:
  - list groups remained together,
  - code examples remained with surrounding explanatory text where reasonable,
  - chunk lengths were within the configured cap.

## How to reproduce

Run the generator script from the repository root:

```bash
python -u src/data_processing/generate_guideline_chunks.py
```

Outputs: per-repo JSON files in `data/processed/guideline_chunks` and `summary.json`.

## Next optional improvements

- Add a semantic re-chunking pass: compute embeddings for the produced chunks using `BAAI/bge-large-en-v1.5`, then cluster/split/merge based on similarity to reduce redundancy or to produce more uniform semantic units.
- Expose tuning parameters (MAX_WORDS, OVERLAP_WORDS) via CLI args or config file for easier experimentation.
- Add automated checks: sample N chunks per repo and assert metadata presence and average word_count in desired range.

-- End of report
