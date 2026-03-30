#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

GITHUB_API = "https://api.github.com"
OWNER = "kannan-dedsec"
FRAMEWORKS = ["flask", "fastapi", "pandas", "sklearn", "django"]

BRANCH_CATEGORY_MAP = {
    "unused-import": "unused_import",
    "indentation": "indentation",
    "naming-convention": "naming_convention",
    "documentation-formatting": "documentation_formatting",
    "mutable-default": "mutable_default",
}


def gh_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def paginate(token: str, url: str, params: dict | None = None) -> list[dict]:
    results = []
    params = dict(params or {})
    params.setdefault("per_page", 100)
    page = 1
    while True:
        params["page"] = page
        resp = requests.get(
            url, headers=gh_headers(token), params=params, timeout=30
        )
        resp.raise_for_status()
        items = resp.json()
        if not items:
            break
        results.extend(items)
        if len(items) < params["per_page"]:
            break
        page += 1
        time.sleep(0.5)
    return results


def extract_category_from_branch(branch: str) -> str | None:
    match = re.match(r"violation/(.+)-(\d+)$", branch)
    if match:
        slug = match.group(1)
        return BRANCH_CATEGORY_MAP.get(slug)
    return None


def parse_fallback_comment(body: str) -> list[dict]:
    entries = []
    pattern = re.compile(
        r"-\s+\*\*(.+?)\*\*\s+\(line\s+(\d+)\):\s+(.+)"
    )
    for m in pattern.finditer(body):
        file_path = m.group(1).strip()
        line_num = int(m.group(2))
        text = m.group(3).strip()
        entries.append({
            "file_path": file_path,
            "line": line_num,
            "text": text,
        })
    return entries


def fetch_repo_review_data(token: str, repo_name: str) -> list[dict]:
    full_repo = f"{OWNER}/{repo_name}"
    print(f"[{repo_name}] Fetching PRs...")

    prs = paginate(
        token,
        f"{GITHUB_API}/repos/{full_repo}/pulls",
        {"state": "all"},
    )
    print(f"[{repo_name}] Found {len(prs)} PRs")

    entries = []

    for pr in prs:
        pr_number = pr["number"]
        branch = pr["head"]["ref"]
        head_sha = pr["head"]["sha"]
        category = extract_category_from_branch(branch)

        if not category:
            print(f"  [PR #{pr_number}] Skipping — can't parse category from '{branch}'")
            continue

        # Inline review comments
        review_comments = paginate(
            token,
            f"{GITHUB_API}/repos/{full_repo}/pulls/{pr_number}/comments",
        )

        for rc in review_comments:
            text = rc.get("body", "").strip()
            if not text:
                continue
            file_path = rc.get("path", "")
            commit_id = rc.get("commit_id", head_sha)
            entries.append({
                "text": text,
                "category": category,
                "file_path": file_path,
                "commit_sha": commit_id,
                "pr_number": pr_number,
                "comment_type": "inline",
            })

        # Fallback issue comments
        issue_comments = paginate(
            token,
            f"{GITHUB_API}/repos/{full_repo}/issues/{pr_number}/comments",
        )

        for ic in issue_comments:
            body = ic.get("body", "")
            if "**Code Review Comments:**" in body:
                parsed = parse_fallback_comment(body)
                for p in parsed:
                    entries.append({
                        "text": p["text"],
                        "category": category,
                        "file_path": p["file_path"],
                        "commit_sha": head_sha,
                        "pr_number": pr_number,
                        "comment_type": "fallback",
                    })
            else:
                text = body.strip()
                if text and len(text) > 10:
                    entries.append({
                        "text": text,
                        "category": category,
                        "file_path": "",
                        "commit_sha": head_sha,
                        "pr_number": pr_number,
                        "comment_type": "issue",
                    })

        time.sleep(0.3)

    print(f"[{repo_name}] Collected {len(entries)} review comments")
    return entries


def build_dataset(
    all_entries: list[dict],
    start_chunk: int,
) -> list[dict]:
    dataset = []
    chunk_num = start_chunk

    for entry in all_entries:
        framework = entry["framework"]
        file_path = entry["file_path"]
        commit_sha = entry["commit_sha"][:8] if entry["commit_sha"] else ""

        source_path = f"{OWNER}/synthetic-{framework}/{file_path}@{commit_sha}"

        dataset.append({
            "text": entry["text"],
            "category": entry["category"],
            "source_type": f"{framework}_review_comment",
            "source_path": source_path,
            "chunk_id": f"chunk_{chunk_num:04d}",
        })
        chunk_num += 1

    return dataset


def main():
    parser = argparse.ArgumentParser(description="Fetch PR review comments and build review.json")
    parser.add_argument("--repos", nargs="+", default=FRAMEWORKS, choices=FRAMEWORKS)
    parser.add_argument("--start-chunk", type=int, default=217)
    parser.add_argument("--output", default="data/raw/review_comments/review.json")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_REPO")
    if not token:
        print("[Error] No token. Set GITHUB_REPO in .env")
        sys.exit(1)

    print("[Auth] Using repo token for API access")
    print(f"[Config] Repos: {args.repos}")
    print(f"[Config] Start chunk: chunk_{args.start_chunk:04d}")
    print(f"[Config] Output: {args.output}")
    print()

    all_entries = []
    for framework in args.repos:
        repo_name = f"synthetic-{framework}"
        entries = fetch_repo_review_data(token, repo_name)
        for e in entries:
            e["framework"] = framework
        all_entries.extend(entries)

    seen = set()
    unique_entries = []
    dupes = 0
    for e in all_entries:
        key = (e["text"], e["category"], e["framework"], e["file_path"], e["commit_sha"])
        if key in seen:
            dupes += 1
            continue
        seen.add(key)
        unique_entries.append(e)
    if dupes:
        print(f"[Dedup] Removed {dupes} duplicate comments")

    unique_entries.sort(key=lambda e: (e["framework"], e["pr_number"], e["file_path"], e["text"]))

    print(f"\n[Total] {len(unique_entries)} unique review comments across all repos")

    if not unique_entries:
        print("[Warn] No comments found. Exiting.")
        sys.exit(0)

    dataset = build_dataset(unique_entries, args.start_chunk)

    output_path = args.output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    print(f"\n[Done] Wrote {len(dataset)} entries to {output_path}")
    print(f"[Done] Chunk IDs: chunk_{args.start_chunk:04d} through chunk_{args.start_chunk + len(dataset) - 1:04d}")

    print(f"\nSummary by source_type:")
    by_fw = Counter()
    by_cat = Counter()
    for entry in dataset:
        by_fw[entry["source_type"]] += 1
        by_cat[entry["category"]] += 1
    for k, v in sorted(by_fw.items()):
        print(f"  {k}: {v}")
    print("\nSummary by category:")
    for k, v in sorted(by_cat.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
