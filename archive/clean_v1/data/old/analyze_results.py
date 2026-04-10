import json
import os
from pathlib import Path

base_dir = r"c:\Users\budhi\Documents\IITM\DSAI Lab\Group-1-DS-and-AI-Lab-Project\results"

# Collect all data
results = {}
for version in ["experiment_results_v1", "experiment_results_v2"]:
    results[version] = {}
    version_path = os.path.join(base_dir, version)
    
    for temp_dir in os.listdir(version_path):
        temp_path = os.path.join(version_path, temp_dir)
        if os.path.isdir(temp_path):
            results[version][temp_dir] = {}
            
            for file in os.listdir(temp_path):
                if file.endswith('.json'):
                    file_path = os.path.join(temp_path, file)
                    with open(file_path, 'r') as f:
                        data = json.load(open(file_path, 'r', encoding='utf-8'))
                    
                    k_value = file.replace('llm_results_k=', '').replace('.json', '')
                    results[version][temp_dir][k_value] = {
                        'accuracy': data['metrics_raw']['accuracy'],
                        'valid_rate': data['parse_quality']['valid_rate'],
                        'num_samples': data['num_samples'],
                        'per_class': data['metrics_raw']['per_class']
                    }

# Print summary table
print("=" * 80)
print("EXPERIMENT RESULTS SUMMARY")
print("=" * 80)

for version in sorted(results.keys()):
    print(f"\n{version.upper()}")
    print("-" * 80)
    for temp in sorted(results[version].keys()):
        print(f"\n  {temp}:")
        print(f"  {'K Value':<10} {'Accuracy':<15} {'Valid Rate':<15} {'Samples':<10}")
        print(f"  {'-'*50}")
        for k in sorted(results[version][temp].keys(), key=lambda x: int(x)):
            acc = results[version][temp][k]['accuracy']
            vrate = results[version][temp][k]['valid_rate']
            samples = results[version][temp][k]['num_samples']
            print(f"  {k:<10} {acc:<15.4f} {vrate:<15.4f} {samples:<10}")

# Export to JSON for processing
print("\n\nDetailed metrics:")
with open(r"c:\Users\budhi\Documents\IITM\DSAI Lab\Group-1-DS-and-AI-Lab-Project\results_summary.json", 'w') as f:
    json.dump(results, f, indent=2)

print("Saved to results_summary.json")
