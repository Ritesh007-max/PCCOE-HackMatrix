"""
Test Health & Diagnostic Endpoints.
Verifies GET /health/live, GET /health/ready, and GET /version.
"""

import unittest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.config import DEFAULT_SERVICE_CONFIG


class TestHealthEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.valid_headers = {"X-AI-Service-Key": DEFAULT_SERVICE_CONFIG.service_api_key}

    def test_live_endpoint_is_public(self):
        """GET /health/live must succeed without authentication headers."""
        response = self.client.get("/health/live")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "fin-ai")

    def test_ready_endpoint_requires_auth(self):
        """GET /health/ready must reject unauthenticated requests with 401."""
        response = self.client.get("/health/ready")
        self.assertEqual(response.status_code, 401)

        bad_response = self.client.get("/health/ready", headers={"X-AI-Service-Key": "invalid_key"})
        self.assertEqual(bad_response.status_code, 401)

    def test_ready_endpoint_with_valid_key(self):
        """GET /health/ready must return ready status and component diagnostics with valid key."""
        response = self.client.get("/health/ready", headers=self.valid_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ready")
        self.assertIn("checks", data)
        self.assertIn("config", data["checks"])
        self.assertIn("corpus", data["checks"])
        self.assertIn("rules", data["checks"])
        self.assertIn("rag", data["checks"])

    def test_version_endpoint_requires_auth(self):
        """GET /version must reject unauthenticated requests with 401."""
        response = self.client.get("/version")
        self.assertEqual(response.status_code, 401)

    def test_version_endpoint_with_valid_key(self):
        """GET /version must return version metadata when properly authenticated."""
        response = self.client.get("/version", headers=self.valid_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["service"], "fin-ai")
        self.assertEqual(data["api_version"], "v1")
        self.assertEqual(data["pipeline_version"], "phase-9")
        self.assertIn("llm_provider_mode", data)
        self.assertIn("knowledge_base_version", data)


if __name__ == "__main__":
    unittest.main()
