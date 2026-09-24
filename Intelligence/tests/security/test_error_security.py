"""
Tests for API Error Security & Sanitization.
Verifies that error responses never leak stack traces, internal filesystem paths, or API keys.
"""

import json
import unittest
from src.api.errors import build_error_response


class TestErrorSecurity(unittest.TestCase):
    def test_error_response_redacts_api_key(self):
        msg = "Failure contacting endpoint with key AIzaSyD123456789012345678901234567890a"
        resp = build_error_response(500, "PROVIDER_ERROR", msg, request_id="req_test_01")
        body = json.loads(resp.body.decode("utf-8"))
        self.assertNotIn("AIzaSyD123456789012345678901234567890a", body["error"]["message"])
        self.assertIn("[SECRET_REDACTED]", body["error"]["message"])

    def test_error_response_redacts_filesystem_paths(self):
        msg = "Error reading config from C:\\Users\\ozhad\\Desktop\\secret_dir\\config.json"
        resp = build_error_response(500, "CONFIG_ERROR", msg, request_id="req_test_02")
        body = json.loads(resp.body.decode("utf-8"))
        self.assertNotIn("C:\\Users\\ozhad", body["error"]["message"])
        self.assertIn("[PATH_REDACTED]", body["error"]["message"])

    def test_error_response_structure_conforms(self):
        resp = build_error_response(400, "BAD_REQUEST", "Invalid input", request_id="req_test_03")
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.body.decode("utf-8"))
        self.assertIn("error", body)
        self.assertEqual(body["error"]["code"], "BAD_REQUEST")
        self.assertEqual(body["error"]["request_id"], "req_test_03")


if __name__ == "__main__":
    unittest.main()
