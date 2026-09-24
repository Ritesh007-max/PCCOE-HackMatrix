"""
Unit tests for Application Re-evaluation and Policy Versioning.
Phase 10: Ensures historical decision snapshots are never mutated when re-evaluating.
"""

import unittest
from unittest.mock import MagicMock
from src.application.service import ApplicationWorkflowService
from src.application.status import ApplicationStatus, StatutoryDecision, ReadinessStatus
from src.application.case import ApplicationCase, FactSnapshot, SchemeEvaluation
from src.application.decision import DecisionSnapshot
from src.application.repository import InMemoryApplicationRepository
from src.rules.models import RuleStatus


class TestReEvaluationWorkflow(unittest.TestCase):
    """Tests for multi-version decision snapshot preservation."""

    def test_re_evaluation_creates_v2_without_mutating_v1(self):
        """
        Scenario:
        1. Application evaluated under policy version V1 -> creates DecisionSnapshot V1.
        2. Policy is updated to V2 or new evidence arrives.
        3. Application is re-evaluated.
        4. DecisionSnapshot V2 is created.
        5. DecisionSnapshot V1 remains 100% historically preserved.
        """
        repo = InMemoryApplicationRepository()
        service = ApplicationWorkflowService(repository=repo)

        # Create application case
        case = service.create_application(citizen_reference="citizen_reeval")
        app_id = case.application_id

        # Update initial facts: income is 150000
        service.update_applicant_profile(
            application_id=app_id,
            facts={"age": 21, "annual_family_income": 150000, "state": "Gujarat"},
        )

        # Mock eligibility engine for controlled deterministic decisions
        mock_decision_v1 = MagicMock()
        mock_decision_v1.status = RuleStatus.PASS
        mock_decision_v1.eligible = True
        mock_decision_v1.rule_results = []
        mock_decision_v1.missing_fields = []

        service.eligibility_engine.evaluate = MagicMock(return_value=mock_decision_v1)  # type: ignore

        # Initial evaluation
        service.evaluate_scheme(
            application_id=app_id,
            scheme_id="scheme_scholarship_gujarat",
            scheme_name="Gujarat Scholarship",
        )

        # Check V1 snapshot
        snapshots_initial = repo.list_decision_snapshots(app_id)
        self.assertEqual(len(snapshots_initial), 1)
        snap_v1 = snapshots_initial[0]
        self.assertEqual(snap_v1.version_index, 1)
        self.assertEqual(snap_v1.decision_status, StatutoryDecision.PASS)
        snap_v1_id = snap_v1.snapshot_id
        snap_v1_policy = snap_v1.policy_snapshot_version

        # Now simulate applicant updating income or policy version changing
        # New income = 450000 (which exceeds threshold -> FAIL)
        service.update_applicant_profile(
            application_id=app_id,
            facts={"annual_family_income": 450000},
        )

        mock_decision_v2 = MagicMock()
        mock_decision_v2.status = RuleStatus.FAIL
        mock_decision_v2.eligible = False
        mock_decision_v2.rule_results = []
        mock_decision_v2.missing_fields = []
        service.eligibility_engine.evaluate = MagicMock(return_value=mock_decision_v2)  # type: ignore

        # Execute re-evaluation with updated policy version "snapshot_20261001_120000"
        updated_case = service.reevaluate_application(
            application_id=app_id,
            reason="APPLICANT_INCOME_UPDATE",
            force_policy_version="snapshot_20261001_120000",
        )

        # Check snapshots list
        snapshots_after = repo.list_decision_snapshots(app_id)
        self.assertEqual(len(snapshots_after), 2)

        # V1 is completely intact
        retrieved_v1 = repo.get_decision_snapshot(snap_v1_id)
        self.assertIsNotNone(retrieved_v1)
        assert retrieved_v1 is not None
        self.assertEqual(retrieved_v1.snapshot_id, snap_v1_id)
        self.assertEqual(retrieved_v1.version_index, 1)
        self.assertEqual(retrieved_v1.decision_status, StatutoryDecision.PASS)
        self.assertEqual(retrieved_v1.policy_snapshot_version, snap_v1_policy)
        self.assertEqual(retrieved_v1.applicant_fact_snapshot.get("annual_family_income"), 150000)

        # V2 is created with new outcome
        snap_v2 = snapshots_after[1]
        self.assertEqual(snap_v2.version_index, 2)
        self.assertEqual(snap_v2.decision_status, StatutoryDecision.FAIL)
        self.assertEqual(snap_v2.policy_snapshot_version, "snapshot_20261001_120000")
        self.assertEqual(snap_v2.applicant_fact_snapshot.get("annual_family_income"), 450000)
        self.assertEqual(snap_v2.reason_for_evaluation, "APPLICANT_INCOME_UPDATE")

        # Active snapshot points to V2
        self.assertEqual(updated_case.active_decision_snapshot_id, snap_v2.snapshot_id)


if __name__ == "__main__":
    unittest.main()
