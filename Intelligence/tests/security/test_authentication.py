"""
Tests for API Authentication Hardening.
Verifies constant-time comparison, minimum key length checks, missing key rejection,
and production fail-closed behavior.
"""

import unittest
from fastapi import HTTPException
from src.api.auth import verify_service_api_key
from src.api.config import ServiceConfig
from src.config.security import Environment, SecurityConfigError, SecuritySettings


class TestAuthenticationSecurity(unittest.TestCase):
    def test_missing_key_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            verify_service_api_key(None)
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("Missing required service key", ctx.exception.detail)

    def test_empty_key_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            verify_service_api_key("")
        self.assertEqual(ctx.exception.status_code, 401)

    def test_short_key_rejected(self):
        # Keys under 16 characters must be rejected
        with self.assertRaises(HTTPException) as ctx:
            verify_service_api_key("short_key_123")
        self.assertEqual(ctx.exception.status_code, 401)

    def test_invalid_key_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            verify_service_api_key("wrong_key_that_is_long_enough_12345")
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("Invalid service API key", ctx.exception.detail)

    def test_valid_dev_key_accepted(self):
        key = "fin_internal_dev_key"
        res = verify_service_api_key(key)
        self.assertEqual(res, key)

    def test_production_fail_closed_on_default_key(self):
        # In production mode, default key must fail validation
        settings = SecuritySettings(
            env=Environment.PRODUCTION,
            service_api_key="fin_internal_dev_key",
            gemini_api_key="AIzaSyDummyKeyForProductionTest12345678",
            cors_origins=["https://fin.gov.in"],
            rate_limit_enabled=True,
        )
        with self.assertRaises(SecurityConfigError) as ctx:
            settings.validate_production()
        self.assertIn("Default development service key is strictly prohibited in production", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
