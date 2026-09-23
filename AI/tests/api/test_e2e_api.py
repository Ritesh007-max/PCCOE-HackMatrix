"""
End-to-End API Integration Workflow Test.
Verifies the complete citizen workflow across all microservice endpoints:
1. Health liveness & readiness check
2. Document pre-processing
3. Statutory scheme search
4. Deterministic eligibility check
5. Grounded chat inquiry
6. Application full analysis
"""

import unittest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.config import DEFAULT_SERVICE_CONFIG
from src.api.dependencies import get_application_pipeline, get_hybrid_retriever, get_llm_client
from src.pipelines.application_pipeline import ApplicationResult
from src.rag.models import RetrievedChunk, SchemeRetrievalResult, SourceTier
from src.llm.router import ProviderExecutionResult


class TestEndToEndApiWorkflow(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.headers = {"X-AI-Service-Key": DEFAULT_SERVICE_CONFIG.service_api_key}

        # Mock retriever
        self.mock_retriever = MagicMock()
        self.mock_chunk = RetrievedChunk(
            chunk_id="chunk_e2e_01",
            content="PM Kisan Samman Nidhi provides financial assistance of Rs 6,000 per year.",
            scheme_slug="pm-kisan",
            scheme_name="PM Kisan Samman Nidhi",
            source_tier=SourceTier.PRIMARY_SCHEME.value,
            dense_score=0.92,
            rerank_score=0.96,
            metadata={"source_url": "https://pmkisan.gov.in", "ministry": "Ministry of Agriculture", "state": "All-India"},
        )
        self.mock_scheme = SchemeRetrievalResult(
            scheme_slug="pm-kisan",
            scheme_name="PM Kisan Samman Nidhi",
            aggregate_score=0.96,
            best_matching_chunks=[self.mock_chunk],
            source_metadata={"source_url": "https://pmkisan.gov.in", "ministry": "Ministry of Agriculture", "state": "All-India"},
        )
        self.mock_retriever.retrieve.return_value = [self.mock_chunk]
        self.mock_retriever.retrieve_schemes.return_value = [self.mock_scheme]
        app.dependency_overrides[get_hybrid_retriever] = lambda: self.mock_retriever

        # Mock LLM Client
        self.mock_llm_client = MagicMock()
        self.mock_llm_client.generate_with_metadata.return_value = ProviderExecutionResult(
            content="PM Kisan provides Rs 6,000 annually in three equal installments [chunk_e2e_01].",
            provider="gemini",
            model="gemini-2.5-flash",
            status="SUCCESS",
            attempt=1,
            latency_ms=105.0,
            fallback_used=False,
        )
        app.dependency_overrides[get_llm_client] = lambda: self.mock_llm_client

        # Mock ApplicationPipeline
        self.mock_pipeline = MagicMock()
        self.mock_pipeline.process_application.return_value = ApplicationResult(
            application_id="app_e2e_workflow_1",
            steps_completed=21,
            processing_status="SUCCESS",
            documents_processed=[
                {
                    "file_name": "land_record.txt",
                    "document_type": "LAND_RECORD",
                    "mime_type": "text/plain",
                    "page_count": 1,
                    "is_scanned": False,
                    "extraction_method": "NATIVE_PDF",
                    "sha256": "1234567890abcdef",
                }
            ],
            applicant_profile={"owns_cultivable_land": True, "annual_income": 80000},
            conflicts_detected=[],
            query_intent={"intent": "SCHEME_DISCOVERY"},
            retrieved_schemes=[{"scheme_id": "pm-kisan", "name": "PM Kisan"}],
            eligibility_decision={"status": "PASS", "eligible": True},
            benefit_calculation={"status": "CALCULATED", "amount": 6000},
            missing_information={"missing_fields": []},
            explanation={"status": "PASS", "text": "Citizen satisfies statutory eligibility."},
            security_audit={"prompt_injection_detected": False},
            telemetry={"total_latency_ms": 320.0},
        )
        app.dependency_overrides[get_application_pipeline] = lambda: self.mock_pipeline

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_complete_citizen_workflow(self):
        """Executes full citizen lifecycle from diagnostics through application analysis."""
        # Step 1: Check Liveness & Readiness
        live_resp = self.client.get("/health/live")
        self.assertEqual(live_resp.status_code, 200)

        ready_resp = self.client.get("/health/ready", headers=self.headers)
        self.assertEqual(ready_resp.status_code, 200)

        # Step 2: Document Pre-Ingestion
        doc_resp = self.client.post(
            "/v1/documents/process",
            headers=self.headers,
            files=[("files", ("land_record.txt", b"Cultivable land record: 1.2 Hectares", "text/plain"))],
        )
        self.assertEqual(doc_resp.status_code, 200)
        self.assertEqual(doc_resp.json()["document_count"], 1)

        # Step 3: Statutory Scheme Search
        search_resp = self.client.post(
            "/v1/schemes/search",
            headers=self.headers,
            json={"query": "farmer income support", "top_k": 3},
        )
        self.assertEqual(search_resp.status_code, 200)
        self.assertTrue(search_resp.json()["total_results"] > 0)

        # Step 4: Deterministic Eligibility Check (Zero LLM)
        elig_resp = self.client.post(
            "/v1/eligibility/check",
            headers=self.headers,
            json={
                "applicant_facts": {
                    "owns_cultivable_land": True,
                    "is_institutional_landholder": False,
                    "is_taxpayer": False,
                    "monthly_pension_amount": 0,
                },
                "scheme_ids": ["pm-kisan"],
            },
        )
        self.assertEqual(elig_resp.status_code, 200)
        elig_data = elig_resp.json()
        self.assertEqual(elig_data["evaluations"][0]["status"], "PASS")
        self.assertTrue(elig_data["evaluations"][0]["is_eligible"])

        # Step 5: Grounded Chat Follow-up
        chat_resp = self.client.post(
            "/v1/chat",
            headers=self.headers,
            json={"query": "How will I receive the PM Kisan payment?", "conversation_id": "conv_e2e_456"},
        )
        self.assertEqual(chat_resp.status_code, 200)
        chat_data = chat_resp.json()
        self.assertIn("6,000", chat_data["answer"])
        self.assertTrue(len(chat_data["citations"]) > 0)

        # Step 6: Full Application Analysis (Phase 8 21-step Pipeline)
        analyze_resp = self.client.post(
            "/v1/applications/analyze",
            headers=self.headers,
            files=[("files", ("land_record.txt", b"Cultivable land record: 1.2 Hectares", "text/plain"))],
            data={"query": "Apply for farmer subsidy", "target_scheme": "pm-kisan"},
        )
        self.assertEqual(analyze_resp.status_code, 200)
        analyze_data = analyze_resp.json()
        self.assertEqual(analyze_data["steps_completed"], 21)
        self.assertEqual(analyze_data["processing_status"], "SUCCESS")
        self.assertEqual(analyze_data["eligibility_decision"]["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
