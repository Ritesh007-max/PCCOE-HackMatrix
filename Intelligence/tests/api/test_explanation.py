"""
Phase 21 Explanation API Route Tests.
Tests:
- Authentication & authorization on /v1/explanation/generate and /v1/explanation/compare
- PASS, FAIL, UNKNOWN generation via HTTP API
- Language localization via API
- Multi-scheme objective comparison via HTTP API
- Rejection of unauthorized or invalid inputs
"""

import unittest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.config import DEFAULT_SERVICE_CONFIG


class TestExplanationEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.headers = {"X-AI-Service-Key": DEFAULT_SERVICE_CONFIG.service_api_key}

    def test_explanation_unauthenticated(self):
        """Unauthenticated requests must be rejected with 401."""
        resp = self.client.post(
            "/v1/explanation/generate",
            json={"applicant_id": "app_anon", "scheme_id": "apy", "applicant_facts": {"age": 25}},
        )
        self.assertEqual(resp.status_code, 401)

    def test_explanation_generate_pass(self):
        """Valid evaluation request returning PASS."""
        facts = {"age": 28, "has_bank_account": True, "is_taxpayer": False}
        resp = self.client.post(
            "/v1/explanation/generate",
            headers=self.headers,
            json={
                "applicant_id": "app_123",
                "scheme_id": "apy",
                "applicant_facts": facts,
                "language": "en",
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("request_id", data)
        bundle = data["explanation"]
        self.assertEqual(bundle["grounding_status"], "GROUNDED")
        self.assertEqual(bundle["eligibility_status"], "PASS")
        self.assertTrue(bundle["is_eligible"])
        self.assertGreater(len(bundle["policy_citations"]), 0)
        self.assertGreater(len(bundle["next_actions"]), 0)

    def test_explanation_generate_fail(self):
        """Valid evaluation request returning FAIL with statutory reason."""
        facts = {"age": 55, "has_bank_account": True, "is_taxpayer": False}
        resp = self.client.post(
            "/v1/explanation/generate",
            headers=self.headers,
            json={
                "applicant_id": "app_456",
                "scheme_id": "apy",
                "applicant_facts": facts,
                "language": "en",
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        bundle = data["explanation"]
        self.assertEqual(bundle["eligibility_status"], "FAIL")
        self.assertFalse(bundle["is_eligible"])
        self.assertGreater(len(bundle["eligibility_explanation"]["failed_conditions"]), 0)

    def test_explanation_multilingual_hindi(self):
        """Valid evaluation request in Hindi."""
        facts = {"age": 28, "has_bank_account": True, "is_taxpayer": False}
        resp = self.client.post(
            "/v1/explanation/generate",
            headers=self.headers,
            json={
                "applicant_id": "app_hi",
                "scheme_id": "apy",
                "applicant_facts": facts,
                "language": "hi",
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        bundle = data["explanation"]
        self.assertEqual(bundle["language"], "hi")
        self.assertEqual(bundle["eligibility_status"], "PASS")
        self.assertIn("पात्रता", bundle["headline"])

    def test_explanation_compare_schemes(self):
        """Objective scheme comparison across candidate schemes."""
        facts = {
            "age": 28,
            "has_bank_account": True,
            "is_taxpayer": False,
            "owns_cultivable_land": True,
            "is_institutional_landholder": False,
            "monthly_pension_amount": 0,
        }
        resp = self.client.post(
            "/v1/explanation/compare",
            headers=self.headers,
            json={
                "applicant_id": "app_cmp",
                "scheme_ids": ["apy", "pm-kisan"],
                "applicant_facts": facts,
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("request_id", data)
        comparison = data["comparison"]
        self.assertEqual(len(comparison["schemes"]), 2)
        # Ensure objective comparison without picking a subjective winner
        self.assertNotIn("best scheme", " ".join(comparison["summary_of_differences"]).lower())


if __name__ == "__main__":
    unittest.main()
