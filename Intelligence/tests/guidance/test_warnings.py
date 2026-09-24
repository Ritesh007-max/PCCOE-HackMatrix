"""
Unit tests for WarningGenerator.
Phase 11: Validates deterministic warning codes, severities, and triggers.
"""

import unittest
from src.application.case import ApplicationCase, FactSnapshot, SchemeEvaluation
from src.application.status import StatutoryDecision, ReadinessStatus
from src.guidance.models import GuidanceWarningCode, WarningSeverity
from src.guidance.warnings import WarningGenerator


class TestGuidanceWarnings(unittest.TestCase):
    """Tests for WarningGenerator."""

    def test_document_missing_warning(self):
        """Generates DOCUMENT_MISSING warning when certificates are missing."""
        case = ApplicationCase(readiness=ReadinessStatus.ACTION_REQUIRED)
        warnings = WarningGenerator.generate_warnings(
            case=case,
            missing_documents=["caste_certificate"],
        )
        codes = [w.code for w in warnings]
        self.assertIn(GuidanceWarningCode.DOCUMENT_MISSING, codes)
        missing_warn = next(w for w in warnings if w.code == GuidanceWarningCode.DOCUMENT_MISSING)
        self.assertEqual(missing_warn.severity, WarningSeverity.CRITICAL)

    def test_document_conflict_warning(self):
        """Generates DOCUMENT_CONFLICT warning when contradictory evidence exists."""
        case = ApplicationCase(
            facts=FactSnapshot(conflicted_fields=["state"]),
            readiness=ReadinessStatus.READY_FOR_REVIEW,
        )
        warnings = WarningGenerator.generate_warnings(case=case)
        codes = [w.code for w in warnings]
        self.assertIn(GuidanceWarningCode.DOCUMENT_CONFLICT, codes)

    def test_human_review_warning(self):
        """Generates HUMAN_REVIEW_REQUIRED warning when decision is REVIEW."""
        case = ApplicationCase(readiness=ReadinessStatus.READY_FOR_REVIEW)
        evaluation = SchemeEvaluation(
            scheme_id="scheme_test",
            decision_status=StatutoryDecision.REVIEW,
        )
        warnings = WarningGenerator.generate_warnings(case=case, evaluation=evaluation)
        codes = [w.code for w in warnings]
        self.assertIn(GuidanceWarningCode.HUMAN_REVIEW_REQUIRED, codes)

    def test_official_link_unavailable_warning(self):
        """Generates OFFICIAL_LINK_UNAVAILABLE warning when portal URL is None."""
        case = ApplicationCase()
        warnings = WarningGenerator.generate_warnings(case=case, official_portal_url=None)
        codes = [w.code for w in warnings]
        self.assertIn(GuidanceWarningCode.OFFICIAL_LINK_UNAVAILABLE, codes)


if __name__ == "__main__":
    unittest.main()
