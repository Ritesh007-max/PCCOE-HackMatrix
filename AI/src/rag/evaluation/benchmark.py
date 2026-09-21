"""
PolicySetu Retrieval Benchmark Runner.
Executes ground-truth test queries through the hybrid retriever, computes
Hit@1, Hit@3, Hit@5, and MRR, and produces structured evaluation reports.
"""

from typing import Any, Dict, List, Optional
from ..retriever import HybridRetriever
from ..models import RetrievalQuery
from .test_cases import EVALUATION_TEST_CASES, RetrievalTestCase
from .metrics import evaluate_batch, compute_hit_at_k, compute_mrr


class RetrievalBenchmarkRunner:
    """
    Executes offline retrieval evaluation and reports factual Hit@K and MRR metrics.
    Never fabricates benchmark figures.
    """

    def __init__(self, retriever: HybridRetriever):
        self.retriever = retriever

    def run_benchmark(
        self,
        test_cases: Optional[List[RetrievalTestCase]] = None,
        top_k: int = 10
    ) -> Dict[str, Any]:
        cases = test_cases or EVALUATION_TEST_CASES
        if not cases:
            return {"status": "NO_TEST_CASES", "total_queries": 0}

        predictions: List[List[str]] = []
        ground_truths: List[str] = []
        breakdown_by_type: Dict[str, Dict[str, Any]] = {}
        per_query_results: List[Dict[str, Any]] = []

        for case in cases:
            q = RetrievalQuery(
                query_text=case.query_text,
                language=case.language,
                top_k=top_k,
                state_filter=case.state_filter
            )

            # Retrieve scheme results
            scheme_results = self.retriever.retrieve_schemes(q)
            pred_slugs = [s.scheme_slug for s in scheme_results]

            predictions.append(pred_slugs)
            ground_truths.append(case.expected_scheme_slug)

            h1 = compute_hit_at_k(pred_slugs, case.expected_scheme_slug, 1)
            h3 = compute_hit_at_k(pred_slugs, case.expected_scheme_slug, 3)
            h5 = compute_hit_at_k(pred_slugs, case.expected_scheme_slug, 5)
            recip_rank = compute_mrr(pred_slugs, case.expected_scheme_slug)

            per_query_results.append({
                "query_id": case.query_id,
                "query_text": case.query_text,
                "expected_slug": case.expected_scheme_slug,
                "predicted_slugs": pred_slugs[:5],
                "hit@1": h1,
                "hit@3": h3,
                "hit@5": h5,
                "mrr": recip_rank,
                "query_type": case.query_type
            })

            # Tally by type
            q_type = case.query_type
            if q_type not in breakdown_by_type:
                breakdown_by_type[q_type] = {"predictions": [], "ground_truths": []}
            breakdown_by_type[q_type]["predictions"].append(pred_slugs)
            breakdown_by_type[q_type]["ground_truths"].append(case.expected_scheme_slug)

        # Overall metrics
        overall_metrics = evaluate_batch(predictions, ground_truths, k_list=(1, 3, 5))

        # Per-type metrics
        type_metrics: Dict[str, Dict[str, float]] = {}
        for q_type, data in breakdown_by_type.items():
            type_metrics[q_type] = evaluate_batch(
                data["predictions"],
                data["ground_truths"],
                k_list=(1, 3, 5)
            )

        return {
            "status": "SUCCESS",
            "overall": overall_metrics,
            "by_query_type": type_metrics,
            "detailed_queries": per_query_results,
        }
