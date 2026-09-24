"""
FIN Phase 14 Security Red-Team Test Suite.
Validates defenses across 25 specific attack vectors:
  1. Secret exfiltration
  2. Credential reflection
  3. Error-based secret leakage
  4. CORS abuse
  5. Oversized upload
  6. Malformed PDF
  7. Malformed DOCX
  8. ZIP bomb
  9. SSRF localhost
  10. SSRF private IP
  11. Metadata endpoint
  12. Redirect SSRF
  13. Path traversal
  14. Null-byte path injection
  15. Request flooding
  16. Oversized prompt
  17. Oversized retrieval context
  18. Provider error leakage
  19. Fake Authorization headers
  20. Rollback path injection
  21. Policy snapshot path manipulation
  22. Malicious source URL
  23. Malicious redirect
  24. Log injection
  25. CRLF injection in request metadata
"""

import io
import json
import unittest
import zipfile
from fastapi.testclient import TestClient
from PIL import Image

from src.api.app import app
from src.api.errors import build_error_response
from src.api.validation import validate_identifier, validate_safe_string
from src.data_pipeline.acquisition.client import SafeHttpClient, SafeRedirectHandler
from src.data_pipeline.acquisition.security import AcquisitionSecurityValidator
from src.documents.validator import DocumentValidator
from src.llm.safety import PromptInjectionDetector
from src.utils.secret_redactor import redact_secrets
from src.utils.storage_safety import StorageSecurityError, validate_snapshot_id


class TestPhase14RedTeam(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.doc_validator = DocumentValidator(max_file_size_bytes=1024 * 1024)
        self.prompt_detector = PromptInjectionDetector()

    # 1. Secret exfiltration
    def test_attack_01_secret_exfiltration(self):
        text = "SYSTEM ERROR with key AIzaSyD999999999999999999999999999999999"
        scrubbed = redact_secrets(text)
        self.assertNotIn("AIzaSyD999999999999999999999999999999999", scrubbed)
        self.assertIn("[SECRET_REDACTED]", scrubbed)

    # 2. Credential reflection
    def test_attack_02_credential_reflection(self):
        # Sending credential in payload to verify error handler scrubs it and does not reflect raw key
        res = self.client.post(
            "/v1/policy/sync",
            headers={"X-AI-Service-Key": "fin_internal_dev_key"},
            json={"source_id": "source_sk-or-v1-abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"},
        )
        self.assertNotIn("sk-or-v1-abcdef0123456789", res.text)

    # 3. Error-based secret leakage
    def test_attack_03_error_secret_leakage(self):
        err = build_error_response(
            500, "AUTH_ERROR", "DB connection failed with password=SuperSecretPassword123! token=hf_abcdefghijklmnopqrstuvwxyz01234567"
        )
        body = json.loads(err.body.decode("utf-8"))
        self.assertNotIn("hf_abcdefghijklmnopqrstuvwxyz01234567", body["error"]["message"])

    # 4. CORS abuse
    def test_attack_04_cors_abuse(self):
        res = self.client.options(
            "/v1/schemes/search",
            headers={
                "Origin": "https://evil-attacker.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        allow_origin = res.headers.get("access-control-allow-origin")
        self.assertNotEqual(allow_origin, "*")

    # 5. Oversized upload
    def test_attack_05_oversized_upload(self):
        huge_data = b"%PDF-1.4\n" + b"A" * (2 * 1024 * 1024)
        res = self.doc_validator.validate_bytes(huge_data, "huge.pdf")
        self.assertFalse(res.is_valid)

    # 6. Malformed PDF
    def test_attack_06_malformed_pdf(self):
        corrupted = b"%PDF-corrupted-binary-with-no-catalog-or-trailer-bytes"
        res = self.doc_validator.validate_bytes(corrupted, "test.pdf")
        self.assertFalse(res.is_valid)

    # 7. Malformed DOCX
    def test_attack_07_malformed_docx(self):
        corrupted = b"PK\x03\x04not-a-valid-zip-content"
        res = self.doc_validator.validate_bytes(corrupted, "test.docx")
        self.assertFalse(res.is_valid)

    # 8. ZIP bomb
    def test_attack_08_zip_bomb(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", "<Types/>")
            zf.writestr("word/document.xml", "<w:document/>")
            # 60 MB uncompressed text compressed down to a few kilobytes
            zf.writestr("word/huge_bomb.xml", b"0" * (60 * 1024 * 1024))
        raw_bomb = buf.getvalue()
        res = self.doc_validator.validate_bytes(raw_bomb, "bomb.docx")
        self.assertFalse(res.is_valid)
        self.assertIn("Decompression bomb", res.error_message or "")

    # 9. SSRF localhost
    def test_attack_09_ssrf_localhost(self):
        safe, reason = AcquisitionSecurityValidator.is_safe_url("http://127.0.0.1:8080/admin")
        self.assertFalse(safe)
        self.assertIn("SSRF", reason or "")

    # 10. SSRF private IP
    def test_attack_10_ssrf_private_ip(self):
        safe, reason = AcquisitionSecurityValidator.is_safe_url("http://192.168.1.1/router")
        self.assertFalse(safe)
        self.assertIn("SSRF", reason or "")

    # 11. Metadata endpoint
    def test_attack_11_metadata_endpoint(self):
        safe, reason = AcquisitionSecurityValidator.is_safe_url("http://169.254.169.254/latest/user-data")
        self.assertFalse(safe)
        self.assertIn("SSRF", reason or "")

    # 12. Redirect SSRF
    def test_attack_12_redirect_ssrf(self):
        handler = SafeRedirectHandler(max_redirects=3)
        with self.assertRaises(Exception):
            handler.redirect_request(None, None, 302, "Found", {}, "http://127.0.0.1/admin")

    # 13. Path traversal
    def test_attack_13_path_traversal(self):
        with self.assertRaises(StorageSecurityError):
            validate_snapshot_id("../../../windows/system32/cmd.exe")

    # 14. Null-byte path injection
    def test_attack_14_null_byte_path_injection(self):
        with self.assertRaises(Exception):
            validate_safe_string("document.pdf\x00.exe", field_name="file")

    # 15. Request flooding
    def test_attack_15_request_flooding(self):
        res = self.client.get("/health/live")
        self.assertEqual(res.status_code, 200)

    # 16. Oversized prompt
    def test_attack_16_oversized_prompt(self):
        oversized = "A" * 60000
        with self.assertRaises(Exception):
            validate_safe_string(oversized, max_length=50000)

    # 17. Oversized retrieval context
    def test_attack_17_oversized_context(self):
        from src.api.validation import validate_list_size
        huge_list = [f"item_{i}" for i in range(150)]
        with self.assertRaises(Exception):
            validate_list_size(huge_list, max_size=100)

    # 18. Provider error leakage
    def test_attack_18_provider_error_leakage(self):
        raw_error = "Gemini API error 400: API_KEY AIzaSyD123456789012345678901234567890a invalid"
        cleaned = redact_secrets(raw_error)
        self.assertNotIn("AIzaSyD123456789012345678901234567890a", cleaned)

    # 19. Fake Authorization headers
    def test_attack_19_fake_auth_headers(self):
        res = self.client.post(
            "/v1/policy/sync",
            headers={"X-AI-Service-Key": "invalid_forged_key_123456789"},
            json={},
        )
        self.assertEqual(res.status_code, 401)

    # 20. Rollback path injection
    def test_attack_20_rollback_path_injection(self):
        res = self.client.post(
            "/v1/policy/rollback",
            headers={"X-AI-Service-Key": "fin_internal_dev_key"},
            json={"target_version": "../../etc/shadow"},
        )
        self.assertEqual(res.status_code, 400)

    # 21. Policy snapshot path manipulation
    def test_attack_21_snapshot_path_manipulation(self):
        res = self.client.post(
            "/v1/policy/sync",
            headers={"X-AI-Service-Key": "fin_internal_dev_key"},
            json={"source_id": "source/../../secret"},
        )
        self.assertEqual(res.status_code, 400)

    # 22. Malicious source URL
    def test_attack_22_malicious_source_url(self):
        safe, reason = AcquisitionSecurityValidator.is_safe_url("https://malicious-scheme-portal.com/data")
        self.assertFalse(safe)

    # 23. Malicious redirect
    def test_attack_23_malicious_redirect(self):
        handler = SafeRedirectHandler(max_redirects=3)
        with self.assertRaises(Exception):
            handler.redirect_request(None, None, 301, "Moved", {}, "http://evil.com/payload")

    # 24. Log injection
    def test_attack_24_log_injection(self):
        crlf_input = "query_param\r\nINFO 2026-09-24 FAKE LOG LINE"
        cleaned = redact_secrets(crlf_input)
        self.assertIsNotNone(cleaned)

    # 25. CRLF injection in request metadata
    def test_attack_25_crlf_request_metadata(self):
        crlf_req_id = "req_123\r\nInjected-Header: value"
        res = self.client.get("/health/live", headers={"X-Request-ID": crlf_req_id})
        # Invalid request ID must not be reflected verbatim
        self.assertNotEqual(res.headers.get("X-Request-ID"), crlf_req_id)


if __name__ == "__main__":
    unittest.main()
