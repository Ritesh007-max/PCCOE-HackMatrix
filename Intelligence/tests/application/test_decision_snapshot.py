"""
Unit tests for Decision Snapshots and Immutability.
Phase 10: Ensures decision snapshots cannot be mutated in place and preserve policy version.
"""

import unittest
from src.application.status import StatutoryDecision
from src.application.decision import DecisionSnapshot, generate_snapshot_id
from src.application.exceptions import ImmutableSnapshotError


class TestDecisionSnapshot(unittest.TestCase):
    """Tests for DecisionSnapshot immutability and version preservation."""

    def test_snapshot_creation_and_attributes(self):
        """Snapshot correctly captures full decision context."""
        snapshot = DecisionSnapshot(
            application_id="app_123",
            scheme_id="scheme_gujarat_scholarship",
            scheme_name="Gujarat Scholarship",
            applicant_fact_snapshot={"age": 20, "state": "Gujarat", "annual_family_income": 120000},
            policy_snapshot_version="snapshot_20260921_193823",
            rule_version="1.0.0",
            decision_status=StatutoryDecision.PASS,
            is_eligible=True,
            matched_rules=[{"rule_id": "r1", "field": "annual_family_income", "operator": "<="}],
            failed_rules=[],
            unknown_rules=[],
            benefit_result={"amount": 25000, "benefit_type": "Direct Benefit Transfer"},
            version_index=1,
            reason_for_evaluation="INITIAL_EVALUATION",
        )

        self.assertEqual(snapshot.application_id, "app_123")
        self.assertEqual(snapshot.decision_status, StatutoryDecision.PASS)
        self.assertEqual(snapshot.policy_snapshot_version, "snapshot_20260921_193823")
        self.assertEqual(snapshot.version_index, 1)

    def test_snapshot_immutability_attribute_modification(self):
        """Modifying any attribute of an initialized DecisionSnapshot must raise ImmutableSnapshotError."""
        snapshot = DecisionSnapshot(
            application_id="app_123",
            scheme_id="scheme_test",
            decision_status=StatutoryDecision.PASS,
            is_eligible=True,
        )

        # Attempt to change decision_status
        with self.assertRaises(ImmutableSnapshotError):
            snapshot.decision_status = StatutoryDecision.FAIL

        # Attempt to change is_eligible
        with self.assertRaises(ImmutableSnapshotError):
            snapshot.is_eligible = False

        # Attempt to change policy version
        with self.assertRaises(ImmutableSnapshotError):
            snapshot.policy_snapshot_version = "snapshot_v2"

        # Attempt to inject new attribute
        with self.assertRaises(ImmutableSnapshotError):
            snapshot.new_field = "hacked"

    def test_snapshot_immutability_attribute_deletion(self):
        """Deleting attributes from an initialized DecisionSnapshot must raise ImmutableSnapshotError."""
        snapshot = DecisionSnapshot(
            application_id="app_123",
            scheme_id="scheme_test",
            decision_status=StatutoryDecision.PASS,
        )

        with self.assertRaises(ImmutableSnapshotError):
            del snapshot.decision_status

    def test_snapshot_serialization_roundtrip(self):
        """DecisionSnapshot converts to and from dict cleanly while preserving immutability."""
        snapshot = DecisionSnapshot(
            application_id="app_456",
            scheme_id="scheme_test_2",
            policy_snapshot_version="snapshot_20260921_193823",
            rule_version="2.1.0",
            decision_status=StatutoryDecision.UNKNOWN,
            is_eligible=False,
            unknown_rules=[{"rule_id": "r_age", "field": "age"}],
            version_index=2,
            reason_for_evaluation="REEVALUATION_NEW_DOCUMENT",
        )

        data = snapshot.to_dict()
        self.assertEqual(data["decision_status"], "UNKNOWN")
        self.assertEqual(data["version_index"], 2)

        reconstructed = DecisionSnapshot.from_dict(data)
        self.assertEqual(reconstructed.snapshot_id, snapshot.snapshot_id)
        self.assertEqual(reconstructed.decision_status, StatutoryDecision.UNKNOWN)
        self.assertEqual(reconstructed.policy_snapshot_version, "snapshot_20260921_193823")

        # Reconstructed object must also be strictly immutable
        with self.assertRaises(ImmutableSnapshotError):
            reconstructed.decision_status = StatutoryDecision.PASS


if __name__ == "__main__":
    unittest.main()
