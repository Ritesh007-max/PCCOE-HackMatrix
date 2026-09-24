"""
Test Deterministic Eligibility Check Endpoint.
Verifies POST /v1/eligibility/check is 100% deterministic with zero LLM calls.
Evaluates statutory rules (PASS, FAIL, UNKNOWN, REVIEW) through RuleEvaluator.
"""

import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.config import DEFAULT_SERVICE_CONFIG


class TestEligibilityEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.headers = {"X-AI-Service-Key": DEFAULT_SERVICE_CONFIG.service_api_key}

    def test_eligibility_unauthenticated(self):
        """Must reject unauthenticated check requests with 401."""
        resp = self.client.post("/v1/eligibility/check", json={"applicant_facts": {}, "scheme_ids": ["pm-kisan"]})
        self.assertEqual(resp.status_code, 401)

    def test_eligibility_deterministic_pass(self):
        """Eligible applicant facts satisfying all criteria must deterministically return PASS and is_eligible=True."""
        facts = {
            "owns_cultivable_land": True,
            "is_institutional_landholder": False,
            "is_taxpayer": False,
            "monthly_pension_amount": 0,
        }
        resp = self.client.post(
            "/v1/eligibility/check",
            headers=self.headers,
            json={"applicant_facts": facts, "scheme_ids": ["pm-kisan"]}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("request_id", data)
        self.assertEqual(data["evaluated_schemes_count"], 1)
        eval_item = data["evaluations"][0]
        self.assertEqual(eval_item["scheme_id"], "9f760605-d17e-5f82-b7cd-a15b625d689f")
        self.assertEqual(eval_item["status"], "PASS")
        self.assertTrue(eval_item["is_eligible"])
        self.assertEqual(len(eval_item["failed_rules"]), 0)

    def test_eligibility_deterministic_fail_hard_constraint(self):
        """Violating statutory hard constraints must deterministically return FAIL and is_eligible=False."""
        facts = {
            "owns_cultivable_land": False,
            "is_institutional_landholder": True,
            "is_taxpayer": True,
            "monthly_pension_amount": 50000,
        }
        resp = self.client.post(
            "/v1/eligibility/check",
            headers=self.headers,
            json={"applicant_facts": facts, "scheme_ids": ["pm-kisan"]}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        eval_item = data["evaluations"][0]
        self.assertEqual(eval_item["status"], "FAIL")
        self.assertFalse(eval_item["is_eligible"])
        self.assertTrue(len(eval_item["failed_rules"]) > 0)

    def test_eligibility_deterministic_unknown_missing_info(self):
        """Missing statutory criteria must return UNKNOWN and is_eligible=False."""
        facts = {
            "owns_cultivable_land": True,
        }
        resp = self.client.post(
            "/v1/eligibility/check",
            headers=self.headers,
            json={"applicant_facts": facts, "scheme_ids": ["pm-kisan"]}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        eval_item = data["evaluations"][0]
        self.assertEqual(eval_item["status"], "UNKNOWN")
        self.assertFalse(eval_item["is_eligible"])
        self.assertTrue(len(eval_item["missing_fields"]) > 0)

    @patch("src.llm.client.LLMClient.generate")
    @patch("src.llm.client.LLMClient.generate_with_metadata")
    def test_zero_llm_calls_in_eligibility_check(self, mock_llm_meta, mock_llm_gen):
        """CRITICAL INVARIANT: Zero Gemini/OpenRouter LLM calls must be made during statutory eligibility check."""
        facts = {
            "owns_cultivable_land": True,
            "is_institutional_landholder": False,
            "is_taxpayer": False,
            "monthly_pension_amount": 0,
        }
        resp = self.client.post(
            "/v1/eligibility/check",
            headers=self.headers,
            json={"applicant_facts": facts, "scheme_ids": ["pm-kisan"]}
        )
        self.assertEqual(resp.status_code, 200)
        # Verify absolutely no LLM generation call occurred
        mock_llm_gen.assert_not_called()
        mock_llm_meta.assert_not_called()


if __name__ == "__main__":
    unittest.main()
