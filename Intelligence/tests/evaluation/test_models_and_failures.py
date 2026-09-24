"""
Tests for Phase 13 Evaluation Models, Failure Taxonomy, and Metric Aggregation.
"""

import unittest
from pathlib import Path
import sys

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.evaluation.models import (
    EvaluationCase,
    EvaluationResult,
    EvaluationRun,
    Severity,
    EvaluationCategory,
)
from src.evaluation.failures import FailureType, classify_failure, DEFAULT_SEVERITY_MAPPING
from src.evaluation.metrics import (
    compute_hit_at_k,
    compute_mrr,
    compute_precision_at_k,
    compute_recall_at_k,
    compute_f1,
    MetricAggregator,
)


class TestModelsAndFailures(unittest.TestCase):
    """Test suite for evaluation data models, failure taxonomy, and metrics."""

    def test_evaluation_case_serialization(self):
        case = EvaluationCase(
            case_id="TEST_001",
            category=EvaluationCategory.ELIGIBILITY,
            input_data={"age": 25},
            expected_output="PASS",
            expected_status="PASS",
            expected_scheme_id="apy",
            severity=Severity.HIGH,
            tags=["unit_test", "age_check"],
        )
        d = case.to_dict()
        self.assertEqual(d["case_id"], "TEST_001")
        self.assertEqual(d["category"], "ELIGIBILITY")
        self.assertEqual(d["severity"], "HIGH")

        reconstructed = EvaluationCase.from_dict(d)
        self.assertEqual(reconstructed.case_id, "TEST_001")
        self.assertEqual(reconstructed.category, EvaluationCategory.ELIGIBILITY)
        self.assertEqual(reconstructed.severity, Severity.HIGH)

    def test_failure_taxonomy_complete(self):
        """Verifies that all 15 required failure taxonomy types are present."""
        expected_failures = {
            "RETRIEVAL_FAILURE",
            "EXTRACTION_FAILURE",
            "NORMALIZATION_FAILURE",
            "RULE_FAILURE",
            "GROUNDING_FAILURE",
            "HALLUCINATION_FAILURE",
            "AUTHORITY_FAILURE",
            "TEMPORAL_FAILURE",
            "SECURITY_FAILURE",
            "INJECTION_FAILURE",
            "POLICY_POISONING_FAILURE",
            "API_SECURITY_FAILURE",
            "MULTILINGUAL_FAILURE",
            "GUIDANCE_FAILURE",
            "VERSIONING_FAILURE",
        }
        actual_failures = {f.value for f in FailureType}
        self.assertEqual(expected_failures, actual_failures)
        self.assertEqual(len(FailureType), 15)

    def test_classify_failure_helper(self):
        record = classify_failure(
            failure_type=FailureType.INJECTION_FAILURE,
            details="Direct prompt injection attempted",
            context={"payload": "Ignore all rules"},
        )
        self.assertEqual(record["failure_type"], "INJECTION_FAILURE")
        self.assertEqual(record["severity"], "CRITICAL")
        self.assertIn("Direct prompt injection", record["details"])

    def test_metrics_computation(self):
        # Hit@K
        retrieved = ["slug_1", "slug_2", "slug_3"]
        self.assertEqual(compute_hit_at_k(retrieved, "slug_1", 1), 1.0)
        self.assertEqual(compute_hit_at_k(retrieved, "slug_2", 1), 0.0)
        self.assertEqual(compute_hit_at_k(retrieved, "slug_2", 3), 1.0)

        # MRR
        self.assertEqual(compute_mrr(retrieved, "slug_1"), 1.0)
        self.assertEqual(compute_mrr(retrieved, "slug_2"), 0.5)
        self.assertEqual(compute_mrr(retrieved, "slug_missing"), 0.0)

        # Precision & Recall
        relevant = ["slug_1", "slug_3"]
        self.assertEqual(compute_precision_at_k(retrieved, relevant, 2), 0.5)
        self.assertEqual(compute_recall_at_k(retrieved, relevant, 3), 1.0)

        # F1
        self.assertAlmostEqual(compute_f1(1.0, 1.0), 1.0)
        self.assertAlmostEqual(compute_f1(0.5, 0.5), 0.5)
        self.assertEqual(compute_f1(0.0, 0.0), 0.0)
