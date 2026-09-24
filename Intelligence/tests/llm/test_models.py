"""
Unit tests for Phase 6 LLM data models and serialization.
"""

import unittest
import sys
from pathlib import Path

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.llm.models import (
    UserIntent,
    ExtractionConfidence,
    AmbiguityType,
    ClaimSupportStatus,
    AmbiguityRecord,
    QueryIntent,
    ApplicantFactCandidate,
    FactExtractionResult,
    FactualClaim,
    GroundedExplanation,
    LLMMetadata,
)
from src.extraction.models import FactVerificationStatus


class TestLLMModels(unittest.TestCase):

    def test_query_intent_serialization(self):
        amb = AmbiguityRecord(
            ambiguity_type=AmbiguityType.APPROXIMATE_VALUE,
            raw_span="around 4 lakh",
            description="Approximate income",
        )
        intent = QueryIntent(
            original_query="Show schemes in Gujarat",
            normalized_query="show schemes in gujarat",
            language="en",
            intent=UserIntent.SCHEME_DISCOVERY,
            state="Gujarat",
            keywords=["scholarship", "schemes"],
            confidence=0.95,
            ambiguities=[amb],
        )

        d = intent.to_dict()
        self.assertEqual(d["intent"], "SCHEME_DISCOVERY")
        self.assertEqual(d["state"], "Gujarat")
        self.assertTrue(d["is_search_hint_only"])

        # Deserialize
        restored = QueryIntent.from_dict(d)
        self.assertEqual(restored.intent, UserIntent.SCHEME_DISCOVERY)
        self.assertEqual(restored.state, "Gujarat")
        self.assertEqual(len(restored.ambiguities), 1)

    def test_applicant_fact_candidate_invariants(self):
        # Must default to SELF_REPORTED and hold only raw_value
        candidate = ApplicantFactCandidate(
            field="annual_family_income",
            raw_value="4.2 lakh",
            confidence=0.95,
            evidence_text="income is 4.2 lakh",
        )
        self.assertEqual(candidate.suggested_verification_status, FactVerificationStatus.SELF_REPORTED)
        self.assertEqual(candidate.raw_value, "4.2 lakh")
        self.assertFalse(hasattr(candidate, "normalized_value"))  # Invariant: Phase 4 normalizes exclusively!

        d = candidate.to_dict()
        self.assertEqual(d["suggested_verification_status"], "SELF_REPORTED")

        restored = ApplicantFactCandidate.from_dict(d)
        self.assertEqual(restored.field, "annual_family_income")
        self.assertEqual(restored.raw_value, "4.2 lakh")

    def test_grounded_explanation_serialization(self):
        claim = FactualClaim(
            statement="Beneficiary must reside in Gujarat.",
            cited_chunk_ids=["chunk_123"],
            cited_urls=["https://scholarships.gujarat.gov.in"],
            support_status=ClaimSupportStatus.SUPPORTED,
            support_score=0.85,
        )
        explanation = GroundedExplanation(
            authoritative_decision="PASS",
            scheme_id="gujarat_sc_scholarship",
            answer="Applicant is eligible according to statutory criteria.",
            claims=[claim],
            supporting_chunk_ids=["chunk_123"],
            supporting_source_urls=["https://scholarships.gujarat.gov.in"],
            passed_rules=["rule_age", "rule_state"],
            failed_rules=[],
            missing_fields=[],
            conflicted_fields=[],
        )

        d = explanation.to_dict()
        self.assertEqual(d["authoritative_decision"], "PASS")
        self.assertEqual(len(d["claims"]), 1)

        restored = GroundedExplanation.from_dict(d)
        self.assertEqual(restored.authoritative_decision, "PASS")
        self.assertEqual(restored.claims[0].support_status, ClaimSupportStatus.SUPPORTED)


if __name__ == "__main__":
    unittest.main()
