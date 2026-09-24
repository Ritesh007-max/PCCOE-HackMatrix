"""
Unit tests for FIN Kleene multi-valued logic (AND, OR, NOT) and nested group evaluation.
"""

import unittest
import sys
from pathlib import Path

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.rules.logic import evaluate_and, evaluate_or, evaluate_not, evaluate_group_operator
from src.rules.models import RuleStatus

class TestLogic(unittest.TestCase):

    def test_and_conjunction(self):
        # All PASS -> PASS
        self.assertEqual(evaluate_and([RuleStatus.PASS, RuleStatus.PASS]), RuleStatus.PASS)

        # Single FAIL -> FAIL (short-circuit / overriding)
        self.assertEqual(evaluate_and([RuleStatus.PASS, RuleStatus.FAIL]), RuleStatus.FAIL)
        self.assertEqual(evaluate_and([RuleStatus.FAIL, RuleStatus.UNKNOWN]), RuleStatus.FAIL)
        self.assertEqual(evaluate_and([RuleStatus.FAIL, RuleStatus.REVIEW]), RuleStatus.FAIL)

        # Invariant: UNKNOWN != FAIL and UNKNOWN != PASS
        # If no failure and any UNKNOWN -> UNKNOWN
        self.assertEqual(evaluate_and([RuleStatus.PASS, RuleStatus.UNKNOWN]), RuleStatus.UNKNOWN)

        # Review behavior: No failure, no unknown, any review -> REVIEW
        self.assertEqual(evaluate_and([RuleStatus.PASS, RuleStatus.REVIEW]), RuleStatus.REVIEW)
        self.assertEqual(evaluate_and([RuleStatus.UNKNOWN, RuleStatus.REVIEW]), RuleStatus.UNKNOWN)

    def test_or_disjunction(self):
        # Single PASS -> PASS (short-circuit / overriding)
        self.assertEqual(evaluate_or([RuleStatus.PASS, RuleStatus.FAIL]), RuleStatus.PASS)
        self.assertEqual(evaluate_or([RuleStatus.PASS, RuleStatus.UNKNOWN]), RuleStatus.PASS)
        self.assertEqual(evaluate_or([RuleStatus.PASS, RuleStatus.REVIEW]), RuleStatus.PASS)

        # All FAIL -> FAIL
        self.assertEqual(evaluate_or([RuleStatus.FAIL, RuleStatus.FAIL]), RuleStatus.FAIL)

        # If no PASS, any UNKNOWN -> UNKNOWN
        self.assertEqual(evaluate_or([RuleStatus.FAIL, RuleStatus.UNKNOWN]), RuleStatus.UNKNOWN)

        # If no PASS and no UNKNOWN, any REVIEW -> REVIEW
        self.assertEqual(evaluate_or([RuleStatus.FAIL, RuleStatus.REVIEW]), RuleStatus.REVIEW)

    def test_not_inversion(self):
        # Exclusion logic
        self.assertEqual(evaluate_not(RuleStatus.PASS), RuleStatus.FAIL)
        self.assertEqual(evaluate_not(RuleStatus.FAIL), RuleStatus.PASS)
        self.assertEqual(evaluate_not(RuleStatus.UNKNOWN), RuleStatus.UNKNOWN)
        self.assertEqual(evaluate_not(RuleStatus.REVIEW), RuleStatus.REVIEW)

    def test_nested_logic_groups(self):
        """
        Tests compound condition: (Category in [SC, ST] OR Income <= 150000) AND State == 'Assam'
        """
        # Case 1: SC category, Assam state -> PASS
        group_or = evaluate_or([RuleStatus.PASS, RuleStatus.FAIL]) # SC=PASS, Income=FAIL
        rule_state = RuleStatus.PASS # Assam=PASS
        final_verdict = evaluate_and([group_or, rule_state])
        self.assertEqual(final_verdict, RuleStatus.PASS)

        # Case 2: General category, low income, Assam state -> PASS
        group_or = evaluate_or([RuleStatus.FAIL, RuleStatus.PASS]) # General=FAIL, Income=PASS
        rule_state = RuleStatus.PASS
        self.assertEqual(evaluate_and([group_or, rule_state]), RuleStatus.PASS)

        # Case 3: General category, high income, Assam state -> FAIL
        group_or = evaluate_or([RuleStatus.FAIL, RuleStatus.FAIL])
        rule_state = RuleStatus.PASS
        self.assertEqual(evaluate_and([group_or, rule_state]), RuleStatus.FAIL)

        # Case 4: Category unknown, income unknown, Assam state -> UNKNOWN (Actionable inquiry)
        group_or = evaluate_or([RuleStatus.UNKNOWN, RuleStatus.UNKNOWN])
        rule_state = RuleStatus.PASS
        self.assertEqual(evaluate_and([group_or, rule_state]), RuleStatus.UNKNOWN)

        # Case 5: Wrong state (Bihar) -> FAIL regardless of category/income
        group_or = evaluate_or([RuleStatus.PASS, RuleStatus.PASS])
        rule_state = RuleStatus.FAIL
        self.assertEqual(evaluate_and([group_or, rule_state]), RuleStatus.FAIL)

    def test_evaluate_group_operator(self):
        self.assertEqual(evaluate_group_operator("AND", [RuleStatus.PASS, RuleStatus.PASS]), RuleStatus.PASS)
        self.assertEqual(evaluate_group_operator("OR", [RuleStatus.PASS, RuleStatus.FAIL]), RuleStatus.PASS)
        self.assertEqual(evaluate_group_operator("NOT", [RuleStatus.PASS]), RuleStatus.FAIL)

if __name__ == "__main__":
    unittest.main()
