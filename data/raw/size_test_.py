# print number of items in the json list in retrieval_corpus.json
import json

with open('.\\data\\raw\\dataset_v2\\evaluation_dataset.json', 'r') as f:
    data = json.load(f)
    print(len(data))