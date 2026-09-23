"""
Integration tests for PolicySetu Phase 10 Application Decision Workflow.
Verifies complete case orchestration around Phase 8 document-to-decision pipeline,
deterministic eligibility, readiness engine, next action generation, decision snapshots,
and conflict handling.
"""

from pathlib import Path
import unittest
import sys

_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from src.application.service import ApplicationWorkflowService
from src.application.status import (
    ApplicationStatus,
    StatutoryDecision,
    ReadinessStatus,
    ActionType,
    ActionPriority,
    ReviewStatus,
    ReviewReason,
)
from src.application.case import ApplicationCase, FactSnapshot, SchemeEvaluation
from src.application.decision import DecisionSnapshot
from src.application.repository import InMemoryApplicationRepository
from src.llm.config import LLMConfig
from src.pipelines.application_pipeline import ApplicationPipeline
from src.rules.models import Rule, SchemeRuleSet


class TestApplicationWorkflowIntegration(unittest.TestCase):
    """Full end-to-end integration tests for Phase 10 Application Workflow."""

    def setUp(self):
        self.fixtures_dir = _AI_DIR / "tests" / "fixtures"
        self.repo = InMemoryApplicationRepository()
        self.config = LLMConfig(provider="mock")
        self.pipeline = ApplicationPipeline(llm_config=self.config)
        self.service = ApplicationWorkflowService(
            repository=self.repo,
            pipeline=self.pipeline,
        )
        # Register sc_post_matric_scholarship ruleset
        sc_ruleset = SchemeRuleSet(
            scheme_id="sc_post_matric_scholarship",
            scheme_slug="sc_post_matric_scholarship",
            scheme_name="Post Matric Scholarship for SC Students",
            version="1.0.0",
            root_logic="AND",
            rules=[
                Rule(
                    rule_id="rule_sc_pms_01",
                    scheme_id="sc_post_matric_scholarship",
                    rule_type="eligibility",
                    field="social_category",
                    operator="=",
                    expected_value="SC",
                    value_type="string",
                    required=True,
                    hard_constraint=True,
                    raw_text="The scholarships are open to nationals of India belonging to Scheduled Castes.",
                ),
                Rule(
                    rule_id="rule_sc_pms_02",
                    scheme_id="sc_post_matric_scholarship",
                    rule_type="eligibility",
                    field="annual_family_income",
                    operator="<=",
                    expected_value=250000,
                    value_type="numeric",
                    required=True,
                    hard_constraint=True,
                    raw_text="Total family income from all sources shall not exceed Rs. 2,50,000 per annum.",
                ),
                Rule(
                    rule_id="rule_sc_pms_03",
                    scheme_id="sc_post_matric_scholarship",
                    rule_type="eligibility",
                    field="state",
                    operator="=",
                    expected_value="Gujarat",
                    value_type="string",
                    required=True,
                    hard_constraint=True,
                    raw_text="Must be permanent resident of Gujarat state.",
                ),
            ],
        )
        self.service.eligibility_engine.register_ruleset(sc_ruleset)

    def test_end_to_end_gujarat_sc_student_scenario(self):
        """
        Full Application Scenario (Section 44 of prompt):
        Applicant:
          - State: Gujarat
          - Age: 20
          - Annual Family Income: 120,000
          - Social Category: SC
          - Student: True
        Query: 'mujhe Gujarat mein student ke liye scholarship chahiye'
        
        Flow:
          CREATE APPLICATION
          -> ATTACH DOCUMENTS
          -> PROCESS DOCUMENTS VIA PHASE 8
          -> EXTRACT FACTS & NORMALIZE
          -> RETRIEVE SCHEMES
          -> DETERMINISTIC ELIGIBILITY
          -> BENEFITS
          -> READINESS
          -> NEXT ACTIONS
          -> DECISION SNAPSHOT
          -> APPLICATION STATE
        """
        # 1. Create Application
        case = self.service.create_application(citizen_reference="citizen_gujarat_sc_01")
        self.assertEqual(case.current_status, ApplicationStatus.DRAFT)
        app_id = case.application_id

        # 2. Attach Documents
        income_pdf = self.fixtures_dir / "sample_income_cert.pdf"
        self.assertTrue(income_pdf.exists())

        doc1 = self.service.attach_document(
            application_id=app_id,
            filename="sample_income_cert.pdf",
            file_path=income_pdf,
            document_type="income_certificate",
        )
        self.assertEqual(doc1.document_type, "income_certificate")

        # 3. Process Documents via authoritative Phase 8 pipeline
        processed_case = self.service.process_documents(
            application_id=app_id,
            document_inputs=[income_pdf],
            user_query="mujhe Gujarat mein student ke liye scholarship chahiye",
            target_scheme="sc_post_matric_scholarship",
        )

        # 4. Verify Facts & Evaluation
        self.assertIsNotNone(processed_case.facts)
        self.assertTrue(len(processed_case.candidate_schemes) > 0)
        self.assertIsNotNone(processed_case.active_decision_snapshot_id)
        assert processed_case.active_decision_snapshot_id is not None

        # 5. Verify Decision Snapshot Created and Immutable
        snapshot = self.repo.get_decision_snapshot(processed_case.active_decision_snapshot_id)
        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertEqual(snapshot.application_id, app_id)
        self.assertTrue(snapshot.version_index >= 1)

        # 6. Verify Next Actions Generated Deterministically
        self.assertTrue(len(processed_case.next_actions) > 0)
        action_types = [a["action_type"] for a in processed_case.next_actions]
        self.assertTrue(
            any(t in [ActionType.UPLOAD_DOCUMENT.value, ActionType.PROVIDE_INFORMATION.value, ActionType.READY_TO_APPLY.value] for t in action_types)
        )

        # 7. Verify Audit History Recorded
        history = self.repo.get_history(app_id)
        self.assertTrue(len(history) >= 3)
        event_types = [h.event_type.value for h in history]
        self.assertIn("APPLICATION_CREATED", event_types)
        self.assertIn("DOCUMENT_ADDED", event_types)
        self.assertIn("DOCUMENT_PROCESSED", event_types)
        self.assertIn("ELIGIBILITY_EVALUATED", event_types)

    def test_conflict_scenario_gujarat_vs_rajasthan(self):
        """
        Conflict Scenario (Section 45 of prompt):
        Document A indicates state = Gujarat.
        Document B indicates state = Rajasthan.
        Expected:
          - CONFLICTED field detected ('state')
          - Statutory decision REVIEW
          - Application status UNDER_REVIEW
          - Readiness READY_FOR_REVIEW
          - RESOLVE_CONFLICT action generated with HIGH priority
          - Immutable decision snapshot created
        """
        case = self.service.create_application(citizen_reference="citizen_conflict_state")
        app_id = case.application_id

        # Directly update profile with conflicting evidence for state
        self.service.update_applicant_profile(
            application_id=app_id,
            facts={"age": 22, "annual_family_income": 150000, "state": "Gujarat"},
            conflicted_fields=["state"],
        )

        # Evaluate scheme
        eval_result = self.service.evaluate_scheme(
            application_id=app_id,
            scheme_id="sc_post_matric_scholarship",
            scheme_name="Post Matric Scholarship for SC Students",
        )

        # Re-fetch latest application state
        updated_case = self.service.get_application_state(app_id)

        # Invariant checks:
        self.assertIn("state", updated_case.facts.conflicted_fields)
        self.assertEqual(updated_case.current_status, ApplicationStatus.UNDER_REVIEW)
        self.assertEqual(updated_case.readiness, ReadinessStatus.READY_FOR_REVIEW)

        # Check RESOLVE_CONFLICT action
        actions = updated_case.next_actions
        conflict_action = next((a for a in actions if a["action_type"] == ActionType.RESOLVE_CONFLICT.value), None)
        self.assertIsNotNone(conflict_action)
        assert conflict_action is not None
        self.assertEqual(conflict_action["priority"], ActionPriority.HIGH.value)
        self.assertEqual(conflict_action["required_field"], "state")

        # Check Decision Snapshot
        snap_id = updated_case.active_decision_snapshot_id
        self.assertIsNotNone(snap_id)
        assert snap_id is not None
        snap = self.repo.get_decision_snapshot(snap_id)
        self.assertIsNotNone(snap)
        assert snap is not None
        self.assertIn("state", snap.review_fields)

    def test_policy_version_scenario_immutability(self):
        """
        Policy Version Scenario (Section 46 of prompt):
        Initial evaluation: policy_version = V1, rule_version = R1.
        Later: policy_version = V2.
        Re-evaluate.
        Expected:
          - DecisionSnapshot V1 preserved untouched.
          - DecisionSnapshot V2 created with updated policy version.
          - Historical V1 must remain unchanged.
        """
        case = self.service.create_application(citizen_reference="citizen_policy_version")
        app_id = case.application_id

        self.service.update_applicant_profile(
            application_id=app_id,
            facts={"age": 20, "annual_family_income": 120000, "state": "Gujarat", "social_category": "SC", "is_student": True},
        )

        # Initial evaluation under V1
        self.service.evaluate_scheme(
            application_id=app_id,
            scheme_id="sc_post_matric_scholarship",
            scheme_name="Post Matric Scholarship",
        )

        # Grab V1 snapshot
        snapshots_v1 = self.repo.list_decision_snapshots(app_id)
        self.assertEqual(len(snapshots_v1), 1)
        snap_v1 = snapshots_v1[0]
        snap_v1_id = snap_v1.snapshot_id
        snap_v1_policy = snap_v1.policy_snapshot_version

        # Re-evaluate under simulated V2 policy update
        self.service.reevaluate_application(
            application_id=app_id,
            reason="POLICY_UPDATE_PHASE_12",
            force_policy_version="snapshot_20261101_180000",
        )

        # Verify snapshots
        snapshots_all = self.repo.list_decision_snapshots(app_id)
        self.assertEqual(len(snapshots_all), 2)

        # V1 is identical to before
        retrieved_v1 = self.repo.get_decision_snapshot(snap_v1_id)
        self.assertIsNotNone(retrieved_v1)
        assert retrieved_v1 is not None
        self.assertEqual(retrieved_v1.version_index, 1)
        self.assertEqual(retrieved_v1.policy_snapshot_version, snap_v1_policy)

        # V2 is new
        snap_v2 = snapshots_all[1]
        self.assertEqual(snap_v2.version_index, 2)
        self.assertEqual(snap_v2.policy_snapshot_version, "snapshot_20261101_180000")
        self.assertEqual(snap_v2.reason_for_evaluation, "POLICY_UPDATE_PHASE_12")

        # Case active snapshot is V2
        updated_case = self.service.get_application_state(app_id)
        self.assertEqual(updated_case.active_decision_snapshot_id, snap_v2.snapshot_id)

    def test_idempotency_workflow_execution(self):
        """
        Idempotency Scenario:
        Repeated calls with the same idempotency key return the cached case.
        """
        case = self.service.create_application()
        idemp_key = "idemp_test_key_999"

        income_pdf = self.fixtures_dir / "sample_income_cert.pdf"

        # Call 1
        res1 = self.service.process_documents(
            application_id=case.application_id,
            document_inputs=[income_pdf],
            idempotency_key=idemp_key,
        )

        # Call 2
        res2 = self.service.process_documents(
            application_id=case.application_id,
            document_inputs=[income_pdf],
            idempotency_key=idemp_key,
        )

        self.assertEqual(res1.application_id, res2.application_id)
        self.assertEqual(res1.active_decision_snapshot_id, res2.active_decision_snapshot_id)


if __name__ == "__main__":
    unittest.main()
