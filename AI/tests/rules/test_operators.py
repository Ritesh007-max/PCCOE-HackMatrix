"""
Unit tests for PolicySetu deterministic operators and multi-valued status handling.
"""

import unittest
import sys
from pathlib import Path

_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from src.rules.operators import evaluate_operator, SUPPORTED_OPERATORS
from src.rules.models import RuleStatus
from src.rules.exceptions import InvalidOperatorError

class TestOperators(unittest.TestCase):

    def test_supported_operators_list(self):
        self.assertIn(">=", SUPPORTED_OPERATORS)
        self.assertIn("<=", SUPPORTED_OPERATORS)
        self.assertIn("between", SUPPORTED_OPERATORS)
        self.assertIn("in", SUPPORTED_OPERATORS)
        self.assertIn("is_true", SUPPORTED_OPERATORS)
        self.assertIn("is_false", SUPPORTED_OPERATORS)

    def test_numeric_comparisons(self):
        # Age >= 18
        status, _ = evaluate_operator(">=", 18, 18, "age")
        self.assertEqual(status, RuleStatus.PASS)
        status, _ = evaluate_operator(">=", 19, 18, "age")
        self.assertEqual(status, RuleStatus.PASS)
        status, _ = evaluate_operator(">=", 17, 18, "age")
        self.assertEqual(status, RuleStatus.FAIL)

        # Strictly greater than
        status, _ = evaluate_operator(">", 500000, 500000, "housing_loan_amount")
        self.assertEqual(status, RuleStatus.FAIL)
        status, _ = evaluate_operator(">", 500001, 500000, "housing_loan_amount")
        self.assertEqual(status, RuleStatus.PASS)

        # Less than or equal to: Income <= 100000
        status, _ = evaluate_operator("<=", 100000, 100000, "annual_family_income")
        self.assertEqual(status, RuleStatus.PASS)
        status, _ = evaluate_operator("<=", 100001, 100000, "annual_family_income")
        self.assertEqual(status, RuleStatus.FAIL)
        status, _ = evaluate_operator("<=", "₹99,999", 100000, "annual_family_income")
        self.assertEqual(status, RuleStatus.PASS)

    def test_between_range_operator(self):
        # Age between 18 and 40 (Atal Pension Yojana)
        range_val = {"min": 18, "max": 40}
        self.assertEqual(evaluate_operator("between", 17, range_val, "age")[0], RuleStatus.FAIL)
        self.assertEqual(evaluate_operator("between", 18, range_val, "age")[0], RuleStatus.PASS)
        self.assertEqual(evaluate_operator("between", 25, range_val, "age")[0], RuleStatus.PASS)
        self.assertEqual(evaluate_operator("between", 40, range_val, "age")[0], RuleStatus.PASS)
        self.assertEqual(evaluate_operator("between", 41, range_val, "age")[0], RuleStatus.FAIL)

    def test_string_equality(self):
        # State matching
        status, _ = evaluate_operator("=", "Assam", "Assam", "state")
        self.assertEqual(status, RuleStatus.PASS)
        status, _ = evaluate_operator("=", "assam ", "Assam", "state")
        self.assertEqual(status, RuleStatus.PASS)
        status, _ = evaluate_operator("=", "Bihar", "Assam", "state")
        self.assertEqual(status, RuleStatus.FAIL)

        # Gender matching
        status, _ = evaluate_operator("=", "Female", "Female", "gender")
        self.assertEqual(status, RuleStatus.PASS)
        status, _ = evaluate_operator("=", "Male", "Female", "gender")
        self.assertEqual(status, RuleStatus.FAIL)

    def test_membership_operators(self):
        # in / not_in
        categories = ["SC", "ST", "OBC"]
        self.assertEqual(evaluate_operator("in", "SC", categories, "social_category")[0], RuleStatus.PASS)
        self.assertEqual(evaluate_operator("in", "General", categories, "social_category")[0], RuleStatus.FAIL)
        self.assertEqual(evaluate_operator("not_in", "General", categories, "social_category")[0], RuleStatus.PASS)
        self.assertEqual(evaluate_operator("not_in", "SC", categories, "social_category")[0], RuleStatus.FAIL)

        # contains_any / contains_all
        self.assertEqual(evaluate_operator("contains_any", ["Aadhaar", "PAN"], ["Aadhaar", "Voter ID"])[0], RuleStatus.PASS)
        self.assertEqual(evaluate_operator("contains_any", ["Driving License"], ["Aadhaar", "Voter ID"])[0], RuleStatus.FAIL)
        self.assertEqual(evaluate_operator("contains_all", ["Aadhaar", "PAN"], ["Aadhaar", "PAN"])[0], RuleStatus.PASS)
        self.assertEqual(evaluate_operator("contains_all", ["Aadhaar"], ["Aadhaar", "PAN"])[0], RuleStatus.FAIL)

    def test_boolean_conditions(self):
        self.assertEqual(evaluate_operator("is_true", True, True, "has_bank_account")[0], RuleStatus.PASS)
        self.assertEqual(evaluate_operator("is_true", False, True, "has_bank_account")[0], RuleStatus.FAIL)
        self.assertEqual(evaluate_operator("is_false", False, False, "is_taxpayer")[0], RuleStatus.PASS)
        self.assertEqual(evaluate_operator("is_false", True, False, "is_taxpayer")[0], RuleStatus.FAIL)

    def test_missing_values_return_unknown(self):
        """Invariant: Missing values must produce UNKNOWN (never PASS, never FAIL)."""
        status, reason = evaluate_operator(">=", None, 18, "age")
        self.assertEqual(status, RuleStatus.UNKNOWN)
        self.assertNotEqual(status, RuleStatus.PASS)
        self.assertNotEqual(status, RuleStatus.FAIL)

        status, _ = evaluate_operator("=", "", "Assam", "state")
        self.assertEqual(status, RuleStatus.UNKNOWN)

    def test_contradictory_evidence_returns_review(self):
        """Invariant: Contradictory evidence must produce REVIEW."""
        status, reason = evaluate_operator("=", "Assam", "Assam", "state", has_conflict=True)
        self.assertEqual(status, RuleStatus.REVIEW)
        self.assertIn("Contradictory evidence", reason)

        status, _ = evaluate_operator("between", 25, {"min": 18, "max": 40}, "age", has_conflict=True)
        self.assertEqual(status, RuleStatus.REVIEW)

    def test_invalid_operator_raises_error(self):
        with self.assertRaises(InvalidOperatorError):
            evaluate_operator("unsupported_op_123", 25, 20)

if __name__ == "__main__":
    unittest.main()
