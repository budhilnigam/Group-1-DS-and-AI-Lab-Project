import requests
import time
import json
import re
from collections import defaultdict
import os
from dotenv import load_dotenv

# =========================
# CONFIG
# =========================
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = "django"
REPO_NAME = "django"

MAX_SAMPLES = 50
PER_PAGE = 30
SLEEP_TIME = 0.5

OUTPUT_FILE = "django_evaluation_dataset.json"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

MAX_ADDED_LINES = 200
CONTEXT_RADIUS = 3

def filter_diff_lines(parsed):
    added_indices = [i for i, x in enumerate(parsed) if x["type"] == "add"]

    if not added_indices:
        return []

    selected_indices = set()

    for idx in added_indices[:MAX_ADDED_LINES]:
        for i in range(idx - CONTEXT_RADIUS, idx + CONTEXT_RADIUS + 1):
            if 0 <= i < len(parsed):
                selected_indices.add(i)

    selected_indices = sorted(selected_indices)

    return [parsed[i]["content"] for i in selected_indices]

# =========================
# FILTERING HEURISTICS
# =========================

USELESS_PATTERNS = [
    r"\blgtm\b", r"\blooks good\b", r"\bnice work\b",
    r"\bgood job\b", r"\bthanks\b", r"\bapproved\b",
    r"\bready to merge\b"
]

def is_useful_comment(text):
    text = text.lower().strip()

    if len(text) < 20:
        return False

    for p in USELESS_PATTERNS:
        if re.search(p, text):
            return False

    # Must contain signal words
    signal_keywords = ["should", "must", "avoid", "fix", "incorrect", "error", "issue"]
    if not any(k in text for k in signal_keywords):
        return False

    return True


# =========================
# API UTILITIES
# =========================

def github_get(url, params=None, retries=3):
    for _ in range(retries):
        res = requests.get(url, headers=HEADERS, params=params)
        if res.status_code == 200:
            return res.json()
        elif res.status_code == 403:
            print("Rate limit hit, sleeping...")
            time.sleep(60)
        else:
            time.sleep(2)
    return None


def get_prs(page):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls"
    return github_get(url, {
        "state": "closed",
        "per_page": PER_PAGE,
        "page": page,
        "sort": "updated",
        "direction": "desc"
    })


def get_review_comments(pr_number):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}/comments"
    return github_get(url)


# =========================
# DIFF PARSING
# =========================

def parse_diff_hunk(diff_hunk):
    """
    Parses diff hunk into structured lines with mapping
    """
    lines = diff_hunk.split("\n")

    parsed = []
    old_line = None
    new_line = None

    header = lines[0]
    match = re.match(r"@@ -(\d+),?\d* \+(\d+),?\d* @@", header)

    if match:
        old_line = int(match.group(1))
        new_line = int(match.group(2))

    for line in lines[1:]:
        entry = {
            "content": line,
            "type": None,
            "old_line": None,
            "new_line": None
        }

        if line.startswith("+"):
            entry["type"] = "add"
            entry["new_line"] = new_line
            new_line += 1

        elif line.startswith("-"):
            entry["type"] = "del"
            entry["old_line"] = old_line
            old_line += 1

        else:
            entry["type"] = "context"
            entry["old_line"] = old_line
            entry["new_line"] = new_line
            old_line += 1
            new_line += 1

        parsed.append(entry)

    return parsed


def find_diff_index(parsed_lines, target_line):
    """
    Maps GitHub 'line' to diff index accurately
    """
    for idx, entry in enumerate(parsed_lines):
        if entry["new_line"] == target_line:
            return idx
    return None


# =========================
# CHUNK MERGING
# =========================

def merge_chunks(existing_chunks, new_chunk_lines):
    """
    Merge overlapping diff chunks to avoid duplication
    """
    new_set = set(new_chunk_lines)

    for chunk in existing_chunks:
        if len(new_set.intersection(set(chunk["diff_lines"]))) > 3:
            # merge
            merged = list(set(chunk["diff_lines"] + new_chunk_lines))
            chunk["diff_lines"] = merged
            return chunk["chunk_id"]

    chunk_id = f"c{len(existing_chunks) + 1}"
    existing_chunks.append({
        "chunk_id": chunk_id,
        "diff_lines": new_chunk_lines
    })
    return chunk_id


# =========================
# MAIN PIPELINE
# =========================

def build_dataset():
    dataset = []
    collected = 0
    page = 1

    while collected < MAX_SAMPLES:
        prs = get_prs(page)
        if not prs:
            break

        print(f"\nProcessing PR page {page}")

        for pr in prs:
            pr_number = pr["number"]
            print(f"PR #{pr_number}")

            comments = get_review_comments(pr_number)
            if not comments:
                continue

            file_data = defaultdict(lambda: {
                "diff_chunks": [],
                "ground_truth_reviews": []
            })

            seen_comments = set()

            for c in comments:
                body = c.get("body", "")
                path = c.get("path")
                diff_hunk = c.get("diff_hunk")
                line = c.get("line")

                if not path or not diff_hunk or not line:
                    continue

                if not is_useful_comment(body):
                    continue

                if body in seen_comments:
                    continue
                seen_comments.add(body)

                parsed = parse_diff_hunk(diff_hunk)
                diff_index = find_diff_index(parsed, line)

                if diff_index is None:
                    continue

                diff_lines = filter_diff_lines(parsed)

                chunk_id = merge_chunks(
                    file_data[path]["diff_chunks"],
                    diff_lines
                )

                file_data[path]["ground_truth_reviews"].append({
                    "review_id": f"r{c['id']}",
                    "chunk_id": chunk_id,
                    "diff_line_index": diff_index,
                    "file_line_number": line,
                    "violation_category": "",
                    "review_comment": body.strip()
                })

            for file_path, data in file_data.items():
                if not data["ground_truth_reviews"]:
                    continue

                dataset.append({
                    "pr_id": f"PR_{pr_number}",
                    "repo": f"{REPO_OWNER}/{REPO_NAME}",
                    "file_path": file_path,
                    "diff_chunks": data["diff_chunks"],
                    "ground_truth_reviews": data["ground_truth_reviews"]
                })

                collected += 1
                print(f"Collected: {collected}")

                if collected >= MAX_SAMPLES:
                    break

            if collected >= MAX_SAMPLES:
                break

            time.sleep(SLEEP_TIME)

        page += 1

    return dataset


# =========================
# RUN
# =========================

if __name__ == "__main__":
    data = build_dataset()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"\nSaved dataset to {OUTPUT_FILE}")