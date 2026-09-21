"""
Unit tests for PolicySetu Multi-Document Evidence and Provenance Layer.
Verifies corroboration, conflict detection, deterministic engine integration, and critical safety invariants.
"""

import unittest
import sys
from pathlib import Path

_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from src.extraction.models import (
    ApplicantFact,
    FactVerificationStatus,
    ExtractionMethod,
)
from src.documents.provenance import DocumentProvenance, DocumentType
from src.documents.evidence import EvidenceRegistry
from src.rules.evaluator import RuleEvaluator
from src.rules.models import Rule, RuleStatus


class TestEvidence(unittest.TestCase):
    """Tests multi-document evidence aggregation, conflict handling, and engine bridge."""

    def setUp(self):
        self.evaluator = RuleEvaluator()

    def test_duplicate_corroborating_evidence(self):
        """
        Tests that multiple documents providing the same normalized value
        corroborate each other and elevate verification status without conflict.
        """
        registry = EvidenceRegistry(applicant_id="app_123")

        # Document A: Extracted from Form
        registry.record_fact(
            field="annual_family_income",
            value="4.2 Lakh",
            source_document="application_form.pdf",
            extraction_method=ExtractionMethod.FORM_FIELD.value,
            verification_status=FactVerificationStatus.EXTRACTED,
            confidence=0.9
        )

        # Document B: Verified from Tahsildar Income Certificate
        registry.record_fact(
            field="annual_family_income",
            value="₹4,20,000",
            source_document="income_certificate_2024.pdf",
            extraction_method=ExtractionMethod.ISSUER_API.value,
            verification_status=FactVerificationStatus.ISSUER_VERIFIED,
            confidence=1.0
        )

        # Assert no conflict exists
        self.assertFalse(registry.has_conflict("annual_family_income"))
        self.assertEqual(len(registry.get_conflicted_fields()), 0)

        # Assert consolidated fact takes highest trust tier
        consolidated = registry.get_consolidated_fact("annual_family_income")
        self.assertIsNotNone(consolidated)
        self.assertEqual(consolidated.normalized_value, 420000.0)
        self.assertEqual(consolidated.verification_status, FactVerificationStatus.ISSUER_VERIFIED)

        # Compile to ApplicantProfile and evaluate with RuleEvaluator
        profile = registry.to_applicant_profile()
        rule = Rule(
            rule_id="R_INC_01",
            scheme_id="test_scheme",
            rule_type="eligibility",
            field="annual_family_income",
            operator="<=",
            expected_value=500000.0,
            value_type="numeric"
        )
        result = self.evaluator.evaluate_rule(rule, profile)
        self.assertEqual(result.status, RuleStatus.PASS)

    def test_conflicting_evidence_across_documents(self):
        """
        Requirement 4 & User Rule:
        Document A -> income = 420000
        Document B -> income = 610000
        This MUST produce CONFLICTED / REVIEW and never silently choose one value.
        CRITICAL INVARIANT: UNKNOWN or CONFLICTED facts must never be converted into PASS;
        conflicting facts must produce REVIEW.
        """
        registry = EvidenceRegistry(applicant_id="app_456")

        # Document A
        registry.record_fact(
            field="annual_family_income",
            value=420000,
            source_document="Document_A_Self_Declaration.pdf",
            verification_status=FactVerificationStatus.SELF_REPORTED,
        )

        # Document B (contradictory value)
        registry.record_fact(
            field="annual_family_income",
            value=610000,
            source_document="Document_B_ITR_Assessment.pdf",
            verification_status=FactVerificationStatus.ISSUER_VERIFIED,
        )

        # Assert conflict is flagged
        self.assertTrue(registry.has_conflict("annual_family_income"))
        self.assertIn("annual_family_income", registry.get_conflicted_fields())

        consolidated = registry.get_consolidated_fact("annual_family_income")
        self.assertIsNotNone(consolidated)
        self.assertEqual(consolidated.verification_status, FactVerificationStatus.CONFLICTED)
        self.assertIsNone(consolidated.normalized_value)

        # Build ApplicantProfile
        profile = registry.to_applicant_profile()
        self.assertTrue(profile.has_conflict("annual_family_income"))

        # Evaluate against rule that would have passed with 420000
        rule = Rule(
            rule_id="R_INC_02",
            scheme_id="test_scheme",
            rule_type="eligibility",
            field="annual_family_income",
            operator="<=",
            expected_value=500000.0,
            value_type="numeric"
        )
        result = self.evaluator.evaluate_rule(rule, profile)

        # CRITICAL INVARIANT ASSERTION
        self.assertEqual(
            result.status,
            RuleStatus.REVIEW,
            "Conflicting facts MUST produce REVIEW and must never convert to PASS or silently pick a value."
        )
        self.assertIn("Contradictory evidence", result.reason)

    def test_missing_evidence_remains_unknown(self):
        """
        Requirements 6 & 7:
        Do not invent missing values. Missing values must remain UNKNOWN.
        CRITICAL INVARIANT: UNKNOWN facts must never be converted into PASS.
        """
        registry = EvidenceRegistry(applicant_id="app_789")
        # Only provide age
        registry.record_fact(
            field="age",
            value="24 years",
            source_document="aadhaar.pdf"
        )

        profile = registry.to_applicant_profile()
        self.assertFalse(profile.has_field("annual_family_income"))

        # Evaluate rule on unprovided field
        rule = Rule(
            rule_id="R_INC_03",
            scheme_id="test_scheme",
            rule_type="eligibility",
            field="annual_family_income",
            operator="<=",
            expected_value=250000.0,
            value_type="numeric"
        )
        result = self.evaluator.evaluate_rule(rule, profile)

        self.assertEqual(
            result.status,
            RuleStatus.UNKNOWN,
            "Missing facts MUST return UNKNOWN (never PASS, never FAIL)."
        )

    def test_provenance_preservation(self):
        """
        Requirement 9: Preserve source document, page number, text span, and issuer metadata.
        """
        provenance = DocumentProvenance(
            source_document="assam_domicile_cert.pdf",
            document_type=DocumentType.DOMICILE_CERTIFICATE,
            issuer="Deputy Commissioner, Kamrup Metro",
            issue_date="2023-08-15",
            page_number=1,
            text_span="Permanent resident of the State of Assam since birth"
        )

        registry = EvidenceRegistry(applicant_id="app_domicile")
        fact = registry.record_fact(
            field="state",
            value="Assam",
            source_document=provenance.source_document,
            page_number=provenance.page_number,
            text_span=provenance.text_span,
            provenance=provenance,
            verification_status=FactVerificationStatus.ISSUER_VERIFIED
        )

        self.assertEqual(fact.source_document, "assam_domicile_cert.pdf")
        self.assertEqual(fact.page_number, 1)
        self.assertEqual(fact.text_span, "Permanent resident of the State of Assam since birth")
        self.assertIn("provenance", fact.metadata)
        self.assertEqual(fact.metadata["provenance"]["issuer"], "Deputy Commissioner, Kamrup Metro")


if __name__ == "__main__":
    unittest.main()
