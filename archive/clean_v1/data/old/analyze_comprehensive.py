import json
import os

base_dir = r"c:\Users\budhi\Documents\IITM\DSAI Lab\Group-1-DS-and-AI-Lab-Project\results"

def extract_all_metrics():
    all_data = {'v1': {}, 'v2': {}}
    
    for version in ["experiment_results_v1", "experiment_results_v2"]:
        version_key = 'v1' if 'v1' in version else 'v2'
        version_path = os.path.join(base_dir, version)
        
        for temp_dir in sorted(os.listdir(version_path)):
            temp_path = os.path.join(version_path, temp_dir)
            if os.path.isdir(temp_path):
                all_data[version_key][temp_dir] = {}
                
                for file in sorted(os.listdir(temp_path)):
                    if file.endswith('.json'):
                        file_path = os.path.join(temp_path, file)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        k_value = int(file.replace('llm_results_k=', '').replace('.json', ''))
                        
                        metrics = {
                            'model': data['model'],
                            'num_samples': data['num_samples'],
                            'valid_count': data['parse_quality']['valid_count'],
                            'valid_rate': data['parse_quality']['valid_rate'],
                            'accuracy': data['metrics_raw']['accuracy'],
                            'per_class': {}
                        }
                        
                        for class_name, class_metrics in data['metrics_raw']['per_class'].items():
                            metrics['per_class'][class_name] = {
                                'precision': class_metrics.get('precision', 0),
                                'recall': class_metrics.get('recall', 0),
                                'f1': class_metrics.get('f1', 0),
                                'support': class_metrics.get('support', 0)
                            }
                        
                        all_data[version_key][temp_dir][k_value] = metrics
    
    return all_data

def print_comprehensive_report(all_data):
    print("\n" + "="*100)
    print("COMPREHENSIVE EXPERIMENT RESULTS REPORT")
    print("="*100)
    
    print("\nOBJECTIVE:")
    print("Evaluate the RAG-based code review system using gpt-oss-20b model")
    print("- Experiment V1: Initial 12-sample cohort")
    print("- Experiment V2: Expanded 35-sample cohort")
    
    print("\nCONFIGURATION:")
    print("- Model: openai/gpt-oss-20b (via Groq API)")
    print("- Retrieval Backend: FAISS Dense Embeddings")
    print("- Generation Backend: Groq LLM Inference")
    print("- Groq RPM Limit: 30")
    print("- Min Interval: 2.0 seconds")
    print("- Max Retries: 3")
    
    print("\n" + "="*100)
    print("EXPERIMENTS V1 (12 SAMPLES)")
    print("="*100)
    for temp in sorted(all_data['v1'].keys()):
        print(f"\nTemperature: {temp}")
        print(f"{'K Value':<10} {'Accuracy':<12} {'Valid Rate':<12} {'Valid Count':<12}")
        print("-" * 50)
        for k in sorted(all_data['v1'][temp].keys()):
            m = all_data['v1'][temp][k]
            print(f"{k:<10} {m['accuracy']:<12.4f} {m['valid_rate']:<12.4f} {m['valid_count']:<12}")
    
    print("\n" + "="*100)
    print("EXPERIMENTS V2 (35 SAMPLES)")
    print("="*100)
    for temp in sorted(all_data['v2'].keys()):
        print(f"\nTemperature: {temp}")
        print(f"{'K Value':<10} {'Accuracy':<12} {'Valid Rate':<12} {'Valid Count':<12}")
        print("-" * 50)
        for k in sorted(all_data['v2'][temp].keys()):
            m = all_data['v2'][temp][k]
            print(f"{k:<10} {m['accuracy']:<12.4f} {m['valid_rate']:<12.4f} {m['valid_count']:<12}")
    
    print("\n" + "="*100)
    print("PER-CLASS PERFORMANCE (V2, Temp=0.1, K=1)")
    print("="*100)
    print(f"{'Class':<30} {'Precision':<12} {'Recall':<12} {'F1 Score':<12} {'Support':<10}")
    print("-" * 80)
    for class_name in sorted(all_data['v2']['temp=0.1'][1]['per_class'].keys()):
        metrics = all_data['v2']['temp=0.1'][1]['per_class'][class_name]
        print(f"{class_name:<30} {metrics['precision']:<12.4f} {metrics['recall']:<12.4f} {metrics['f1']:<12.4f} {metrics['support']:<10}")
    
    print("\n" + "="*100)
    print("KEY OBSERVATIONS")
    print("="*100)
    
    all_configs = []
    for version_key in ['v1', 'v2']:
        for temp in all_data[version_key]:
            for k in all_data[version_key][temp]:
                all_configs.append({
                    'version': version_key,
                    'temp': temp,
                    'k': k,
                    'accuracy': all_data[version_key][temp][k]['accuracy'],
                    'valid_rate': all_data[version_key][temp][k]['valid_rate']
                })
    
    best_config = max(all_configs, key=lambda x: x['accuracy'])
    print(f"\nBest Configuration: {best_config['version']} - temp={best_config['temp']}, k={best_config['k']}")
    print(f"  Accuracy: {best_config['accuracy']:.4f}")
    print(f"  Valid Rate: {best_config['valid_rate']:.4f}")
    
    v1_avg_acc = sum(all_data['v1'][t][k]['accuracy'] for t in all_data['v1'] for k in all_data['v1'][t]) / sum(len(all_data['v1'][t]) for t in all_data['v1'])
    v2_avg_acc = sum(all_data['v2'][t][k]['accuracy'] for t in all_data['v2'] for k in all_data['v2'][t]) / sum(len(all_data['v2'][t]) for t in all_data['v2'])
    
    print(f"\nV1 vs V2 Comparison:")
    print(f"  V1 Average Accuracy: {v1_avg_acc:.4f}")
    print(f"  V2 Average Accuracy: {v2_avg_acc:.4f}")
    print(f"  Improvement: {((v2_avg_acc - v1_avg_acc) / v1_avg_acc * 100):+.2f}%")

all_data = extract_all_metrics()
print_comprehensive_report(all_data)

with open(r"c:\Users\budhi\Documents\IITM\DSAI Lab\Group-1-DS-and-AI-Lab-Project\results_comprehensive.json", 'w') as f:
    json_data = {}
    for version_key in all_data:
        json_data[version_key] = {}
        for temp in all_data[version_key]:
            json_data[version_key][temp] = {}
            for k in all_data[version_key][temp]:
                json_data[version_key][temp][str(k)] = all_data[version_key][temp][k]
    json.dump(json_data, f, indent=2)

print("\n\nResults saved to results_comprehensive.json")
