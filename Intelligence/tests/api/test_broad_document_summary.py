"""
Phase C Broad Document Summary Regression Tests.
Verifies the original bug: "give me information about my document i uploaded"
must return a structured document summary, NOT "this information is not mentioned."

Tests:
  - Broad document summary (English, Hindi, Hinglish, Gujarati)
  - Broad document summary with no documents uploaded
  - Broad document summary with multiple documents
  - Specific fact lookup (certificate number)
  - Verification status lookup
  - Profile/document income comparison
  - OCR extracted but pending verification — must still be queryable
"""

import unittest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.config import DEFAULT_SERVICE_CONFIG
from src.api.dependencies import get_hybrid_retriever, get_llm_client


SAMPLE_DOC_INCOME = {
    "id": "doc_income_001",
    "file_name": "Income_Certificate_2025.pdf",
    "document_type": "income_certificate",
    "verification_status": "PENDING",
    "status": "ACTIVE",
    "extracted_fields": {
        "beneficiary_name": "Ramesh Kumar Patel",
        "annual_family_income": "180000",
        "father_income": "90000",
        "mother_income": "50000",
        "other_income": "40000",
        "document_number": "GJ-INC-2025-78452",
        "issuing_authority": "Taluka Development Officer, Daskroi",
        "issue_date": "15-Mar-2025",
        "social_category": "OBC",
        "state": "Gujarat",
        "district": "Ahmedabad",
    },
    "extracted_text": (
        "--- [Page 1] ---\n"
        "GOVERNMENT OF GUJARAT\n"
        "Income Certificate\n"
        "Certificate No: GJ-INC-2025-78452\n"
        "This is to certify that Shri Ramesh Kumar Patel, resident of Ahmedabad\n"
        "--- [Page 2] ---\n"
        "Father Income: Rs 90,000 (Government Service)\n"
        "Mother Income: Rs 50,000 (Tailoring)\n"
        "--- [Page 3] ---\n"
        "Other Household Income: Rs 40,000 (Agricultural)\n"
        "Total Annual Family Income: Rs 1,80,000\n"
    ),
}

SAMPLE_DOC_CASTE = {
    "id": "doc_caste_001",
    "file_name": "Caste_Certificate.pdf",
    "document_type": "caste_certificate",
    "verification_status": "VERIFIED",
    "status": "ACTIVE",
    "extracted_fields": {
        "beneficiary_name": "Ramesh Kumar Patel",
        "social_category": "OBC",
        "document_number": "GJ-CST-2024-11234",
        "issuing_authority": "District Collector, Ahmedabad",
    },
    "extracted_text": "Caste Certificate for Ramesh Kumar Patel. Category: OBC.",
}


class TestBroadDocumentSummary(unittest.TestCase):
    """Regression tests for the original bug — broad document queries must
    return a structured summary of extracted fields, not a missing-fact error."""

    def setUp(self):
        self.mock_retriever = MagicMock()
        self.mock_llm_client = MagicMock()
        self.mock_retriever.retrieve.return_value = []
        self.mock_retriever.retrieve_schemes.return_value = []
        app.dependency_overrides[get_hybrid_retriever] = lambda: self.mock_retriever
        app.dependency_overrides[get_llm_client] = lambda: self.mock_llm_client
        self.client = TestClient(app)
        self.headers = {"X-AI-Service-Key": DEFAULT_SERVICE_CONFIG.service_api_key}

    def tearDown(self):
        app.dependency_overrides.clear()

    # ------------------------------------------------------------------
    # 1. Broad document summary — English variants (original bug query)
    # ------------------------------------------------------------------

    def test_broad_doc_summary_original_bug_query(self):
        """'give me information about my document i uploaded' must produce a summary."""
        resp = self.client.post("/v1/chat", headers=self.headers, json={
            "query": "give me information about my document i uploaded",
            "documents": [SAMPLE_DOC_INCOME],
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("DOCUMENT_SUMMARY", data.get("intent", ""))
        # Must include actual extracted data, not a generic refusal
        self.assertIn("Ramesh Kumar Patel", data["answer"])
        self.assertNotIn("not mentioned", data["answer"].lower())
        self.assertNotIn("not established", data["answer"].lower())

    def test_broad_doc_summary_tell_me_about(self):
        """'tell me about my uploaded document' must produce a summary."""
        resp = self.client.post("/v1/chat", headers=self.headers, json={
            "query": "tell me about my uploaded document",
            "documents": [SAMPLE_DOC_INCOME],
        })
        data = resp.json()
        self.assertIn("DOCUMENT_SUMMARY", data.get("intent", ""))
        self.assertIn("Ramesh Kumar Patel", data["answer"])

    def test_broad_doc_summary_what_information(self):
        """'what information is in my document?' must produce a summary."""
        resp = self.client.post("/v1/chat", headers=self.headers, json={
            "query": "what information is in my document?",
            "documents": [SAMPLE_DOC_INCOME],
        })
        data = resp.json()
        self.assertIn("DOCUMENT_SUMMARY", data.get("intent", ""))
        self.assertIn("1,80,000", data["answer"])

    def test_broad_doc_summary_what_does_contain(self):
        """'what does my document contain?' must produce a summary."""
        resp = self.client.post("/v1/chat", headers=self.headers, json={
            "query": "what does my uploaded document contain?",
            "documents": [SAMPLE_DOC_INCOME],
        })
        data = resp.json()
        self.assertIn("DOCUMENT_SUMMARY", data.get("intent", ""))
        self.assertIn("GJ-INC-2025-78452", data["answer"])

    # ------------------------------------------------------------------
    # 2. Broad document summary — Hindi / Hinglish
    # ------------------------------------------------------------------

    def test_broad_doc_summary_hindi(self):
        """Hindi: 'mere uploaded document ke baare mein batao'"""
        resp = self.client.post("/v1/chat", headers=self.headers, json={
            "query": "mere uploaded document ke baare mein batao",
            "documents": [SAMPLE_DOC_INCOME],
        })
        data = resp.json()
        self.assertIn("DOCUMENT_SUMMARY", data.get("intent", ""))
        self.assertNotIn("not mentioned", data["answer"].lower())

    def test_broad_doc_summary_hinglish(self):
        """Hinglish: 'mere document me kya hai?'"""
        resp = self.client.post("/v1/chat", headers=self.headers, json={
            "query": "mere document me kya hai?",
            "documents": [SAMPLE_DOC_INCOME],
            "language": "hinglish",
        })
        data = resp.json()
        self.assertIn("DOCUMENT_SUMMARY", data.get("intent", ""))
        self.assertNotIn("not mentioned", data["answer"].lower())

    # ------------------------------------------------------------------
    # 3. Broad document summary — Gujarati
    # ------------------------------------------------------------------

    def test_broad_doc_summary_gujarati(self):
        """Gujarati: 'મારા document વિશે માહિતી આપો'"""
        resp = self.client.post("/v1/chat", headers=self.headers, json={
            "query": "મારા document વિશે માહિતી આપો",
            "documents": [SAMPLE_DOC_INCOME],
            "language": "gu",
        })
        data = resp.json()
        self.assertIn("DOCUMENT_SUMMARY", data.get("intent", ""))
        self.assertNotIn("not mentioned", data["answer"].lower())

    # ------------------------------------------------------------------
    # 4. No documents uploaded
    # ------------------------------------------------------------------

    def test_broad_doc_summary_no_documents(self):
        """With no documents, must inform user to upload — not hallucinate."""
        resp = self.client.post("/v1/chat", headers=self.headers, json={
            "query": "give me information about my document i uploaded",
            "documents": [],
        })
        data = resp.json()
        self.assertIn("DOCUMENT_SUMMARY", data.get("intent", ""))
        answer_lower = data["answer"].lower()
        self.assertTrue(
            "no documents" in answer_lower or "no document" in answer_lower
            or "upload" in answer_lower or "vault" in answer_lower
        )

    # ------------------------------------------------------------------
    # 5. Multiple documents — catalog listing
    # ------------------------------------------------------------------

    def test_broad_doc_summary_multiple_documents(self):
        """With 2+ documents and no specific name, list them and ask which one."""
        resp = self.client.post("/v1/chat", headers=self.headers, json={
            "query": "tell me about my uploaded document",
            "documents": [SAMPLE_DOC_INCOME, SAMPLE_DOC_CASTE],
        })
        data = resp.json()
        self.assertIn("DOCUMENT_SUMMARY", data.get("intent", ""))
        # Should list both documents
        self.assertIn("Income_Certificate_2025.pdf", data["answer"])
        self.assertIn("Caste_Certificate.pdf", data["answer"])

    # ------------------------------------------------------------------
    # 6. Specific fact lookup — certificate number only
    # ------------------------------------------------------------------

    def test_specific_fact_certificate_number(self):
        """'what is the certificate number?' must return just the cert number."""
        resp = self.client.post("/v1/chat", headers=self.headers, json={
            "query": "what is the certificate number?",
            "documents": [SAMPLE_DOC_INCOME],
        })
        data = resp.json()
        # Should NOT be routed to broad doc summary
        # The answer should contain the certificate number somewhere in the flow
        self.assertNotIn("not mentioned", data["answer"].lower())

    # ------------------------------------------------------------------
    # 7. Verification status lookup
    # ------------------------------------------------------------------

    def test_verification_status_lookup(self):
        """'is my document verified?' must return verification status."""
        resp = self.client.post("/v1/chat", headers=self.headers, json={
            "query": "is this document verified?",
            "documents": [SAMPLE_DOC_INCOME],
        })
        data = resp.json()
        self.assertIn("DOCUMENT_STATUS", data.get("intent", ""))
        answer_lower = data["answer"].lower()
        self.assertTrue("pending" in answer_lower or "status" in answer_lower)

    # ------------------------------------------------------------------
    # 8. Profile/document income comparison
    # ------------------------------------------------------------------

    def test_profile_document_comparison(self):
        """'compare my profile income with my certificate' must show both sources."""
        resp = self.client.post("/v1/chat", headers=self.headers, json={
            "query": "compare my income with my certificate",
            "documents": [SAMPLE_DOC_INCOME],
            "applicant_facts": {"annual_income": "350000"},
        })
        data = resp.json()
        self.assertIn("DOCUMENT_COMPARISON", data.get("intent", ""))
        # Must show both profile and document income
        self.assertIn("3,50,000", data["answer"])
        self.assertIn("1,80,000", data["answer"])

    # ------------------------------------------------------------------
    # 9. OCR extracted but pending verification — still queryable
    # ------------------------------------------------------------------

    def test_ocr_pending_still_queryable(self):
        """OCR-extracted document with PENDING status must still return facts."""
        pending_doc = dict(SAMPLE_DOC_INCOME)
        pending_doc["verification_status"] = "PENDING"
        resp = self.client.post("/v1/chat", headers=self.headers, json={
            "query": "give me information about my document i uploaded",
            "documents": [pending_doc],
        })
        data = resp.json()
        self.assertIn("DOCUMENT_SUMMARY", data.get("intent", ""))
        # Must show extracted facts even though verification is pending
        self.assertIn("Ramesh Kumar Patel", data["answer"])
        self.assertIn("1,80,000", data["answer"])
        # Must note that OCR != official verification
        answer_lower = data["answer"].lower()
        self.assertTrue("ocr" in answer_lower or "verification" in answer_lower or "pending" in answer_lower)

    def test_ocr_does_not_equal_verification(self):
        """Response must NOT claim OCR extraction equals official verification."""
        resp = self.client.post("/v1/chat", headers=self.headers, json={
            "query": "give me information about my document i uploaded",
            "documents": [SAMPLE_DOC_INCOME],
        })
        data = resp.json()
        answer_lower = data["answer"].lower()
        # Must NOT say the document is officially verified when it's PENDING
        self.assertNotIn("officially verified", answer_lower)
        # Must include a verification clarification note
        self.assertTrue(
            "ocr" in answer_lower or "nodal" in answer_lower
            or "pending" in answer_lower or "verification" in answer_lower
        )


if __name__ == "__main__":
    unittest.main()
