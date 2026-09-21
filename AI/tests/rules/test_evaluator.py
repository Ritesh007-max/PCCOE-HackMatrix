"""
Unit tests for PolicySetu RuleEvaluator.
"""

import unittest
from src.rules.evaluator import RuleEvaluator
from src.rules.models import Rule, SchemeRuleSet, RuleStatus, ApplicantProfile

class TestRuleEvaluator(unittest.TestCase):

    def setUp(self):
        self.evaluator = RuleEvaluator()
        self.sample_rule = Rule(
            rule_id="test_age_01",
            scheme_id="test_scheme",
            rule_type="eligibility",
            field="age",
            operator="between",
            expected_value={"min": 18, "max": 40},
            value_type="range",
            required=True,
            hard_constraint=True,
            raw_text="The minimum age of joining is 18 years and maximum is 40 years."
        )

    def test_evaluate_rule_pass(self):
        profile = ApplicantProfile({"age": 25})
        res = self.evaluator.evaluate_rule(self.sample_rule, profile)
        self.assertEqual(res.status, RuleStatus.PASS)
        self.assertEqual(res.applicant_value, 25)

    def test_evaluate_rule_fail(self):
        profile = ApplicantProfile({"age": 45})
        res = self.evaluator.evaluate_rule(self.sample_rule, profile)
        self.assertEqual(res.status, RuleStatus.FAIL)
        self.assertTrue(res.hard_constraint)

    def test_evaluate_rule_unknown(self):
        # Missing age
        profile = ApplicantProfile({})
        res = self.evaluator.evaluate_rule(self.sample_rule, profile)
        self.assertEqual(res.status, RuleStatus.UNKNOWN)

    def test_evaluate_rule_contradictory_evidence(self):
        profile = ApplicantProfile({"age": 25}, conflicts=["age"])
        res = self.evaluator.evaluate_rule(self.sample_rule, profile)
        self.assertEqual(res.status, RuleStatus.REVIEW)
        self.assertIn("Contradictory evidence", res.reason)

    def test_hard_constraint_failure_disqualifies_ruleset(self):
        rule1 = Rule(
            rule_id="r1",
            scheme_id="s1",
            rule_type="eligibility",
            field="state",
            operator="=",
            expected_value="Uttarakhand",
            value_type="string",
            hard_constraint=True
        )
        rule2 = Rule(
            rule_id="r2",
            scheme_id="s1",
            rule_type="eligibility",
            field="requires_emergency_medical_care",
            operator="is_true",
            expected_value=True,
            value_type="boolean",
            hard_constraint=False
        )
        ruleset = SchemeRuleSet(
            scheme_id="s1",
            scheme_slug="108easuk",
            scheme_name="108 Emergency Ambulance Service",
            rules=[rule1, rule2]
        )

        # Applicant from Gujarat (fails hard constraint state)
        profile = ApplicantProfile({"state": "Gujarat", "requires_emergency_medical_care": True})
        overall_status, results = self.evaluator.evaluate_ruleset(ruleset, profile)
        self.assertEqual(overall_status, RuleStatus.FAIL)

if __name__ == "__main__":
    unittest.main()
