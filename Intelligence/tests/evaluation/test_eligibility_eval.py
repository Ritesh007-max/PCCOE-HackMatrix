"""
Tests for Phase 13 Eligibility and Benefit Calculation Evaluator.
"""

import unittest
from pathlib import Path
import sys

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.evaluation.models import EvaluationCase, EvaluationCategory, Severity
from src.evaluation.eligibility_eval import EligibilityEvaluator


class TestEligibilityEvaluator(unittest.TestCase):
    """Verifies statutory deterministic evaluation and invariant preservation."""

    def setUp(self):
        self.evaluator = EligibilityEvaluator()

    def test_eligible_case_pass(self):
        case = EvaluationCase(
            case_id="TEST_ELIG_PASS",
            category=EvaluationCategory.ELIGIBILITY,
            expected_scheme_id="apy",
            input_data={"age": 28, "has_bank_account": True, "is_taxpayer": False},
            expected_status="PASS",
        )
        res = self.evaluator.evaluate_case(case)
        self.assertTrue(res.passed)
        self.assertEqual(res.actual_output["status"], "PASS")

    def test_invariant_1_missing_info_never_pass(self):
        """Invariant 1: Missing information must never evaluate to PASS."""
        case = EvaluationCase(
            case_id="TEST_INVARIANT_1",
            category=EvaluationCategory.ELIGIBILITY,
            expected_scheme_id="apy",
            input_data={"has_bank_account": True, "is_taxpayer": False},
            expected_status="UNKNOWN",
        )
        res = self.evaluator.evaluate_case(case)
        self.assertTrue(res.passed)
        self.assertEqual(res.actual_output["status"], "UNKNOWN")

    def test_invariant_2_conflicted_facts_trigger_review(self):
        """Invariant 2: Contradictory evidence must trigger REVIEW, not silent PASS/FAIL."""
        case = EvaluationCase(
            case_id="TEST_INVARIANT_2",
            category=EvaluationCategory.ELIGIBILITY,
            expected_scheme_id="apy",
            input_data={"age": 28, "has_bank_account": True, "is_taxpayer": False, "_conflicts": ["is_taxpayer"]},
            expected_status="REVIEW",
        )
        res = self.evaluator.evaluate_case(case)
        self.assertTrue(res.passed)
        self.assertEqual(res.actual_output["status"], "REVIEW")

    def test_benefit_calculation_determinism(self):
        res = self.evaluator.evaluate_benefit_calculation(
            scheme_id="pm_kisan",
            applicant_facts={"is_farmer": True},
            expected_min_amount=6000.0,
            expected_max_amount=6000.0,
        )
        self.assertTrue(res["passed"])
        self.assertEqual(res["monetary_value"], 6000.0)
        self.assertEqual(res["frequency"], "ANNUAL")
