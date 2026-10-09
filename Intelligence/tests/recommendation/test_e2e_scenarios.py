"""
FIN Phase 19 End-to-End Test Scenarios (Specification Part 28).
Validates the six canonical test scenarios:
E2E 1 — Personalized Scholarship Search (Gujarat, OBC, Student)
E2E 2 — Family Income Distinction (annual_family_income vs annual_income)
E2E 3 — Missing Information (diagnostic missing_fields on structured schemes)
E2E 4 — Conflict Detection (discordant document vs user declaration)
E2E 5 — Unregistered Rule (eligibility_status = UNKNOWN)
E2E 6 — Registered Rule (engine's actual result reported without reimplementation)
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
from src.query.models import CanonicalIntent, QueryUnderstandingResult
from src.query.service import QueryUnderstandingService
from src.rag.models import RetrievedChunk, SchemeRetrievalResult, SourceTier
from src.rag.retriever import HybridRetriever
from src.eligibility.engine import EligibilityEngine
from src.rules.models import RuleStatus
from src.recommendation.service import SchemeRecommendationService


class TestPhase19E2EScenarios(unittest.TestCase):
    """End-to-End scenario tests directly validating Part 28 specifications."""

    @classmethod
    def setUpClass(cls):
        rules_dir = Path(__file__).resolve().parents[2] / "data" / "schemes" / "rules" / "examples"
        cls.engine = EligibilityEngine()
        if rules_dir.exists():
            cls.engine.load_rules_from_directory(rules_dir)

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_e2e.db")
        self.repo = FactPersistenceRepository(db_path=self.db_path)
        self.context_service = ApplicantContextService(repository=self.repo)
        self.query_service = QueryUnderstandingService(applicant_context_service=self.context_service)
        self.mock_retriever = MagicMock(spec=HybridRetriever)

        self.service = SchemeRecommendationService(
            context_service=self.context_service,
            query_service=self.query_service,
            retriever=self.mock_retriever,
            eligibility_engine=self.engine,
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_mock_result(self, slug: str, name: str, state: str = "All India", category: str = "All") -> SchemeRetrievalResult:
        chunk = RetrievedChunk(
            chunk_id=f"chunk_{slug}",
            content=f"Statutory text for {name}",
            scheme_slug=slug,
            scheme_name=name,
            source_tier=SourceTier.PRIMARY_SCHEME.value,
            dense_score=0.9,
            rerank_score=0.9,
            metadata={"source_url": f"https://myscheme.gov.in/{slug}", "state": state, "category": category},
        )
        return SchemeRetrievalResult(
            scheme_slug=slug,
            scheme_name=name,
            aggregate_score=0.9,
            best_matching_chunks=[chunk],
            source_metadata={"source_url": f"https://myscheme.gov.in/{slug}", "state": state, "category": category, "highest_source_tier": SourceTier.PRIMARY_SCHEME.value},
        )

    # ------------------------------------------------------------------------
    # E2E 1 — PERSONALIZED SCHOLARSHIP SEARCH
    # ------------------------------------------------------------------------
    def test_e2e_1_personalized_scholarship_search(self):
        """
        Applicant: age=19, state=Gujarat, social_category=OBC, is_student=True
        Query: 'Which scholarships are relevant to me?'
        """
        app_id = "applicant_e2e_1"
        self.context_service.record_user_fact(app_id, "age", 19)
        self.context_service.record_user_fact(app_id, "state", "Gujarat")
        self.context_service.record_user_fact(app_id, "social_category", "OBC")
        self.context_service.record_user_fact(app_id, "is_student", True)

        # Mock retriever response
        scholarship_result = self._create_mock_result("guj-obc-scholarship", "Gujarat Post-Matric OBC Scholarship", state="Gujarat", category="OBC")
        self.mock_retriever.retrieve_schemes.return_value = [scholarship_result]

        # Execute
        res = self.service.recommend_schemes(app_id, "Which scholarships are relevant to me?")

        # Verifications
        self.assertEqual(res.applied_filters.get("state_filter", {}).get("value"), "Gujarat")
        self.assertEqual(res.applied_filters.get("category_filter", {}).get("value"), "OBC")
        self.assertEqual(res.applied_filters.get("beneficiary_filter", {}).get("value"), "Student")
        self.assertEqual(len(res.recommendations), 1)

        rec = res.recommendations[0]
        self.assertEqual(rec.scheme_slug, "guj-obc-scholarship")
        self.assertGreater(rec.compatibility_score, 0.7)
        self.assertIsNotNone(rec.evidence)
        self.assertEqual(rec.evidence.source_tier, SourceTier.PRIMARY_SCHEME.value)
        # Eligibility not fabricated for unregistered scheme
        self.assertEqual(rec.eligibility_status, RuleStatus.UNKNOWN.value)

    # ------------------------------------------------------------------------
    # E2E 2 — FAMILY INCOME
    # ------------------------------------------------------------------------
    def test_e2e_2_family_income(self):
        """
        Applicant: annual_family_income = 300000
        Query: 'What government schemes could help my family?'
        """
        app_id = "applicant_e2e_2"
        self.context_service.record_user_fact(app_id, "annual_family_income", 300000)

        ctx = self.context_service.get_applicant_context(app_id)
        # Critical verification: family income remains family income, not personal income
        self.assertEqual(ctx.get_value("annual_family_income"), 300000)
        self.assertIsNone(ctx.get_value("annual_income"))

        welfare_result = self._create_mock_result("family-welfare", "National Family Welfare Scheme")
        self.mock_retriever.retrieve_schemes.return_value = [welfare_result]

        res = self.service.recommend_schemes(app_id, "What government schemes could help my family?")

        self.assertIn("annual_family_income", res.active_facts_summary)
        self.assertNotIn("annual_income", res.active_facts_summary)
        self.assertEqual(len(res.recommendations), 1)
        # Invariant: Retrieval never decides eligibility
        self.assertEqual(res.recommendations[0].eligibility_status, RuleStatus.UNKNOWN.value)

    # ------------------------------------------------------------------------
    # E2E 3 — MISSING INFORMATION
    # ------------------------------------------------------------------------
    def test_e2e_3_missing_information(self):
        """
        Applicant: age=19, state=Gujarat
        Query: 'Which schemes may be suitable for me?'
        """
        app_id = "applicant_e2e_3"
        self.context_service.record_user_fact(app_id, "age", 19)
        self.context_service.record_user_fact(app_id, "state", "Gujarat")

        # Mock retrieval returning pm-kisan (which has registered rules)
        kisan_result = self._create_mock_result("pm-kisan", "Pradhan Mantri Kisan Samman Nidhi")
        self.mock_retriever.retrieve_schemes.return_value = [kisan_result]

        res = self.service.recommend_schemes(app_id, "Which schemes may be suitable for me?")
        rec = res.recommendations[0]

        # Missing fields must be reported from structured rules
        self.assertEqual(rec.missing_fields_status, "DETERMINISTIC_RULES")
        missing_names = [m["field"] for m in rec.missing_fields]
        self.assertIn("owns_cultivable_land", missing_names)
        self.assertIn("is_taxpayer", missing_names)

    # ------------------------------------------------------------------------
    # E2E 4 — CONFLICT
    # ------------------------------------------------------------------------
    def test_e2e_4_conflict_detection(self):
        """
        Document: annual_family_income = 420000
        User: 'My family income is 800000.'
        """
        app_id = "applicant_e2e_4"
        # Stored document fact
        fact_doc = ApplicantFact(
            applicant_id=app_id,
            field="annual_family_income",
            value=420000,
            normalized_value=420000,
            data_type="numeric",
            confidence=0.95,
            source_type=FactSourceType.DOCUMENT,
            source_document="income_cert.pdf",
            verification_status=FactVerificationStatus.EXTRACTED,
        )
        self.repo.save_fact(fact_doc, Evidence(applicant_fact_id=fact_doc.id, applicant_id=app_id, source_type=FactSourceType.DOCUMENT, source_uri="income_cert.pdf"))

        # User declares discordant value
        fact_user = ApplicantFact(
            applicant_id=app_id,
            field="annual_family_income",
            value=800000,
            normalized_value=800000,
            data_type="numeric",
            confidence=1.0,
            source_type=FactSourceType.USER_INPUT,
            source_document="user_declaration",
            verification_status=FactVerificationStatus.SELF_REPORTED,
        )
        self.repo.save_fact(fact_user, Evidence(applicant_fact_id=fact_user.id, applicant_id=app_id, source_type=FactSourceType.USER_INPUT, source_uri="dialogue"))

        ctx = self.context_service.get_applicant_context(app_id)
        self.assertTrue(ctx.has_conflict("annual_family_income"))

        scheme_result = self._create_mock_result("income-support", "Income Support Scheme")
        self.mock_retriever.retrieve_schemes.return_value = [scheme_result]

        res = self.service.recommend_schemes(app_id, "Which schemes can I apply for?")

        # Conflict is detected and preserved
        self.assertIn("annual_family_income", res.conflicts_detected)
        # Never silently overwrite or produce false PASS
        self.assertNotEqual(res.recommendations[0].eligibility_status, RuleStatus.PASS.value)

    # ------------------------------------------------------------------------
    # E2E 5 — UNKNOWN RULE
    # ------------------------------------------------------------------------
    def test_e2e_5_unknown_rule(self):
        """
        Retrieve a scheme without a registered deterministic rule.
        Expected: eligibility_status = UNKNOWN, not FAIL and not PASS.
        """
        app_id = "applicant_e2e_5"
        self.context_service.record_user_fact(app_id, "state", "Rajasthan")

        unreg_result = self._create_mock_result("state-unregistered-scheme", "Rajasthan Rural Craft Scheme", state="Rajasthan")
        self.mock_retriever.retrieve_schemes.return_value = [unreg_result]

        res = self.service.recommend_schemes(app_id, "Rural schemes in Rajasthan")
        rec = res.recommendations[0]

        self.assertEqual(rec.eligibility_status, RuleStatus.UNKNOWN.value)
        self.assertIsNone(rec.is_eligible)
        self.assertNotEqual(rec.eligibility_status, RuleStatus.PASS.value)
        self.assertNotEqual(rec.eligibility_status, RuleStatus.FAIL.value)

    # ------------------------------------------------------------------------
    # E2E 6 — REGISTERED RULE
    # ------------------------------------------------------------------------
    def test_e2e_6_registered_rule(self):
        """
        Retrieve a scheme with an existing deterministic rule (pm-kisan).
        Call EligibilityEngine.
        Expected: Phase 19 reports the engine's actual result (PASS/FAIL/UNKNOWN/REVIEW).
        """
        app_id = "applicant_e2e_6"
        # Seed facts that satisfy pm-kisan rules 100%
        self.context_service.record_user_fact(app_id, "owns_cultivable_land", True)
        self.context_service.record_user_fact(app_id, "is_institutional_landholder", False)
        self.context_service.record_user_fact(app_id, "is_taxpayer", False)
        self.context_service.record_user_fact(app_id, "monthly_pension_amount", 0)

        kisan_result = self._create_mock_result("pm-kisan", "Pradhan Mantri Kisan Samman Nidhi")
        self.mock_retriever.retrieve_schemes.return_value = [kisan_result]

        res = self.service.recommend_schemes(app_id, "Am I eligible for PM Kisan?")
        rec = res.recommendations[0]

        # Engine evaluated directly
        self.assertEqual(rec.eligibility_status, RuleStatus.PASS.value)
        self.assertTrue(rec.is_eligible)


if __name__ == "__main__":
    unittest.main()
