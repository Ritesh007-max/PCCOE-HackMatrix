"""
Unit tests for Policy and Rule Versioning Engines.
Verifies content-hash revisions, supersedes chaining, and smart rule rebuild suppression.
"""

from pathlib import Path
import sys
import unittest

_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from src.data_pipeline.versioning.policy import PolicyVersionManager
from src.data_pipeline.versioning.rules import RuleVersionManager
from src.data_pipeline.models import RecordDiff, FieldDiff, ChangeType, PolicyStatus


class TestVersioning(unittest.TestCase):

    def test_policy_version_creation_and_chaining(self):
        pvm = PolicyVersionManager()
        rec_v1 = {"slug": "pm-kisan", "name": "PM Kisan", "income_limit": 250000}
        v1 = pvm.create_version("pm-kisan", rec_v1, source_revision="rev_commit_001")

        self.assertTrue(v1.policy_version_id.startswith("policy_"))
        self.assertEqual(v1.source_revision, "rev_commit_001")
        self.assertEqual(v1.status, PolicyStatus.ACTIVE)
        self.assertIsNone(v1.supersedes_version)

        # Update record -> v2
        rec_v2 = {"slug": "pm-kisan", "name": "PM Kisan", "income_limit": 300000}
        v2 = pvm.create_version("pm-kisan", rec_v2, source_revision="rev_commit_002")

        self.assertEqual(v2.status, PolicyStatus.ACTIVE)
        self.assertEqual(v2.supersedes_version, v1.policy_version_id)

        # v1 must now be SUPERSEDED
        history = pvm.get_version_history("pm-kisan")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].status, PolicyStatus.SUPERSEDED)

    def test_rule_rebuild_suppression_on_benefit_only_change(self):
        """
        When only benefits change and eligibility is unchanged,
        should_rebuild_rules must return False to avoid needless rule recompilation.
        """
        rvm = RuleVersionManager()

        # 1. Eligibility changed -> MUST rebuild
        eligibility_diff = RecordDiff(
            scheme_slug="pm-kisan",
            change_type=ChangeType.MODIFIED,
            field_diffs=[
                FieldDiff(field_name="annual_family_income", old_value=250000, new_value=300000, is_threshold_changed=True)
            ]
        )
        self.assertTrue(rvm.should_rebuild_rules(eligibility_diff))

        # 2. Benefit only changed -> MUST NOT rebuild
        benefits_diff = RecordDiff(
            scheme_slug="pm-kisan",
            change_type=ChangeType.MODIFIED,
            field_diffs=[
                FieldDiff(field_name="benefits", old_value="6000", new_value="Enhanced 8000")
            ]
        )
        self.assertFalse(rvm.should_rebuild_rules(benefits_diff))

        # 3. Newly added scheme -> MUST rebuild
        add_diff = RecordDiff(scheme_slug="new-scheme", change_type=ChangeType.ADDED)
        self.assertTrue(rvm.should_rebuild_rules(add_diff))


if __name__ == "__main__":
    unittest.main()
