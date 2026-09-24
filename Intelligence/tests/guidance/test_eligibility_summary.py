"""
Unit tests for EligibilitySummaryBuilder.
Phase 11: Validates citizen explanations across PASS, FAIL, UNKNOWN, and REVIEW.
"""

import unittest
from src.application.status import StatutoryDecision
from src.application.case import SchemeEvaluation
from src.application.decision import DecisionSnapshot
from src.guidance.eligibility_summary import EligibilitySummaryBuilder


class TestEligibilitySummary(unittest.TestCase):
    """Tests for EligibilitySummaryBuilder."""

    def test_pass_explanation_satisfied_criteria(self):
        """PASS decision clearly lists satisfied criteria."""
        evaluation = SchemeEvaluation(
            scheme_id="scheme_1",
            scheme_name="Gujarat Scholarship",
            decision_status=StatutoryDecision.PASS,
            is_eligible=True,
            matched_rules=[
                {"field": "age", "reason": "Applicant age 20 is within 18 to 25"},
                {"field": "state", "reason": "Domicile is Gujarat"},
            ],
        )
        summary = EligibilitySummaryBuilder.build_summary(evaluation=evaluation)
        self.assertEqual(summary.status, "PASS")
        self.assertIn("satisfy the evaluated statutory eligibility criteria", summary.summary)
        self.assertEqual(len(summary.satisfied_criteria), 2)
        self.assertFalse(summary.failed_criteria)

    def test_fail_explanation_unsoftened_criteria(self):
        """FAIL decision states exact disqualifications without softening."""
        evaluation = SchemeEvaluation(
            scheme_id="scheme_1",
            scheme_name="Scholarship Scheme",
            decision_status=StatutoryDecision.FAIL,
            is_eligible=False,
            failed_rules=[
                {"field": "annual_family_income", "reason": "Income ₹4,50,000 exceeds ceiling ₹2,50,000"}
            ],
        )
        summary = EligibilitySummaryBuilder.build_summary(evaluation=evaluation)
        self.assertEqual(summary.status, "FAIL")
        self.assertIn("you are not eligible", summary.summary)
        self.assertIn("annual_family_income", summary.summary)
        self.assertEqual(len(summary.failed_criteria), 1)

    def test_unknown_explanation_missing_information(self):
        """UNKNOWN decision clearly identifies missing required information."""
        evaluation = SchemeEvaluation(
            scheme_id="scheme_1",
            scheme_name="PMAY",
            decision_status=StatutoryDecision.UNKNOWN,
            is_eligible=False,
            unknown_rules=[{"field": "has_pucca_house"}],
            missing_fields=["has_pucca_house"],
        )
        summary = EligibilitySummaryBuilder.build_summary(evaluation=evaluation)
        self.assertEqual(summary.status, "UNKNOWN")
        self.assertIn("cannot be determined yet", summary.summary)
        self.assertIn("has_pucca_house", summary.summary)
        self.assertIn("has_pucca_house", summary.missing_information)

    def test_review_explanation_conflicting_evidence(self):
        """REVIEW decision highlights contradiction for caseworker arbitration."""
        evaluation = SchemeEvaluation(
            scheme_id="scheme_1",
            scheme_name="State Scheme",
            decision_status=StatutoryDecision.REVIEW,
            is_eligible=False,
            conflicted_fields=["state"],
        )
        summary = EligibilitySummaryBuilder.build_summary(evaluation=evaluation)
        self.assertEqual(summary.status, "REVIEW")
        self.assertIn("requires administrative caseworker review", summary.summary)
        self.assertIn("state", summary.conflicting_evidence)


if __name__ == "__main__":
    unittest.main()
