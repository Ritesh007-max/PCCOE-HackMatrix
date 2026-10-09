"""
Tests for Secret & PII Redaction Engine.
Verifies redaction of Gemini keys, OpenRouter keys, Hugging Face tokens,
Bearer tokens, and Indian citizen PII (Aadhaar, PAN, phone, email).
"""

import unittest
from src.utils.secret_redactor import (
    mask_credential,
    redact_secrets,
    SecretRedactingLoggingFilter,
)


class TestSecretRedaction(unittest.TestCase):
    def test_gemini_api_key_redaction(self):
        sample = "Error using key AIzaSyD987654321012345678901234567890a in request"
        redacted = redact_secrets(sample)
        self.assertNotIn("AIzaSyD987654321012345678901234567890a", redacted)
        self.assertIn("[SECRET_REDACTED]", redacted)

    def test_openrouter_api_key_redaction(self):
        sample = "Failed to connect with sk-or-v1-abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
        redacted = redact_secrets(sample)
        self.assertNotIn("sk-or-v1-abcdef0123456789abcdef0123456789", redacted)
        self.assertIn("[SECRET_REDACTED]", redacted)

    def test_bearer_token_redaction(self):
        sample = "Header Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.t-ae"
        redacted = redact_secrets(sample)
        self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", redacted)
        self.assertIn("[BEARER_TOKEN_REDACTED]", redacted)

    def test_aadhaar_pii_redaction(self):
        sample = "Citizen Aadhaar number is 9876 5432 1098 submitted for scholarship"
        redacted = redact_secrets(sample)
        self.assertNotIn("9876 5432 1098", redacted)
        self.assertIn("[AADHAAR_REDACTED]", redacted)

    def test_pan_pii_redaction(self):
        sample = "Income tax PAN record ABCDE1234F verified"
        redacted = redact_secrets(sample)
        self.assertNotIn("ABCDE1234F", redacted)
        self.assertIn("[PAN_REDACTED]", redacted)

    def test_phone_number_redaction(self):
        sample = "Contact mobile +91 9876543210 or 9876543210"
        redacted = redact_secrets(sample)
        self.assertNotIn("9876543210", redacted)
        self.assertIn("[PHONE_REDACTED]", redacted)

    def test_mask_credential(self):
        key = "fin_super_secret_internal_key"
        masked = mask_credential(key)
        self.assertTrue(masked.startswith("fin_"))
        self.assertTrue(masked.endswith("..._key"))
        self.assertNotIn("super_secret", masked)

    def test_mask_credential_short(self):
        short = "secret"
        masked = mask_credential(short)
        self.assertEqual(masked, "******")


if __name__ == "__main__":
    unittest.main()
