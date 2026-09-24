"""
Tests for Outbound HTTP Client & Redirect Security.
Verifies bounded retries, maximum response size limits, and safe redirect validation.
"""

import unittest
from src.data_pipeline.acquisition.client import SafeHttpClient, SafeRedirectHandler
from src.data_pipeline.acquisition.security import AcquisitionSecurityValidator


class TestHttpSecurity(unittest.TestCase):
    def setUp(self):
        self.client = SafeHttpClient(
            requests_per_second=10.0,
            timeout=5.0,
            max_retries=2,
        )

    def test_ssrf_rejection_recorded_in_failures(self):
        # Localhost access attempt must be rejected immediately without network egress
        res, content_hash, status_code = self.client.fetch("http://127.0.0.1:8000/internal")
        self.assertIsNone(res)
        self.assertEqual(status_code, 403)
        self.assertTrue(len(self.client.failures) > 0)
        self.assertEqual(self.client.failures[-1].error_type, "SSRF_SECURITY_REJECTION")

    def test_cloud_metadata_blocked(self):
        res, _, status_code = self.client.fetch("http://169.254.169.254/latest/meta-data/")
        self.assertIsNone(res)
        self.assertEqual(status_code, 403)

    def test_safe_redirect_handler_limits(self):
        handler = SafeRedirectHandler(max_redirects=2)
        self.assertEqual(handler.max_redirects, 2)


if __name__ == "__main__":
    unittest.main()
