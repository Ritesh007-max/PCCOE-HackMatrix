"""
Test Scheme Search Endpoint.
Verifies POST /v1/schemes/search hybrid dense-sparse retrieval and validation.
Uses FastAPI dependency overrides for fast, deterministic unit test execution.
"""

import unittest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.config import DEFAULT_SERVICE_CONFIG
from src.api.dependencies import get_hybrid_retriever
from src.rag.models import SchemeRetrievalResult, RetrievedChunk, SourceTier


class TestSchemeEndpoints(unittest.TestCase):
    def setUp(self):
        self.mock_retriever = MagicMock()
        self.mock_chunk = RetrievedChunk(
            chunk_id="chunk_test_1",
            content="Statutory farmer irrigation benefit of Rs 6000 per annum.",
            scheme_slug="pm-kisan",
            scheme_name="PM Kisan Samman Nidhi",
            source_tier=SourceTier.PRIMARY_SCHEME.value,
            dense_score=0.92,
            rerank_score=0.95,
            metadata={"source_url": "https://pmkisan.gov.in", "ministry": "Ministry of Agriculture", "state": "All-India"},
        )
        self.mock_result = SchemeRetrievalResult(
            scheme_slug="pm-kisan",
            scheme_name="PM Kisan Samman Nidhi",
            aggregate_score=0.95,
            best_matching_chunks=[self.mock_chunk],
            source_metadata={"source_url": "https://pmkisan.gov.in", "ministry": "Ministry of Agriculture", "state": "All-India"},
        )
        self.mock_retriever.retrieve_schemes.return_value = [self.mock_result]
        app.dependency_overrides[get_hybrid_retriever] = lambda: self.mock_retriever

        self.client = TestClient(app)
        self.headers = {"X-AI-Service-Key": DEFAULT_SERVICE_CONFIG.service_api_key}

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_search_unauthenticated(self):
        """Must reject unauthenticated search queries with 401."""
        resp = self.client.post("/v1/schemes/search", json={"query": "scholarships for students"})
        self.assertEqual(resp.status_code, 401)

    def test_search_valid_query(self):
        """Valid search query returns SchemeSearchResponse structure."""
        resp = self.client.post(
            "/v1/schemes/search",
            headers=self.headers,
            json={"query": "farmer irrigation subsidy", "top_k": 5}
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("request_id", data)
        self.assertEqual(data["query"], "farmer irrigation subsidy")
        self.assertEqual(data["total_results"], 1)
        self.assertIsInstance(data["results"], list)
        self.assertEqual(data["results"][0]["scheme_id"], "pm-kisan")
        self.assertEqual(data["results"][0]["scheme_name"], "PM Kisan Samman Nidhi")

    def test_search_empty_query_rejected(self):
        """Empty query string must be rejected by Pydantic validation (422)."""
        resp = self.client.post(
            "/v1/schemes/search",
            headers=self.headers,
            json={"query": ""}
        )
        self.assertEqual(resp.status_code, 422)


if __name__ == "__main__":
    unittest.main()
