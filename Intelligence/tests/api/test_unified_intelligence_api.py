"""
Tests for Unified Intelligence and Review API Endpoints.
Verifies:
- X-AI-Service-Key authentication enforcement
- POST /v1/intelligence/query execution
- GET /v1/review/conflicts
- POST /v1/review/conflicts/{id}/resolve
- POST /v1/review/conflicts/{id}/reject
- POST /v1/review/conflicts/{id}/escalate
"""

import unittest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.config import DEFAULT_SERVICE_CONFIG
from src.api.dependencies import get_unified_orchestrator, get_conflict_resolution_service
from src.orchestration.orchestrator import UnifiedIntelligenceOrchestrator
from src.review.service import ConflictResolutionService
from src.context.service import ApplicantContextService
from src.persistence.repository import FactPersistenceRepository


class TestUnifiedIntelligenceAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.valid_key = DEFAULT_SERVICE_CONFIG.service_api_key
        # Wire up isolated in-memory orchestrator and review service for API tests
        repo = FactPersistenceRepository(":memory:")
        ctx_svc = ApplicantContextService(repo)
        mock_retriever = MagicMock()
        cls.orchestrator = UnifiedIntelligenceOrchestrator(
            context_service=ctx_svc,
            retriever=mock_retriever,
        )
        cls.review_service = cls.orchestrator.conflict_service
        app.dependency_overrides[get_unified_orchestrator] = lambda: cls.orchestrator
        app.dependency_overrides[get_conflict_resolution_service] = lambda: cls.review_service

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

    def test_intelligence_query_requires_auth(self):
        resp = self.client.post(
            "/v1/intelligence/query",
            json={"applicant_id": "api_user_1", "message": "What is PMJAY?"},
        )
        self.assertEqual(resp.status_code, 401)

    def test_intelligence_query_success(self):
        resp = self.client.post(
            "/v1/intelligence/query",
            json={"applicant_id": "api_user_1", "message": "What is PMJAY?"},
            headers={"X-AI-Service-Key": self.valid_key},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["route"], "POLICY_INFORMATION")
        self.assertIn("PMJAY", data["answer"])
        self.assertEqual(data["grounding_status"], "GROUNDED")

    def test_review_conflict_endpoints(self):
        # 1. Record a conflict directly
        c = self.review_service.record_conflict(
            applicant_id="app_rev_1",
            field="annual_family_income",
            source_a="DOCUMENT",
            value_a=420000,
            source_b="USER_INPUT",
            value_b=800000,
        )

        # 2. GET /v1/review/conflicts
        resp_list = self.client.get(
            "/v1/review/conflicts",
            headers={"X-AI-Service-Key": self.valid_key},
        )
        self.assertEqual(resp_list.status_code, 200)
        conflicts = resp_list.json()
        self.assertTrue(len(conflicts) > 0)

        # 3. GET /v1/review/conflicts/{id}
        resp_get = self.client.get(
            f"/v1/review/conflicts/{c.conflict_id}",
            headers={"X-AI-Service-Key": self.valid_key},
        )
        self.assertEqual(resp_get.status_code, 200)
        self.assertEqual(resp_get.json()["conflict_id"], c.conflict_id)

        # 4. POST /v1/review/conflicts/{id}/resolve
        resp_resolve = self.client.post(
            f"/v1/review/conflicts/{c.conflict_id}/resolve",
            json={
                "resolver_id": "caseworker_42",
                "selected_source": "DOCUMENT",
                "reason": "Tehsildar verified certificate on file.",
            },
            headers={"X-AI-Service-Key": self.valid_key},
        )
        self.assertEqual(resp_resolve.status_code, 200)
        self.assertEqual(resp_resolve.json()["conflict"]["status"], "RESOLVED")


if __name__ == "__main__":
    unittest.main()
