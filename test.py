# This file should load the test_chunks.json, then perform each query and log the ids of the chunks returned, then for each query calculate the precision and recall of each query compared to the relevent chunk ids from test_chunks.json

import json
from query import perform_vector_search
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

def load_test_chunks():
    with open("test_chunks.json", "r") as f:
        return json.load(f)

def precision(retrieved_chunk_ids, relevant_chunk_ids):
    r = set(relevant_chunk_ids)
    t = set(retrieved_chunk_ids)
    if not t:
        return 0.0
    return len(t & r) / len(t)

def recall(retrieved_chunk_ids, relevant_chunk_ids):
    r = set(relevant_chunk_ids)
    t = set(retrieved_chunk_ids)
    if not r:
        return 0.0
    return len(t & r) / len(r)

def f1_score(p, r):
    if p + r == 0:
        return 0.0
    return 2 * p * r / (p + r)

def mrr(retrieved_chunk_ids, relevant_chunk_ids):
    rel = set(relevant_chunk_ids)
    for rank, chunk_id in enumerate(retrieved_chunk_ids, start=1):
        if chunk_id in rel:
            return 1.0 / rank
    return 0.0

test_chunks = load_test_chunks()
# for query in test_chunks:
#     relevant_chunk_ids = query["relevant_chunk_ids"]
#     retrieved_chunks = perform_vector_search(query["query"], relevance_limit=0)
#     retrieved_chunk_ids = [str(chunk[0]) for chunk in retrieved_chunks]
#     p = precision(retrieved_chunk_ids, relevant_chunk_ids)
#     r = recall(retrieved_chunk_ids, relevant_chunk_ids)
#     results.append({
#         "query": query["query"],
#         "relevant_chunk_ids": relevant_chunk_ids,
#         "retrieved_chunk_ids": retrieved_chunk_ids,
#         "precision": p,
#         "recall": r,
#         "f1_score": f1_score(p, r),
#         "mrr": mrr(retrieved_chunk_ids, relevant_chunk_ids)
#     })
# print(results)

# print(f"Average Precision: {sum([result['precision'] for result in results]) / len(results)}")
# print(f"Average Recall: {sum([result['recall'] for result in results]) / len(results)}")
# print(f"Average F1 Score: {sum([result['f1_score'] for result in results]) / len(results)}")
# print(f"Average MRR: {sum([result['mrr'] for result in results]) / len(results)}")

# 2D grids: rows = relevance threshold, columns = k (for heatmaps)
relevance_limits = [0.3, 0.31, 0.32, 0.33, 0.34, 0.35, 0.36, 0.37, 0.38, 0.39, 0.4, 0.41, 0.42, 0.43, 0.44, 0.45, 0.46, 0.47, 0.48, 0.49, 0.5]
k_values = [2, 3, 4, 5, 6, 7, 8, 9, 10]

precision_scores = pd.DataFrame(index=relevance_limits, columns=k_values, dtype=float)
recall_scores = pd.DataFrame(index=relevance_limits, columns=k_values, dtype=float)
f1_scores = pd.DataFrame(index=relevance_limits, columns=k_values, dtype=float)
mrr_scores = pd.DataFrame(index=relevance_limits, columns=k_values, dtype=float)

for relevance_limit in relevance_limits:
    for k in k_values:
        results = []
        for query in test_chunks:
            retrieved_chunks = perform_vector_search(query["query"], relevance_limit=relevance_limit, k=k)
            retrieved_chunk_ids = [str(chunk[0]) for chunk in retrieved_chunks]
            p = precision(retrieved_chunk_ids, query["relevant_chunk_ids"])
            r = recall(retrieved_chunk_ids, query["relevant_chunk_ids"])
            f1 = f1_score(p, r)
            mrr_val = mrr(retrieved_chunk_ids, query["relevant_chunk_ids"])
            results.append({
                "query": query["query"],
                "relevant_chunk_ids": query["relevant_chunk_ids"],
                "retrieved_chunk_ids": retrieved_chunk_ids,
                "precision": p,
                "recall": r,
                "f1_score": f1,
                "mrr": mrr_val
            })
        
        n = len(results)
        precision_scores.loc[relevance_limit, k] = sum(r["precision"] for r in results) / n
        recall_scores.loc[relevance_limit, k] = sum(r["recall"] for r in results) / n
        f1_scores.loc[relevance_limit, k] = sum(r["f1_score"] for r in results) / n
        mrr_scores.loc[relevance_limit, k] = sum(r["mrr"] for r in results) / n

# turn the dataframes into heatmaps and save these heatmaps to png files
plt.figure(figsize=(10, 10))
sns.heatmap(precision_scores, annot=True, fmt=".2f")
plt.savefig("precision_scores_1.png")
plt.close()
plt.figure(figsize=(10, 10))
sns.heatmap(recall_scores, annot=True, fmt=".2f")
plt.savefig("recall_scores_1.png")
plt.close()
plt.figure(figsize=(10, 10))
sns.heatmap(f1_scores, annot=True, fmt=".2f")
plt.savefig("f1_scores_1.png")
plt.close()
plt.figure(figsize=(10, 10))
sns.heatmap(mrr_scores, annot=True, fmt=".2f")
plt.savefig("mrr_scores_1.png")
plt.close()
