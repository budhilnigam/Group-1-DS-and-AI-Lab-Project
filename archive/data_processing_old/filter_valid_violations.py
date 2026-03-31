import sys
import json
import argparse
import os

# The exact 5 categories required by your dataset schema.
ALLOWED_CATEGORIES = {
    "naming_convention",
    "unused_import",
    "mutable_default",
    "indentation",
    "documentation_formatting",
    "guideline" # Including this just in case your LLM labels it as "guideline" instead of "documentation_formatting"
}

def main():
    parser = argparse.ArgumentParser(description="Filter labeled chunks to strictly keep the 5 main violation categories.")
    parser.add_argument("repo_name", help="Repository prefix used for the file name (e.g. 'django' or 'flask')")
    
    args = parser.parse_args()
    repo_name = args.repo_name
    
    # Dynamically build file targets based on the passed repository prefix
    input_file = f"{repo_name}_labeled_chunks.json"
    output_file = f"{repo_name}_final_eval_dataset.json"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found. Ensure static_filter.py has run on this repository.")
        sys.exit(1)
        
    with open(input_file, 'r', encoding='utf-8') as f:
        dataset = json.load(f)
        
    filtered_dataset = []
    dropped_count = 0
    
    for sample in dataset:
        violations = sample.get("violations", [])
        if not violations:
            dropped_count += 1
            continue
            
        v_type = violations[0].get("type", "").strip()
        
        # We strictly check if the labeled type is inside the 5 allowed categories.
        # This will automatically DROP anything left as an empty string ("")
        if v_type in ALLOWED_CATEGORIES:
            filtered_dataset.append(sample)
        else:
            dropped_count += 1
            
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_dataset, f, indent=2)
        
    print(f"Processed: {len(dataset)}")
    print(f"Dropped (Blanks/Irrelevant): {dropped_count}")
    print(f"Kept (Valid 5 Categories): {len(filtered_dataset)}")
    print(f"====>\nSuccessfully saved strictly categorized PRs to {output_file}")

if __name__ == "__main__":
    main()
