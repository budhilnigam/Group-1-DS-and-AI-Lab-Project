import os
import re
import glob
import json
import uuid
import html
from typing import List


RAW_DIR = "data/raw/guidelines_raw"
OUT_DIR = "data/processed/guideline_chunks"
EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"
MAX_WORDS = 180
OVERLAP_WORDS = 40


def ensure_out():
    os.makedirs(OUT_DIR, exist_ok=True)


def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def simple_frontmatter(text: str) -> dict:
    fm = {}
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            block = parts[1]
            for line in block.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip()
    return fm


def parse_guideline_blocks(text: str) -> List[dict]:
    lines = text.splitlines()
    i = 0
    blocks = []
    while i < len(lines):
        if lines[i].strip() == "BEGIN_GUIDELINE_BLOCK":
            i += 1
            meta = {}
            # read metadata until BEGIN_TEXT
            while i < len(lines) and lines[i].strip() != "BEGIN_TEXT":
                line = lines[i].strip()
                if line and ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
                i += 1
            # skip BEGIN_TEXT
            if i < len(lines) and lines[i].strip() == "BEGIN_TEXT":
                i += 1
            # collect text until END_TEXT
            text_lines = []
            while i < len(lines) and lines[i].strip() != "END_TEXT":
                text_lines.append(lines[i])
                i += 1
            # skip END_TEXT and END_GUIDELINE_BLOCK (if present)
            while i < len(lines) and lines[i].strip() not in ("END_TEXT", "END_GUIDELINE_BLOCK"):
                i += 1
            # advance past END_TEXT
            if i < len(lines) and lines[i].strip() == "END_TEXT":
                i += 1
            # advance to END_GUIDELINE_BLOCK
            while i < len(lines) and lines[i].strip() != "END_GUIDELINE_BLOCK":
                i += 1
            # skip END_GUIDELINE_BLOCK
            if i < len(lines) and lines[i].strip() == "END_GUIDELINE_BLOCK":
                i += 1

            block_text = "\n".join(text_lines).strip()
            block_text = html.unescape(block_text)
            blocks.append({"meta": meta, "text": block_text})
        else:
            i += 1
    return blocks


def word_count(s: str) -> int:
    return len(s.split())


def split_on_list_boundaries(text: str) -> List[str]:
    # Group contiguous list items into a single part and leave them attached
    lines = text.splitlines()
    parts = []
    buf = []
    in_list = False
    for ln in lines:
        if re.match(r"\s*(?:\*|\-|\d+\.)\s+", ln):
            if not in_list and buf:
                parts.append("\n".join(buf).strip())
                buf = []
            in_list = True
            buf.append(ln)
        else:
            if in_list:
                parts.append("\n".join(buf).strip())
                buf = []
                in_list = False
            buf.append(ln)
    if buf:
        parts.append("\n".join(buf).strip())
    # further split only if parts are large
    return [p for p in parts if p]


def split_on_paragraphs(text: str) -> List[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return parts


def split_into_sentences(text: str) -> List[str]:
    # naive sentence split that works for our content
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def chunk_sentences(sentences: List[str], max_words: int, overlap: int) -> List[str]:
    parts = []
    cur = []
    cur_words = 0
    i = 0
    while i < len(sentences):
        s = sentences[i]
        w = word_count(s)
        if cur_words + w <= max_words or not cur:
            cur.append(s)
            cur_words += w
            i += 1
        else:
            parts.append(" ".join(cur))
            # prepare overlap: take last `overlap` words from current
            overlap_words = []
            if overlap > 0:
                acc = " ".join(cur).split()
                overlap_words = acc[-overlap:]
            cur = []
            if overlap_words:
                cur = [" ".join(overlap_words)]
                cur_words = len(overlap_words)
            else:
                cur_words = 0
    if cur:
        parts.append(" ".join(cur))
    return parts


def recursive_split(text: str, max_words: int = MAX_WORDS, overlap: int = OVERLAP_WORDS) -> List[str]:
    # Document-first: split into coherent segments (paragraphs, grouped lists, code blocks)
    # then merge segments into chunks up to max_words to preserve meaning.
    segments = []
    # Identify fenced code blocks and keep them with surrounding text
    code_fences = re.split(r"(```[\s\S]*?```)", text)
    for part in code_fences:
        if part.startswith("```"):
            segments.append(part.strip())
        else:
            # split non-code into grouped paragraphs/lists
            segs = split_on_list_boundaries(part)
            for s in segs:
                paras = split_on_paragraphs(s)
                for p in paras:
                    if p.strip():
                        segments.append(p.strip())

    # merge segments into chunks up to max_words
    chunks: List[str] = []
    cur = []
    cur_words = 0
    for seg in segments:
        w = word_count(seg)
        # if a single segment is small enough, consider adding it
        if cur_words + w <= max_words or not cur:
            cur.append(seg)
            cur_words += w
        else:
            chunks.append("\n\n".join(cur).strip())
            # start new buffer, keep overlap by carrying some tail words
            tail = []
            if overlap > 0:
                acc = " ".join(cur).split()
                tail = acc[-overlap:]
            cur = []
            if tail:
                cur = [" ".join(tail)]
                cur_words = len(tail)
            else:
                cur_words = 0
            cur.append(seg)
            cur_words += w

    if cur:
        chunks.append("\n\n".join(cur).strip())

    # final safety: split any chunk still too large on sentences
    final = []
    for c in chunks:
        if word_count(c) <= max_words:
            final.append(c)
        else:
            sents = split_into_sentences(c)
            final.extend(chunk_sentences(sents, max_words, overlap))
    return final


def make_chunks_for_blocks(blocks: List[dict], repo_name: str, filename: str) -> List[dict]:
    chunks = []
    for b in blocks:
        meta = b.get("meta", {})
        text = b.get("text", "").strip()
        if not text:
            continue
        src_id = meta.get("source_id") or meta.get("source_id") or str(uuid.uuid4())
        parts = [text]
        if word_count(text) > MAX_WORDS:
            parts = recursive_split(text)
        for idx, p in enumerate(parts, start=1):
            chunk_id = f"{src_id}__{idx}"
            entry = {
                "id": uuid.uuid4().hex,
                "chunk_id": chunk_id,
                "repo": repo_name,
                "source_file": filename,
                "source_id": src_id,
                "source_url": meta.get("source_url"),
                "source_title": meta.get("source_title"),
                "section_hint": meta.get("section_hint"),
                "text": p.strip(),
                "word_count": word_count(p),
                "embedding_model": EMBEDDING_MODEL,
            }
            chunks.append(entry)
    return chunks


def process_file(path: str) -> List[dict]:
    text = read_file(path)
    fm = simple_frontmatter(text)
    repo_name = fm.get("repo_name") or fm.get("repo") or os.path.basename(path).split("_")[0]
    blocks = parse_guideline_blocks(text)
    chunks = make_chunks_for_blocks(blocks, repo_name, os.path.relpath(path))
    return repo_name, chunks


def main():
    ensure_out()
    files = glob.glob(os.path.join(RAW_DIR, "*_guidelines_raw.md"))
    if not files:
        print("No guideline raw files found in", RAW_DIR)
        return
    summary = {}
    for f in files:
        repo_name, chunks = process_file(f)
        out_path = os.path.join(OUT_DIR, f"{repo_name}_chunks.json")
        with open(out_path, "w", encoding="utf-8") as of:
            json.dump(chunks, of, ensure_ascii=False, indent=2)
        summary[repo_name] = {"chunks": len(chunks), "out_path": out_path}
        print(f"Wrote {len(chunks)} chunks for {repo_name} -> {out_path}")

    # also write a summary
    summary_path = os.path.join(OUT_DIR, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as sf:
        json.dump(summary, sf, ensure_ascii=False, indent=2)
    print("Summary written to", summary_path)


if __name__ == "__main__":
    main()
