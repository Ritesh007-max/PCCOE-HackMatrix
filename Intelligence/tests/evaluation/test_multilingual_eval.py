"""
Tests for Phase 13 Multilingual Quality & Statutory Decision Invariance Evaluator.
"""

import unittest
from pathlib import Path
import sys

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.evaluation.models import EvaluationCase, EvaluationCategory, Severity
from src.evaluation.multilingual_eval import MultilingualEvaluator


class TestMultilingualEvaluator(unittest.TestCase):
    """Verifies intent understanding across EN/HI/Hinglish and statutory decision invariance."""

    def setUp(self):
        self.evaluator = MultilingualEvaluator()

    def test_english_query_intent(self):
        case = EvaluationCase(
            case_id="TEST_MULTI_EN",
            category=EvaluationCategory.MULTILINGUAL,
            expected_language="en",
            input_data={"query": "What are the documents needed for Atal Pension Yojana?", "language": "en"},
            expected_scheme_id="apy",
            expected_output={"intent": "DOCUMENT_REQUIREMENTS"},
        )
        res = self.evaluator.evaluate_case(case)
        self.assertTrue(res.passed)

    def test_statutory_decision_invariance_across_languages(self):
        """Invariant: Language of inquiry must NEVER alter deterministic eligibility outcome."""
        case = EvaluationCase(
            case_id="MULTI_INVARIANCE_01",
            category=EvaluationCategory.MULTILINGUAL,
            severity=Severity.CRITICAL,
            input_data={
                "profile": {"age": 28, "has_bank_account": True, "is_taxpayer": False},
                "queries": [
                    "Am I eligible for APY?",
                    "क्या मैं अटल पेंशन योजना के लिए पात्र हूँ?",
                    "kya mai atal pension yojana ke liye eligible hu?",
                ],
            },
            expected_status="PASS",
        )
        res = self.evaluator.evaluate_case(case)
        self.assertTrue(res.passed)
        self.assertTrue(res.actual_output.get("invariant_preserved"))
        self.assertEqual(res.actual_output.get("decisions_by_language"), ["PASS", "PASS", "PASS"])
