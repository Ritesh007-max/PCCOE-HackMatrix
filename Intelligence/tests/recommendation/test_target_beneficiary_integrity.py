"""
Comprehensive Target-Beneficiary & Eligibility Correctness Test Suite.
Validates:
1. Target-beneficiary match independence from generic taxonomy and statutory rules.
2. Source precedence: Structured canonical data > document facts > text heuristics > semantic retrieval.
3. Invariant: Student != automatically eligible for every student/individual scheme.
4. Invariant: UNKNOWN != PASS.
5. Invariant: NO_MATCH / MISMATCH != PASS.
6. Invariant: Relevance score != statutory eligibility.
7. Regression tests for Safai Karamchari, Fishermen, Farmers, and Students.
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

from src.context.models import ApplicantContext
from src.persistence.repository import FactPersistenceRepository
from src.context.service import ApplicantContextService
from src.eligibility.engine import EligibilityEngine
from src.extraction.models import ApplicantFact, Evidence, FactSourceType, FactVerificationStatus
from src.query.service import QueryUnderstandingService
from src.rag.models import RetrievedChunk, SchemeRetrievalResult, SourceTier
from src.rag.retriever import HybridRetriever
from src.recommendation.compatibility import CompatibilityAnalyzer
from src.recommendation.models import CompatibilityState
from src.recommendation.service import SchemeRecommendationService
from src.rules.models import RuleStatus


class TestTargetBeneficiaryIntegrity(unittest.TestCase):
    """Rigorous test suite for target beneficiary matching and eligibility integrity."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_target_integrity.db")
        self.repo = FactPersistenceRepository(db_path=self.db_path)
        self.context_service = ApplicantContextService(repository=self.repo)
        self.query_service = QueryUnderstandingService(applicant_context_service=self.context_service)
        self.analyzer = CompatibilityAnalyzer()

        self.mock_retriever = MagicMock(spec=HybridRetriever)
        self.engine = EligibilityEngine()

        self.service = SchemeRecommendationService(
            context_service=self.context_service,
            query_service=self.query_service,
            retriever=self.mock_retriever,
            eligibility_engine=self.engine,
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _seed_fact(self, applicant_id: str, field: str, value: any, data_type: str = "string"):
        fact = ApplicantFact(
            applicant_id=applicant_id,
            field=field,
            value=value,
            normalized_value=value,
            data_type=data_type,
            confidence=1.0,
            source_type=FactSourceType.USER_INPUT,
            source_document="user_profile",
            verification_status=FactVerificationStatus.USER_CONFIRMED,
        )
        ev = Evidence(
            applicant_fact_id=fact.id,
            applicant_id=applicant_id,
            source_type=FactSourceType.USER_INPUT,
            source_uri="profile",
            confidence=1.0,
            metadata={"field": field},
        )
        self.repo.save_fact(fact, ev)

    def _seed_test_applicant(self, applicant_id: str = "test_applicant"):
        """Seed the standard test applicant: Gujarat, Ahmedabad, SC, student, personal ₹3.5L, family ₹1.8L."""
        self._seed_fact(applicant_id, "state", "Gujarat")
        self._seed_fact(applicant_id, "district", "Ahmedabad")
        self._seed_fact(applicant_id, "social_category", "SC")
        self._seed_fact(applicant_id, "occupation", "student")
        self._seed_fact(applicant_id, "is_student", True, data_type="boolean")
        self._seed_fact(applicant_id, "personal_income", 350000, data_type="number")
        self._seed_fact(applicant_id, "family_income", 180000, data_type="number")
        self._seed_fact(applicant_id, "gender", "male")
        self._seed_fact(applicant_id, "age", 20, data_type="number")
        return self.context_service.get_applicant_context(applicant_id)

    def _create_scheme_candidate(
        self,
        slug: str,
        name: str,
        tags: list = None,
        state: str = "All India",
        caste: str = None,
        eligibility: str = "",
        beneficiary_type: str = "Individual",
        score: float = 0.90,
    ) -> SchemeRetrievalResult:
        meta = {
            "source_url": f"https://myscheme.gov.in/{slug}",
            "state": state,
            "tags": tags or [],
            "eligibility": eligibility,
            "caste": caste,
            "beneficiary_type": beneficiary_type,
            "scheme_name": name,
            "highest_source_tier": SourceTier.PRIMARY_SCHEME.value,
        }
        chunk = RetrievedChunk(
            chunk_id=f"chunk_{slug}",
            content=f"{name}. {eligibility}",
            scheme_id=slug,
            scheme_slug=slug,
            scheme_name=name,
            source_tier=SourceTier.PRIMARY_SCHEME.value,
            dense_score=score,
            rerank_score=score,
            metadata=meta,
        )
        return SchemeRetrievalResult(
            scheme_slug=slug,
            scheme_name=name,
            aggregate_score=score,
            best_matching_chunks=[chunk],
            source_metadata=meta,
        )

    # -------------------------------------------------------------------------
    # Regression Test 1: Safai Karamchari Education Loan (Section 2 & 16)
    # -------------------------------------------------------------------------
    def test_regression_safai_karamchari_education_loan(self):
        """
        Scheme: Loan Based Schemes For Safai Karamchari - Education Loan Scheme
        Applicant: Student, SC, Gujarat, Ahmedabad, Personal 3.5L, Family 1.8L.
        Target Beneficiary: Safai Karamcharis / Manual Scavengers and their dependents.
        Must NOT be explained as generic student match.
        Target-group match MUST be UNKNOWN.
        Eligibility MUST be UNKNOWN (never PASS).
        """
        ctx = self._seed_test_applicant("app_safai_reg")
        candidate = self._create_scheme_candidate(
            slug="lbssf-els",
            name="Loan Based Schemes For Safai Karamchari - Education Loan Scheme",
            tags=["safai karamchari", "education loan", "students"],
            eligibility="Applicant must be a Safai Karamchari or Manual Scavenger or dependent thereof.",
        )

        compat = self.analyzer.analyze(candidate, ctx)
        # Target group match is UNKNOWN because safai karamchari status is missing
        self.assertEqual(compat.target_group_match, CompatibilityState.UNKNOWN)
        self.assertEqual(compat.target_group_name, "Safai Karamcharis")

        # Must NOT explain as "Student profile matches education scheme"
        explanations = " ".join(compat.explanation)
        self.assertNotIn("Student profile matches education & scholarship scheme", explanations)
        self.assertIn("Safai Karamcharis", explanations)
        self.assertIn("does not contain verified Safai Karamchari status", explanations)

        # Full service evaluation
        self.mock_retriever.retrieve_schemes.return_value = [candidate]
        res = self.service.recommend_schemes("app_safai_reg", "education loan")
        rec = res.recommendations[0]

        self.assertEqual(rec.target_group_match, "UNKNOWN")
        self.assertEqual(rec.target_group_name, "Safai Karamcharis")
        # Invariant: UNKNOWN != PASS
        self.assertNotEqual(rec.eligibility_status, "PASS")
        self.assertEqual(rec.eligibility_status, "UNKNOWN")
        self.assertIsNone(rec.is_eligible)

    # -------------------------------------------------------------------------
    # Regression Test 2: Fishermen Scheme (Section 17)
    # -------------------------------------------------------------------------
    def test_regression_fishermen_scheme_mismatch(self):
        """
        Student applicant without fisheries background MUST be MISMATCH on target group.
        Eligibility MUST be FAIL (not PASS, not UNKNOWN).
        """
        ctx = self._seed_test_applicant("app_fish_reg")
        candidate = self._create_scheme_candidate(
            slug="afpfribm",
            name="Assistance For Purchase Of Fishery Requisites - Inboard Marine",
            tags=["fishermen", "marine", "fisheries requisites"],
            eligibility="Targeted exclusively at active marine fishermen holding biometric ID.",
        )

        compat = self.analyzer.analyze(candidate, ctx)
        self.assertEqual(compat.target_group_match, CompatibilityState.MISMATCH)
        self.assertEqual(compat.target_group_name, "Fishermen")

        # Full service evaluation
        self.mock_retriever.retrieve_schemes.return_value = [candidate]
        res = self.service.recommend_schemes("app_fish_reg", "fishery assistance")
        rec = res.recommendations[0]

        self.assertEqual(rec.target_group_match, "MISMATCH")
        self.assertEqual(rec.eligibility_status, "FAIL")
        self.assertFalse(rec.is_eligible)
        self.assertLessEqual(rec.compatibility_score, 0.20)

    # -------------------------------------------------------------------------
    # Regression Test 3: Farmer Scheme (Section 18)
    # -------------------------------------------------------------------------
    def test_regression_farmer_scheme_mismatch_for_student(self):
        """
        Student applicant with no cultivable land MUST be MISMATCH on farmer target group.
        Eligibility MUST be FAIL.
        """
        ctx = self._seed_test_applicant("app_farmer_reg")
        candidate = self._create_scheme_candidate(
            slug="pm-kisan",
            name="Pradhan Mantri Kisan Samman Nidhi",
            tags=["farmer", "kisan", "agriculture"],
            eligibility="All landholding farmer families with cultivable land.",
        )

        compat = self.analyzer.analyze(candidate, ctx)
        self.assertEqual(compat.target_group_match, CompatibilityState.MISMATCH)
        self.assertEqual(compat.target_group_name, "Farmers")

        # Full service evaluation
        self.mock_retriever.retrieve_schemes.return_value = [candidate]
        res = self.service.recommend_schemes("app_farmer_reg", "farmer support")
        rec = res.recommendations[0]

        self.assertEqual(rec.target_group_match, "MISMATCH")
        self.assertEqual(rec.eligibility_status, "FAIL")

    # -------------------------------------------------------------------------
    # Regression Test 4: Student Scheme (Section 19)
    # -------------------------------------------------------------------------
    def test_regression_student_scheme_match(self):
        """
        Student applicant with verified student occupation matches Student target group.
        """
        ctx = self._seed_test_applicant("app_student_reg")
        candidate = self._create_scheme_candidate(
            slug="csmsu",
            name="Central Sector Scheme of Scholarship for College and University Students",
            tags=["scholarship", "higher education", "students"],
            eligibility="Students who are above 80th percentile of successful candidates in class XII.",
        )

        compat = self.analyzer.analyze(candidate, ctx)
        self.assertEqual(compat.target_group_match, CompatibilityState.MATCH)
        self.assertEqual(compat.target_group_name, "Students")
        self.assertIn("student", " ".join(compat.explanation).lower())

    # -------------------------------------------------------------------------
    # Test Matrix: Social Category Matching (Section 7)
    # -------------------------------------------------------------------------
    def test_social_category_sc_match(self):
        """SC applicant matches SC-targeted scheme."""
        ctx = self._seed_test_applicant("app_sc_match")
        candidate = self._create_scheme_candidate(
            slug="post-matric-sc",
            name="Post Matric Scholarship for SC Students",
            caste="SC",
            tags=["sc", "scholarship", "students"],
        )
        compat = self.analyzer.analyze(candidate, ctx)
        sc_matches = [m for m in compat.matched_facts if m.field == "social_category"]
        self.assertTrue(len(sc_matches) > 0)
        self.assertEqual(sc_matches[0].status, CompatibilityState.MATCH)

    def test_social_category_restricted_mismatch(self):
        """SC applicant mismatches ST-only scheme."""
        ctx = self._seed_test_applicant("app_st_mismatch")
        candidate = self._create_scheme_candidate(
            slug="post-matric-st",
            name="Post Matric Scholarship for ST Students",
            caste="ST",
            tags=["st", "scholarship", "students"],
        )
        compat = self.analyzer.analyze(candidate, ctx)
        sc_mismatches = [m for m in compat.unmatched_facts if m.field == "social_category"]
        self.assertTrue(len(sc_mismatches) > 0)
        self.assertEqual(sc_mismatches[0].status, CompatibilityState.MISMATCH)

    def test_social_category_missing_yields_unknown(self):
        """Applicant with no social category yields UNKNOWN when scheme requires SC."""
        self._seed_fact("app_no_caste", "occupation", "student")
        ctx = self.context_service.get_applicant_context("app_no_caste")
        candidate = self._create_scheme_candidate(
            slug="post-matric-sc",
            name="Post Matric Scholarship for SC Students",
            caste="SC",
            tags=["sc", "students"],
        )
        compat = self.analyzer.analyze(candidate, ctx)
        caste_unk = [u for u in compat.unknown_facts if u.field == "social_category"]
        self.assertTrue(len(caste_unk) > 0)
        self.assertEqual(caste_unk[0].status, CompatibilityState.UNKNOWN)

    # -------------------------------------------------------------------------
    # Test Matrix: Jurisdiction Matching (Section 9)
    # -------------------------------------------------------------------------
    def test_jurisdiction_gujarat_state_match(self):
        """Gujarat applicant matches Gujarat-specific scheme."""
        ctx = self._seed_test_applicant("app_guj_match")
        candidate = self._create_scheme_candidate(
            slug="1pmy",
            name="Mukhyamantri Yuva Swavalamban Yojana Gujarat",
            state="Gujarat",
            tags=["scholarship", "students"],
        )
        compat = self.analyzer.analyze(candidate, ctx)
        state_matches = [m for m in compat.matched_facts if m.field == "state"]
        self.assertTrue(len(state_matches) > 0)
        self.assertEqual(state_matches[0].status, CompatibilityState.MATCH)

    def test_jurisdiction_all_india_central_match(self):
        """Gujarat applicant matches Central / All-India scheme without state penalty."""
        ctx = self._seed_test_applicant("app_central_match")
        candidate = self._create_scheme_candidate(
            slug="central-scholarship",
            name="National Scholarship Scheme",
            state="All India",
            tags=["scholarship", "students"],
        )
        compat = self.analyzer.analyze(candidate, ctx)
        state_matches = [m for m in compat.matched_facts if m.field == "state"]
        self.assertTrue(len(state_matches) > 0)
        self.assertEqual(state_matches[0].status, CompatibilityState.NOT_APPLICABLE)

    def test_jurisdiction_other_state_mismatch(self):
        """Gujarat applicant strictly mismatches Haryana-only scheme."""
        ctx = self._seed_test_applicant("app_other_state")
        candidate = self._create_scheme_candidate(
            slug="haryana-pension",
            name="Haryana State Welfare Scheme",
            state="Haryana",
            tags=["welfare"],
        )
        compat = self.analyzer.analyze(candidate, ctx)
        state_mismatches = [m for m in compat.unmatched_facts if m.field == "state"]
        self.assertTrue(len(state_mismatches) > 0)
        self.assertEqual(state_mismatches[0].status, CompatibilityState.MISMATCH)

    # -------------------------------------------------------------------------
    # Test Matrix: Income Separation (Section 8)
    # -------------------------------------------------------------------------
    def test_income_personal_vs_family_separation(self):
        """
        Applicant Personal Income = ₹3,50,000, Family Income = ₹1,80,000.
        Rule for family income <= ₹2,50,000 -> PASS.
        Rule for personal income <= ₹2,50,000 -> FAIL.
        Must NOT conflate personal with family income.
        """
        ctx = self._seed_test_applicant("app_income_sep")
        self.assertEqual(ctx.get_value("personal_income"), 350000)
        self.assertEqual(ctx.get_value("family_income"), 180000)

        # Family income candidate
        cand_family = self._create_scheme_candidate(
            slug="family-scheme",
            name="Scheme with Family Income Ceiling",
            eligibility="Family income must be below Rs 2,50,000 per annum.",
        )
        cand_family.source_metadata["max_family_income"] = 250000
        compat_fam = self.analyzer.analyze(cand_family, ctx)
        fam_matches = [m for m in compat_fam.matched_facts if m.field == "family_income"]
        self.assertTrue(len(fam_matches) > 0)
        self.assertEqual(fam_matches[0].status, CompatibilityState.MATCH)

        # Personal income candidate
        cand_pers = self._create_scheme_candidate(
            slug="personal-scheme",
            name="Scheme with Personal Income Ceiling",
            eligibility="Applicant personal income must not exceed Rs 2,50,000.",
        )
        cand_pers.source_metadata["max_personal_income"] = 250000
        compat_pers = self.analyzer.analyze(cand_pers, ctx)
        pers_mismatches = [m for m in compat_pers.unmatched_facts if m.field == "personal_income"]
        self.assertTrue(len(pers_mismatches) > 0)
        self.assertEqual(pers_mismatches[0].status, CompatibilityState.MISMATCH)

    # -------------------------------------------------------------------------
    # Invariant Tests: UNKNOWN and MISMATCH never become PASS (Sections 12, 13, 15)
    # -------------------------------------------------------------------------
    def test_unknown_never_becomes_pass(self):
        """
        When target-group match is UNKNOWN, statutory eligibility can NEVER be PASS.
        """
        ctx = self._seed_test_applicant("app_unk_pass_guard")
        candidate = self._create_scheme_candidate(
            slug="unknown-group-scheme",
            name="Scheme for Safai Karamchari Rehabilitation",
            tags=["safai karamchari", "rehabilitation"],
            score=0.99,
        )
        self.mock_retriever.retrieve_schemes.return_value = [candidate]
        res = self.service.recommend_schemes("app_unk_pass_guard", "safai karamchari loan")
        rec = res.recommendations[0]

        self.assertEqual(rec.target_group_match, "UNKNOWN")
        self.assertNotEqual(rec.eligibility_status, "PASS")
        self.assertEqual(rec.eligibility_status, "UNKNOWN")
        self.assertIsNone(rec.is_eligible)

    def test_mismatch_never_becomes_pass_even_with_high_relevance(self):
        """
        A high retrieval relevance score (0.99) can NEVER override target-group MISMATCH.
        """
        ctx = self._seed_test_applicant("app_mismatch_pass_guard")
        candidate = self._create_scheme_candidate(
            slug="high-rel-mismatch",
            name="Fisheries Deep Sea Trawler Subsidy",
            tags=["fishermen", "marine"],
            score=0.99,
        )
        self.mock_retriever.retrieve_schemes.return_value = [candidate]
        res = self.service.recommend_schemes("app_mismatch_pass_guard", "trawler subsidy")
        rec = res.recommendations[0]

        self.assertEqual(rec.target_group_match, "MISMATCH")
        self.assertEqual(rec.eligibility_status, "FAIL")
        self.assertFalse(rec.is_eligible)
        self.assertLessEqual(rec.compatibility_score, 0.20)
        self.assertLessEqual(rec.overall_match_score, 0.40)


if __name__ == "__main__":
    unittest.main()
