"""
FIN Phase 19 MissingFieldGapAnalyzer Tests.
Verifies:
- Identification of missing statutory facts from registered SchemeRuleSets.
- Identification of conflicted fields as missing/unresolved.
- Mandatory vs optional criticality tagging based on hard_constraint.
- UNKNOWN status and zero fabrication for schemes lacking registered rule sets.
"""

from pathlib import Path
import unittest
from typing import Any

from src.context.models import ApplicantContext
from src.extraction.models import ApplicantFact, FactSourceType, FactVerificationStatus
from src.recommendation.gap_analysis import MissingFieldGapAnalyzer
from src.recommendation.models import MissingFieldCriticality
from src.eligibility.engine import EligibilityEngine
from src.rag.models import SchemeRetrievalResult, RetrievedChunk, SourceTier


class TestMissingFieldGapAnalyzer(unittest.TestCase):
    """Test suite for MissingFieldGapAnalyzer."""

    @classmethod
    def setUpClass(cls):
        rules_dir = Path(__file__).resolve().parents[2] / "data" / "schemes" / "rules" / "examples"
        cls.engine = EligibilityEngine()
        if rules_dir.exists():
            cls.engine.load_rules_from_directory(rules_dir)

    def setUp(self):
        self.analyzer = MissingFieldGapAnalyzer(eligibility_engine=self.engine)

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

    def _create_scheme_result(self, slug: str, name: str) -> SchemeRetrievalResult:
        chunk = RetrievedChunk(
            chunk_id=f"chunk_{slug}",
            content=f"Statutory text for {name}",
            scheme_slug=slug,
            scheme_name=name,
            source_tier=SourceTier.PRIMARY_SCHEME.value,
        )
        return SchemeRetrievalResult(
            scheme_slug=slug,
            scheme_name=name,
            aggregate_score=0.9,
            best_matching_chunks=[chunk],
            source_metadata={},
        )

    def test_missing_fields_for_registered_scheme(self):
        """When applicant lacks required fields for a registered scheme, reports them."""
        # pm-kisan rules require 'owns_cultivable_land' and 'is_institutional_landholder'
        ctx = ApplicantContext(applicant_id="app_empty")
        scheme = self._create_scheme_result("pm-kisan", "Pradhan Mantri Kisan Samman Nidhi")

        missing, status = self.analyzer.analyze(scheme, ctx)

        self.assertEqual(status, "DETERMINISTIC_RULES")
        self.assertGreater(len(missing), 0)
        missing_field_names = [m.field for m in missing]
        self.assertIn("owns_cultivable_land", missing_field_names)

        # Check that hard constraint rule is marked MANDATORY
        cultivable_mf = next(m for m in missing if m.field == "owns_cultivable_land")
        self.assertEqual(cultivable_mf.criticality, MissingFieldCriticality.MANDATORY)

    def test_satisfied_field_is_not_reported_as_missing(self):
        """When applicant has the fact, it is NOT reported in missing_fields."""
        ctx = ApplicantContext(applicant_id="app_farmer")
        ctx.add_fact(self._create_fact("owns_cultivable_land", True, True, "app_farmer"))

        scheme = self._create_scheme_result("pm-kisan", "Pradhan Mantri Kisan Samman Nidhi")
        missing, status = self.analyzer.analyze(scheme, ctx)

        missing_field_names = [m.field for m in missing]
        self.assertNotIn("owns_cultivable_land", missing_field_names)

    def test_conflicted_field_is_reported_as_missing(self):
        """A field in conflict across documents is reported as missing/unresolved."""
        ctx = ApplicantContext(applicant_id="app_conflict")
        ctx.add_fact(self._create_fact("owns_cultivable_land", True, True, "app_conflict"))
        ctx.add_fact(self._create_fact("owns_cultivable_land", False, False, "app_conflict"))

        self.assertTrue(ctx.has_conflict("owns_cultivable_land"))

        scheme = self._create_scheme_result("pm-kisan", "Pradhan Mantri Kisan Samman Nidhi")
        missing, status = self.analyzer.analyze(scheme, ctx)

        missing_field_names = [m.field for m in missing]
        self.assertIn("owns_cultivable_land", missing_field_names)
        mf = next(m for m in missing if m.field == "owns_cultivable_land")
        self.assertIn("conflict", mf.reason.lower())

    def test_unregistered_scheme_returns_unknown_status(self):
        """
        CRITICAL: For schemes without registered deterministic rules,
        missing_fields_status must be 'UNKNOWN', never fabricating requirements.
        """
        ctx = ApplicantContext(applicant_id="app_1")
        scheme = self._create_scheme_result("unregistered-state-scheme-xyz", "Unregistered Scheme")

        missing, status = self.analyzer.analyze(scheme, ctx)

        self.assertEqual(status, "UNKNOWN")
        self.assertEqual(len(missing), 0)


if __name__ == "__main__":
    unittest.main()
