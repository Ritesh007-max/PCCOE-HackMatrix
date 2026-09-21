"""
PolicySetu Retrieval Evaluation Package.
Exports benchmark runners, ground-truth test cases, and evaluation metrics.
"""

from .metrics import compute_hit_at_k, compute_mrr, evaluate_batch
from .test_cases import EVALUATION_TEST_CASES, RetrievalTestCase
from .benchmark import RetrievalBenchmarkRunner

__all__ = [
    "compute_hit_at_k",
    "compute_mrr",
    "evaluate_batch",
    "EVALUATION_TEST_CASES",
    "RetrievalTestCase",
    "RetrievalBenchmarkRunner",
]
