"""
Unit tests for BenefitSummaryBuilder.
Phase 11: Validates transparent benefit presentation from BenefitCalculator results.
"""

import unittest
from src.guidance.benefit_summary import BenefitSummaryBuilder


class TestBenefitGuidance(unittest.TestCase):
    """Tests for BenefitSummaryBuilder."""

    def test_calculated_fixed_benefit(self):
        """Presents calculated benefit transparently."""
        b_data = {
            "status": "CALCULATED",
            "benefit_type": "DIRECT_BENEFIT_TRANSFER",
            "amount": 6000.0,
            "currency": "INR",
            "disbursement_frequency": "ANNUAL",
            "reasoning": "Three equal installments of Rs 2,000 each.",
            "verbatim_policy_evidence": "Rs. 6,000 per year payable in three installments.",
        }
        guidance = BenefitSummaryBuilder.build_guidance(benefit_data=b_data, scheme_name="PM Kisan")
        self.assertEqual(guidance.status, "CALCULATED")
        self.assertEqual(guidance.amount, 6000.0)
        self.assertIn("₹6,000", guidance.explanation)
        self.assertIn("Aadhaar-linked", guidance.disbursement_structure)

    def test_cannot_determine_benefit(self):
        """CANNOT_DETERMINE explicitly states ambiguity without inventing amount."""
        b_data = {
            "status": "CANNOT_DETERMINE",
            "benefit_type": "SUBSIDY",
            "amount": None,
        }
        guidance = BenefitSummaryBuilder.build_guidance(benefit_data=b_data, scheme_name="State Scheme")
        self.assertEqual(guidance.status, "CANNOT_DETERMINE")
        self.assertIsNone(guidance.amount)
        self.assertIn("cannot be determined deterministically", guidance.explanation)

    def test_empty_benefit_data(self):
        """Handles missing benefit record gracefully."""
        guidance = BenefitSummaryBuilder.build_guidance(benefit_data=None)
        self.assertEqual(guidance.status, "CANNOT_DETERMINE")
        self.assertIsNone(guidance.amount)


if __name__ == "__main__":
    unittest.main()
