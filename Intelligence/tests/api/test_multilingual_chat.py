"""
Tests for FIN Multilingual NLP and Website Assistance (/v1/chat).
Verifies:
1. Multilingual response invariant (Hindi, Gujarati, English, Hinglish).
2. Website architecture and navigation questions.
3. Strict question scope understanding.
4. Clean deterministic no-evidence messaging.
"""

import unittest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.config import DEFAULT_SERVICE_CONFIG
from src.api.dependencies import get_llm_client, get_hybrid_retriever
from src.llm.client import LLMClient
from src.llm.router import ProviderExecutionResult
from src.rag.retriever import HybridRetriever


class TestMultilingualChatEndpoints(unittest.TestCase):
    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClient)
        self.mock_llm_client.generate.return_value = "આ PMEGP યોજના હેઠળ જરૂરી દસ્તાવેજો છે: આધાર કાર્ડ, પાન કાર્ડ, અને પ્રોજેક્ટ રિપોર્ટ."
        self.mock_llm_client.generate_with_metadata.return_value = ProviderExecutionResult(
            content="FIN Citizen Dashboard provides a comprehensive view of your active applications and recommended schemes.",
            provider="mock",
            model="mock-model",
            status="SUCCESS",
            attempt=1,
            latency_ms=12.5,
            fallback_used=False,
        )

        self.mock_retriever = MagicMock(spec=HybridRetriever)
        self.mock_retriever.retrieve.return_value = []
        self.mock_retriever.retrieve_schemes.return_value = []

        app.dependency_overrides[get_llm_client] = lambda: self.mock_llm_client

        self.client = TestClient(app)
        self.headers = {"X-AI-Service-Key": DEFAULT_SERVICE_CONFIG.service_api_key}

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_hindi_query_language_detection_and_response(self):
        payload = {
            "query": "PMEGP योजना के लिए कौन से दस्तावेज आवश्यक हैं?",
            "language": "hi",
            "conversation_id": "conv_hi_01"
        }
        response = self.client.post("/v1/chat", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn(data["detected_language"], ("hi", "hinglish"))
        self.assertIn(data["intent"], ("SCHEME_DISCOVERY", "CANONICAL_SCHEME_DIRECT"))

    def test_gujarati_query_language_detection(self):
        payload = {
            "query": "મને PMEGP યોજના માટે કયા દસ્તાવેજો જોઈએ?",
            "language": "gu",
            "conversation_id": "conv_gu_01"
        }
        response = self.client.post("/v1/chat", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["detected_language"], "gu")

    def test_english_query_canonical_scheme(self):
        payload = {
            "query": "What documents are required for PMEGP?",
            "language": "en",
            "conversation_id": "conv_en_01"
        }
        response = self.client.post("/v1/chat", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["detected_language"], "en")
        self.assertTrue("Document" in data["answer"] or "Aadhaar" in data["answer"])

    def test_website_navigation_question(self):
        self.mock_llm_client.generate_with_metadata.return_value = ProviderExecutionResult(
            content="FIN's Citizen Dashboard allows you to view your application metrics, verified document statuses, and deadlines.",
            provider="mock",
            model="mock-model",
            status="SUCCESS",
            attempt=1,
            latency_ms=10.0,
            fallback_used=False,
        )
        payload = {
            "query": "What is the citizen dashboard on FIN website?",
            "language": "en",
            "conversation_id": "conv_web_01"
        }
        response = self.client.post("/v1/chat", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["intent"], "WEBSITE_NAVIGATION")
        self.assertIn("Dashboard", data["answer"])

    def test_no_evidence_gujarati_response(self):
        app.dependency_overrides[get_hybrid_retriever] = lambda: self.mock_retriever
        payload = {
            "query": "કોઈ અસ્તિત્વમાં ન હોય તેવી યોજના xyz987654321",
            "language": "gu",
            "conversation_id": "conv_gu_no_ev"
        }
        response = self.client.post("/v1/chat", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["detected_language"], "gu")
        self.assertIn("સત્તાવાર રિપોઝિટરીમાં મળ્યા નથી", data["answer"])


    def test_out_of_scope_deflection(self):
        payload = {
            "query": "Write me a python game",
            "language": "en",
            "conversation_id": "conv_oos_01"
        }
        response = self.client.post("/v1/chat", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["intent"], "OUT_OF_SCOPE")
        self.assertIn("FIN AI is focused exclusively", data["answer"])

    def test_document_status_query_with_ocr_clarification(self):
        payload = {
            "query": "Mere documents verify hue hain ya nahi?",
            "language": "hi",
            "conversation_id": "conv_doc_st_01",
            "documents": [
                {
                    "file_name": "Income_Certificate.pdf",
                    "document_type": "income_certificate",
                    "verification_status": "PENDING",
                    "extracted_fields": {"annual_family_income": "180000"}
                }
            ]
        }
        response = self.client.post("/v1/chat", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["intent"], "DOCUMENT_STATUS")
        self.assertIn("Income_Certificate.pdf", data["answer"])
        self.assertIn("OCR", data["answer"])

    def test_profile_vs_certificate_income_comparison(self):
        payload = {
            "query": "Compare my income with my certificate",
            "language": "en",
            "conversation_id": "conv_comp_01",
            "applicant_facts": {"annual_income": "350000"},
            "documents": [
                {
                    "file_name": "Family_Income_Cert.pdf",
                    "extracted_fields": {"annual_family_income": "180000"}
                }
            ]
        }
        response = self.client.post("/v1/chat", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["intent"], "DOCUMENT_COMPARISON")
        self.assertIn("3,50,000", data["answer"])
        self.assertIn("1,80,000", data["answer"])
        self.assertIn("Source Separation", data["answer"])

    def test_application_post_submission_lifecycle(self):
        payload = {
            "query": "Application submit karne ke baad kya hoga?",
            "language": "hi",
            "conversation_id": "conv_app_proc_01"
        }
        response = self.client.post("/v1/chat", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["intent"], "APPLICATION_PROCESS")
        self.assertTrue("5-stage" in data["answer"] or "5-चरणीय" in data["answer"])

    def test_recommendation_reason_signals_and_invariant(self):
        payload = {
            "query": "Ye scheme mere liye kyu suggest hui?",
            "language": "hi",
            "conversation_id": "conv_rec_01"
        }
        response = self.client.post("/v1/chat", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["intent"], "RECOMMENDATION_REASON")
        self.assertTrue("Crucial Invariant" in data["answer"] or "सिफारिश बनाम पात्रता" in data["answer"])
        self.assertIn("eligibility", data["answer"].lower())

    def test_deterministic_eligibility_unknown_explanation(self):
        payload = {
            "query": "Why is my eligibility UNKNOWN?",
            "language": "en",
            "conversation_id": "conv_elig_01"
        }
        response = self.client.post("/v1/chat", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["intent"], "ELIGIBILITY_REASON")
        self.assertIn("PASS", data["answer"])
        self.assertIn("UNKNOWN", data["answer"])

    def test_conversational_follow_up_scheme_resolution(self):
        payload = {
            "query": "documents?",
            "language": "en",
            "conversation_id": "conv_pmegp_followup",
            "conversation_history": [
                {"role": "user", "content": "Tell me about PMEGP"},
                {"role": "assistant", "content": "PMEGP is a credit-linked subsidy scheme."}
            ]
        }
        response = self.client.post("/v1/chat", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["intent"], "SCHEME_DISCOVERY")
        self.assertIn("Required Documents", data["answer"])
        self.assertIn("PMEGP", data["answer"])

    def test_website_capabilities_what_can_i_do(self):
        self.mock_llm_client.generate_with_metadata.return_value = ProviderExecutionResult(
            content="On FIN platform, you can Discover Schemes, get personalized suggestions, upload documents, and track applications.",
            provider="mock",
            model="mock-model",
            status="SUCCESS",
            attempt=1,
            latency_ms=10.0,
            fallback_used=False,
        )
        payload = {
            "query": "What can I do on this website?",
            "language": "en",
            "conversation_id": "conv_web_cap"
        }
        response = self.client.post("/v1/chat", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["intent"], "WEBSITE_NAVIGATION")
        self.assertIn("Discover Schemes", data["answer"])


if __name__ == "__main__":
    unittest.main()

