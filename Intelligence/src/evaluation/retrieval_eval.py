"""
FIN Retrieval Quality & Adversarial Retrieval Evaluator.
Measures Hit@1, Hit@3, Hit@5, MRR, Precision@K, and Recall@K over English, Hindi, Hinglish, and adversarial queries.
"""

from pathlib import Path
import json
import time
from typing import Any, Dict, List, Optional

import sys
_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.evaluation.models import EvaluationCase, EvaluationResult, Severity
from src.evaluation.failures import FailureType
from src.evaluation.metrics import (
    compute_hit_at_k,
    compute_mrr,
    compute_precision_at_k,
    compute_recall_at_k,
    MetricAggregator,
)
from src.rag.retriever import HybridRetriever
from src.rag.models import RetrievalQuery


class RetrievalEvaluator:
    """
    Offline and online evaluation harness for information retrieval quality.
    Evaluates against golden test cases without fabricating success metrics.
    """

    def __init__(self, retriever: Optional[HybridRetriever] = None):
        if retriever is None:
            from src.rag.config import RAGConfig
            from src.rag.embeddings import DeterministicMockEmbeddingModel
            from src.rag.ingestion import RAGIngestionPipeline
            config = RAGConfig(use_faiss=False, embedding_dimension=32)
            retriever = HybridRetriever(
                config=config,
                embedding_model=DeterministicMockEmbeddingModel(dimension=32),
            )
            try:
                ingestion = RAGIngestionPipeline(config=config)
                docs = ingestion.load_primary_schemes(
                    limit=25,
                    include_slugs=["apy", "pm-kisan", "pmmvy", "ab-pmjay", "pm-svanidhi", "mj-fapm", "aag", "aasgsmse", "108easuk", "25-ciss"],
                )
                if docs:
                    retriever.index_documents(docs)
            except Exception:
                pass
        self.retriever = retriever

    def evaluate_case(self, case: EvaluationCase, top_k: int = 5) -> EvaluationResult:
        """Evaluates a single retrieval case."""
        start_time = time.perf_counter()
        inp = case.input_data if isinstance(case.input_data, dict) else {"query": str(case.input_data)}
        query_text = inp.get("query", "")
        lang = inp.get("language", case.expected_language)
        state_filter = inp.get("state")
        expected_slug = case.expected_scheme_id or ""

        # Execute retrieval
        try:
            q = RetrievalQuery(
                query_text=query_text,
                language=lang,
                top_k=top_k,
                state_filter=state_filter,
            )
            results = self.retriever.retrieve_schemes(q)
            retrieved_slugs = [r.scheme_slug for r in results]
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000.0
            return EvaluationResult(
                case_id=case.case_id,
                passed=False,
                errors=[f"Retrieval error: {str(e)}"],
                latency_ms=latency,
                failure_type=FailureType.RETRIEVAL_FAILURE.value,
                severity=case.severity,
            )

        latency = (time.perf_counter() - start_time) * 1000.0
        h1 = compute_hit_at_k(retrieved_slugs, expected_slug, 1)
        h3 = compute_hit_at_k(retrieved_slugs, expected_slug, 3)
        h5 = compute_hit_at_k(retrieved_slugs, expected_slug, 5)
        mrr = compute_mrr(retrieved_slugs, expected_slug)
        prec = compute_precision_at_k(retrieved_slugs, [expected_slug], 5)
        rec = compute_recall_at_k(retrieved_slugs, [expected_slug], 5)

        passed = h5 > 0.0

        actual_output = {
            "retrieved_slugs": retrieved_slugs,
            "hit@1": h1,
            "hit@3": h3,
            "hit@5": h5,
            "mrr": mrr,
            "precision@5": prec,
            "recall@5": rec,
        }

        return EvaluationResult(
            case_id=case.case_id,
            passed=passed,
            actual_output=actual_output,
            expected_output=expected_slug,
            latency_ms=latency,
            failure_type=None if passed else FailureType.RETRIEVAL_FAILURE.value,
            severity=case.severity,
        )

    def evaluate_suite(
        self,
        cases: List[EvaluationCase],
        top_k: int = 5
    ) -> Dict[str, Any]:
        """Runs batch evaluation over a list of retrieval cases."""
        results: List[EvaluationResult] = []
        raw_metrics_list: List[Dict[str, Any]] = []

        for c in cases:
            res = self.evaluate_case(c, top_k=top_k)
            results.append(res)
            if res.actual_output and isinstance(res.actual_output, dict):
                raw_metrics_list.append(res.actual_output)

        aggregated = MetricAggregator.aggregate_retrieval(raw_metrics_list)
        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count

        return {
            "suite": "retrieval",
            "total_cases": len(cases),
            "passed": passed_count,
            "failed": failed_count,
            "metrics": aggregated,
            "results": [r.to_dict() for r in results],
        }
