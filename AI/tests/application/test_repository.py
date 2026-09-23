"""
Unit tests for Application Repository.
Phase 10: In-memory persistence, snapshot immutability enforcement, and query contracts.
"""

import unittest
from src.application.case import ApplicationCase, DocumentReference
from src.application.decision import DecisionSnapshot
from src.application.status import StatutoryDecision
from src.application.repository import InMemoryApplicationRepository
from src.application.exceptions import ImmutableSnapshotError, ApplicationNotFoundError


class TestApplicationRepository(unittest.TestCase):
    """Tests for ApplicationRepository persistence operations."""

    def test_save_and_retrieve_case(self):
        """Case can be saved and retrieved by ID."""
        repo = InMemoryApplicationRepository()
        case = ApplicationCase(citizen_reference="citizen_123")
        repo.save(case)

        retrieved = repo.get(case.application_id)
        self.assertIsNotNone(retrieved)
        assert retrieved is not None
        self.assertEqual(retrieved.application_id, case.application_id)
        self.assertEqual(retrieved.citizen_reference, "citizen_123")

    def test_update_nonexistent_case_raises(self):
        """Updating a case that does not exist raises ApplicationNotFoundError."""
        repo = InMemoryApplicationRepository()
        case = ApplicationCase(application_id="app_nonexistent")
        with self.assertRaises(ApplicationNotFoundError):
            repo.update(case)

    def test_save_decision_snapshot_and_prohibit_overwrite(self):
        """Decision snapshots can be stored; attempting to overwrite must raise ImmutableSnapshotError."""
        repo = InMemoryApplicationRepository()
        snap = DecisionSnapshot(
            snapshot_id="snap_unique_1",
            application_id="app_1",
            scheme_id="scheme_1",
            decision_status=StatutoryDecision.PASS,
        )
        repo.save_decision_snapshot(snap)

        retrieved = repo.get_decision_snapshot("snap_unique_1")
        self.assertIsNotNone(retrieved)
        assert retrieved is not None
        self.assertEqual(retrieved.decision_status, StatutoryDecision.PASS)

        # Attempt to save a new snapshot with the same snapshot_id
        snap_dup = DecisionSnapshot(
            snapshot_id="snap_unique_1",
            application_id="app_1",
            scheme_id="scheme_1",
            decision_status=StatutoryDecision.FAIL,
        )
        with self.assertRaises(ImmutableSnapshotError):
            repo.save_decision_snapshot(snap_dup)

    def test_list_decision_snapshots_for_application(self):
        """Retrieves all decision snapshots belonging to a given application in creation order."""
        repo = InMemoryApplicationRepository()
        app_id = "app_multi_snap"

        snap1 = DecisionSnapshot(
            snapshot_id="snap_v1",
            application_id=app_id,
            scheme_id="scheme_test",
            version_index=1,
            decision_status=StatutoryDecision.UNKNOWN,
        )
        snap2 = DecisionSnapshot(
            snapshot_id="snap_v2",
            application_id=app_id,
            scheme_id="scheme_test",
            version_index=2,
            decision_status=StatutoryDecision.PASS,
        )
        # Snapshot for another application
        snap_other = DecisionSnapshot(
            snapshot_id="snap_other",
            application_id="app_other",
            scheme_id="scheme_test",
            version_index=1,
        )

        repo.save_decision_snapshot(snap1)
        repo.save_decision_snapshot(snap2)
        repo.save_decision_snapshot(snap_other)

        snapshots = repo.list_decision_snapshots(app_id)
        self.assertEqual(len(snapshots), 2)
        self.assertEqual(snapshots[0].snapshot_id, "snap_v1")
        self.assertEqual(snapshots[1].snapshot_id, "snap_v2")


if __name__ == "__main__":
    unittest.main()
