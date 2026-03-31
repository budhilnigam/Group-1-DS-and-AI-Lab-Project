#!/usr/bin/env python
# coding: utf-8

# In[1]:


import requests
import time
import json
import re
import os
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}
REPO = "django/django"
OUTPUT_FILE = "django_prs.json"
STATE_FILE = "django_pr_state.json"

MAX_SAMPLES = 50
MAX_DIFF_LINES = 200


# In[2]:


def github_get(url, params=None):
    while True:
        res = requests.get(url, headers=HEADERS, params=params)
        if res.status_code == 200:
            return res.json()
        elif res.status_code == 403:
            reset_time = int(res.headers.get("X-RateLimit-Reset", time.time() + 60))
            sleep_time = max(0, reset_time - time.time()) + 1
            print(f"Rate limited. Sleeping for {sleep_time} seconds...")
            time.sleep(sleep_time)
        else:
            print(f"Error {res.status_code}: {res.text}")
            return None


# In[3]:


USELESS_PATTERNS = [
    r"\blgtm\b", r"\blooks good\b", r"\bnice work\b",
    r"\bgood job\b", r"\bthanks\b", r"\bapproved\b",
    r"\bready to merge\b", r"^\s*nit:?\s*$"
]

def is_useful_comment(text):
    text = text.lower().strip()
    if len(text) < 15:
        return False
    for p in USELESS_PATTERNS:
        if re.search(p, text):
            return False
    return True

def is_bot(user):
    login = user.get("login", "").lower()
    user_type = user.get("type", "")
    return user_type == "Bot" or "[bot]" in login or "bot" in login.split("-")


# In[4]:


def load_state():
    dataset = []
    processed_prs = set()
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                dataset = json.load(f)
        except Exception as e:
            print("Could not load existing dataset:", e)
            
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                processed_prs = set(json.load(f).get("processed", []))
        except Exception as e:
            print("Could not load existing state file:", e)
            
    return dataset, processed_prs

def save_state(dataset, processed_prs):
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2)
    with open(STATE_FILE, 'w') as f:
        json.dump({"processed": list(processed_prs)}, f)


# In[5]:


dataset, processed_prs = load_state()
print(f"Loaded {len(dataset)} existing samples. Processed PRs: {len(processed_prs)}")

collected = len(dataset)
page = 1

print("Starting extraction...")
while collected < MAX_SAMPLES:
    search_url = "https://api.github.com/search/issues"
    # Changed search query to target old and potentially unmerged PRs where syntax/logic errors are prevalent
    query = f"is:pr is:closed repo:{REPO} language:Python comments:>0 created:<2024-01-01"
    
    print(f"Fetching search page {page}...")
    search_res = github_get(search_url, params={"q": query, "per_page": 30, "page": page, "sort": "created", "order": "desc"})
    
    if not search_res or "items" not in search_res or len(search_res["items"]) == 0:
        print("No more PRs found or hit a limit.")
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
        
        comments_url = f"https://api.github.com/repos/{REPO}/pulls/{pr_number}/comments"
        comments = github_get(comments_url)
        
        if not comments:
            save_state(dataset, processed_prs)
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
                "repo": REPO,
                "file": path,
                "chunk_id": chunk_id,
                "diff": diff_hunk,
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
            
        # Save process tracking even if no useful samples
        save_state(dataset, processed_prs)
        print(f"  Total collected: {collected}/{MAX_SAMPLES}")
            
    page += 1
    time.sleep(1)

print(f"Finished extraction. Total samples: {min(collected, MAX_SAMPLES)}")

