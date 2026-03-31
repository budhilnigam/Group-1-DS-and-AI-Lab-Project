import argparse
import requests
import time
import json
import re
import os
import sys
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

MAX_SAMPLES = 1000
MAX_DIFF_LINES = 200

USELESS_PATTERNS = [
    r"\blgtm\b", r"\blooks good\b", r"\bnice work\b",
    r"\bgood job\b", r"\bthanks\b", r"\bapproved\b",
    r"\bready to merge\b", r"^\s*nit:?\s*$"
]

def github_get(url, params=None):
    while True:
        res = requests.get(url, headers=HEADERS, params=params)
        if res.status_code == 200:
            return res.json()
        elif res.status_code in [403, 429]:
            reset_time = int(res.headers.get("X-RateLimit-Reset", time.time() + 60))
            sleep_time = max(0, reset_time - time.time()) + 1
            print(f"Rate limited. Sleeping for {sleep_time} seconds...")
            time.sleep(sleep_time)
        else:
            print(f"Error {res.status_code}: {res.text}")
            return None

def is_useful_comment(text):
    text = text.lower().strip()
    if len(text)<=1:
        return False
    for p in USELESS_PATTERNS:
        if re.search(p, text):
            return False
    return True

def is_bot(user):
    login = user.get("login", "").lower()
    user_type = user.get("type", "")
    return user_type == "Bot" or "[bot]" in login or "bot" in login.split("-")

def parse_diff_hunk(diff_str):
    """Parses a unified diff hunk into a list of structured line objects."""
    lines = diff_str.split('\n')
    structured = []
    
    old_line = 0
    new_line = 0
    
    for line in lines:
        if line.startswith('@@'):
            match = re.search(r'@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@', line)
            if match:
                old_line = int(match.group(1))
                new_line = int(match.group(2))
            structured.append({
                "type": "hunk_header",
                "old_line": None,
                "new_line": None,
                "content": line
            })
        elif line.startswith('-'):
            structured.append({
                "type": "deletion",
                "old_line": old_line,
                "new_line": None,
                "content": line[1:] if len(line) > 1 else ""
            })
            old_line += 1
        elif line.startswith('+'):
            structured.append({
                "type": "addition",
                "old_line": None,
                "new_line": new_line,
                "content": line[1:] if len(line) > 1 else ""
            })
            new_line += 1
        elif line.startswith('\\'):
            structured.append({
                "type": "meta",
                "old_line": None,
                "new_line": None,
                "content": line
            })
        else:
            content = line[1:] if line.startswith(' ') else line
            structured.append({
                "type": "context",
                "old_line": old_line if old_line > 0 else None,
                "new_line": new_line if new_line > 0 else None,
                "content": content
            })
            if old_line > 0: old_line += 1
            if new_line > 0: new_line += 1
            
    return structured

def load_state(output_file, state_file):
    dataset = []
    processed_prs = set()
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                dataset = json.load(f)
        except Exception as e:
            print("Could not load existing dataset:", e)
            
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                processed_prs = set(json.load(f).get("processed", []))
        except Exception as e:
            print("Could not load existing state file:", e)
            
    return dataset, processed_prs

def save_state(dataset, processed_prs, output_file, state_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2)
    with open(state_file, 'w') as f:
        json.dump({"processed": list(processed_prs)}, f)

def main():
    parser = argparse.ArgumentParser(description="Extract PR review comments dynamically.")
    parser.add_argument("repo", help="Target repository (e.g. pallets/flask)")
    args = parser.parse_args()
    
    repo = args.repo
    repo_prefix = repo.split("/")[-1]
    
    # Create the versioned sub-folder
    output_dir = os.path.join(os.path.dirname(__file__), repo_prefix, "v1")
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f"{repo_prefix}_prs.json")
    state_file = os.path.join(output_dir, f"{repo_prefix}_pr_state.json")
    
    dataset, processed_prs = load_state(output_file, state_file)
    print(f"Loaded {len(dataset)} existing samples for {repo}. Processed PRs: {len(processed_prs)}")

    collected = len(dataset)
    page = 1

    print(f"Starting extraction for {repo}...")
    while collected < MAX_SAMPLES:
        search_url = "https://api.github.com/search/issues"
        query = f"is:pr is:closed repo:{repo} language:Python -review:none"
        
        print(f"Fetching search page {page}...")
        search_res = github_get(search_url, params={"q": query, "per_page": 30, "page": page, "sort": "created", "order": "desc"})
        
        if not search_res or "items" not in search_res:
            print("Hit a limit or encountered an error.")
            break
        if len(search_res["items"]) == 0:
            print("No more PRs found.")
            break
            
        items = search_res["items"]
        
        for item in items:
            if collected >= MAX_SAMPLES:
                break
                
            pr_number = item["number"]
            if pr_number in processed_prs:
                continue
                
            pr_author = item["user"]["login"]
            print(f"Inspecting PR #{pr_number}...")
            
            processed_prs.add(pr_number)
            
            comments_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/comments"
            comments = github_get(comments_url)
            
            if not comments:
                save_state(dataset, processed_prs, output_file, state_file)
                continue
                
            useful_samples = []
            for c in comments:
                if is_bot(c.get("user", {})):
                    continue
                    
                comment_author = c.get("user", {}).get("login", "")
                if comment_author == pr_author:
                    continue
                    
                body = c.get("body", "")
                if not is_useful_comment(body):
                    continue
                    
                path = c.get("path", "")
                if not path.endswith(".py"):
                    continue
                    
                diff_hunk = c.get("diff_hunk", "")
                diff_lines = len(diff_hunk.split('\n'))
                if diff_lines > MAX_DIFF_LINES:
                    print(f"  Skipped huge chunk in {path} ({diff_lines} lines)")
                    continue
                    
                chunk_id = f"PR{pr_number}_{c['id']}"
                sample = {
                    "repo": repo,
                    "file": path,
                    "chunk_id": chunk_id,
                    "diff_structured": parse_diff_hunk(diff_hunk),
                    "violations": [
                        {
                            "type": "",
                            "line": c.get("line") or c.get("original_line"),
                            "review_comment": body
                        }
                    ]
                }
                useful_samples.append(sample)
                
            if useful_samples:
                print(f"  Found {len(useful_samples)} useful samples in PR #{pr_number}")
                dataset.extend(useful_samples)
                collected = len(dataset)
                
            save_state(dataset, processed_prs, output_file, state_file)
            print(f"  Total collected: {collected}/{MAX_SAMPLES}")
                
        page += 1
        time.sleep(1)

    print(f"Finished extraction. Total samples: {min(collected, MAX_SAMPLES)}")

if __name__ == "__main__":
    main()
