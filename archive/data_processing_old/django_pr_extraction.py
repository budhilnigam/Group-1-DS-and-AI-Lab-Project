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

OUTPUT_FILE = "django_evaluation_dataset.jsonl"
CHECKPOINT_FILE = "django_checkpoint.json"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

# =========================
# CHECKPOINT HANDLING
# =========================

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            return json.load(f)
    return {"page": 1, "pr_index": 0, "collected": 0}


def save_checkpoint(state):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(state, f)


# =========================
# FILTERING
# =========================

USELESS_PATTERNS = [
    r"\blgtm\b", r"\blooks good\b", r"\bnice work\b",
    r"\bgood job\b", r"\bthanks\b", r"\bapproved\b"
]

def is_useful_comment(text):
    text = text.lower().strip()

    if len(text) < 20:
        return False

    for p in USELESS_PATTERNS:
        if re.search(p, text):
            return False

    keywords = ["should", "must", "fix", "error", "issue", "incorrect"]
    return any(k in text for k in keywords)


# =========================
# API
# =========================

def github_get(url, params=None):
    while True:
        res = requests.get(url, headers=HEADERS, params=params)

        if res.status_code == 200:
            return res.json()

        if res.status_code == 403:
            print("Rate limit hit. Sleeping 60s...")
            time.sleep(60)
        else:
            print(f"Retrying... ({res.status_code})")
            time.sleep(2)


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
        entry = {"content": line, "type": None, "old": None, "new": None}

        if line.startswith("+"):
            entry["type"] = "add"
            entry["new"] = new_line
            new_line += 1
        elif line.startswith("-"):
            entry["type"] = "del"
            entry["old"] = old_line
            old_line += 1
        else:
            entry["type"] = "context"
            entry["old"] = old_line
            entry["new"] = new_line
            old_line += 1
            new_line += 1

        parsed.append(entry)

    return parsed


def find_diff_index(parsed, target_line):
    for i, p in enumerate(parsed):
        if p["new"] == target_line:
            return i
    return None


# =========================
# DIFF FILTERING (200 ADDED LINES RULE)
# =========================

MAX_ADDED_LINES = 200
CONTEXT_RADIUS = 3

def filter_diff(parsed):
    added_indices = [i for i, x in enumerate(parsed) if x["type"] == "add"]

    if not added_indices:
        return [], {}

    selected = set()

    for idx in added_indices[:MAX_ADDED_LINES]:
        for i in range(idx - CONTEXT_RADIUS, idx + CONTEXT_RADIUS + 1):
            if 0 <= i < len(parsed):
                selected.add(i)

    selected = sorted(selected)

    index_map = {}
    filtered_lines = []

    for new_idx, old_idx in enumerate(selected):
        index_map[old_idx] = new_idx
        filtered_lines.append(parsed[old_idx]["content"])

    return filtered_lines, index_map


# =========================
# STREAM WRITE
# =========================

def append_to_file(entry):
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# =========================
# MAIN
# =========================

def run():
    state = load_checkpoint()

    page = state["page"]
    pr_index = state["pr_index"]
    collected = state["collected"]

    print("Resuming from:", state)

    while collected < MAX_SAMPLES:
        prs = get_prs(page)

        if not prs:
            break

        for i in range(pr_index, len(prs)):
            pr = prs[i]
            pr_number = pr["number"]

            print(f"Processing PR #{pr_number}")

            comments = get_review_comments(pr_number)
            if not comments:
                continue

            file_data = defaultdict(lambda: {
                "diff_chunks": [],
                "ground_truth_reviews": []
            })

            for c in comments:
                body = c.get("body", "")
                path = c.get("path")
                diff_hunk = c.get("diff_hunk")
                line = c.get("line")

                if not path or not diff_hunk or not line:
                    continue

                if not is_useful_comment(body):
                    continue

                parsed = parse_diff_hunk(diff_hunk)
                diff_index = find_diff_index(parsed, line)

                if diff_index is None:
                    continue

                diff_lines, index_map = filter_diff(parsed)

                if diff_index not in index_map:
                    continue

                new_index = index_map[diff_index]

                chunk_id = f"c{len(file_data[path]['diff_chunks'])+1}"

                file_data[path]["diff_chunks"].append({
                    "chunk_id": chunk_id,
                    "diff_lines": diff_lines
                })

                file_data[path]["ground_truth_reviews"].append({
                    "review_id": f"r{c['id']}",
                    "chunk_id": chunk_id,
                    "diff_line_index": new_index,
                    "file_line_number": line,
                    "violation_category": "",
                    "review_comment": body.strip()
                })

            for file_path, data in file_data.items():
                if not data["ground_truth_reviews"]:
                    continue

                entry = {
                    "pr_id": f"PR_{pr_number}",
                    "repo": f"{REPO_OWNER}/{REPO_NAME}",
                    "file_path": file_path,
                    "diff_chunks": data["diff_chunks"],
                    "ground_truth_reviews": data["ground_truth_reviews"]
                }

                append_to_file(entry)

                collected += 1
                print(f"Collected: {collected}")

                if collected >= MAX_SAMPLES:
                    break

            # ✅ SAVE CHECKPOINT AFTER EACH PR
            state = {
                "page": page,
                "pr_index": i + 1,
                "collected": collected
            }
            save_checkpoint(state)

            time.sleep(SLEEP_TIME)

            if collected >= MAX_SAMPLES:
                break

        page += 1
        pr_index = 0


if __name__ == "__main__":
    run()