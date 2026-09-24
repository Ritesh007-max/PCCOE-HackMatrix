"""
Unit tests for GuidanceValidator.
Phase 11: Validates consistency enforcement and anti-contradiction protections.
"""

import unittest
from src.guidance.models import (
    ApplicationGuidancePackage,
    EligibilitySummary,
    BenefitGuidance,
)
from src.guidance.validator import GuidanceValidator
from src.guidance.exceptions import GuidanceValidationError, ContradictoryGuidanceError


class TestGuidanceValidator(unittest.TestCase):
    """Tests for GuidanceValidator."""

    def _build_valid_package(self) -> ApplicationGuidancePackage:
        return ApplicationGuidancePackage(
            application_id="app_val_01",
            scheme_id="scheme_1",
            scheme_name="Scholarship",
            statutory_decision="PASS",
            readiness_status="READY_TO_APPLY",
            readiness={"status": "READY_TO_APPLY"},
            eligibility=EligibilitySummary(status="PASS", summary="Criteria satisfied"),
            documents={"available": ["Income Certificate"], "missing": []},
            information={"known": ["age: 20"], "missing": [], "conflicted": []},
            benefit=BenefitGuidance(status="CALCULATED", amount=5000.0),
            application={"official_portal_url": "https://scholarships.gov.in"},
            actions=[],
            warnings=[],
            sources=[],
            policy_snapshot_version="snapshot_20260921_193823",
            rule_version="1.0.0",
        )

    def test_valid_package_passes(self):
        """Standard valid package passes without exception."""
        pkg = self._build_valid_package()
        # Should not raise
        GuidanceValidator.validate_package(pkg)

    def test_reject_eligibility_decision_mismatch(self):
        """Rejects package when statutory decision does not match eligibility summary status."""
        pkg = self._build_valid_package()
        pkg.statutory_decision = "PASS"
        pkg.eligibility.status = "FAIL"

        with self.assertRaises(GuidanceValidationError):
            GuidanceValidator.validate_package(pkg)

    def test_reject_ready_to_apply_with_missing_documents(self):
        """Rejects READY_TO_APPLY if mandatory documents are missing."""
        pkg = self._build_valid_package()
        pkg.readiness_status = "READY_TO_APPLY"
        pkg.documents["missing"] = ["Caste Certificate"]

        with self.assertRaises(GuidanceValidationError):
            GuidanceValidator.validate_package(pkg)

    def test_reject_undetermined_benefit_with_amount(self):
        """Rejects package if benefit status is CANNOT_DETERMINE but amount is populated."""
        pkg = self._build_valid_package()
        pkg.benefit.status = "CANNOT_DETERMINE"
        pkg.benefit.amount = 10000.0

        with self.assertRaises(GuidanceValidationError):
            GuidanceValidator.validate_package(pkg)

    def test_reject_untrusted_portal_url(self):
        """Rejects package if official portal URL is on an untrusted commercial domain."""
        pkg = self._build_valid_package()
        pkg.application["official_portal_url"] = "https://sarkariyojana.blogspot.com/apply"

        with self.assertRaises(GuidanceValidationError):
            GuidanceValidator.validate_package(pkg)

    def test_reject_textual_contradiction_fail_claimed_eligible(self):
        """Rejects package when decision is FAIL but generated summary claims citizen is eligible."""
        pkg = self._build_valid_package()
        pkg.statutory_decision = "FAIL"
        pkg.eligibility.status = "FAIL"
        pkg.readiness_status = "NOT_READY"
        pkg.eligibility.summary = "Congratulations, you are eligible for this benefit!"

        with self.assertRaises(ContradictoryGuidanceError):
            GuidanceValidator.validate_package(pkg)


if __name__ == "__main__":
    unittest.main()
