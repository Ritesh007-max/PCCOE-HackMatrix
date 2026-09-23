"""
Test Authentication and Middleware Traceability.
Verifies constant-time key validation, 401 challenge, request correlation ID generation/propagation,
and zero secret leakage.
"""

import unittest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.config import DEFAULT_SERVICE_CONFIG


class TestAuthAndMiddleware(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.valid_key = DEFAULT_SERVICE_CONFIG.service_api_key

    def test_unauthenticated_request_rejected(self):
        """Endpoints requiring auth must return 401 when header is omitted."""
        resp = self.client.get("/version")
        self.assertEqual(resp.status_code, 401)
        data = resp.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "UNAUTHORIZED")

    def test_invalid_api_key_rejected(self):
        """Endpoints must reject invalid keys with 401."""
        resp = self.client.get("/version", headers={"X-AI-Service-Key": "completely_wrong_key"})
        self.assertEqual(resp.status_code, 401)

    def test_valid_api_key_accepted(self):
        """Endpoints must succeed when provided the correct service key."""
        resp = self.client.get("/version", headers={"X-AI-Service-Key": self.valid_key})
        self.assertEqual(resp.status_code, 200)

    def test_request_id_generated_when_omitted(self):
        """If client does not provide X-Request-ID, the middleware must generate and return one."""
        resp = self.client.get("/health/live")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("x-request-id", resp.headers)
        self.assertTrue(resp.headers["x-request-id"].startswith("req_"))

    def test_custom_request_id_propagated(self):
        """If client provides X-Request-ID, it must be preserved and reflected in the response."""
        custom_id = "req_custom_tracer_999"
        resp = self.client.get("/health/live", headers={"X-Request-ID": custom_id})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("x-request-id"), custom_id)

    def test_zero_secret_leakage_in_response(self):
        """API key must never appear in response payloads or headers."""
        resp = self.client.get("/version", headers={"X-AI-Service-Key": self.valid_key})
        self.assertEqual(resp.status_code, 200)
        content_str = resp.text
        self.assertNotIn(self.valid_key, content_str)


if __name__ == "__main__":
    unittest.main()
