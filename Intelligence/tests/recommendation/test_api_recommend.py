"""
FIN Phase 19 POST /v1/schemes/recommend API Endpoint Tests.
Verifies HTTP contract, authentication guard, Pydantic request/response schemas,
top_k bounds, and dependency injection overrides.
"""

import unittest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.config import DEFAULT_SERVICE_CONFIG
from src.api.dependencies import get_scheme_recommendation_service
from src.recommendation.models import (
    RecommendationEvidence,
    SchemeRecommendationItem,
    SchemeRecommendationResult,
)


class TestRecommendationApi(unittest.TestCase):
    """Test suite for POST /v1/schemes/recommend."""

    def setUp(self):
        self.mock_service = MagicMock()
        self.mock_evidence = RecommendationEvidence(
            source_tier="PRIMARY_SCHEME",
            source_url="https://myscheme.gov.in/pm-kisan",
            snippets=["PM Kisan Samman Nidhi provides financial support."],
            chunk_ids=["chunk_1"],
            applicant_evidence_ids=["ev_1"],
        )
        self.mock_item = SchemeRecommendationItem(
            scheme_id="pm-kisan",
            scheme_slug="pm-kisan",
            scheme_name="PM Kisan Samman Nidhi",
            relevance_score=0.92,
            compatibility_score=0.88,
            overall_match_score=0.95,
            matched_facts=[{"field": "state", "status": "MATCH"}],
            unmatched_facts=[],
            missing_fields=[],
            missing_fields_status="DETERMINISTIC_RULES",
            conflict_fields=[],
            eligibility_status="PASS",
            is_eligible=True,
            evidence=self.mock_evidence,
            source_metadata={"state": "All India"},
            recommendation_reasons=["Confirmed statutory eligibility PASS."],
        )
        self.mock_result = SchemeRecommendationResult(
            applicant_id="app_test_api",
            query="Which farmer schemes can I apply for?",
            total_candidates_retrieved=1,
            recommendations=[self.mock_item],
            applied_filters={"state_filter": {"value": "Gujarat", "source": "applicant_context"}},
            active_facts_summary={"state": "Gujarat"},
            conflicts_detected=[],
        )
        self.mock_service.recommend_schemes.return_value = self.mock_result

        app.dependency_overrides[get_scheme_recommendation_service] = lambda: self.mock_service
        self.client = TestClient(app)
        self.headers = {"X-AI-Service-Key": DEFAULT_SERVICE_CONFIG.service_api_key}

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_recommend_unauthenticated(self):
        """Must reject unauthenticated request with 401."""
        resp = self.client.post("/v1/schemes/recommend", json={"applicant_id": "app_1", "query": "scholarships"})
        self.assertEqual(resp.status_code, 401)

    def test_recommend_valid_request(self):
        """Valid authenticated request returns SchemeRecommendationResponse schema."""
        resp = self.client.post(
            "/v1/schemes/recommend",
            headers=self.headers,
            json={
                "applicant_id": "app_test_api",
                "query": "Which farmer schemes can I apply for?",
                "top_k": 5,
                "include_eligibility": True,
                "include_missing_fields": True,
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertIn("request_id", data)
        self.assertEqual(data["applicant_id"], "app_test_api")
        self.assertEqual(data["query"], "Which farmer schemes can I apply for?")
        self.assertEqual(data["total_candidates_retrieved"], 1)
        self.assertIsInstance(data["recommendations"], list)
        self.assertEqual(len(data["recommendations"]), 1)

        rec = data["recommendations"][0]
        self.assertEqual(rec["scheme_id"], "pm-kisan")
        self.assertEqual(rec["scheme_name"], "PM Kisan Samman Nidhi")
        self.assertEqual(rec["eligibility_status"], "PASS")
        self.assertTrue(rec["is_eligible"])
        self.assertIn("evidence", rec)
        self.assertEqual(rec["evidence"]["source_tier"], "PRIMARY_SCHEME")

    def test_recommend_missing_applicant_id_rejected(self):
        """Missing applicant_id must be rejected with 422."""
        resp = self.client.post(
            "/v1/schemes/recommend",
            headers=self.headers,
            json={"applicant_id": "", "query": "scholarships"},
        )
        self.assertEqual(resp.status_code, 422)

    def test_recommend_missing_query_rejected(self):
        """Missing query must be rejected with 422."""
        resp = self.client.post(
            "/v1/schemes/recommend",
            headers=self.headers,
            json={"applicant_id": "app_1", "query": ""},
        )
        self.assertEqual(resp.status_code, 422)

    def test_recommend_top_k_bounds(self):
        """top_k < 1 or > 50 must be rejected with 422."""
        resp_too_low = self.client.post(
            "/v1/schemes/recommend",
            headers=self.headers,
            json={"applicant_id": "app_1", "query": "schemes", "top_k": 0},
        )
        self.assertEqual(resp_too_low.status_code, 422)

        resp_too_high = self.client.post(
            "/v1/schemes/recommend",
            headers=self.headers,
            json={"applicant_id": "app_1", "query": "schemes", "top_k": 100},
        )
        self.assertEqual(resp_too_high.status_code, 422)


if __name__ == "__main__":
    unittest.main()
