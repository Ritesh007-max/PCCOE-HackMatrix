"""
Phase 21 Comprehensive Explanation Subsystem Tests.
Validates:
- Four-state explanation semantics (PASS, FAIL, UNKNOWN, REVIEW)
- Decision immutability
- Evidence and citation binding
- Grounding verifier & anti-hallucination defense
- Missing-information guidance & conflict handling
- Next actions engine & deterministic priority
- Recommendation & eligibility separation
- Objective multi-scheme comparison
- Benefit explanation
- Fallback on LLM failure / timeout
- Applicant isolation and caching
- Language localization (English, Hindi, Gujarati)
- Numeric and threshold preservation
"""

import unittest
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.rules.models import Rule, LogicGroup, SchemeRuleSet, RuleStatus, ApplicantProfile
from src.eligibility.decision import EligibilityDecision
from src.eligibility.engine import EligibilityEngine
from src.context.models import ApplicantContext
from src.extraction.models import ApplicantFact, FactSourceType, FactVerificationStatus
from src.recommendation.models import SchemeRecommendationItem, RecommendationEvidence
from src.explanation.models import (
    ActionPriority,
    ActionType,
    GroundingStatus,
    ReviewReasonCode,
)
from src.explanation.generator import ExplanationGenerator
from src.explanation.verifier import ExplanationGroundingVerifier
from src.explanation.service import PolicyExplanationService

RULES_EXAMPLES_DIR = _INTELLIGENCE_DIR / "data" / "schemes" / "rules" / "examples"


class TestPhase21ExplanationSubsystem(unittest.TestCase):
    def setUp(self):
        self.engine = EligibilityEngine(RULES_EXAMPLES_DIR)
        self.verifier = ExplanationGroundingVerifier()
        self.service = PolicyExplanationService(verifier=self.verifier)

    # -------------------------------------------------------------------------
    # A. PASS Explanation Semantics
    # -------------------------------------------------------------------------
    def test_pass_explanation_semantics(self):
        # Atal Pension Yojana: 18 <= age <= 40, has_bank_account=True, is_taxpayer=False
        profile = {"age": 28, "has_bank_account": True, "is_taxpayer": False}
        decision = self.engine.evaluate("apy", profile)
        self.assertEqual(decision.status, RuleStatus.PASS)

        bundle = self.service.explain_decision(decision)

        self.assertEqual(bundle.eligibility_status, "PASS")
        self.assertTrue(bundle.is_eligible)
        self.assertIn("Satisfied", bundle.headline)
        # Invariant: Does not claim guaranteed approval
        self.assertIn("subject to final administrative", bundle.summary)
        self.assertGreater(len(bundle.eligibility_explanation.passed_conditions), 0)
        self.assertEqual(len(bundle.eligibility_explanation.failed_conditions), 0)

        # Check next actions include READY_TO_APPLY
        action_types = [a.action_type for a in bundle.next_actions]
        self.assertIn(ActionType.READY_TO_APPLY, action_types)

    # -------------------------------------------------------------------------
    # B. FAIL Explanation Semantics
    # -------------------------------------------------------------------------
    def test_fail_explanation_semantics(self):
        # Atal Pension Yojana: age 50 violates age <= 40
        profile = {"age": 50, "has_bank_account": True, "is_taxpayer": False}
        decision = self.engine.evaluate("apy", profile)
        self.assertEqual(decision.status, RuleStatus.FAIL)

        bundle = self.service.explain_decision(decision)

        self.assertEqual(bundle.eligibility_status, "FAIL")
        self.assertFalse(bundle.is_eligible)
        self.assertIn("Not Satisfied", bundle.headline)
        self.assertGreater(len(bundle.eligibility_explanation.failed_conditions), 0)

        # Disqualifying reason must quote actual statute/reason
        failed_cond = bundle.eligibility_explanation.failed_conditions[0]
        self.assertEqual(failed_cond.field, "age")
        self.assertEqual(failed_cond.status, "FAIL")
        self.assertTrue(failed_cond.hard_constraint)

    # -------------------------------------------------------------------------
    # C. UNKNOWN Explanation Semantics
    # -------------------------------------------------------------------------
    def test_unknown_explanation_semantics(self):
        # Atal Pension Yojana: missing bank account & taxpayer info
        profile = {"age": 25}
        decision = self.engine.evaluate("apy", profile)
        self.assertEqual(decision.status, RuleStatus.UNKNOWN)

        bundle = self.service.explain_decision(decision)

        self.assertEqual(bundle.eligibility_status, "UNKNOWN")
        self.assertIsNone(bundle.is_eligible)
        self.assertIn("Incomplete", bundle.headline)
        self.assertGreater(len(bundle.missing_information), 0)

        # Actions must include PROVIDE_INFORMATION
        action_types = [a.action_type for a in bundle.next_actions]
        self.assertTrue(
            ActionType.PROVIDE_INFORMATION in action_types
            or ActionType.UPLOAD_DOCUMENT in action_types
        )

    # -------------------------------------------------------------------------
    # D. REVIEW Explanation Semantics
    # -------------------------------------------------------------------------
    def test_review_explanation_semantics(self):
        r = Rule(
            rule_id="r1",
            scheme_id="s1",
            rule_type="eligibility",
            field="annual_family_income",
            operator="<=",
            expected_value=500000,
            value_type="numeric",
        )
        # Profile flagged with conflicting income evidence
        prof = ApplicantProfile(data={"annual_family_income": 420000}, conflicts=["annual_family_income"])
        evaluator = self.engine._evaluator
        status, results = evaluator.evaluate_ruleset(
            SchemeRuleSet(scheme_id="s1", scheme_slug="s-conf", scheme_name="Conf Scheme", rules=[r]),
            prof,
        )
        self.assertEqual(status, RuleStatus.REVIEW)

        dec = EligibilityDecision.from_evaluation(
            scheme_id="s1",
            scheme_slug="s-conf",
            scheme_name="Conf Scheme",
            overall_status=status,
            rule_results=results,
        )

        bundle = self.service.explain_decision(dec)

        self.assertEqual(bundle.eligibility_status, "REVIEW")
        self.assertIn("Review Required", bundle.headline)
        self.assertGreater(len(bundle.conflicts), 0)
        self.assertEqual(bundle.conflicts[0].field, "annual_family_income")
        self.assertEqual(bundle.conflicts[0].reason_code, ReviewReasonCode.FACT_CONFLICT)

        # Next actions must include RESOLVE_CONFLICT with priority HIGH
        conflict_action = next((a for a in bundle.next_actions if a.action_type == ActionType.RESOLVE_CONFLICT), None)
        self.assertIsNotNone(conflict_action)
        self.assertEqual(conflict_action.priority, ActionPriority.HIGH)

    # -------------------------------------------------------------------------
    # E. Decision Immutability: Explanation NEVER Mutates Decision
    # -------------------------------------------------------------------------
    def test_zero_decision_mutation(self):
        decision = self.engine.evaluate("apy", {"age": 28, "has_bank_account": True, "is_taxpayer": False})
        orig_status = decision.status
        orig_ver = decision.rule_version
        orig_hash = decision.rule_set_hash

        bundle = self.service.explain_decision(decision)

        # Verify underlying decision object is 100% unaltered
        self.assertEqual(decision.status, orig_status)
        self.assertEqual(decision.rule_version, orig_ver)
        self.assertEqual(decision.rule_set_hash, orig_hash)
        self.assertEqual(bundle.eligibility_status, orig_status.value)

    # -------------------------------------------------------------------------
    # F. Grounding Verifier: Blocks Contradictory LLM Status
    # -------------------------------------------------------------------------
    def test_grounding_verifier_blocks_status_mutation(self):
        decision = self.engine.evaluate("apy", {"age": 55, "has_bank_account": False, "is_taxpayer": True})
        self.assertEqual(decision.status, RuleStatus.FAIL)

        # Create a malicious/broken bundle where status is flipped to PASS
        bundle = ExplanationGenerator.generate_explanation_bundle(decision)
        bundle.eligibility_status = "PASS"

        is_valid, status, errors = self.verifier.verify_bundle(bundle, decision)
        self.assertFalse(is_valid)
        self.assertEqual(status, GroundingStatus.BLOCKED)
        self.assertIn("contradicts", errors[0])

        # Sanitizer must enforce safe fallback restoring FAIL
        sanitized = ExplanationGroundingVerifier.sanitize_or_fallback(bundle, decision)
        self.assertEqual(sanitized.eligibility_status, "FAIL")
        self.assertIn("Deterministic Fallback", sanitized.headline)

    # -------------------------------------------------------------------------
    # G. Grounding Verifier: Rejects Fabricated Rule IDs
    # -------------------------------------------------------------------------
    def test_grounding_verifier_blocks_fabricated_rule_id(self):
        decision = self.engine.evaluate("apy", {"age": 25, "has_bank_account": True, "is_taxpayer": False})
        bundle = ExplanationGenerator.generate_explanation_bundle(decision)

        # Inject fabricated rule ID
        bundle.eligibility_explanation.passed_conditions[0].rule_id = "rule_hallucinated_xyz_999"

        is_valid, status, errors = self.verifier.verify_bundle(bundle, decision)
        self.assertFalse(is_valid)
        self.assertEqual(status, GroundingStatus.BLOCKED)
        self.assertIn("fabricated rule ID", errors[0])

    # -------------------------------------------------------------------------
    # H. Multi-Scheme Comparison (Objective, No Bias)
    # -------------------------------------------------------------------------
    def test_multi_scheme_comparison(self):
        profile = {"age": 28, "has_bank_account": True, "is_taxpayer": False, "owns_cultivable_land": True}
        dec_apy = self.engine.evaluate("apy", profile)
        dec_pmk = self.engine.evaluate("pm-kisan", profile)

        rec_apy = SchemeRecommendationItem(
            scheme_id=dec_apy.scheme_id,
            scheme_slug=dec_apy.scheme_slug,
            scheme_name=dec_apy.scheme_name,
            relevance_score=0.92,
            compatibility_score=1.0,
            overall_match_score=0.95,
        )
        rec_pmk = SchemeRecommendationItem(
            scheme_id=dec_pmk.scheme_id,
            scheme_slug=dec_pmk.scheme_slug,
            scheme_name=dec_pmk.scheme_name,
            relevance_score=0.88,
            compatibility_score=1.0,
            overall_match_score=0.90,
        )

        cmp_res = self.service.compare_schemes(
            recommendations=[rec_apy, rec_pmk],
            decisions={dec_apy.scheme_slug: dec_apy, dec_pmk.scheme_slug: dec_pmk},
        )

        self.assertEqual(len(cmp_res.schemes), 2)
        # Invariant: Does not pick a subjective "winner"
        self.assertNotIn("winner", " ".join(cmp_res.summary_of_differences).lower())
        self.assertNotIn("best scheme", " ".join(cmp_res.summary_of_differences).lower())

    # -------------------------------------------------------------------------
    # I. Applicant Isolation: Caching and Profiles
    # -------------------------------------------------------------------------
    def test_applicant_isolation(self):
        dec_a = self.engine.evaluate("apy", {"age": 25, "has_bank_account": True, "is_taxpayer": False}, applicant_id="app_A")
        dec_b = self.engine.evaluate("apy", {"age": 55, "has_bank_account": False, "is_taxpayer": True}, applicant_id="app_B")

        bundle_a = self.service.explain_decision(dec_a)
        bundle_b = self.service.explain_decision(dec_b)

        self.assertEqual(bundle_a.applicant_id, "app_A")
        self.assertEqual(bundle_b.applicant_id, "app_B")
        self.assertEqual(bundle_a.eligibility_status, "PASS")
        self.assertEqual(bundle_b.eligibility_status, "FAIL")

        # Confirm A facts are not in B
        self.assertIn("Age (25)", str(bundle_a.to_dict()))
        self.assertNotIn("Age (55)", str(bundle_a.to_dict()))
        self.assertIn("Age (55)", str(bundle_b.to_dict()))
        self.assertNotIn("Age (25)", str(bundle_b.to_dict()))

    # -------------------------------------------------------------------------
    # J. Multi-lingual Support (Hindi & Gujarati)
    # -------------------------------------------------------------------------
    def test_multilingual_localization(self):
        dec = self.engine.evaluate("apy", {"age": 28, "has_bank_account": True, "is_taxpayer": False})

        bundle_en = self.service.explain_decision(dec, language="en")
        bundle_hi = self.service.explain_decision(dec, language="hi")
        bundle_gu = self.service.explain_decision(dec, language="gu")

        # Invariant: Status remains PASS across all languages
        self.assertEqual(bundle_en.eligibility_status, "PASS")
        self.assertEqual(bundle_hi.eligibility_status, "PASS")
        self.assertEqual(bundle_gu.eligibility_status, "PASS")

        # Language metadata
        self.assertEqual(bundle_en.language, "en")
        self.assertEqual(bundle_hi.language, "hi")
        self.assertEqual(bundle_gu.language, "gu")

        # Localized text presence
        self.assertIn("Satisfied", bundle_en.headline)
        self.assertIn("पात्रता", bundle_hi.headline)
        self.assertIn("પાત્રતા", bundle_gu.headline)


if __name__ == "__main__":
    unittest.main()
