"""
Unit tests for grounded explanation generation and decision immutability.
"""

import unittest
import sys
from pathlib import Path

_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from src.llm.explanation import GroundedExplanationGenerator
from src.llm.client import LLMClient
from src.llm.config import LLMConfig
from src.rules.models import (
    SchemeRuleSet,
    Rule,
    RuleStatus,
    RuleEvaluationResult,
    ApplicantProfile,
)


class TestGroundedExplanation(unittest.TestCase):

    def setUp(self):
        self.config = LLMConfig(provider="mock")
        self.client = LLMClient(config=self.config)
        self.generator = GroundedExplanationGenerator(llm_client=self.client)

        self.rule = Rule(
            rule_id="rule_sc_income",
            scheme_id="scheme_sc_postmatric",
            rule_type="eligibility",
            field="annual_family_income",
            operator="<=",
            expected_value=250000.0,
            value_type="numeric",
            hard_constraint=True,
        )
        self.ruleset = SchemeRuleSet(
            scheme_id="scheme_sc_postmatric",
            scheme_slug="scheme_sc_postmatric",
            scheme_name="Post-Matric Scholarship for SC Students",
            rules=[self.rule]
        )
        self.retrieved_chunks = [
            {
                "id": "chunk_pm_sc_01",
                "content": "Annual family income must not exceed 2.5 lakh rupees.",
                "source_url": "https://scholarships.gov.in/sc_postmatric.pdf",
            }
        ]

    def test_explanation_for_pass(self):
        profile = ApplicantProfile(data={"annual_family_income": 180000.0})
        rule_res = RuleEvaluationResult(
            rule_id="rule_sc_income",
            rule_type="eligibility",
            field="annual_family_income",
            operator="<=",
            status=RuleStatus.PASS,
            applicant_value=180000.0,
            expected_value=250000.0,
            hard_constraint=True,
            reason="Income 180000.0 is <= 250000.0",
            raw_text="Income <= 2.5L",
        )

        explanation = self.generator.generate_explanation(
            ruleset=self.ruleset,
            profile=profile,
            rule_status=RuleStatus.PASS,
            rule_results=[rule_res],
            retrieved_chunks=self.retrieved_chunks,
        )

        self.assertEqual(explanation.authoritative_decision, "PASS")
        self.assertEqual(explanation.passed_rules, ["rule_sc_income"])
        self.assertFalse(explanation.review_required)
        self.assertFalse(explanation.rejection_fallback_used)

    def test_explanation_for_fail(self):
        profile = ApplicantProfile(data={"annual_family_income": 350000.0})
        rule_res = RuleEvaluationResult(
            rule_id="rule_sc_income",
            rule_type="eligibility",
            field="annual_family_income",
            operator="<=",
            status=RuleStatus.FAIL,
            applicant_value=350000.0,
            expected_value=250000.0,
            hard_constraint=True,
            reason="Income 350000.0 exceeds threshold 250000.0",
            raw_text="Income <= 2.5L",
        )

        explanation = self.generator.generate_explanation(
            ruleset=self.ruleset,
            profile=profile,
            rule_status=RuleStatus.FAIL,
            rule_results=[rule_res],
            retrieved_chunks=self.retrieved_chunks,
        )

        self.assertEqual(explanation.authoritative_decision, "FAIL")
        self.assertEqual(explanation.failed_rules, ["rule_sc_income"])

    def test_explanation_rejection_on_contradiction(self):
        # Create a mock provider that intentionally outputs a contradictory answer claiming eligibility on FAIL
        from src.llm.providers import MockLLMProvider
        from src.llm.models import GroundedExplanation

        class ContradictoryMockProvider(MockLLMProvider):
            def generate_structured(self, prompt, schema_cls, system_prompt=None, **kwargs):
                exp = super().generate_structured(prompt, schema_cls, system_prompt=system_prompt, **kwargs)
                # Intentionally insert contradictory claim: "you are eligible"
                exp.answer = "Congratulations, you are eligible for this scheme!"
                return exp

        contradictory_client = LLMClient(config=self.config, provider=ContradictoryMockProvider())
        gen = GroundedExplanationGenerator(llm_client=contradictory_client)

        profile = ApplicantProfile(data={"annual_family_income": 350000.0})
        rule_res = RuleEvaluationResult(
            rule_id="rule_sc_income",
            rule_type="eligibility",
            field="annual_family_income",
            operator="<=",
            status=RuleStatus.FAIL,
            applicant_value=350000.0,
            expected_value=250000.0,
            hard_constraint=True,
            reason="Income 350000.0 exceeds threshold 250000.0",
            raw_text="Income <= 2.5L",
        )

        explanation = gen.generate_explanation(
            ruleset=self.ruleset,
            profile=profile,
            rule_status=RuleStatus.FAIL,
            rule_results=[rule_res],
            retrieved_chunks=self.retrieved_chunks,
        )

        # Invariant: Contradictory explanation is REJECTED and template fallback used!
        self.assertTrue(explanation.rejection_fallback_used)
        self.assertEqual(explanation.authoritative_decision, "FAIL")
        self.assertIn("Statutory Evaluation: FAIL", explanation.answer)
        self.assertNotIn("you are eligible", explanation.answer.lower())


if __name__ == "__main__":
    unittest.main()
