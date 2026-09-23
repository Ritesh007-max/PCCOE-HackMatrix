"""
Unit tests for Change Detection, Hashing, and Field-Level Diffing.
Verifies that statutory thresholds (income, age) produce explicit diffs and never overwrite silently.
"""

from pathlib import Path
import sys
import unittest

_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from src.data_pipeline.change_detection import ChangeDetector
from src.data_pipeline.models import ChangeType


class TestChangeDetection(unittest.TestCase):

    def setUp(self):
        self.old_corpus = [
            {
                "slug": "pm-kisan",
                "scheme_name": "PM Kisan",
                "annual_family_income": 250000,
                "benefits": "6000 per year",
                "eligibility": "Small farmers",
            },
            {
                "slug": "post-matric-sc",
                "scheme_name": "Post Matric SC",
                "annual_family_income": 250000,
                "benefits": "Tuition fees reimbursement",
                "eligibility": "SC students",
            },
            {
                "slug": "discontinued-scheme",
                "scheme_name": "Old Scheme",
                "benefits": "Old benefit",
            }
        ]

    def test_unchanged_detection(self):
        """Identical records produce UNCHANGED and zero field diffs."""
        summary = ChangeDetector.diff_datasets(
            old_records=self.old_corpus,
            new_records=self.old_corpus,
            key_field="slug"
        )
        self.assertEqual(summary.unchanged_count, 3)
        self.assertEqual(summary.added_count, 0)
        self.assertEqual(summary.modified_count, 0)
        self.assertEqual(summary.removed_count, 0)
        self.assertFalse(summary.has_eligibility_changes)

    def test_threshold_modification_diff(self):
        """
        Critical test: income limit change (250000 -> 300000)
        must produce an explicit POLICY_FIELD_CHANGED field diff.
        """
        new_corpus = [
            {
                "slug": "pm-kisan",
                "scheme_name": "PM Kisan",
                "annual_family_income": 300000,  # Changed threshold
                "benefits": "6000 per year",
                "eligibility": "Small farmers",
            },
            self.old_corpus[1],
            self.old_corpus[2],
        ]
        summary = ChangeDetector.diff_datasets(
            old_records=self.old_corpus,
            new_records=new_corpus,
            key_field="slug"
        )
        self.assertEqual(summary.modified_count, 1)
        self.assertEqual(summary.unchanged_count, 2)
        self.assertTrue(summary.has_eligibility_changes)

        mod_diff = [d for d in summary.diffs if d.scheme_slug == "pm-kisan"][0]
        self.assertEqual(mod_diff.change_type, ChangeType.MODIFIED)
        self.assertTrue(mod_diff.has_eligibility_change)
        self.assertEqual(len(mod_diff.field_diffs), 1)

        fd = mod_diff.field_diffs[0]
        self.assertEqual(fd.field_name, "annual_family_income")
        self.assertEqual(fd.old_value, 250000)
        self.assertEqual(fd.new_value, 300000)
        self.assertTrue(fd.is_threshold_changed)
        self.assertIn("POLICY_FIELD_CHANGED", fd.description or "")

    def test_added_and_removed_schemes(self):
        """Test scheme addition and deprecation."""
        new_corpus = [
            self.old_corpus[0],
            self.old_corpus[1],
            # discontinued-scheme is removed
            {
                "slug": "new-solar-yojana",
                "scheme_name": "PM Surya Ghar",
                "benefits": "Free electricity up to 300 units",
            }
        ]
        summary = ChangeDetector.diff_datasets(
            old_records=self.old_corpus,
            new_records=new_corpus,
            key_field="slug"
        )
        self.assertEqual(summary.added_count, 1)
        self.assertEqual(summary.removed_count, 1)
        self.assertEqual(summary.unchanged_count, 2)

        added = [d for d in summary.diffs if d.change_type == ChangeType.ADDED][0]
        self.assertEqual(added.scheme_slug, "new-solar-yojana")

        removed = [d for d in summary.diffs if d.change_type == ChangeType.REMOVED][0]
        self.assertEqual(removed.scheme_slug, "discontinued-scheme")

    def test_benefits_only_change_flag(self):
        """When only benefits change, has_benefits_only_change is True and has_eligibility_change is False."""
        new_corpus = [
            {
                "slug": "pm-kisan",
                "scheme_name": "PM Kisan",
                "annual_family_income": 250000,
                "benefits": "Enhanced 8000 per year via DBT",  # Only benefit text changed
                "eligibility": "Small farmers",
            },
            self.old_corpus[1],
            self.old_corpus[2],
        ]
        summary = ChangeDetector.diff_datasets(
            old_records=self.old_corpus,
            new_records=new_corpus,
            key_field="slug"
        )
        mod_diff = [d for d in summary.diffs if d.scheme_slug == "pm-kisan"][0]
        self.assertTrue(mod_diff.has_benefits_only_change)
        self.assertFalse(mod_diff.has_eligibility_change)


if __name__ == "__main__":
    unittest.main()
