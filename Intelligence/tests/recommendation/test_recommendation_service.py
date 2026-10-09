"""
FIN Phase 19 SchemeRecommendationService Tests.
Verifies end-to-end recommendation orchestration:
- Applicant context loading and validation
- Deterministic bridge invocation
- Hybrid retrieval execution
- Compatibility analysis and score computation
- Statutory gap analysis
- Deterministic eligibility evaluation boundary (registered vs unregistered rules)
- Evidence & provenance preservation
- Ranking logic
"""

import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

from src.context.models import ApplicantContext
from src.context.service import ApplicantContextService
from src.extraction.models import ApplicantFact, Evidence, FactSourceType, FactVerificationStatus
from src.persistence.repository import FactPersistenceRepository
from src.query.service import QueryUnderstandingService
from src.rag.models import RetrievalQuery, RetrievedChunk, SchemeRetrievalResult, SourceTier
from src.rag.retriever import HybridRetriever
from src.eligibility.engine import EligibilityEngine
from src.rules.models import RuleStatus
from src.recommendation.service import SchemeRecommendationService


class TestSchemeRecommendationService(unittest.TestCase):
    """Test suite for SchemeRecommendationService."""

    @classmethod
    def setUpClass(cls):
        rules_dir = Path(__file__).resolve().parents[2] / "data" / "schemes" / "rules" / "examples"
        cls.engine = EligibilityEngine()
        if rules_dir.exists():
            cls.engine.load_rules_from_directory(rules_dir)

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_recommendation.db")
        self.repo = FactPersistenceRepository(db_path=self.db_path)
        self.context_service = ApplicantContextService(repository=self.repo)
        self.query_service = QueryUnderstandingService(applicant_context_service=self.context_service)

        # Mock HybridRetriever
        self.mock_retriever = MagicMock(spec=HybridRetriever)
        self.pm_kisan_chunk = RetrievedChunk(
            chunk_id="chunk_pm_kisan_1",
            content="Pradhan Mantri Kisan Samman Nidhi provides financial support to cultivable landholders.",
            scheme_id="9f760605-d17e-5f82-b7cd-a15b625d689f",
            scheme_slug="pm-kisan",
            scheme_name="Pradhan Mantri Kisan Samman Nidhi",
            source_tier=SourceTier.PRIMARY_SCHEME.value,
            dense_score=0.92,
            rerank_score=0.95,
            metadata={"source_url": "https://pmkisan.gov.in", "state": "All India", "ministry": "Ministry of Agriculture"},
        )
        self.pm_kisan_result = SchemeRetrievalResult(
            scheme_slug="pm-kisan",
            scheme_name="Pradhan Mantri Kisan Samman Nidhi",
            aggregate_score=0.95,
            best_matching_chunks=[self.pm_kisan_chunk],
            source_metadata={"source_url": "https://pmkisan.gov.in", "state": "All India", "ministry": "Ministry of Agriculture", "highest_source_tier": SourceTier.PRIMARY_SCHEME.value},
        )

        self.unregistered_chunk = RetrievedChunk(
            chunk_id="chunk_unreg_1",
            content="General welfare scheme for citizens.",
            scheme_id="unreg-123",
            scheme_slug="general-citizen-welfare",
            scheme_name="General Citizen Welfare Scheme",
            source_tier=SourceTier.PRIMARY_SCHEME.value,
            dense_score=0.75,
            rerank_score=0.78,
            metadata={"source_url": "https://welfare.gov.in", "state": "All India"},
        )
        self.unregistered_result = SchemeRetrievalResult(
            scheme_slug="general-citizen-welfare",
            scheme_name="General Citizen Welfare Scheme",
            aggregate_score=0.78,
            best_matching_chunks=[self.unregistered_chunk],
            source_metadata={"source_url": "https://welfare.gov.in", "state": "All India", "highest_source_tier": SourceTier.PRIMARY_SCHEME.value},
        )

        self.mock_retriever.retrieve_schemes.return_value = [self.pm_kisan_result, self.unregistered_result]

        self.service = SchemeRecommendationService(
            context_service=self.context_service,
            query_service=self.query_service,
            retriever=self.mock_retriever,
            eligibility_engine=self.engine,
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _seed_farmer_applicant(self, applicant_id: str):
        fact = ApplicantFact(
            applicant_id=applicant_id,
            field="owns_cultivable_land",
            value=True,
            normalized_value=True,
            data_type="boolean",
            confidence=1.0,
            source_type=FactSourceType.USER_INPUT,
            source_document="user_declaration",
            verification_status=FactVerificationStatus.USER_CONFIRMED,
        )
        ev = Evidence(
            applicant_fact_id=fact.id,
            applicant_id=applicant_id,
            source_type=FactSourceType.USER_INPUT,
            source_uri="dialogue",
            confidence=1.0,
            metadata={"field": "owns_cultivable_land"},
        )
        self.repo.save_fact(fact, ev)

        # Also add non-institutional landholder fact
        f2 = ApplicantFact(
            applicant_id=applicant_id,
            field="is_institutional_landholder",
            value=False,
            normalized_value=False,
            data_type="boolean",
            confidence=1.0,
            source_type=FactSourceType.USER_INPUT,
            source_document="user_declaration",
            verification_status=FactVerificationStatus.USER_CONFIRMED,
        )
        self.repo.save_fact(f2, Evidence(applicant_fact_id=f2.id, applicant_id=applicant_id, source_type=FactSourceType.USER_INPUT, source_uri="dialogue"))

        # Add is_taxpayer = False
        f3 = ApplicantFact(
            applicant_id=applicant_id,
            field="is_taxpayer",
            value=False,
            normalized_value=False,
            data_type="boolean",
            confidence=1.0,
            source_type=FactSourceType.USER_INPUT,
            source_document="user_declaration",
            verification_status=FactVerificationStatus.USER_CONFIRMED,
        )
        self.repo.save_fact(f3, Evidence(applicant_fact_id=f3.id, applicant_id=applicant_id, source_type=FactSourceType.USER_INPUT, source_uri="dialogue"))

        # Add monthly_pension_amount = 0
        f4 = ApplicantFact(
            applicant_id=applicant_id,
            field="monthly_pension_amount",
            value=0,
            normalized_value=0,
            data_type="numeric",
            confidence=1.0,
            source_type=FactSourceType.USER_INPUT,
            source_document="user_declaration",
            verification_status=FactVerificationStatus.USER_CONFIRMED,
        )
        self.repo.save_fact(f4, Evidence(applicant_fact_id=f4.id, applicant_id=applicant_id, source_type=FactSourceType.USER_INPUT, source_uri="dialogue"))

    def test_recommendation_validation_requires_inputs(self):
        """Service raises ValueError if applicant_id or query is missing/empty."""
        with self.assertRaises(ValueError):
            self.service.recommend_schemes("", "scholarships")
        with self.assertRaises(ValueError):
            self.service.recommend_schemes("app_1", "")

    def test_end_to_end_recommendation_flow(self):
        """Valid recommendation flow produces structured recommendations with evidence."""
        self._seed_farmer_applicant("app_farmer_1")

        result = self.service.recommend_schemes(
            applicant_id="app_farmer_1",
            query="Which farmer assistance schemes can I get?",
            top_k=5,
        )

        self.assertEqual(result.applicant_id, "app_farmer_1")
        self.assertEqual(result.query, "Which farmer assistance schemes can I get?")
        self.assertEqual(result.total_candidates_retrieved, 2)
        self.assertEqual(len(result.recommendations), 2)

        # First recommendation is pm-kisan
        rec_kisan = next(r for r in result.recommendations if r.scheme_slug == "pm-kisan")
        self.assertEqual(rec_kisan.scheme_name, "Pradhan Mantri Kisan Samman Nidhi")
        self.assertGreater(rec_kisan.relevance_score, 0.9)
        self.assertGreater(rec_kisan.compatibility_score, 0.5)

        # Registered rule evaluation
        self.assertEqual(rec_kisan.eligibility_status, RuleStatus.PASS.value)
        self.assertTrue(rec_kisan.is_eligible)

        # Evidence preservation
        self.assertIsNotNone(rec_kisan.evidence)
        self.assertEqual(rec_kisan.evidence.source_tier, SourceTier.PRIMARY_SCHEME.value)
        self.assertIn("https://pmkisan.gov.in", rec_kisan.evidence.source_url)
        self.assertGreater(len(rec_kisan.evidence.snippets), 0)

    def test_unregistered_scheme_has_unknown_eligibility(self):
        """
        CRITICAL ARCHITECTURAL INVARIANT:
        Unregistered scheme NEVER receives fabricated PASS or FAIL.
        eligibility_status must be UNKNOWN and is_eligible must be None.
        """
        result = self.service.recommend_schemes(
            applicant_id="app_unreg_test",
            query="general welfare",
        )

        rec_unreg = next(r for r in result.recommendations if r.scheme_slug == "general-citizen-welfare")
        self.assertEqual(rec_unreg.eligibility_status, RuleStatus.UNKNOWN.value)
        self.assertIsNone(rec_unreg.is_eligible)
        self.assertEqual(rec_unreg.missing_fields_status, "UNKNOWN")

    def test_ranking_prioritizes_pass_over_unregistered(self):
        """PASS schemes receive rank bonus, ranking higher than UNKNOWN or FAIL."""
        self._seed_farmer_applicant("app_rank_test")

        result = self.service.recommend_schemes(
            applicant_id="app_rank_test",
            query="farmer and citizen schemes",
        )

        # The first ranked scheme should be pm-kisan because it has high relevance + high compatibility + PASS bonus
        self.assertEqual(result.recommendations[0].scheme_slug, "pm-kisan")
        self.assertGreaterEqual(
            result.recommendations[0].overall_match_score,
            result.recommendations[1].overall_match_score,
        )

    def test_distinguishes_personal_and_family_income(self):
        """Service respects distinction between personal income and family income."""
        # Record family income
        self.context_service.record_user_fact("app_income_test", "annual_family_income", 350000)

        ctx = self.context_service.get_applicant_context("app_income_test")
        self.assertEqual(ctx.get_value("annual_family_income"), 350000)
        self.assertIsNone(ctx.get_value("annual_income"))

        result = self.service.recommend_schemes("app_income_test", "schemes for low income families")
        self.assertIn("annual_family_income", result.active_facts_summary)
        self.assertNotIn("annual_income", result.active_facts_summary)


if __name__ == "__main__":
    unittest.main()
