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

    def test_production_rejects_localhost_cors(self):
        settings = SecuritySettings(
            env=Environment.PRODUCTION,
            service_api_key="a_valid_long_production_key_12345678",
            gemini_api_key="AIzaSyDummyKeyForProductionTest12345678",
            cors_origins=["http://localhost:5173"],
            rate_limit_enabled=True,
        )
        with self.assertRaises(SecurityConfigError) as ctx:
            settings.validate_production()
        self.assertIn("Localhost or loopback origin", str(ctx.exception))

    def test_production_rejects_insecure_http_cors(self):
        settings = SecuritySettings(
            env=Environment.PRODUCTION,
            service_api_key="a_valid_long_production_key_12345678",
            gemini_api_key="AIzaSyDummyKeyForProductionTest12345678",
            cors_origins=["http://fin.gov.in"],
            rate_limit_enabled=True,
        )
        with self.assertRaises(SecurityConfigError) as ctx:
            settings.validate_production()
        self.assertIn("Insecure non-HTTPS CORS origin", str(ctx.exception))

    def test_production_requires_explicit_cors_origins(self):
        settings = SecuritySettings(
            env=Environment.PRODUCTION,
            service_api_key="a_valid_long_production_key_12345678",
            gemini_api_key="AIzaSyDummyKeyForProductionTest12345678",
            cors_origins=[],
            rate_limit_enabled=True,
        )
        with self.assertRaises(SecurityConfigError) as ctx:
            settings.validate_production()
        self.assertIn("Production requires explicit AI_CORS_ORIGINS list", str(ctx.exception))

    def test_cors_preflight_trusted_origin(self):
        res = self.client.options(
            "/v1/health/live",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type, X-AI-Service-Key",
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("access-control-allow-origin"), "http://localhost:5173")
        # Credentials must NOT be allowed
        self.assertIsNone(res.headers.get("access-control-allow-credentials"))
        # Allow headers must not be wildcard
        allow_headers = res.headers.get("access-control-allow-headers", "")
        self.assertNotEqual(allow_headers, "*")

    def test_cors_preflight_untrusted_origin_rejected(self):
        res = self.client.options(
            "/v1/health/live",
            headers={
                "Origin": "https://malicious-attacker.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        self.assertNotEqual(res.headers.get("access-control-allow-origin"), "https://malicious-attacker.com")
        self.assertNotEqual(res.headers.get("access-control-allow-origin"), "*")


if __name__ == "__main__":
    unittest.main()
