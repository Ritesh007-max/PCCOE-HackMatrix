"""
Unit tests for DocumentGuidanceBuilder.
Phase 11: Validates document requirements, preparation notes, and status detection.
"""

import unittest
from src.application.case import ApplicationCase, DocumentReference
from src.guidance.documents import DocumentGuidanceBuilder


class TestDocumentGuidance(unittest.TestCase):
    """Tests for DocumentGuidanceBuilder."""

    def test_document_requirements_categorization(self):
        """Categorizes attached vs missing documents accurately."""
        case = ApplicationCase()
        case.attach_document(
            DocumentReference(
                document_id="doc_inc_1",
                filename="income_cert.pdf",
                document_type="income_certificate",
            )
        )

        guidance = DocumentGuidanceBuilder.build_guidance(
            case=case,
            required_doc_types=["income_certificate", "caste_certificate"],
        )

        self.assertIn("Income Certificate", guidance["available"])
        self.assertIn("Caste / Social Category Certificate", guidance["missing"])
        self.assertEqual(len(guidance["items"]), 2)

        # Inspect preparation notes and authority
        inc_item = next(it for it in guidance["items"] if it["document_type"] == "income_certificate")
        self.assertEqual(inc_item["status"], "AVAILABLE")
        self.assertIn("Revenue Department", inc_item["issuing_authority"])
        self.assertTrue(inc_item["already_provided"])

        caste_item = next(it for it in guidance["items"] if it["document_type"] == "caste_certificate")
        self.assertEqual(caste_item["status"], "MISSING")
        self.assertFalse(caste_item["already_provided"])
        self.assertIn("Sub-Divisional Magistrate", caste_item["issuing_authority"])

    def test_unfamiliar_document_safe_fallback(self):
        """Unrecognized custom document uses safe fallback notes without hallucination."""
        case = ApplicationCase()
        case.attach_document(
            DocumentReference(
                document_id="doc_custom_1",
                filename="special_affidavit.pdf",
                document_type="custom_notary_affidavit",
            )
        )

        guidance = DocumentGuidanceBuilder.build_guidance(
            case=case,
            required_doc_types=["custom_notary_affidavit"],
        )

        item = guidance["items"][0]
        self.assertEqual(item["status"], "AVAILABLE")
        self.assertEqual(item["issuing_authority"], "Not specified in available policy evidence.")


if __name__ == "__main__":
    unittest.main()
