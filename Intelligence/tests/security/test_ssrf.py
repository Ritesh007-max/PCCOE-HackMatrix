"""
Tests for Server-Side Request Forgery (SSRF) Defenses.
Verifies rejection of loopback, private RFC 1918 IPs, cloud metadata IPs,
encoded numeric/hex host representations, and deceptive domain spoofing.
"""

import unittest
from src.data_pipeline.acquisition.security import AcquisitionSecurityValidator


class TestSSRFDefenses(unittest.TestCase):
    def test_localhost_ipv4_blocked(self):
        safe, reason = AcquisitionSecurityValidator.is_safe_url("http://127.0.0.1/admin")
        self.assertFalse(safe)
        self.assertIn("SSRF", reason or "")

    def test_localhost_named_blocked(self):
        safe, reason = AcquisitionSecurityValidator.is_safe_url("http://localhost:8000/api")
        self.assertFalse(safe)
        self.assertIn("SSRF", reason or "")

    def test_cloud_metadata_ip_blocked(self):
        safe, reason = AcquisitionSecurityValidator.is_safe_url("http://169.254.169.254/latest/meta-data/")
        self.assertFalse(safe)
        self.assertIn("SSRF", reason or "")

    def test_google_cloud_metadata_hostname_blocked(self):
        safe, reason = AcquisitionSecurityValidator.is_safe_url("http://metadata.google.internal/computeMetadata/v1/")
        self.assertFalse(safe)
        self.assertIn("SSRF", reason or "")

    def test_encoded_integer_ip_blocked(self):
        # 2130706433 is integer decimal for 127.0.0.1
        safe, reason = AcquisitionSecurityValidator.is_safe_url("http://2130706433/")
        self.assertFalse(safe)
        self.assertIn("SSRF", reason or "")

    def test_hex_encoded_ip_blocked(self):
        # 0x7f000001 is hex for 127.0.0.1
        safe, reason = AcquisitionSecurityValidator.is_safe_url("http://0x7f000001/")
        self.assertFalse(safe)
        self.assertIn("SSRF", reason or "")

    def test_deceptive_gov_domain_blocked(self):
        safe, reason = AcquisitionSecurityValidator.is_safe_url("https://myscheme.gov.in.evilattacker.com/steal")
        self.assertFalse(safe)
        self.assertIn("deceptive", reason or "")

    def test_phishing_hyphen_domain_blocked(self):
        safe, reason = AcquisitionSecurityValidator.is_safe_url("https://pmkisan-gov.in/phishing")
        self.assertFalse(safe)

    def test_official_myscheme_portal_allowed(self):
        safe, _ = AcquisitionSecurityValidator.is_safe_url("https://www.myscheme.gov.in/api/apisetu/schemes")
        self.assertTrue(safe)

    def test_official_nic_domain_allowed(self):
        safe, _ = AcquisitionSecurityValidator.is_safe_url("https://indiacode.nic.in/handle/123456789/1362")
        self.assertTrue(safe)


if __name__ == "__main__":
    unittest.main()
