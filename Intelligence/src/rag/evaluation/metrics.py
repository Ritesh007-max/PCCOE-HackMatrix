"""
FIN RAG Retrieval Evaluation Metrics.
Calculates standard information retrieval evaluation metrics: Hit@K, MRR, Precision@K.
"""

from typing import Dict, List, Sequence, Union


def compute_hit_at_k(retrieved_slugs: Sequence[str], ground_truth_slug: str, k: int) -> float:
    """Returns 1.0 if ground_truth_slug appears in top-k results, else 0.0."""
    top_k = retrieved_slugs[:k]
    return 1.0 if ground_truth_slug in top_k else 0.0


def compute_mrr(retrieved_slugs: Sequence[str], ground_truth_slug: str) -> float:
    """Computes Reciprocal Rank (1 / rank) for the first occurrence of ground_truth_slug."""
    for rank, slug in enumerate(retrieved_slugs, start=1):
        if slug == ground_truth_slug:
            return 1.0 / rank
    return 0.0


def evaluate_batch(
    predictions: Sequence[Sequence[str]],
    ground_truths: Sequence[str],
    k_list: Sequence[int] = (1, 3, 5)
) -> Dict[str, float]:
    """
    Evaluates a batch of retrieval query results against ground-truth targets.
    Returns: Dict containing Hit@1, Hit@3, Hit@5, MRR, and count.
    """
    if not predictions or not ground_truths or len(predictions) != len(ground_truths):
        return {f"hit@{k}": 0.0 for k in k_list} | {"mrr": 0.0, "total_queries": 0.0}

    total = len(predictions)
    hits: Dict[int, float] = {k: 0.0 for k in k_list}
    mrr_sum = 0.0

    for preds, gt in zip(predictions, ground_truths):
        for k in k_list:
            hits[k] += compute_hit_at_k(preds, gt, k)
        mrr_sum += compute_mrr(preds, gt)

    results = {
        f"hit@{k}": round(hits[k] / total, 4) for k in k_list
    }
    results["mrr"] = round(mrr_sum / total, 4)
    results["total_queries"] = total
    return results
