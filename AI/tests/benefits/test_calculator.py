"""
Unit tests for PolicySetu Deterministic Benefit Calculator.
Verifies:
1. Static pre-compiled rules execute with 100% deterministic arithmetic.
2. Structured metadata subsidy calculation with statutory capping.
3. Strict prohibition of runtime formula synthesis for unstructured policy text.
4. Verbatim evidence preservation and full serialization roundtrip.
"""

import unittest
from src.benefits.calculator import (
    BenefitCalculator,
    BenefitResult,
    BenefitType,
    BenefitCalculationStatus,
)


class TestBenefitCalculator(unittest.TestCase):

    def setUp(self):
        self.calculator = BenefitCalculator()

    def test_pm_kisan_flat_benefit(self):
        result = self.calculator.calculate(
            scheme_id="pm_kisan",
            scheme_name="PM-KISAN",
            applicant_facts={"landholding_acres": 2.5},
            raw_benefit_text="Financial benefit of Rs 6000 per year is given in 3 installments.",
        )
        self.assertEqual(result.status, BenefitCalculationStatus.CALCULATED)
        self.assertEqual(result.amount, 6000.0)
        self.assertEqual(result.benefit_type, BenefitType.DIRECT_BENEFIT_TRANSFER)
        self.assertEqual(result.disbursement_frequency, "ANNUAL")
        self.assertEqual(result.formula_applied, "RULE_PM_KISAN_2019")
        self.assertIn("6,000", result.reasoning)

    def test_pm_awas_rural_plain_vs_hilly(self):
        # Plain area
        plain_res = self.calculator.calculate(
            scheme_id="pmay_g",
            scheme_name="PMAY-G",
            applicant_facts={"terrain": "plain"},
        )
        self.assertEqual(plain_res.status, BenefitCalculationStatus.CALCULATED)
        self.assertEqual(plain_res.amount, 120000.0)
        self.assertEqual(plain_res.benefit_type, BenefitType.SUBSIDY)

        # Hilly area
        hilly_res = self.calculator.calculate(
            scheme_id="pmay_g",
            scheme_name="PMAY-G",
            applicant_facts={"terrain": "hilly"},
        )
        self.assertEqual(hilly_res.status, BenefitCalculationStatus.CALCULATED)
        self.assertEqual(hilly_res.amount, 130000.0)

    def test_sc_scholarship_hosteller_tiers(self):
        # Hosteller
        hosteller_res = self.calculator.calculate(
            scheme_id="sc_post_matric_scholarship",
            scheme_name="Post Matric SC Scholarship",
            applicant_facts={"is_hosteller": True, "course_group": "Group 1"},
        )
        self.assertEqual(hosteller_res.status, BenefitCalculationStatus.CALCULATED)
        self.assertEqual(hosteller_res.amount, 13500.0)
        self.assertEqual(hosteller_res.benefit_type, BenefitType.SCHOLARSHIP)

        # Day scholar
        dayscholar_res = self.calculator.calculate(
            scheme_id="sc_post_matric_scholarship",
            scheme_name="Post Matric SC Scholarship",
            applicant_facts={"is_hosteller": False, "course_group": "Group 1"},
        )
        self.assertEqual(dayscholar_res.status, BenefitCalculationStatus.CALCULATED)
        self.assertEqual(dayscholar_res.amount, 7000.0)

    def test_structured_metadata_subsidy_capped(self):
        meta = {
            "subsidy_percentage": 40.0,
            "subsidy_cap": 30000.0,
        }
        facts = {"project_cost": 100000.0}
        # 40% of 100,000 = 40,000, capped at 30,000
        res = self.calculator.calculate(
            scheme_id="solar_rooftop",
            scheme_name="Solar Rooftop Scheme",
            applicant_facts=facts,
            structured_metadata=meta,
        )
        self.assertEqual(res.status, BenefitCalculationStatus.CALCULATED)
        self.assertEqual(res.amount, 30000.0)
        self.assertEqual(res.formula_applied, "METADATA_SUBSIDY_PERCENTAGE_CAPPED")
        self.assertIn("capped", res.reasoning)

    def test_unstructured_policy_text_strictly_cannot_determine(self):
        narrative = "Financial assistance will be provided as determined by the District Welfare Committee upon scrutiny."
        res = self.calculator.calculate(
            scheme_id="custom_welfare_grant",
            scheme_name="Custom Welfare Grant",
            applicant_facts={"annual_family_income": 80000.0},
            raw_benefit_text=narrative,
        )
        # CRITICAL INVARIANT: NEVER invent formulas from narrative text
        self.assertEqual(res.status, BenefitCalculationStatus.CANNOT_DETERMINE)
        self.assertIsNone(res.amount)
        self.assertIsNone(res.formula_applied)
        self.assertEqual(res.verbatim_policy_evidence, narrative)
        self.assertIn("No registered structured calculation rule exists", res.reasoning)

    def test_serialization_roundtrip(self):
        res = self.calculator.calculate(
            scheme_id="pmsby",
            scheme_name="PMSBY",
            applicant_facts={},
        )
        d = res.to_dict()
        self.assertEqual(d["amount"], 200000.0)
        self.assertEqual(d["benefit_type"], "DIRECT_BENEFIT_TRANSFER")
        self.assertEqual(d["status"], "CALCULATED")

        restored = BenefitResult.from_dict(d)
        self.assertEqual(restored.scheme_id, res.scheme_id)
        self.assertEqual(restored.amount, res.amount)
        self.assertEqual(restored.benefit_type, res.benefit_type)
        self.assertEqual(restored.status, res.status)


if __name__ == "__main__":
    unittest.main()
