"""
Tests for Structured Logging & Privacy Interception.
Verifies that SecretRedactingLoggingFilter intercepts logger records and scrubs
citizen PII and secret API keys before output streams.
"""

import io
import logging
import unittest
from src.utils.secret_redactor import SecretRedactingLoggingFilter


class TestLoggingPrivacy(unittest.TestCase):
    def setUp(self):
        self.stream = io.StringIO()
        self.handler = logging.StreamHandler(self.stream)
        self.handler.addFilter(SecretRedactingLoggingFilter())
        self.logger = logging.getLogger("test.security.privacy")
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(self.handler)

    def tearDown(self):
        self.logger.removeHandler(self.handler)

    def test_log_scrubs_gemini_key(self):
        self.logger.info("Initializing provider with key AIzaSyD123456789012345678901234567890a")
        output = self.stream.getvalue()
        self.assertNotIn("AIzaSyD123456789012345678901234567890a", output)
        self.assertIn("[SECRET_REDACTED]", output)

    def test_log_scrubs_aadhaar_pii(self):
        self.logger.info("Processing application for citizen with Aadhaar 1234 5678 9012")
        output = self.stream.getvalue()
        self.assertNotIn("1234 5678 9012", output)
        self.assertIn("[AADHAAR_REDACTED]", output)

    def test_log_scrubs_pan_pii(self):
        self.logger.info("Applicant submitted PAN card ABCDE1234F for age verification")
        output = self.stream.getvalue()
        self.assertNotIn("ABCDE1234F", output)
        self.assertIn("[PAN_REDACTED]", output)


if __name__ == "__main__":
    unittest.main()
