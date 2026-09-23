"""
Unit tests for Manual Review Cases.
Phase 10: Validates structured human-in-the-loop review cases.
"""

import unittest
from src.application.status import ReviewStatus, ReviewReason
from src.application.review import ReviewManager, ReviewCase


class TestManualReview(unittest.TestCase):
    """Tests for ReviewCase creation and status management."""

    def test_create_review_case(self):
        """Review case correctly initialized with reason and conflicting fields."""
        manager = ReviewManager()
        review = manager.create_review(
            application_id="app_rev_1",
            reason=ReviewReason.FACT_CONFLICT,
            scheme_id="scheme_demo",
            conflicting_fields=["state", "annual_family_income"],
            unresolved_rules=["rule_state_domicile"],
            supporting_documents=["doc_income_1", "doc_income_2"],
        )

        self.assertTrue(review.review_id.startswith("rev_"))
        self.assertEqual(review.status, ReviewStatus.OPEN)
        self.assertEqual(review.reason, ReviewReason.FACT_CONFLICT)
        self.assertEqual(len(review.conflicting_fields), 2)

    def test_review_status_progression(self):
        """Review case status can progress from OPEN to IN_REVIEW to RESOLVED."""
        manager = ReviewManager()
        review = manager.create_review(
            application_id="app_rev_2",
            reason=ReviewReason.UNSTRUCTURED_RULE,
        )

        # Assign to caseworker
        updated = manager.update_status(
            review_id=review.review_id,
            status=ReviewStatus.IN_REVIEW,
            assigned_to="caseworker_patel",
        )
        self.assertEqual(updated.status, ReviewStatus.IN_REVIEW)
        self.assertEqual(updated.assigned_to, "caseworker_patel")

        # Resolve
        resolved = manager.update_status(
            review_id=review.review_id,
            status=ReviewStatus.RESOLVED,
            notes="Applicant provided attested domicile certificate. Conflict resolved.",
        )
        self.assertEqual(resolved.status, ReviewStatus.RESOLVED)
        assert resolved.resolution_notes is not None
        self.assertIn("attested domicile", resolved.resolution_notes)

    def test_serialization_roundtrip(self):
        """ReviewCase converts cleanly to and from dictionary."""
        case = ReviewCase(
            review_id="rev_123",
            application_id="app_123",
            reason=ReviewReason.DOCUMENT_AMBIGUITY,
            status=ReviewStatus.OPEN,
        )
        data = case.to_dict()
        self.assertEqual(data["reason"], "DOCUMENT_AMBIGUITY")
        recon = ReviewCase.from_dict(data)
        self.assertEqual(recon.review_id, "rev_123")
        self.assertEqual(recon.reason, ReviewReason.DOCUMENT_AMBIGUITY)


if __name__ == "__main__":
    unittest.main()
