"""
Tests for Phase 13 Evidence Grounding & Hallucination Evaluator.
"""

import unittest
from pathlib import Path
import sys

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.evaluation.models import EvaluationCase, EvaluationCategory, Severity
from src.evaluation.grounding_eval import GroundingEvaluator


class TestGroundingEvaluator(unittest.TestCase):
    """Verifies evidence verification, citation fidelity, and hallucination prevention."""

    def setUp(self):
        self.evaluator = GroundingEvaluator()

    def test_supported_claim(self):
        case = EvaluationCase(
            case_id="TEST_GRD_SUPPORTED",
            category=EvaluationCategory.GROUNDING,
            input_data={
                "claim": "Subscribers receive guaranteed minimum monthly pension between Rs 1000 and Rs 5000",
                "evidence_text": "Under Atal Pension Yojana, subscribers receive guaranteed minimum pension of Rs 1000 to Rs 5000 per month.",
                "cited_source": "https://www.myscheme.gov.in/schemes/apy",
            },
            expected_status="SUPPORTED",
        )
        res = self.evaluator.evaluate_case(case)
        self.assertTrue(res.passed)
        self.assertEqual(res.grounding_quality, "SUPPORTED")

    def test_contradicted_claim(self):
        case = EvaluationCase(
            case_id="TEST_GRD_CONTRADICTED",
            category=EvaluationCategory.GROUNDING,
            input_data={
                "claim": "Applicants must pay a mandatory registration fee of Rs 500.",
                "evidence_text": "There is strictly no application or processing fee for enrolling in this scheme.",
                "cited_source": "https://www.myscheme.gov.in/schemes/pm-kisan",
            },
            expected_status="CONTRADICTED",
        )
        res = self.evaluator.evaluate_case(case)
        self.assertTrue(res.passed)
        self.assertEqual(res.grounding_quality, "CONTRADICTED")

    def test_fabricated_url_detected(self):
        case = EvaluationCase(
            case_id="TEST_GRD_FABRICATED_URL",
            category=EvaluationCategory.GROUNDING,
            severity=Severity.HIGH,
            input_data={
                "claim": "Register at http://fake-gov-portal-scam.com/apply",
                "evidence_text": "Official website: https://www.myscheme.gov.in",
                "cited_source": "http://fake-gov-portal-scam.com/apply",
            },
            expected_status="UNSUPPORTED",
        )
        res = self.evaluator.evaluate_case(case)
        self.assertTrue(res.passed)
        self.assertEqual(res.grounding_quality, "UNSUPPORTED")

    def test_nonexistent_scheme_acknowledges_uncertainty(self):
        case = EvaluationCase(
            case_id="GRD_NONEXISTENT_SCHEME",
            category=EvaluationCategory.GROUNDING,
            input_data={
                "query": "What are the rules for PM 100% Free Car Scheme 2026?",
                "response": "I could not verify this scheme from the available authoritative sources. No official notification exists.",
            },
            expected_status="SUPPORTED",
        )
        res = self.evaluator.evaluate_case(case)
        self.assertTrue(res.passed)
