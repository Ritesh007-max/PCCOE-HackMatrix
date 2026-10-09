"""
FIN Phase 19 ContextRetrievalBridge Tests.
Verifies deterministic mapping of canonical applicant facts into RetrievalQuery filters,
preservation of semantic query intent, conflict isolation, and non-filtering of unsupported fields.
"""

import unittest
from typing import Any

from src.context.models import ApplicantContext
from src.extraction.models import ApplicantFact, FactSourceType, FactVerificationStatus
from src.query.models import CanonicalIntent, DownstreamRoute, QueryUnderstandingResult
from src.recommendation.bridge import ContextRetrievalBridge


class TestContextRetrievalBridge(unittest.TestCase):
    """Test suite for ContextRetrievalBridge."""

    def _create_fact(self, field: str, value: Any, norm_value: Any, applicant_id: str = "app_1") -> ApplicantFact:
        return ApplicantFact(
            id=f"fact_{field}",
            applicant_id=applicant_id,
            field=field,
            value=value,
            normalized_value=norm_value,
            data_type="string",
            confidence=1.0,
            source_type=FactSourceType.USER_INPUT,
            source_document="user_test",
            verification_status=FactVerificationStatus.USER_CONFIRMED,
        )

    def test_state_mapping_and_canonicalization(self):
        """Valid non-conflicted state maps to state_filter with canonical naming."""
        ctx = ApplicantContext(applicant_id="app_gujarat")
        ctx.add_fact(self._create_fact("state", "gujarat", "Gujarat", "app_gujarat"))

        query, audit = ContextRetrievalBridge.build_retrieval_query(
            applicant_context=ctx,
            user_query="Which scholarships are available?",
        )

        self.assertEqual(query.state_filter, "Gujarat")
        self.assertEqual(query.query_text, "Which scholarships are available?")
        self.assertIn("state_filter", audit["applied_filters"])

    def test_state_alias_resolution(self):
        """State alias such as 'up' resolves to 'Uttar Pradesh' in state_filter."""
        ctx = ApplicantContext(applicant_id="app_up")
        ctx.add_fact(self._create_fact("state", "UP", "UP", "app_up"))

        query, _ = ContextRetrievalBridge.build_retrieval_query(
            applicant_context=ctx,
            user_query="housing schemes",
        )
        self.assertEqual(query.state_filter, "Uttar Pradesh")

    def test_social_category_mapping(self):
        """Social category maps to standard acronym (OBC, SC, ST, EWS, General)."""
        ctx = ApplicantContext(applicant_id="app_obc")
        ctx.add_fact(self._create_fact("social_category", "other backward class", "OBC", "app_obc"))

        query, audit = ContextRetrievalBridge.build_retrieval_query(
            applicant_context=ctx,
            user_query="schemes for me",
        )
        self.assertEqual(query.category_filter, "OBC")
        self.assertIn("category_filter", audit["applied_filters"])

    def test_beneficiary_mapping_student(self):
        """is_student=True maps to beneficiary_filter='Student'."""
        ctx = ApplicantContext(applicant_id="app_student")
        ctx.add_fact(self._create_fact("is_student", True, True, "app_student"))

        query, audit = ContextRetrievalBridge.build_retrieval_query(
            applicant_context=ctx,
            user_query="scholarship options",
        )
        self.assertEqual(query.beneficiary_filter, "Student")

    def test_beneficiary_mapping_occupation_farmer(self):
        """Occupation 'farmer' maps to beneficiary_filter='Farmer'."""
        ctx = ApplicantContext(applicant_id="app_farmer")
        ctx.add_fact(self._create_fact("occupation", "farmer", "farmer", "app_farmer"))

        query, audit = ContextRetrievalBridge.build_retrieval_query(
            applicant_context=ctx,
            user_query="crop subsidies",
        )
        self.assertEqual(query.beneficiary_filter, "Farmer")

    def test_conflicted_facts_never_become_hard_filters(self):
        """
        CRITICAL: If a fact is conflicted across documents, it MUST NOT
        be converted into a hard retrieval filter.
        """
        ctx = ApplicantContext(applicant_id="app_conflict")
        # Add two discordant state facts to create a conflict
        ctx.add_fact(self._create_fact("state", "Gujarat", "Gujarat", "app_conflict"))
        ctx.add_fact(self._create_fact("state", "Maharashtra", "Maharashtra", "app_conflict"))

        self.assertTrue(ctx.has_conflict("state"))

        query, audit = ContextRetrievalBridge.build_retrieval_query(
            applicant_context=ctx,
            user_query="welfare schemes",
        )

        self.assertIsNone(query.state_filter)
        self.assertIn("state", audit["ignored_conflicts"])

    def test_unsupported_facts_are_preserved_not_forced_into_filters(self):
        """
        CRITICAL: Fields like age, income, disability are NOT hard retrieval filters.
        They must be preserved for compatibility analysis / eligibility rules.
        """
        ctx = ApplicantContext(applicant_id="app_unsupported")
        ctx.add_fact(self._create_fact("age", 19, 19, "app_unsupported"))
        ctx.add_fact(self._create_fact("annual_family_income", 300000, 300000, "app_unsupported"))
        ctx.add_fact(self._create_fact("disability_percentage", 40, 40, "app_unsupported"))

        query, audit = ContextRetrievalBridge.build_retrieval_query(
            applicant_context=ctx,
            user_query="financial assistance",
        )

        self.assertIsNone(query.state_filter)
        self.assertIsNone(query.category_filter)
        self.assertIsNone(query.beneficiary_filter)
        self.assertIn("age", audit["unsupported_facts_preserved"])
        self.assertIn("annual_family_income", audit["unsupported_facts_preserved"])
        self.assertIn("disability_percentage", audit["unsupported_facts_preserved"])

    def test_user_query_semantics_preserved(self):
        """Query text must preserve citizen semantic intent, never replaced by raw facts."""
        ctx = ApplicantContext(applicant_id="app_student")
        ctx.add_fact(self._create_fact("age", 19, 19, "app_student"))
        ctx.add_fact(self._create_fact("state", "Gujarat", "Gujarat", "app_student"))
        ctx.add_fact(self._create_fact("social_category", "OBC", "OBC", "app_student"))

        user_query = "What higher education scholarships are open for me?"
        query, _ = ContextRetrievalBridge.build_retrieval_query(
            applicant_context=ctx,
            user_query=user_query,
        )

        self.assertEqual(query.query_text, user_query)
        self.assertNotIn("19", query.query_text)
        self.assertNotIn("Gujarat", query.query_text)

    def test_query_understanding_integration(self):
        """Bridge consumes Phase 18 QueryUnderstandingResult normalized message."""
        qu = QueryUnderstandingResult(
            applicant_id="app_1",
            raw_message="which  scholarships   can I get?? ",
            normalized_message="which scholarships can I get?",
            intent=CanonicalIntent.SCHEME_RECOMMENDATION,
            intent_confidence=0.95,
            route=DownstreamRoute.SCHEME_RECOMMENDATION_PIPELINE,
            routing_reason="Recommendation intent",
        )

        query, _ = ContextRetrievalBridge.build_retrieval_query(
            applicant_context=None,
            user_query="which scholarships can I get??",
            query_understanding=qu,
        )

        self.assertEqual(query.query_text, "which scholarships can I get?")

    def test_explicit_overrides_take_precedence(self):
        """Explicit state and category overrides take precedence over context facts."""
        ctx = ApplicantContext(applicant_id="app_override")
        ctx.add_fact(self._create_fact("state", "Gujarat", "Gujarat", "app_override"))

        query, audit = ContextRetrievalBridge.build_retrieval_query(
            applicant_context=ctx,
            user_query="schemes in Delhi",
            state_override="Delhi",
            category_override="SC",
        )

        self.assertEqual(query.state_filter, "Delhi")
        self.assertEqual(query.category_filter, "SC")
        self.assertEqual(audit["applied_filters"]["state_filter"]["source"], "explicit_override")
        self.assertEqual(audit["applied_filters"]["category_filter"]["source"], "explicit_override")


if __name__ == "__main__":
    unittest.main()
