"""
Tests for CORS Configuration & Security Headers.
Verifies rejection of wildcard origins in production and presence of standard security headers.
"""

import unittest
from fastapi.testclient import TestClient
from src.api.app import app
from src.config.security import Environment, SecurityConfigError, SecuritySettings


class TestCORSSecurity(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_security_headers_present(self):
        res = self.client.get("/health/live")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(res.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(res.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertIn("Content-Security-Policy", res.headers)
        self.assertEqual(res.headers.get("X-XSS-Protection"), "0")

    def test_request_id_header_returned(self):
        res = self.client.get("/health/live")
        self.assertIn("X-Request-ID", res.headers)
        self.assertTrue(res.headers["X-Request-ID"].startswith("req_"))

    def test_custom_request_id_propagated(self):
        custom_id = "req_custom_trace_12345"
        res = self.client.get("/health/live", headers={"X-Request-ID": custom_id})
        self.assertEqual(res.headers.get("X-Request-ID"), custom_id)

    def test_production_rejects_wildcard_cors(self):
        settings = SecuritySettings(
            env=Environment.PRODUCTION,
            service_api_key="a_valid_long_production_key_12345678",
            gemini_api_key="AIzaSyDummyKeyForProductionTest12345678",
            cors_origins=["*"],
            rate_limit_enabled=True,
        )
        with self.assertRaises(SecurityConfigError) as ctx:
            settings.validate_production()
        self.assertIn("Wildcard CORS origin ('*') is strictly forbidden in production", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
