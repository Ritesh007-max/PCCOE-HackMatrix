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

    def test_eligibility_api_exposes_version_and_diagnostics(self):
        """Verifies that API response returns rule_version, decision_id, hash, and evidence."""
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
        eval_item = data["evaluations"][0]
        self.assertEqual(eval_item["rule_version"], "1.0.0")
        self.assertIsNotNone(eval_item["decision_id"])
        self.assertIsNotNone(eval_item["rule_set_hash"])
        self.assertGreater(len(eval_item["evidence"]), 0)

    def test_eligibility_api_unregistered_scheme_handled_safely(self):
        """Unregistered scheme returns UNKNOWN with missing_fields diagnostic and does not crash."""
        resp = self.client.post(
            "/v1/eligibility/check",
            headers=self.headers,
            json={"applicant_facts": {"age": 25}, "scheme_ids": ["non_existent_scheme_abc"]}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        eval_item = data["evaluations"][0]
        self.assertEqual(eval_item["status"], "UNKNOWN")
        self.assertFalse(eval_item["is_eligible"])
        self.assertIn("scheme_non_existent_scheme_abc_not_registered", eval_item["missing_fields"])

    def test_eligibility_api_missing_scheme_ids_returns_400(self):
        """Missing or empty scheme_ids returns 400 or 422 validation error."""
        resp = self.client.post(
            "/v1/eligibility/check",
            headers=self.headers,
            json={"applicant_facts": {"age": 25}, "scheme_ids": []}
        )
        self.assertIn(resp.status_code, [400, 422])



if __name__ == "__main__":
    unittest.main()

