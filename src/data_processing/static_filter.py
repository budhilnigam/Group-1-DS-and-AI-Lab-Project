import os
import json
import requests
import time
import re
import subprocess
import sys
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

INPUT_FILE = "django_ast_chunks.json"
OUTPUT_FILE = "django_labeled_chunks.json"
TEMP_FILE = ".temp_file.py"

def github_get(url):
    while True:
        res = requests.get(url, headers=HEADERS)
        if res.status_code == 200:
            return res.json()
        elif res.status_code in [403, 429]:
            reset = int(res.headers.get("X-RateLimit-Reset", time.time() + 60))
            time.sleep(max(0, reset - time.time()) + 1)
        elif res.status_code == 404:
            return None
        else:
            return None

def fetch_raw_file(repo, sha, file_path):
    url = f"https://raw.githubusercontent.com/{repo}/{sha}/{file_path}"
    res = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if res.status_code == 200:
        return res.text
    return None

def run_linters(target_line):
    # Allow a margin of ±1 lines since exact AST matching can sometimes skew by one line
    allowed_lines = {target_line - 1, target_line, target_line + 1}
    violation_matched = ""
    
    # 1. Run Flake8
    try:
        # sys.executable ensures it uses the same virtual environment python safely on Windows
        result = subprocess.run([sys.executable, "-m", "flake8", TEMP_FILE], capture_output=True, text=True)
        # Format expects: .temp_file.py:12:5: F401 'os' imported but unused
        for line in result.stdout.split('\n'):
            match = re.search(rf"{TEMP_FILE}:(\d+):", line)
            if match:
                lineno = int(match.group(1))
                if lineno in allowed_lines:
                    if "F401" in line:
                        violation_matched = "unused_import"
                        break
                    elif re.search(r"E1\d{2}", line): # E1xx relates to indentation
                        violation_matched = "indentation"
                        break
    except Exception as e:
        print("Flake8 error:", e)
        
    if violation_matched:
        return violation_matched
        
    # 2. Run Pylint
    try:
        # W0102 = dangerous-default-value
        # C0103 = invalid-name
        cmd = [
            sys.executable,
            "-m",
            "pylint", 
            "--disable=all", 
            "--enable=invalid-name,dangerous-default-value", 
            "--msg-template={path}:{line}:{msg_id}", 
            TEMP_FILE
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            match = re.search(rf"{TEMP_FILE}:(\d+):", line)
            if match:
                lineno = int(match.group(1))
                if lineno in allowed_lines:
                    if "W0102" in line or "dangerous-default-value" in line:
                        violation_matched = "mutable_default"
                        break
                    elif "C0103" in line or "invalid-name" in line:
                        violation_matched = "naming_convention"
                        break
    except Exception as e:
        print("Pylint error:", e)
        
    return violation_matched

def process_dataset():
    if not os.path.exists(INPUT_FILE):
        print(f"Input file {INPUT_FILE} not found. Run ast_chunker.py first.")
        return
        
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        dataset = json.load(f)
        
    sha_cache = {}
    file_cache = {}
    
    for i, sample in enumerate(dataset):
        print(f"Labeling {i+1}/{len(dataset)}: {sample['chunk_id']}")
        
        violations = sample.get("violations", [])
        if not violations:
            continue
            
        target_line = violations[0].get("line")
        if not target_line:
            continue
            
        repo = sample["repo"]
        file_path = sample["file"]
        
        chunk_id = sample.get("chunk_id", "")
        pr_match = re.search(r"PR(\d+)_", chunk_id)
        if not pr_match:
            continue
            
        pr_number = pr_match.group(1)
        
        cache_key = f"{repo}_{pr_number}"
        if cache_key not in sha_cache:
            pr_data = github_get(f"https://api.github.com/repos/{repo}/pulls/{pr_number}")
            sha_cache[cache_key] = pr_data["head"]["sha"] if pr_data and "head" in pr_data else None
            time.sleep(0.1)
                
        sha = sha_cache[cache_key]
        if not sha:
            continue
            
        file_key = f"{repo}_{sha}_{file_path}"
        if file_key not in file_cache:
            file_cache[file_key] = fetch_raw_file(repo, sha, file_path)
            
        source_code = file_cache[file_key]
        if not source_code:
            continue
            
        with open(TEMP_FILE, "w", encoding="utf-8") as f:
            f.write(source_code)
            
        detected_label = run_linters(target_line)
        
        if detected_label:
            violations[0]["type"] = detected_label
            print(f"  -> Detected: {detected_label} on line {target_line}")
        else:
            violations[0]["type"] = ""
            print(f"  -> No linter match on line {target_line}. Set to empty string.")
            
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2)

    if os.path.exists(TEMP_FILE):
        os.remove(TEMP_FILE)
        
    print(f"\nFinished static filtering. Saved dataset labels to {OUTPUT_FILE}")

if __name__ == "__main__":
    process_dataset()
