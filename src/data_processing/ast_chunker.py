import os
import json
import requests
import time
import re
import argparse
import tree_sitter
import tree_sitter_python
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# Initialize Tree-sitter for modern python versions
LANG = tree_sitter.Language(tree_sitter_python.language())
parser = tree_sitter.Parser(LANG)

def github_get(url):
    while True:
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                return res.json()
            elif res.status_code in [403, 429]:
                reset_time = int(res.headers.get("X-RateLimit-Reset", time.time() + 60))
                sleep_time = max(0, reset_time - time.time()) + 1
                print(f"Rate limited. Sleeping for {sleep_time} seconds...")
                time.sleep(sleep_time)
            elif res.status_code == 404:
                return None
            else:
                print(f"Error {res.status_code}: {res.text}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Network error: {e}. Retrying in 5 seconds...")
            time.sleep(5)

def fetch_raw_file(repo, sha, file_path):
    url = f"https://raw.githubusercontent.com/{repo}/{sha}/{file_path}"
    while True:
        try:
            res = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"}, timeout=15)
            if res.status_code == 200:
                return res.text
            return None
        except requests.exceptions.RequestException as e:
            print(f"Network error: {e}. Retrying in 5 seconds...")
            time.sleep(5)

def find_target_node(node, target_row):
    """
    DFS to find the narrowest function or class definition wrapping the target_row.
    target_row is 0-indexed.
    """
    best_match = None
    
    if node.start_point.row <= target_row <= node.end_point.row:
        if node.type in ["function_definition", "class_definition"]:
            best_match = node
            
        for child in node.children:
            child_match = find_target_node(child, target_row)
            if child_match:
                best_match = child_match
                
    return best_match

def process_dataset(input_file, output_file):
    if not os.path.exists(input_file):
        print(f"Input file {input_file} not found. Ensure extraction has run.")
        return
        
    with open(input_file, "r", encoding="utf-8") as f:
        dataset = json.load(f)
        
    sha_cache = {}
    file_cache = {}
    
    output_data = []
    
    print(f"Found {len(dataset)} samples to chunk.")
    
    for i, sample in enumerate(dataset):
        print(f"Processing sample {i+1}/{len(dataset)}: {sample['chunk_id']}")
        
        repo = sample["repo"]
        file_path = sample["file"]
        violations = sample.get("violations", [])
        if not violations:
            output_data.append(sample)
            continue
            
        target_line = violations[0].get("line")
        if target_line is None:
            output_data.append(sample)
            continue
            
        chunk_id = sample.get("chunk_id", "")
        pr_match = re.search(r"PR(\d+)_", chunk_id)
        if not pr_match:
            print("Could not parse PR number. Skipping AST.")
            output_data.append(sample)
            continue
            
        pr_number = pr_match.group(1)
        
        cache_key = f"{repo}_{pr_number}"
        if cache_key not in sha_cache:
            pr_data = github_get(f"https://api.github.com/repos/{repo}/pulls/{pr_number}")
            if pr_data and "head" in pr_data:
                sha_cache[cache_key] = pr_data["head"]["sha"]
            else:
                sha_cache[cache_key] = None
            # slight sleep to be kind to the api
            time.sleep(0.1)
                
        sha = sha_cache[cache_key]
        if not sha:
            print(f"Could not get HEAD SHA for PR {pr_number}. Skipping AST.")
            output_data.append(sample)
            continue
            
        file_key = f"{repo}_{sha}_{file_path}"
        if file_key not in file_cache:
            source = fetch_raw_file(repo, sha, file_path)
            file_cache[file_key] = source
            
        source_code = file_cache[file_key]
        
        ast_context = None
        if source_code:
            tree = parser.parse(bytes(source_code, "utf8"))
            target_row = target_line - 1
            node = find_target_node(tree.root_node, target_row)
            
            lines = source_code.split('\n')
            
            if node:
                start_row = node.start_point.row
                end_row = node.end_point.row
                context_code = '\n'.join(lines[start_row:end_row+1])
                
                # Extract name if possible (works for both func & class in typical py grammar)
                name_node = node.child_by_field_name("name")
                name = name_node.text.decode("utf8") if name_node else ""
                
                ast_context = {
                    "type": node.type,
                    "name": name,
                    "start_line": start_row + 1,
                    "end_line": end_row + 1,
                    "code": context_code,
                    "fallback": False
                }
            else:
                # Fallback: sliding window +/- 10 lines
                start_row = max(0, target_row - 10)
                end_row = min(len(lines) - 1, target_row + 10)
                context_code = '\n'.join(lines[start_row:end_row+1])
                ast_context = {
                    "type": "sliding_window",
                    "name": "",
                    "start_line": start_row + 1,
                    "end_line": end_row + 1,
                    "code": context_code,
                    "fallback": True
                }
                
        if ast_context:
            sample["ast_context"] = ast_context
            
        output_data.append(sample)
        
        # Save incrementally
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)

    print(f"\nFinished processing. Saved chunks to {output_file}")

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="AST Chunking tool for arbitrary repos")
    arg_parser.add_argument("repo", help="Target repository (e.g. pallets/flask)")
    args = arg_parser.parse_args()
    
    repo_prefix = args.repo.split("/")[-1]
    input_file = f"{repo_prefix}_prs.json"
    output_file = f"{repo_prefix}_ast_chunks.json"
    
    process_dataset(input_file, output_file)
