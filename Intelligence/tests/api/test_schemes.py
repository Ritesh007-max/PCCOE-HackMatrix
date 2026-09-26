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

    def test_search_nan_ministry_handled_safely(self):
        """Regression test: float('nan') or numpy.nan in metadata must normalize to null, not 500 error."""
        import math
        nan_chunk = RetrievedChunk(
            chunk_id="chunk_nan_1",
            content="Scheme with missing ministry and state.",
            scheme_slug="nan-scheme",
            scheme_name="NaN Scheme Test",
            source_tier=SourceTier.PRIMARY_SCHEME.value,
            dense_score=0.88,
            rerank_score=0.90,
            metadata={"source_url": float("nan"), "ministry": float("nan"), "state": float("nan")},
        )
        nan_result = SchemeRetrievalResult(
            scheme_slug="nan-scheme",
            scheme_name="NaN Scheme Test",
            aggregate_score=0.90,
            best_matching_chunks=[nan_chunk],
            source_metadata={"source_url": float("nan"), "ministry": float("nan"), "state": float("nan")},
        )
        self.mock_retriever.retrieve_schemes.return_value = [nan_result]

        resp = self.client.post(
            "/v1/schemes/search",
            headers=self.headers,
            json={"query": "test query"}
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total_results"], 1)
        item = data["results"][0]
        self.assertEqual(item["scheme_id"], "nan-scheme")
        self.assertIsNone(item["source_authority"])
        self.assertIsNone(item["source_url"])
        self.assertIsNone(item["state"])
        self.assertEqual(item["relevance_score"], 0.90)

    def test_search_valid_ministry_preserved(self):
        """Valid string ministry and state must be preserved exactly."""
        valid_chunk = RetrievedChunk(
            chunk_id="chunk_valid_1",
            content="Scheme with valid ministry and state.",
            scheme_slug="valid-scheme",
            scheme_name="Valid Scheme Test",
            source_tier=SourceTier.PRIMARY_SCHEME.value,
            dense_score=0.92,
            rerank_score=0.95,
            metadata={"source_url": "https://example.gov.in", "ministry": "Ministry of Agriculture", "state": "All-India"},
        )
        valid_result = SchemeRetrievalResult(
            scheme_slug="valid-scheme",
            scheme_name="Valid Scheme Test",
            aggregate_score=0.95,
            best_matching_chunks=[valid_chunk],
            source_metadata={"source_url": "https://example.gov.in", "ministry": "Ministry of Agriculture", "state": "All-India"},
        )
        self.mock_retriever.retrieve_schemes.return_value = [valid_result]

        resp = self.client.post(
            "/v1/schemes/search",
            headers=self.headers,
            json={"query": "valid query"}
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        item = data["results"][0]
        self.assertEqual(item["source_authority"], "Ministry of Agriculture")
        self.assertEqual(item["source_url"], "https://example.gov.in")
        self.assertEqual(item["state"], "All-India")

    def test_search_missing_ministry_handled_safely(self):
        """Missing ministry key in metadata must result in null without error."""
        missing_chunk = RetrievedChunk(
            chunk_id="chunk_missing_1",
            content="Scheme without ministry key.",
            scheme_slug="missing-scheme",
            scheme_name="Missing Scheme Test",
            source_tier=SourceTier.PRIMARY_SCHEME.value,
            dense_score=0.85,
            rerank_score=0.87,
            metadata={},
        )
        missing_result = SchemeRetrievalResult(
            scheme_slug="missing-scheme",
            scheme_name="Missing Scheme Test",
            aggregate_score=0.87,
            best_matching_chunks=[missing_chunk],
            source_metadata={},
        )
        self.mock_retriever.retrieve_schemes.return_value = [missing_result]

        resp = self.client.post(
            "/v1/schemes/search",
            headers=self.headers,
            json={"query": "missing query"}
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        item = data["results"][0]
        self.assertIsNone(item["source_authority"])


if __name__ == "__main__":
    unittest.main()
