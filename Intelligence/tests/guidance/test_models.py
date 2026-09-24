"""
Unit tests for Guidance Domain Models.
Phase 11: Validates serialization, roundtrips, and enum mappings.
"""

import unittest
from src.guidance.models import (
    ApplicationMode,
    GuidanceWarningCode,
    WarningSeverity,
    StepSourceType,
    DeadlineStatus,
    GuidanceWarning,
    DocumentGuidanceItem,
    ApplicationStep,
    DeadlineGuidance,
    EligibilitySummary,
    BenefitGuidance,
    SourceCitation,
    ApplicationGuidancePackage,
)


class TestGuidanceModels(unittest.TestCase):
    """Tests for Phase 11 data models."""

    def test_application_mode_parsing(self):
        """ApplicationMode correctly maps strings."""
        self.assertEqual(ApplicationMode.from_string("Online"), ApplicationMode.ONLINE)
        self.assertEqual(ApplicationMode.from_string("Offline"), ApplicationMode.OFFLINE)
        self.assertEqual(ApplicationMode.from_string("Online and Offline"), ApplicationMode.BOTH)
        self.assertEqual(ApplicationMode.from_string("CSC Center"), ApplicationMode.CSC)
        self.assertEqual(ApplicationMode.from_string("Department"), ApplicationMode.DEPARTMENT_OFFICE)
        self.assertEqual(ApplicationMode.from_string(None), ApplicationMode.UNKNOWN)

    def test_guidance_warning_roundtrip(self):
        """GuidanceWarning serializes and deserializes cleanly."""
        warn = GuidanceWarning(
            code=GuidanceWarningCode.DOCUMENT_MISSING,
            severity=WarningSeverity.CRITICAL,
            message="Income certificate is required.",
            related_field="annual_family_income",
            related_scheme="pm_kisan",
        )
        d = warn.to_dict()
        self.assertEqual(d["code"], "DOCUMENT_MISSING")
        self.assertEqual(d["severity"], "CRITICAL")
        recon = GuidanceWarning.from_dict(d)
        self.assertEqual(recon.code, warn.code)
        self.assertEqual(recon.severity, warn.severity)
        self.assertEqual(recon.message, warn.message)

    def test_document_guidance_item_roundtrip(self):
        """DocumentGuidanceItem preserves attestation notes and authority."""
        item = DocumentGuidanceItem(
            document_type="income_certificate",
            display_name="Income Certificate",
            status="AVAILABLE",
            required=True,
            why_needed="Income threshold check",
            already_provided=True,
            issuing_authority="Tehsildar",
            preparation_notes="Must be recent",
        )
        d = item.to_dict()
        recon = DocumentGuidanceItem.from_dict(d)
        self.assertEqual(recon.document_type, "income_certificate")
        self.assertEqual(recon.issuing_authority, "Tehsildar")
        self.assertTrue(recon.already_provided)

    def test_application_step_roundtrip(self):
        """ApplicationStep preserves source type and instructions."""
        step = ApplicationStep(
            step_number=1,
            instruction="Open official portal",
            source_type=StepSourceType.POLICY_SOURCED,
            source_reference="https://pmkisan.gov.in",
            mandatory=True,
            notes="Use Aadhaar login",
        )
        d = step.to_dict()
        recon = ApplicationStep.from_dict(d)
        self.assertEqual(recon.step_number, 1)
        self.assertEqual(recon.source_type, StepSourceType.POLICY_SOURCED)
        self.assertEqual(recon.source_reference, "https://pmkisan.gov.in")

    def test_guidance_package_complete_roundtrip(self):
        """Full ApplicationGuidancePackage roundtrip serialization."""
        pkg = ApplicationGuidancePackage(
            application_id="app_test_123",
            scheme_id="scheme_post_matric",
            scheme_name="Post Matric Scholarship",
            statutory_decision="PASS",
            readiness_status="READY_TO_APPLY",
            readiness={"status": "READY_TO_APPLY", "reason": "All checks satisfied"},
            eligibility=EligibilitySummary(status="PASS", summary="Criteria met"),
            documents={"available": ["Income Certificate"], "missing": [], "conflicted": []},
            information={"known": ["age: 20"], "missing": [], "conflicted": []},
            benefit=BenefitGuidance(status="CALCULATED", amount=12000.0, currency="INR"),
            application={"mode": "ONLINE", "official_portal_url": "https://scholarships.gov.in", "steps": []},
            actions=[{"action_type": "VISIT_OFFICIAL_PORTAL", "title": "Visit Portal"}],
            warnings=[],
            sources=[SourceCitation(scheme_id="scheme_post_matric", scheme_name="Scholarship", source_authority="Ministry of Education")],
            policy_snapshot_version="snapshot_20260921_193823",
            rule_version="1.0.0",
            language="en",
        )
        d = pkg.to_dict()
        self.assertEqual(d["application_id"], "app_test_123")
        self.assertEqual(d["statutory_decision"], "PASS")

        recon = ApplicationGuidancePackage.from_dict(d)
        self.assertEqual(recon.application_id, pkg.application_id)
        self.assertEqual(recon.statutory_decision, "PASS")
        self.assertEqual(recon.eligibility.summary, "Criteria met")
        self.assertEqual(recon.benefit.amount, 12000.0)


if __name__ == "__main__":
    unittest.main()
