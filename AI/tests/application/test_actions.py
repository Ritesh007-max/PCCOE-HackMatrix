"""
Unit tests for Deterministic Next Action Engine.
Phase 10: Validates rule-based action generation without LLM hallucination.
"""

import unittest
from src.application.status import (
    ActionType,
    ActionPriority,
    ReadinessStatus,
    StatutoryDecision,
)
from src.application.case import ApplicationCase, FactSnapshot, SchemeEvaluation
from src.application.readiness import DocumentCompletenessReport
from src.application.actions import NextActionEngine, NextAction


class TestNextActions(unittest.TestCase):
    """Tests for deterministic Next Action generation."""

    def test_missing_document_action(self):
        """Missing required document produces UPLOAD_DOCUMENT action with HIGH priority."""
        case = ApplicationCase()
        doc_report = DocumentCompletenessReport(
            missing_documents=["caste_certificate"],
            is_complete=False,
        )
        actions = NextActionEngine.generate_actions(case=case, doc_report=doc_report)
        upload_actions = [a for a in actions if a.action_type == ActionType.UPLOAD_DOCUMENT]
        self.assertEqual(len(upload_actions), 1)
        self.assertEqual(upload_actions[0].priority, ActionPriority.HIGH)
        self.assertEqual(upload_actions[0].required_document_type, "caste_certificate")

    def test_missing_profile_field_action(self):
        """Missing profile fact produces PROVIDE_INFORMATION action."""
        case = ApplicationCase()
        evaluation = SchemeEvaluation(
            scheme_id="scheme_test",
            scheme_name="Test Scheme",
            missing_fields=["annual_family_income"],
        )
        actions = NextActionEngine.generate_actions(case=case, target_evaluation=evaluation)
        info_actions = [a for a in actions if a.action_type == ActionType.PROVIDE_INFORMATION]
        self.assertEqual(len(info_actions), 1)
        self.assertEqual(info_actions[0].required_field, "annual_family_income")

    def test_conflict_resolution_action(self):
        """Contradictory facts produce RESOLVE_CONFLICT action with HIGH priority."""
        case = ApplicationCase(
            facts=FactSnapshot(conflicted_fields=["state"]),
        )
        actions = NextActionEngine.generate_actions(case=case)
        conflict_actions = [a for a in actions if a.action_type == ActionType.RESOLVE_CONFLICT]
        self.assertEqual(len(conflict_actions), 1)
        self.assertEqual(conflict_actions[0].priority, ActionPriority.HIGH)
        self.assertEqual(conflict_actions[0].required_field, "state")

    def test_review_eligibility_action(self):
        """Statutory REVIEW decision produces REVIEW_ELIGIBILITY action."""
        case = ApplicationCase()
        evaluation = SchemeEvaluation(
            scheme_id="scheme_test",
            decision_status=StatutoryDecision.REVIEW,
        )
        actions = NextActionEngine.generate_actions(case=case, target_evaluation=evaluation)
        rev_actions = [a for a in actions if a.action_type == ActionType.REVIEW_ELIGIBILITY]
        self.assertEqual(len(rev_actions), 1)

    def test_ready_to_apply_portal_actions(self):
        """READY_TO_APPLY status generates VISIT_OFFICIAL_PORTAL and submission steps."""
        case = ApplicationCase(
            readiness=ReadinessStatus.READY_TO_APPLY,
        )
        evaluation = SchemeEvaluation(
            scheme_id="pm_kisan",
            scheme_name="PM Kisan",
            decision_status=StatutoryDecision.PASS,
            is_eligible=True,
            benefit_summary={"amount": 6000, "benefit_type": "Direct Benefit Transfer"},
        )
        actions = NextActionEngine.generate_actions(
            case=case,
            target_evaluation=evaluation,
            official_portal_url="https://pmkisan.gov.in",
        )
        portal_actions = [a for a in actions if a.action_type == ActionType.VISIT_OFFICIAL_PORTAL]
        ready_actions = [a for a in actions if a.action_type == ActionType.READY_TO_APPLY]
        benefit_actions = [a for a in actions if a.action_type == ActionType.VIEW_BENEFIT]

        self.assertEqual(len(portal_actions), 1)
        self.assertEqual(portal_actions[0].action_metadata.get("portal_url"), "https://pmkisan.gov.in")
        self.assertEqual(len(ready_actions), 1)
        self.assertEqual(len(benefit_actions), 1)

    def test_action_serialization_roundtrip(self):
        """NextAction cleanly converts to and from dictionary."""
        action = NextAction(
            action_id="act_test_1",
            action_type=ActionType.PROVIDE_INFORMATION,
            priority=ActionPriority.HIGH,
            title="Provide Income",
            reason="Income is required",
            required_field="annual_family_income",
        )
        data = action.to_dict()
        self.assertEqual(data["action_type"], "PROVIDE_INFORMATION")
        recon = NextAction.from_dict(data)
        self.assertEqual(recon.action_id, action.action_id)
        self.assertEqual(recon.action_type, ActionType.PROVIDE_INFORMATION)


if __name__ == "__main__":
    unittest.main()
