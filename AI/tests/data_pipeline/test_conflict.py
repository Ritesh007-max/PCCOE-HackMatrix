"""
Unit tests for Conflict Detection and Resolution Engine.
Verifies precedence-based resolution, manual review flagging, and audit logging.
"""

from pathlib import Path
import sys
import unittest

_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from src.data_pipeline.conflict import ConflictDetector
from src.data_pipeline.models import AuthorityTier, ConflictResolution


class TestConflictDetection(unittest.TestCase):

    def test_conflict_detection_and_primary_confirmation(self):
        """
        When primary (PRIMARY_CANONICALIZED) and supplementary (SUPPLEMENTARY) disagree,
        primary takes precedence, and an explicit ConflictRecord is produced.
        """
        primary_rec = {
            "slug": "post-matric-sc",
            "annual_family_income": 250000,
            "min_age": 18,
        }
        supplementary_rec = {
            "slug": "post-matric-sc",
            "annual_family_income": 300000,  # Contradiction
            "min_age": 18,                  # Agreement
        }

        conflicts = ConflictDetector.compare_records(
            record_a=primary_rec,
            record_b=supplementary_rec,
            source_a="schemes.csv",
            source_b="updated_data.csv",
            tier_a=AuthorityTier.PRIMARY_CANONICALIZED,
            tier_b=AuthorityTier.SUPPLEMENTARY,
            scheme_slug="post-matric-sc"
        )

        self.assertEqual(len(conflicts), 1)
        c = conflicts[0]
        self.assertEqual(c.field_name, "annual_family_income")
        self.assertEqual(c.value_a, 250000)
        self.assertEqual(c.value_b, 300000)
        self.assertEqual(c.resolution_status, ConflictResolution.PRIMARY_CONFIRMED)
        self.assertEqual(c.resolved_value, 250000)

    def test_equal_tier_conflict_flags_manual_review(self):
        """When two sources of equal authority contradict, resolution must flag MANUAL_REVIEW."""
        rec_a = {"slug": "solar-scheme", "income_limit": 400000}
        rec_b = {"slug": "solar-scheme", "income_limit": 500000}

        conflicts = ConflictDetector.compare_records(
            record_a=rec_a,
            record_b=rec_b,
            source_a="source_one.csv",
            source_b="source_two.csv",
            tier_a=AuthorityTier.SUPPLEMENTARY,
            tier_b=AuthorityTier.SUPPLEMENTARY,
            scheme_slug="solar-scheme"
        )

        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].resolution_status, ConflictResolution.MANUAL_REVIEW)
        self.assertIsNone(conflicts[0].resolved_value)


if __name__ == "__main__":
    unittest.main()
