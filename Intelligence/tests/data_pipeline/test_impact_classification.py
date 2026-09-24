"""
Unit tests for Phase 12 Change Impact Classification and Rule Impact Detection.
Verifies the 15 semantic impact categories and statutory rule recompile detection.
"""

from pathlib import Path
import sys
import unittest

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.data_pipeline.models import (
    ChangeImpactType,
    ChangeType,
    FieldDiff,
    RecordDiff,
)
from src.data_pipeline.impact import PolicyChangeClassifier, RuleImpactAnalyzer


class TestImpactClassification(unittest.TestCase):
    """Test suite for semantic diff classification and rule impact triggers."""

    def test_no_change_classification(self):
        """Unchanged diff produces NO_CHANGE."""
        diff = RecordDiff(scheme_slug="scheme_a", change_type=ChangeType.UNCHANGED)
        impacts = PolicyChangeClassifier.classify_diff(diff)
        self.assertIn(ChangeImpactType.NO_CHANGE, impacts)
        self.assertFalse(RuleImpactAnalyzer.requires_rule_recompile(diff))

    def test_scheme_added_and_removed(self):
        """Added and removed schemes trigger RULE_AFFECTING_CHANGE."""
        diff_add = RecordDiff(scheme_slug="scheme_new", change_type=ChangeType.ADDED)
        impacts_add = PolicyChangeClassifier.classify_diff(diff_add)
        self.assertIn(ChangeImpactType.SCHEME_ADDED, impacts_add)
        self.assertIn(ChangeImpactType.RULE_AFFECTING_CHANGE, impacts_add)
        self.assertTrue(RuleImpactAnalyzer.requires_rule_recompile(diff_add))

        diff_rem = RecordDiff(scheme_slug="scheme_old", change_type=ChangeType.REMOVED)
        impacts_rem = PolicyChangeClassifier.classify_diff(diff_rem)
        self.assertIn(ChangeImpactType.SCHEME_REMOVED, impacts_rem)
        self.assertIn(ChangeImpactType.RULE_AFFECTING_CHANGE, impacts_rem)
        self.assertTrue(RuleImpactAnalyzer.requires_rule_recompile(diff_rem))

    def test_eligibility_and_rule_affecting_fields(self):
        """Statutory field changes (income, age, caste, state) trigger ELIGIBILITY_CHANGED and RULE_AFFECTING_CHANGE."""
        diff = RecordDiff(
            scheme_slug="sc_scholarship",
            change_type=ChangeType.MODIFIED,
            field_diffs=[
                FieldDiff(field_name="annual_family_income", old_value=250000, new_value=300000, is_threshold_changed=True),
            ],
        )
        impacts = PolicyChangeClassifier.classify_diff(diff)
        self.assertIn(ChangeImpactType.SCHEME_UPDATED, impacts)
        self.assertIn(ChangeImpactType.ELIGIBILITY_CHANGED, impacts)
        self.assertIn(ChangeImpactType.RULE_AFFECTING_CHANGE, impacts)
        self.assertTrue(RuleImpactAnalyzer.requires_rule_recompile(diff))

    def test_benefit_only_change(self):
        """Benefit description changes do NOT trigger rule recompilation."""
        diff = RecordDiff(
            scheme_slug="subsidy_scheme",
            change_type=ChangeType.MODIFIED,
            field_diffs=[
                FieldDiff(field_name="benefit_details", old_value="Rs 5,000", new_value="Rs 6,000"),
            ],
        )
        impacts = PolicyChangeClassifier.classify_diff(diff)
        self.assertIn(ChangeImpactType.BENEFIT_CHANGED, impacts)
        self.assertNotIn(ChangeImpactType.RULE_AFFECTING_CHANGE, impacts)
        self.assertFalse(RuleImpactAnalyzer.requires_rule_recompile(diff))

    def test_document_requirement_change(self):
        """Document changes trigger DOCUMENT_REQUIREMENT_CHANGED."""
        diff = RecordDiff(
            scheme_slug="doc_scheme",
            change_type=ChangeType.MODIFIED,
            field_diffs=[
                FieldDiff(field_name="documents_required", old_value="Income cert", new_value="Income cert, Aadhaar"),
            ],
        )
        impacts = PolicyChangeClassifier.classify_diff(diff)
        self.assertIn(ChangeImpactType.DOCUMENT_REQUIREMENT_CHANGED, impacts)
        self.assertFalse(RuleImpactAnalyzer.requires_rule_recompile(diff))

    def test_application_step_and_url_change(self):
        """Application process and portal URL changes trigger respective impact flags."""
        diff = RecordDiff(
            scheme_slug="portal_scheme",
            change_type=ChangeType.MODIFIED,
            field_diffs=[
                FieldDiff(field_name="application_process", old_value="Apply at CSC", new_value="Apply online at portal"),
                FieldDiff(field_name="source_url", old_value="https://old.gov.in", new_value="https://new.gov.in"),
            ],
        )
        impacts = PolicyChangeClassifier.classify_diff(diff)
        self.assertIn(ChangeImpactType.APPLICATION_STEP_CHANGED, impacts)
        self.assertIn(ChangeImpactType.SOURCE_URL_CHANGED, impacts)

    def test_deadline_change(self):
        """Deadline changes trigger DEADLINE_CHANGED."""
        diff = RecordDiff(
            scheme_slug="deadline_scheme",
            change_type=ChangeType.MODIFIED,
            field_diffs=[
                FieldDiff(field_name="close_date", old_value="2025-08-31", new_value="2025-10-31"),
            ],
        )
        impacts = PolicyChangeClassifier.classify_diff(diff)
        self.assertIn(ChangeImpactType.DEADLINE_CHANGED, impacts)

    def test_supplementary_only_classification(self):
        """Changes originating from supplementary feeds receive SUPPLEMENTARY_ONLY_CHANGE tag."""
        diff = RecordDiff(
            scheme_slug="supp_scheme",
            change_type=ChangeType.MODIFIED,
            field_diffs=[
                FieldDiff(field_name="tags", old_value="tag1", new_value="tag2"),
            ],
        )
        impacts = PolicyChangeClassifier.classify_diff(diff, is_supplementary_source=True)
        self.assertIn(ChangeImpactType.SUPPLEMENTARY_ONLY_CHANGE, impacts)


if __name__ == "__main__":
    unittest.main()
