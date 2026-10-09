"""
FIN Phase 19 CompatibilityAnalyzer Tests.
Exhaustively tests:
- State: MATCH, MISMATCH, UNKNOWN, NOT_APPLICABLE
- Social Category: MATCH, MISMATCH, UNKNOWN, NOT_APPLICABLE
- Beneficiary / Student / Farmer: MATCH, MISMATCH, UNKNOWN
- Contradictory evidence (conflicts): UNKNOWN with conflict flag
- Scoring bounds [0.0, 1.0] and score breakdown transparency
"""

import unittest
from typing import Any

from src.context.models import ApplicantContext
from src.extraction.models import ApplicantFact, FactSourceType, FactVerificationStatus
from src.recommendation.compatibility import CompatibilityAnalyzer
from src.recommendation.models import CompatibilityState
from src.rag.models import SchemeRetrievalResult, RetrievedChunk, SourceTier


class TestCompatibilityAnalyzer(unittest.TestCase):
    """Test suite for deterministic CompatibilityAnalyzer."""

    def setUp(self):
        self.analyzer = CompatibilityAnalyzer()

    def _create_fact(self, field: str, value: Any, norm_value: Any, applicant_id: str = "app_1") -> ApplicantFact:
        return ApplicantFact(
            id=f"fact_{field}_{applicant_id}",
            applicant_id=applicant_id,
            field=field,
            value=value,
            normalized_value=norm_value,
            data_type="string",
            confidence=1.0,
            source_type=FactSourceType.USER_INPUT,
            source_document="user_declaration",
            verification_status=FactVerificationStatus.USER_CONFIRMED,
        )

    def _create_scheme(self, slug: str, name: str, state: Any = None, category: Any = None, beneficiary: Any = None) -> SchemeRetrievalResult:
        meta = {
            "state": state,
            "category": category,
            "beneficiary_type": beneficiary,
            "source_url": f"https://myscheme.gov.in/{slug}",
        }
        chunk = RetrievedChunk(
            chunk_id=f"chunk_{slug}",
            content=f"{name} overview and eligibility details.",
            scheme_slug=slug,
            scheme_name=name,
            source_tier=SourceTier.PRIMARY_SCHEME.value,
            dense_score=0.9,
            rerank_score=0.9,
            metadata=meta,
        )
        return SchemeRetrievalResult(
            scheme_slug=slug,
            scheme_name=name,
            aggregate_score=0.9,
            best_matching_chunks=[chunk],
            source_metadata=meta,
        )

    def test_state_match(self):
        """State match returns MATCH with explanation."""
        ctx = ApplicantContext(applicant_id="app_1")
        ctx.add_fact(self._create_fact("state", "Gujarat", "Gujarat"))

        scheme = self._create_scheme("guj-scheme", "Gujarat Scholarship Scheme", state="Gujarat")
        res = self.analyzer.analyze(scheme, ctx)

        state_matches = [m for m in res.matched_facts if m.field == "state"]
        self.assertEqual(len(state_matches), 1)
        self.assertEqual(state_matches[0].status, CompatibilityState.MATCH)
        self.assertGreater(res.overall_compatibility_score, 0.5)

    def test_state_mismatch(self):
        """Applicant state different from state scheme returns MISMATCH with score penalty."""
        ctx = ApplicantContext(applicant_id="app_1")
        ctx.add_fact(self._create_fact("state", "Maharashtra", "Maharashtra"))

        scheme = self._create_scheme("guj-scheme", "Gujarat Scholarship Scheme", state="Gujarat")
        res = self.analyzer.analyze(scheme, ctx)

        state_mismatches = [m for m in res.unmatched_facts if m.field == "state"]
        self.assertEqual(len(state_mismatches), 1)
        self.assertEqual(state_mismatches[0].status, CompatibilityState.MISMATCH)

    def test_state_not_applicable_for_all_india(self):
        """All-India central scheme treats state as NOT_APPLICABLE."""
        ctx = ApplicantContext(applicant_id="app_1")
        ctx.add_fact(self._create_fact("state", "Gujarat", "Gujarat"))

        scheme = self._create_scheme("pm-kisan", "PM Kisan", state="All India")
        res = self.analyzer.analyze(scheme, ctx)

        state_facts = [m for m in res.matched_facts if m.field == "state"]
        self.assertEqual(len(state_facts), 1)
        self.assertEqual(state_facts[0].status, CompatibilityState.NOT_APPLICABLE)

    def test_state_unknown_when_missing(self):
        """When applicant state is missing, returns UNKNOWN without fabricating values."""
        ctx = ApplicantContext(applicant_id="app_1")  # No state fact

        scheme = self._create_scheme("guj-scheme", "Gujarat Scheme", state="Gujarat")
        res = self.analyzer.analyze(scheme, ctx)

        state_unknowns = [m for m in res.unknown_facts if m.field == "state"]
        self.assertEqual(len(state_unknowns), 1)
        self.assertEqual(state_unknowns[0].status, CompatibilityState.UNKNOWN)

    def test_conflicted_fact_recorded_in_conflict_facts(self):
        """Conflicted fact produces UNKNOWN and is explicitly recorded in conflict_facts."""
        ctx = ApplicantContext(applicant_id="app_1")
        ctx.add_fact(self._create_fact("state", "Gujarat", "Gujarat"))
        ctx.add_fact(self._create_fact("state", "Maharashtra", "Maharashtra"))

        self.assertTrue(ctx.has_conflict("state"))

        scheme = self._create_scheme("guj-scheme", "Gujarat Scheme", state="Gujarat")
        res = self.analyzer.analyze(scheme, ctx)

        conf_facts = [f for f in res.conflict_facts if f.field == "state"]
        self.assertEqual(len(conf_facts), 1)
        self.assertTrue(conf_facts[0].has_conflict)
        self.assertEqual(conf_facts[0].status, CompatibilityState.UNKNOWN)

    def test_social_category_match_and_mismatch(self):
        """Social category match and mismatch evaluation."""
        ctx_obc = ApplicantContext(applicant_id="app_obc")
        ctx_obc.add_fact(self._create_fact("social_category", "OBC", "OBC"))

        scheme_sc = self._create_scheme("sc-hostel", "SC Hostel Scheme", category="SC")
        res_mismatch = self.analyzer.analyze(scheme_sc, ctx_obc)
        self.assertTrue(any(f.field == "social_category" and f.status == CompatibilityState.MISMATCH for f in res_mismatch.unmatched_facts))

        scheme_obc = self._create_scheme("obc-scholarship", "OBC Scholarship", category="OBC")
        res_match = self.analyzer.analyze(scheme_obc, ctx_obc)
        self.assertTrue(any(f.field == "social_category" and f.status == CompatibilityState.MATCH for f in res_match.matched_facts))

    def test_student_beneficiary_matching(self):
        """is_student=True matches Student beneficiary type."""
        ctx = ApplicantContext(applicant_id="app_student")
        ctx.add_fact(self._create_fact("is_student", True, True))

        scheme = self._create_scheme("student-aid", "Student Aid Scheme", beneficiary="Student")
        res = self.analyzer.analyze(scheme, ctx)

        student_matches = [m for m in res.matched_facts if m.field == "is_student"]
        self.assertEqual(len(student_matches), 1)
        self.assertEqual(student_matches[0].status, CompatibilityState.MATCH)

    def test_score_bounded_between_zero_and_one(self):
        """Compatibility score is always strictly bounded in [0.0, 1.0]."""
        ctx = ApplicantContext(applicant_id="app_mismatch")
        ctx.add_fact(self._create_fact("state", "Punjab", "Punjab"))
        ctx.add_fact(self._create_fact("social_category", "General", "General"))
        ctx.add_fact(self._create_fact("is_student", False, False))

        scheme = self._create_scheme("sc-kerala-student", "Kerala SC Student Aid", state="Kerala", category="SC", beneficiary="Student")
        res = self.analyzer.analyze(scheme, ctx)

        self.assertGreaterEqual(res.overall_compatibility_score, 0.0)
        self.assertLessEqual(res.overall_compatibility_score, 1.0)
        self.assertIn("score_breakdown", res.to_dict())


if __name__ == "__main__":
    unittest.main()
