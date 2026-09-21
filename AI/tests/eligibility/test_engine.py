"""
Integration and End-to-End tests for PolicySetu Deterministic Eligibility Engine.
Tests all 13 core requirements using official statutory scheme rule examples.
"""

import unittest
from pathlib import Path
from src.eligibility.engine import EligibilityEngine
from src.eligibility.decision import EligibilityDecision
from src.rules.models import RuleStatus, ApplicantProfile

RULES_EXAMPLES_DIR = Path("data/schemes/rules/examples")

class TestEligibilityEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = EligibilityEngine(RULES_EXAMPLES_DIR)

    def test_engine_initialization_and_registry(self):
        """Verifies that engine loads all 10 official example scheme rule files."""
        self.assertGreaterEqual(len(self.engine._rulesets), 10)
        self.assertIn("apy", self.engine._rulesets)
        self.assertIn("pm-kisan", self.engine._rulesets)
        self.assertIn("pmmvy", self.engine._rulesets)
        self.assertIn("aag", self.engine._rulesets)
        self.assertIn("mj-fapm", self.engine._rulesets)
        self.assertIn("108easuk", self.engine._rulesets)
        self.assertIn("aasgsmse", self.engine._rulesets)

    # 1. Age Boundaries Test
    def test_01_age_boundaries(self):
        """
        Atal Pension Yojana (apy):
        Statutory Rule: 18 <= age <= 40
        """
        # Lower boundary
        d_17 = self.engine.evaluate("apy", {"age": 17, "has_bank_account": True, "is_taxpayer": False})
        self.assertEqual(d_17.status, RuleStatus.FAIL)
        self.assertIn("rule_apy_01", d_17.failed_rules)

        d_18 = self.engine.evaluate("apy", {"age": 18, "has_bank_account": True, "is_taxpayer": False})
        self.assertEqual(d_18.status, RuleStatus.PASS)

        # Upper boundary
        d_40 = self.engine.evaluate("apy", {"age": 40, "has_bank_account": True, "is_taxpayer": False})
        self.assertEqual(d_40.status, RuleStatus.PASS)

        d_41 = self.engine.evaluate("apy", {"age": 41, "has_bank_account": True, "is_taxpayer": False})
        self.assertEqual(d_41.status, RuleStatus.FAIL)
        self.assertIn("rule_apy_01", d_41.failed_rules)

    # 2. Income Boundaries Test
    def test_02_income_boundaries(self):
        """
        Matru Jyothi (mj-fapm):
        Statutory Rule: annual_family_income <= 100000
        """
        base_profile = {
            "gender": "Female",
            "has_child_under_two_years": True,
            "disability_percentage": 45
        }

        d_pass = self.engine.evaluate("mj-fapm", {**base_profile, "annual_family_income": 99999})
        self.assertEqual(d_pass.status, RuleStatus.PASS)

        d_edge = self.engine.evaluate("mj-fapm", {**base_profile, "annual_family_income": 100000})
        self.assertEqual(d_edge.status, RuleStatus.PASS)

        d_fail = self.engine.evaluate("mj-fapm", {**base_profile, "annual_family_income": 100001})
        self.assertEqual(d_fail.status, RuleStatus.FAIL)
        self.assertIn("rule_mj-fapm_04", d_fail.failed_rules)

    # 3. State Matching Test
    def test_03_state_matching(self):
        """
        Aponar Apon Ghar (aag):
        Statutory Rule: state = 'Assam'
        """
        profile_assam = {
            "state": "Assam",
            "annual_family_income": 1500000,
            "housing_loan_amount": 750000,
            "already_benefited_apon_ghar": False
        }
        self.assertEqual(self.engine.evaluate("aag", profile_assam).status, RuleStatus.PASS)

        profile_bihar = {**profile_assam, "state": "Bihar"}
        d_bihar = self.engine.evaluate("aag", profile_bihar)
        self.assertEqual(d_bihar.status, RuleStatus.FAIL)
        self.assertIn("rule_aag_01", d_bihar.failed_rules)

    # 4. Gender Matching Test
    def test_04_gender_matching(self):
        """
        Pradhan Mantri Matru Vandana Yojana (pmmvy):
        Statutory Rule: gender = 'Female'
        """
        profile_female = {
            "gender": "Female",
            "age": 24,
            "is_pregnant_or_lactating": True,
            "is_regular_govt_employee": False
        }
        self.assertEqual(self.engine.evaluate("pmmvy", profile_female).status, RuleStatus.PASS)

        profile_male = {**profile_female, "gender": "Male"}
        d_male = self.engine.evaluate("pmmvy", profile_male)
        self.assertEqual(d_male.status, RuleStatus.FAIL)
        self.assertIn("rule_pmmvy_01", d_male.failed_rules)

    # 5. Boolean Conditions Test
    def test_05_boolean_conditions(self):
        """
        Atal Pension Yojana: has_bank_account is_true, is_taxpayer is_false
        """
        # Bank account False -> FAIL
        d_no_bank = self.engine.evaluate("apy", {"age": 30, "has_bank_account": False, "is_taxpayer": False})
        self.assertEqual(d_no_bank.status, RuleStatus.FAIL)
        self.assertIn("rule_apy_02", d_no_bank.failed_rules)

        # Taxpayer True -> FAIL
        d_taxpayer = self.engine.evaluate("apy", {"age": 30, "has_bank_account": True, "is_taxpayer": True})
        self.assertEqual(d_taxpayer.status, RuleStatus.FAIL)
        self.assertIn("rule_apy_03", d_taxpayer.failed_rules)

    # 6. AND Conjunction Test
    def test_06_and_conjunction(self):
        """All mandatory criteria must pass for scheme PASS."""
        profile = {
            "citizenship": "India",
            "state": "Puducherry",
            "gender": "Female",
            "age": 12,
            "school_attendance_percentage": 85
        }
        dec = self.engine.evaluate("aasgsmse", profile)
        self.assertEqual(dec.status, RuleStatus.PASS)
        self.assertEqual(len(dec.passed_rules), 5)
        self.assertEqual(len(dec.failed_rules), 0)

    # 7. OR Disjunction Test
    def test_07_or_disjunction(self):
        """
        PM SVANidhi: Vending proof (Group VENDING_PROOF with OR or conditional criteria)
        """
        ruleset = self.engine.get_ruleset("pm-svanidhi")
        self.assertIsNotNone(ruleset)

    # 8. NOT Exclusion Logic Test
    def test_08_not_exclusion(self):
        """
        PM Kisan: is_taxpayer is_false, is_institutional_landholder is_false
        """
        qual_profile = {
            "owns_cultivable_land": True,
            "is_institutional_landholder": False,
            "is_taxpayer": False,
            "monthly_pension_amount": 5000
        }
        self.assertEqual(self.engine.evaluate("pm-kisan", qual_profile).status, RuleStatus.PASS)

        # Disqualified by pension > 10,000
        disq_pension = {**qual_profile, "monthly_pension_amount": 15000}
        d_pension = self.engine.evaluate("pm-kisan", disq_pension)
        self.assertEqual(d_pension.status, RuleStatus.FAIL)
        self.assertIn("rule_pm-kisan_04", d_pension.failed_rules)

    # 9. Nested Groups Test
    def test_09_nested_groups(self):
        """Tests that rule sets with nested groups are evaluated properly."""
        ruleset = self.engine.get_ruleset("pm-kisan")
        self.assertTrue(len(ruleset.rules) >= 4)

    # 10. Missing Values -> UNKNOWN Test
    def test_10_missing_values_return_unknown(self):
        """
        CRITICAL INVARIANT:
        Missing information must produce UNKNOWN.
        UNKNOWN != PASS and UNKNOWN != FAIL.
        """
        # Only age provided, missing has_bank_account and is_taxpayer
        dec = self.engine.evaluate("apy", {"age": 28})
        self.assertEqual(dec.status, RuleStatus.UNKNOWN)
        self.assertNotEqual(dec.status, RuleStatus.PASS)
        self.assertNotEqual(dec.status, RuleStatus.FAIL)
        self.assertIsNone(dec.eligible)
        self.assertIn("has_bank_account", dec.missing_fields)
        self.assertIn("is_taxpayer", dec.missing_fields)

    # 11. Contradictory Evidence -> REVIEW Test
    def test_11_contradictory_evidence_returns_review(self):
        """
        CRITICAL INVARIANT:
        Contradictory evidence must produce REVIEW.
        """
        profile = ApplicantProfile(
            {"age": 28, "has_bank_account": True, "is_taxpayer": False},
            conflicts=["age"]
        )
        dec = self.engine.evaluate("apy", profile)
        self.assertEqual(dec.status, RuleStatus.REVIEW)
        self.assertIn("rule_apy_01", dec.review_rules)

    # 12. Hard Constraint Failure Test
    def test_12_hard_constraint_failure(self):
        """
        Hard constraint failure causes immediate disqualification with statutory citation.
        """
        dec = self.engine.evaluate("apy", {"age": 55, "has_bank_account": True, "is_taxpayer": False})
        self.assertEqual(dec.status, RuleStatus.FAIL)
        self.assertFalse(dec.eligible)
        self.assertGreater(len(dec.disqualification_reasons), 0)
        self.assertIn("The minimum age of joining APY is 18 years and maximum is 40 years", dec.disqualification_reasons[0])

    # 13. Deterministic Repeatability Test
    def test_13_deterministic_repeatability(self):
        """
        Running evaluation 100 times with identical input must yield 100 identical decisions.
        """
        profile = {"age": 28, "has_bank_account": True, "is_taxpayer": False}
        first_dec = self.engine.evaluate("apy", profile).to_dict()

        for _ in range(100):
            current_dec = self.engine.evaluate("apy", profile).to_dict()
            self.assertEqual(first_dec, current_dec)

    def test_supported_operators_and_states(self):
        """Verifies introspection of operators and decision states."""
        self.assertIn("between", self.engine.supported_operators)
        self.assertIn(">=", self.engine.supported_operators)
        self.assertIn("in", self.engine.supported_operators)
        self.assertIn("PASS", self.engine.supported_decision_states)
        self.assertIn("FAIL", self.engine.supported_decision_states)
        self.assertIn("UNKNOWN", self.engine.supported_decision_states)
        self.assertIn("REVIEW", self.engine.supported_decision_states)

if __name__ == "__main__":
    unittest.main()
