"""
FIN Phase B: Dynamic PDF Fact Citation Integrity Regression Test Suite.

Tests:
1. Income located on Page 1 produces Page 1 citation.
2. Income located on Page 2 produces Page 2 citation and NEVER Page 1.
3. Income located on Page 3 produces Page 3 citation and NEVER Page 1.
4. Same income value appearing on multiple pages disambiguates to correct page via field context.
5. Different income values across documents flag REVIEW and cite actual respective pages.
6. Missing page provenance explicitly marks page as Unknown, never falsely asserting Page 1.
7. Single-page PDF without page delimiters preserves Page 1 behavior.
8. Deleted / inactive source document is excluded without fabricating citations.
9. Cross-applicant citation isolation ensures no citation leakage across tenants.
10. Direct fact-level page provenance precedence is honored.
"""

import sys
import unittest
from pathlib import Path

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.api.routes.chat import (
    resolve_document_fact_page,
    format_document_citation_page,
)
from src.extraction.models import (
    ApplicantFact,
    FactSourceType,
    FactVerificationStatus,
)
from src.context.service import ApplicantContextService


class TestPhaseBCitationIntegrity(unittest.TestCase):

    def setUp(self):
        self.context_service = ApplicantContextService()

    # -------------------------------------------------------------------------
    # Test 1: Income located on Page 1
    # -------------------------------------------------------------------------
    def test_income_located_on_page_1(self):
        doc = {
            "id": "doc_p1",
            "file_name": "Income_Cert_P1.pdf",
            "extracted_text": (
                "--- [Page 1] ---\n"
                "GOVERNMENT OF GUJARAT\n"
                "Revenue Department\n"
                "Annual Family Income: ₹1,50,000\n"
                "Certificate No: GJR-2026-901\n\n"
                "--- [Page 2] ---\n"
                "General Statutory Terms and Signatures.\n"
            ),
            "extracted_fields": {
                "annual_family_income": "150000",
                "document_number": "GJR-2026-901"
            }
        }
        page = resolve_document_fact_page(doc, "150000", "annual_family_income")
        self.assertEqual(page, 1)
        self.assertEqual(format_document_citation_page(page), "Page 1")

    # -------------------------------------------------------------------------
    # Test 2: Income located on Page 2 (Must NOT produce Page 1)
    # -------------------------------------------------------------------------
    def test_income_located_on_page_2_does_not_produce_page_1(self):
        doc = {
            "id": "doc_p2",
            "file_name": "Revenue_Record_P2.pdf",
            "extracted_text": (
                "--- [Page 1] ---\n"
                "APPLICATION COVER PAGE\n"
                "Instructions for Verification Officer.\n\n"
                "--- [Page 2] ---\n"
                "OFFICIAL VALUATION RECORD\n"
                "The competent authority certifies that Annual Family Income is ₹2,20,000.\n"
                "Certificate Reference: REV-VAL-7712\n\n"
                "--- [Page 3] ---\n"
                "Appendix: List of Authorized Signatories.\n"
            ),
            "extracted_fields": {
                "annual_family_income": "220000",
                "document_number": "REV-VAL-7712"
            }
        }
        page = resolve_document_fact_page(doc, "220000", "annual_family_income")
        self.assertNotEqual(page, 1, "Income on Page 2 must not produce a Page 1 citation")
        self.assertEqual(page, 2)
        self.assertEqual(format_document_citation_page(page), "Page 2")

    # -------------------------------------------------------------------------
    # Test 3: Income located on Page 3 (Must NOT produce Page 1)
    # -------------------------------------------------------------------------
    def test_income_located_on_page_3_does_not_produce_page_1(self):
        doc = {
            "id": "doc_p3",
            "file_name": "Multi_Assessment_P3.pdf",
            "extracted_text": (
                "--- [Page 1] ---\n"
                "Cover Page & Index.\n\n"
                "--- [Page 2] ---\n"
                "Land & Domicile Assessment.\n\n"
                "--- [Page 3] ---\n"
                "FINAL REVENUE CERTIFICATE\n"
                "Annual Family Income is declared as ₹3,40,000 only.\n"
                "Issuing Officer: Tahsildar Anand.\n"
            ),
            "extracted_fields": {
                "annual_family_income": "340000"
            }
        }
        page = resolve_document_fact_page(doc, "340000", "annual_family_income")
        self.assertNotEqual(page, 1, "Income on Page 3 must not produce a Page 1 citation")
        self.assertEqual(page, 3)
        self.assertEqual(format_document_citation_page(page), "Page 3")

    # -------------------------------------------------------------------------
    # Test 4: Same income value appearing on multiple pages
    # -------------------------------------------------------------------------
    def test_same_income_appearing_on_multiple_pages(self):
        """
        Page 1 mentions application processing fee ₹1,80,000 (casual mention).
        Page 2 specifies 'Annual Family Income: ₹1,80,000'.
        Resolver must prioritize Page 2 using field context disambiguation.
        """
        doc = {
            "id": "doc_multi_mention",
            "file_name": "Audit_Report.pdf",
            "extracted_text": (
                "--- [Page 1] ---\n"
                "Bank deposit balance guarantee: ₹1,80,000.\n\n"
                "--- [Page 2] ---\n"
                "Statutory Income Certification:\n"
                "Total Annual Family Income: ₹1,80,000\n"
                "Competent Authority Seal.\n"
            ),
            "extracted_fields": {
                "annual_family_income": "180000"
            }
        }
        page = resolve_document_fact_page(doc, "180000", "annual_family_income")
        self.assertEqual(page, 2, "Field context must disambiguate to Page 2")

    # -------------------------------------------------------------------------
    # Test 5: Different income values across documents
    # -------------------------------------------------------------------------
    def test_different_income_values_across_documents(self):
        doc_a = {
            "id": "doc_a",
            "file_name": "DocA.pdf",
            "extracted_text": (
                "--- [Page 1] ---\nOverview\n\n"
                "--- [Page 2] ---\nAnnual Family Income: ₹1,50,000\n"
            ),
            "extracted_fields": {"annual_family_income": "150000"}
        }
        doc_b = {
            "id": "doc_b",
            "file_name": "DocB.pdf",
            "extracted_text": (
                "--- [Page 1] ---\nIndex\n\n"
                "--- [Page 2] ---\nTerms\n\n"
                "--- [Page 3] ---\nCertified Annual Family Income: ₹2,80,000\n"
            ),
            "extracted_fields": {"annual_family_income": "280000"}
        }

        page_a = resolve_document_fact_page(doc_a, "150000", "annual_family_income")
        page_b = resolve_document_fact_page(doc_b, "280000", "annual_family_income")

        self.assertEqual(page_a, 2, "Doc A income must resolve to Page 2")
        self.assertEqual(page_b, 3, "Doc B income must resolve to Page 3")
        self.assertNotEqual(page_a, 1)
        self.assertNotEqual(page_b, 1)

    # -------------------------------------------------------------------------
    # Test 6: Missing page provenance (unlocatable in multi-page doc)
    # -------------------------------------------------------------------------
    def test_missing_page_provenance_returns_unknown(self):
        doc = {
            "id": "doc_missing",
            "file_name": "Unlocatable_Doc.pdf",
            "extracted_text": (
                "--- [Page 1] ---\nText block without income\n\n"
                "--- [Page 2] ---\nAnother text block without income\n"
            ),
            "extracted_fields": {
                "annual_family_income": "999999"
            }
        }
        page = resolve_document_fact_page(doc, "999999", "annual_family_income")
        self.assertIsNone(page, "Unlocatable fact in multi-page doc must return None")
        self.assertEqual(format_document_citation_page(page), "Page Unknown")

    # -------------------------------------------------------------------------
    # Test 7: Single-page PDF without page delimiters
    # -------------------------------------------------------------------------
    def test_single_page_pdf_without_delimiters(self):
        doc = {
            "id": "doc_single",
            "file_name": "Single_Page_Cert.pdf",
            "extracted_text": "Annual Family Income: ₹1,20,000. Verified by Mamlatdar.",
            "extracted_fields": {"annual_family_income": "120000"}
        }
        page = resolve_document_fact_page(doc, "120000", "annual_family_income")
        self.assertEqual(page, 1, "Single-page document without delimiters must resolve to Page 1")
        self.assertEqual(format_document_citation_page(page), "Page 1")

    # -------------------------------------------------------------------------
    # Test 8: Deleted or inactive source document
    # -------------------------------------------------------------------------
    def test_deleted_or_inactive_source_document(self):
        """
        Documents with status DELETED or INACTIVE are removed from repository and cannot produce citations.
        """
        from src.documents.models import DocumentContent, DocumentType, PageContent
        app_id = "test_applicant_del_check"
        doc = DocumentContent(
            document_id="doc_del_123",
            file_path="mock.pdf",
            file_name="Old_Income_Doc.pdf",
            mime_type="application/pdf",
            document_type=DocumentType.INCOME_CERTIFICATE,
            pages=[PageContent(page_number=1, text="Annual Family Income: 180000")],
        )
        doc_ctx, facts, _ = self.context_service.process_and_store_document(doc, applicant_id=app_id)
        deleted = self.context_service.delete_document(app_id, doc_ctx.document_id)
        self.assertTrue(deleted)

        docs_after = self.context_service.repository.get_applicant_documents(app_id)
        self.assertEqual(len(docs_after), 0)

        # None document returns None without fabricating citations
        page = resolve_document_fact_page(None, "180000", "annual_family_income")
        self.assertIsNone(page)

    # -------------------------------------------------------------------------
    # Test 9: Cross-applicant citation isolation
    # -------------------------------------------------------------------------
    def test_cross_applicant_citation_isolation(self):
        app_1 = "tenant_user_1"
        app_2 = "tenant_user_2"

        self.context_service.record_user_fact(
            applicant_id=app_1,
            fact_key="annual_family_income",
            raw_value="180000",
            source_type=FactSourceType.DOCUMENT,
            verification_status=FactVerificationStatus.EXTRACTED,
            source_document="User1_Income.pdf",
            page_number=2,
        )
        self.context_service.record_user_fact(
            applicant_id=app_2,
            fact_key="annual_family_income",
            raw_value="350000",
            source_type=FactSourceType.DOCUMENT,
            verification_status=FactVerificationStatus.EXTRACTED,
            source_document="User2_Income.pdf",
            page_number=3,
        )

        ctx_1 = self.context_service.get_applicant_context(app_1)
        ctx_2 = self.context_service.get_applicant_context(app_2)

        fact_1 = ctx_1.get_fact("annual_family_income")
        fact_2 = ctx_2.get_fact("annual_family_income")

        self.assertEqual(fact_1.page_number, 2)
        self.assertEqual(fact_1.source_document, "User1_Income.pdf")
        self.assertEqual(fact_2.page_number, 3)
        self.assertEqual(fact_2.source_document, "User2_Income.pdf")

        # Ensure User 1 context has zero facts or citations from User 2
        self.assertNotIn("User2_Income.pdf", [f.source_document for f in ctx_1.all_facts])

    # -------------------------------------------------------------------------
    # Test 10: Direct fact-level page provenance precedence
    # -------------------------------------------------------------------------
    def test_direct_fact_level_page_provenance_precedence(self):
        doc = {
            "id": "doc_fact_page",
            "file_name": "Direct_Page.pdf",
            "page_number": 3,
            "extracted_text": "--- [Page 1] ---\nSome text\n--- [Page 2] ---\n₹1,00,000",
            "extracted_fields": {"annual_family_income": "100000"}
        }
        # If doc.page_number is explicitly set (e.g. from Fact extraction), it must take precedence
        page = resolve_document_fact_page(doc, "100000", "annual_family_income")
        self.assertEqual(page, 3, "Explicit doc.page_number must take precedence")


if __name__ == "__main__":
    unittest.main()
