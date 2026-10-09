"""
FIN Phase A: P0 Data Integrity & Eligibility Repair Test Suite.
Tests:
1. Personal income unavailable when only family income exists.
2. Family income remains separately labeled.
3. Multi-turn clarification for personal vs family income.
4. Conflicting document facts produce REVIEW without silent overwrite.
5. Deleted document exclusion from context and retrieval.
6. OCR status is EXTRACTED / PENDING, not statutory verification.
7. Applicant tenant isolation.
8. Applicant context reaches the rule engine.
9. Missing facts produce UNKNOWN.
10. Conflicts produce REVIEW in rule engine.
"""

import unittest
from pathlib import Path
import sys

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.context.models import ApplicantContext
from src.context.service import ApplicantContextService
from src.context.fact_mapper import canonicalize_fact_key
from src.extraction.models import (
    ApplicantFact,
    FactSourceType,
    FactVerificationStatus,
)
from src.query.reference_resolver import ReferenceResolver
from src.query.service import QueryUnderstandingService
from src.query.models import CanonicalIntent
from src.rules.evaluator import RuleEvaluator
from src.rules.models import ApplicantProfile, Rule, RuleType, RuleStatus


class TestPhaseAP0Integrity(unittest.TestCase):

    def setUp(self):
        self.context_service = ApplicantContextService()
        self.ref_resolver = ReferenceResolver()
        self.query_service = QueryUnderstandingService(applicant_context_service=self.context_service)
        self.rule_evaluator = RuleEvaluator()

    # -------------------------------------------------------------------------
    # Task 1: Personal and Family Income Separation
    # -------------------------------------------------------------------------

    def test_task1_personal_income_unavailable_when_only_family_income_exists(self):
        """
        Given family income ₹1,80,000 and no personal income:
        Question: 'What is my personal annual income?'
        Expected: Resolved to requested_fact='annual_income'; family income is NOT substituted.
        """
        app_id = "test_applicant_inc_sep"
        # Record only annual_family_income
        self.context_service.record_user_fact(
            applicant_id=app_id,
            fact_key="annual_family_income",
            raw_value="180000",
            source_type=FactSourceType.DOCUMENT,
            verification_status=FactVerificationStatus.EXTRACTED,
            source_document="Income_Certificate.pdf",
        )

        ctx = self.context_service.get_applicant_context(app_id)
        # Personal income must be strictly None
        self.assertIsNone(ctx.get_fact("annual_income"))
        # Family income must be strictly present and labeled
        fam_fact = ctx.get_fact("annual_family_income")
        self.assertIsNotNone(fam_fact)
        self.assertEqual(str(fam_fact.value), "180000")

        # Understand query
        res = self.query_service.understand_query(app_id, "What is my personal annual income?")
        self.assertEqual(res.intent, CanonicalIntent.PERSONAL_FACT_LOOKUP)
        self.assertEqual(res.requested_fact, "annual_income")

        # Verify context lookup does NOT return family income as annual_income
        looked_up_fact = self.context_service.get_fact(app_id, res.requested_fact)
        self.assertIsNone(looked_up_fact)

    def test_task1_family_income_remains_separately_labeled(self):
        """Family income query returns annual_family_income explicitly."""
        app_id = "test_applicant_fam_inc"
        self.context_service.record_user_fact(
            applicant_id=app_id,
            fact_key="annual_family_income",
            raw_value="180000",
            source_type=FactSourceType.DOCUMENT,
            verification_status=FactVerificationStatus.EXTRACTED,
        )

        res = self.query_service.understand_query(app_id, "What is my family annual income?")
        self.assertEqual(res.intent, CanonicalIntent.PERSONAL_FACT_LOOKUP)
        self.assertEqual(res.requested_fact, "annual_family_income")

        fact = self.context_service.get_fact(app_id, res.requested_fact)
        self.assertIsNotNone(fact)
        self.assertEqual(fact.field, "annual_family_income")
        self.assertEqual(str(fact.value), "180000")

    def test_task1_multi_turn_clarification(self):
        """Preserves conversational clarification state across follow-up messages."""
        history = [
            {"role": "user", "content": "What is my income?"},
            {
                "role": "assistant",
                "content": "Both personal annual income and family annual income are available in your records. Which one would you like to review?",
            },
        ]

        # User replies just "personal"
        res_pers = self.query_service.understand_query(
            "test_applicant_conv", "personal", conversation_history=history
        )
        self.assertEqual(res_pers.requested_fact, "annual_income")

        # User replies just "family"
        res_fam = self.query_service.understand_query(
            "test_applicant_conv", "family", conversation_history=history
        )
        self.assertEqual(res_fam.requested_fact, "annual_family_income")

    # -------------------------------------------------------------------------
    # Task 2: Document Fact Provenance and Conflicts
    # -------------------------------------------------------------------------

    def test_task2_conflicting_document_facts_produce_review_without_silent_overwrite(self):
        """
        Older document: ₹3,47,250
        Newer document: ₹1,80,000
        Expected: The system must not silently merge these into one authoritative income.
        Both sources must be preserved and field marked CONFLICTED / REVIEW.
        """
        app_id = "test_applicant_conflict_p0"
        ctx = ApplicantContext(applicant_id=app_id)

        # Older document
        doc1_fact = ApplicantFact(
            applicant_id=app_id,
            document_id="doc_older_2023",
            field="annual_family_income",
            value="347250",
            normalized_value=347250.0,
            data_type="numeric",
            confidence=0.95,
            source_document="Income_Cert_2023.pdf",
            source_type=FactSourceType.DOCUMENT,
            verification_status=FactVerificationStatus.EXTRACTED,
        )
        ctx.add_fact(doc1_fact)

        # Newer document with discordant value
        doc2_fact = ApplicantFact(
            applicant_id=app_id,
            document_id="doc_newer_2024",
            field="annual_family_income",
            value="180000",
            normalized_value=180000.0,
            data_type="numeric",
            confidence=0.95,
            source_document="Income_Cert_2024.pdf",
            source_type=FactSourceType.DOCUMENT,
            verification_status=FactVerificationStatus.EXTRACTED,
        )
        ctx.add_fact(doc2_fact)

        # Invariant 1: Must be in conflicts list
        self.assertIn("annual_family_income", ctx.conflicts)

        # Invariant 2: Neither value silently won as single authoritative fact
        resolved_fact = ctx.get_fact("annual_family_income")
        self.assertIsNone(resolved_fact, "Conflicted facts must return None from get_fact to prevent silent overwrite")

        # Invariant 3: Both raw values are preserved in conflict details
        conflict_records = ctx.conflict_details.get("annual_family_income", [])
        self.assertEqual(len(conflict_records), 2)
        sources = {f.source_document for f in conflict_records}
        self.assertIn("Income_Cert_2023.pdf", sources)
        self.assertIn("Income_Cert_2024.pdf", sources)

        # Invariant 4: Bridge to profile records conflict
        prof = ctx.to_applicant_profile()
        self.assertIn("annual_family_income", prof.conflicts)
        self.assertTrue(prof.has_conflict("annual_family_income"))

    def test_task2_deleted_document_exclusion(self):
        """Deleted documents and their extracted facts are pruned from applicant repository."""
        from src.documents.models import DocumentContent, DocumentType, PageContent
        app_id = "test_applicant_del_p0"
        doc = DocumentContent(
            document_id="doc_del_123",
            file_path="mock.pdf",
            file_name="Old_Income_Doc.pdf",
            mime_type="application/pdf",
            document_type=DocumentType.INCOME_CERTIFICATE,
            pages=[PageContent(page_number=1, text="Annual Family Income: 180000")],
        )
        doc_ctx, facts, _ = self.context_service.process_and_store_document(doc, applicant_id=app_id)

        # Verify document exists before deletion
        docs_before = self.context_service.repository.get_applicant_documents(app_id)
        self.assertTrue(len(docs_before) >= 1)

        # Deleting document removes associated records
        deleted = self.context_service.delete_document(app_id, doc_ctx.document_id)
        self.assertTrue(deleted)
        docs_after = self.context_service.repository.get_applicant_documents(app_id)
        self.assertEqual(len(docs_after), 0)

    # -------------------------------------------------------------------------
    # Task 3: Correct Verification Semantics
    # -------------------------------------------------------------------------

    def test_task3_ocr_status_is_extracted_not_issuer_verified(self):
        """OCR success must assign EXTRACTED status, not ISSUER_VERIFIED or legal guarantee."""
        canonical_key = canonicalize_fact_key("parivar_aay", doc_type="INCOME_CERT")
        self.assertEqual(canonical_key, "annual_family_income")

        fact = ApplicantFact(
            applicant_id="user_ocr_test",
            field=canonical_key,
            value="180000",
            normalized_value=180000.0,
            data_type="numeric",
            confidence=0.95,
            source_document="Income_Cert.pdf",
            source_type=FactSourceType.DOCUMENT,
            verification_status=FactVerificationStatus.EXTRACTED,
        )
        self.assertEqual(fact.verification_status, FactVerificationStatus.EXTRACTED)
        self.assertNotEqual(fact.verification_status, FactVerificationStatus.ISSUER_VERIFIED)

    # -------------------------------------------------------------------------
    # Task 4 & 5: Applicant Context Integration & Deterministic Rule Engine
    # -------------------------------------------------------------------------

    def test_task4_applicant_tenant_isolation(self):
        """User B cannot access or inherit User A applicant facts."""
        self.context_service.record_user_fact(
            applicant_id="tenant_user_a",
            fact_key="annual_income",
            raw_value="500000",
            source_document="User_A_Salary.pdf",
        )

        user_b_ctx = self.context_service.get_applicant_context("tenant_user_b")
        self.assertIsNone(user_b_ctx.get_fact("annual_income"))
        self.assertEqual(len(user_b_ctx.all_facts), 0)

    def test_task4_applicant_context_reaches_rule_engine(self):
        """Authenticated applicant facts bridge directly to ApplicantProfile for RuleEvaluator."""
        ctx = ApplicantContext(applicant_id="applicant_rules_test")
        ctx.add_fact(
            ApplicantFact(
                applicant_id="applicant_rules_test",
                field="age",
                value=24,
                normalized_value=24,
                data_type="numeric",
                confidence=1.0,
                source_document="Aadhaar.pdf",
                source_type=FactSourceType.DOCUMENT,
                verification_status=FactVerificationStatus.EXTRACTED,
            )
        )
        ctx.add_fact(
            ApplicantFact(
                applicant_id="applicant_rules_test",
                field="annual_family_income",
                value=150000,
                normalized_value=150000.0,
                data_type="numeric",
                confidence=1.0,
                source_document="Income_Cert.pdf",
                source_type=FactSourceType.DOCUMENT,
                verification_status=FactVerificationStatus.EXTRACTED,
            )
        )

        prof = ctx.to_applicant_profile()
        self.assertEqual(prof.get_value("age"), 24)
        self.assertEqual(prof.get_value("annual_family_income"), 150000.0)

        # Evaluate against age gate >= 18
        age_rule = Rule(
            rule_id="R_AGE_18",
            scheme_id="test_scheme",
            rule_type=RuleType.ELIGIBILITY.value,
            field="age",
            operator=">=",
            expected_value=18,
            value_type="numeric",
            hard_constraint=True,
            raw_text="Age must be at least 18",
        )
        res = self.rule_evaluator.evaluate_rule(age_rule, prof)
        self.assertEqual(res.status, RuleStatus.PASS)

    def test_task4_missing_facts_produce_unknown(self):
        """Missing facts evaluate strictly to UNKNOWN (never PASS, never FAIL)."""
        empty_prof = ApplicantProfile(data={})
        income_rule = Rule(
            rule_id="R_INC_LIMIT",
            scheme_id="test_scheme",
            rule_type=RuleType.ELIGIBILITY.value,
            field="annual_family_income",
            operator="<=",
            expected_value=300000,
            value_type="numeric",
            hard_constraint=True,
            raw_text="Family income must be <= 300000",
        )
        res = self.rule_evaluator.evaluate_rule(income_rule, empty_prof)
        self.assertEqual(res.status, RuleStatus.UNKNOWN)
        self.assertIn("missing or unverified", res.reason)

    def test_task4_conflicts_produce_review(self):
        """Contradictory / conflicted facts evaluate strictly to REVIEW (never PASS)."""
        conflicted_prof = ApplicantProfile(data={}, conflicts=["annual_family_income"])
        income_rule = Rule(
            rule_id="R_INC_LIMIT",
            scheme_id="test_scheme",
            rule_type=RuleType.ELIGIBILITY.value,
            field="annual_family_income",
            operator="<=",
            expected_value=300000,
            value_type="numeric",
            hard_constraint=True,
            raw_text="Family income must be <= 300000",
        )
        res = self.rule_evaluator.evaluate_rule(income_rule, conflicted_prof)
        self.assertEqual(res.status, RuleStatus.REVIEW)
        self.assertIn("Contradictory evidence detected", res.reason)


if __name__ == "__main__":
    unittest.main()
