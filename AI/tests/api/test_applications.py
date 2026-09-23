"""
Test Application Analysis Endpoint.
Verifies POST /v1/applications/analyze directly invokes ApplicationPipeline, validates/transforms
the request, and serializes the 21-step pipeline result.
"""

import unittest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.config import DEFAULT_SERVICE_CONFIG
from src.api.dependencies import get_application_pipeline
from src.pipelines.application_pipeline import ApplicationResult


class TestApplicationEndpoints(unittest.TestCase):
    def setUp(self):
        self.mock_pipeline = MagicMock()
        self.mock_result = ApplicationResult(
            application_id="app_test_999",
            steps_completed=21,
            processing_status="SUCCESS",
            documents_processed=[
                {
                    "file_name": "income_cert.pdf",
                    "document_type": "INCOME_CERTIFICATE",
                    "mime_type": "application/pdf",
                    "page_count": 1,
                    "is_scanned": False,
                    "extraction_method": "NATIVE_PDF",
                    "sha256": "abcdef1234567890",
                }
            ],
            applicant_profile={"annual_income": 120000, "occupation": "farmer"},
            conflicts_detected=[],
            query_intent={"intent": "SCHEME_DISCOVERY"},
            retrieved_schemes=[{"scheme_id": "pm-kisan", "name": "PM Kisan"}],
            eligibility_decision={"status": "PASS", "eligible": True},
            benefit_calculation={"status": "CALCULATED", "amount": 6000},
            missing_information={"missing_fields": []},
            explanation={"status": "PASS", "text": "Applicant is eligible under PM Kisan."},
            security_audit={"prompt_injection_detected": False},
            telemetry={"total_latency_ms": 250.0},
        )
        self.mock_pipeline.process_application.return_value = self.mock_result
        app.dependency_overrides[get_application_pipeline] = lambda: self.mock_pipeline

        self.client = TestClient(app)
        self.headers = {"X-AI-Service-Key": DEFAULT_SERVICE_CONFIG.service_api_key}

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_analyze_unauthenticated(self):
        """Must reject unauthenticated analysis requests with 401."""
        files = [("files", ("test.pdf", b"%PDF-1.4 dummy content", "application/pdf"))]
        resp = self.client.post("/v1/applications/analyze", files=files)
        self.assertEqual(resp.status_code, 401)

    def test_analyze_no_files_rejected(self):
        """Request without any files must be rejected with 422 or 400."""
        resp = self.client.post("/v1/applications/analyze", headers=self.headers)
        self.assertIn(resp.status_code, (400, 422))

    def test_analyze_direct_pipeline_call(self):
        """Verifies that /v1/applications/analyze calls ApplicationPipeline.process_application directly."""
        files = [("files", ("income_cert.txt", b"Income Certificate\nAnnual Income: 120000", "text/plain"))]
        data = {
            "query": "What schemes am I eligible for?",
            "target_scheme": "pm-kisan",
            "session_id": "session_custom_001",
        }
        resp = self.client.post(
            "/v1/applications/analyze",
            headers=self.headers,
            files=files,
            data=data,
        )
        self.assertEqual(resp.status_code, 200)
        res_data = resp.json()

        # Check serialization into ApplicationAnalyzeResponse
        self.assertIn("request_id", res_data)
        self.assertEqual(res_data["application_id"], "app_test_999")
        self.assertEqual(res_data["steps_completed"], 21)
        self.assertEqual(res_data["processing_status"], "SUCCESS")
        self.assertEqual(res_data["eligibility_decision"]["status"], "PASS")

        # Verify ApplicationPipeline was directly invoked
        self.mock_pipeline.process_application.assert_called_once()
        call_kwargs = self.mock_pipeline.process_application.call_args.kwargs
        self.assertEqual(call_kwargs["user_query"], "What schemes am I eligible for?")
        self.assertEqual(call_kwargs["target_scheme"], "pm-kisan")
        self.assertEqual(call_kwargs["session_id"], "session_custom_001")
        self.assertEqual(len(call_kwargs["documents"]), 1)


if __name__ == "__main__":
    unittest.main()
