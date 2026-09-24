"""
Unit tests for AST-aware missing field analysis.
Enforces the critical invariant: Missing fields are NOT naive set subtraction.
They inspect AST condition trees (AND/OR/NOT logic groups) and respect satisfied branches.
"""

import unittest
import sys
from pathlib import Path

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.llm.ast_analyzer import RuleASTMissingFieldAnalyzer
from src.rules.models import (
    SchemeRuleSet,
    LogicGroup,
    Rule,
    ApplicantProfile,
)


class TestRuleASTMissingFieldAnalyzer(unittest.TestCase):

    def setUp(self):
        self.analyzer = RuleASTMissingFieldAnalyzer()

    def test_composite_or_branch_already_satisfied(self):
        """
        Condition:
        (Age >= 18 AND State = 'Gujarat') OR (bpl_card_holder = True)

        Applicant profile has: bpl_card_holder = True, but Age and State are unknown.
        Invariant: Since the OR branch is satisfied, missing fields must be empty!
        A naive set subtraction would wrongly claim 'age' and 'state' are required.
        """
        r1 = Rule(
            rule_id="r_age",
            scheme_id="s1",
            rule_type="eligibility",
            field="age",
            operator=">=",
            expected_value=18,
            value_type="numeric",
            logic_group="G1"
        )
        r2 = Rule(
            rule_id="r_state",
            scheme_id="s1",
            rule_type="eligibility",
            field="state",
            operator="=",
            expected_value="Gujarat",
            value_type="string",
            logic_group="G1"
        )
        r3 = Rule(
            rule_id="r_bpl",
            scheme_id="s1",
            rule_type="eligibility",
            field="bpl_card_holder",
            operator="=",
            expected_value=True,
            value_type="boolean",
            logic_group="G2"
        )

        g1 = LogicGroup(group_id="G1", operator="AND", rule_ids=["r_age", "r_state"])
        g2 = LogicGroup(group_id="G2", operator="AND", rule_ids=["r_bpl"])

        ruleset = SchemeRuleSet(
            scheme_id="s1",
            scheme_slug="s1",
            scheme_name="Test Scheme",
            root_logic="OR",
            rules=[r1, r2, r3],
            logic_groups=[g1, g2]
        )

        # Profile with BPL satisfied
        profile = ApplicantProfile(data={"bpl_card_holder": True})

        missing = self.analyzer.find_missing_fields_for_pass(ruleset, profile)
        self.assertEqual(missing, [], "Missing fields must be empty when an OR branch is already satisfied!")

    def test_composite_or_branch_unresolved(self):
        """
        Condition:
        (Age >= 18 AND State = 'Gujarat') OR (bpl_card_holder = True)

        Applicant profile is empty.
        Candidate missing fields should identify viable paths to satisfy either branch.
        """
        r1 = Rule(
            rule_id="r_age",
            scheme_id="s1",
            rule_type="eligibility",
            field="age",
            operator=">=",
            expected_value=18,
            value_type="numeric",
            logic_group="G1"
        )
        r2 = Rule(
            rule_id="r_state",
            scheme_id="s1",
            rule_type="eligibility",
            field="state",
            operator="=",
            expected_value="Gujarat",
            value_type="string",
            logic_group="G1"
        )
        r3 = Rule(
            rule_id="r_bpl",
            scheme_id="s1",
            rule_type="eligibility",
            field="bpl_card_holder",
            operator="=",
            expected_value=True,
            value_type="boolean",
            logic_group="G2"
        )

        g1 = LogicGroup(group_id="G1", operator="AND", rule_ids=["r_age", "r_state"])
        g2 = LogicGroup(group_id="G2", operator="AND", rule_ids=["r_bpl"])

        ruleset = SchemeRuleSet(
            scheme_id="s1",
            scheme_slug="s1",
            scheme_name="Test Scheme",
            root_logic="OR",
            rules=[r1, r2, r3],
            logic_groups=[g1, g2]
        )

        profile = ApplicantProfile(data={})

        missing = self.analyzer.find_missing_fields_for_pass(ruleset, profile)
        self.assertIn("bpl_card_holder", missing)
        self.assertIn("age", missing)
        self.assertIn("state", missing)

    def test_hard_fail_discards_dead_and_branch(self):
        """
        Condition:
        (Age >= 18 AND State = 'Gujarat') where root logic is AND.
        If Age is 15 (FAIL on hard constraint), providing State will never produce PASS.
        Missing fields must return empty list.
        """
        r1 = Rule(
            rule_id="r_age",
            scheme_id="s1",
            rule_type="eligibility",
            field="age",
            operator=">=",
            expected_value=18,
            value_type="numeric",
            hard_constraint=True
        )
        r2 = Rule(
            rule_id="r_state",
            scheme_id="s1",
            rule_type="eligibility",
            field="state",
            operator="=",
            expected_value="Gujarat",
            value_type="string",
            hard_constraint=True
        )

        ruleset = SchemeRuleSet(
            scheme_id="s1",
            scheme_slug="s1",
            scheme_name="Test AND Scheme",
            root_logic="AND",
            rules=[r1, r2]
        )

        # Disqualified on age
        profile = ApplicantProfile(data={"age": 15})

        missing = self.analyzer.find_missing_fields_for_pass(ruleset, profile)
        self.assertEqual(missing, [], "Must return empty when ruleset is irrevocably disqualified.")


if __name__ == "__main__":
    unittest.main()
