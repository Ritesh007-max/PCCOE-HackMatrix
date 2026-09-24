"""
Unit tests for Application Lifecycle State Machine.
Phase 10: Validates allowed state transitions and strict rejection of illegal jumps.
"""

import unittest
from src.application.status import ApplicationStatus
from src.application.lifecycle import ApplicationStateMachine, ALLOWED_TRANSITIONS
from src.application.exceptions import InvalidStateTransitionError


class TestApplicationStateMachine(unittest.TestCase):
    """Tests for lifecycle state progression and transition guards."""

    def test_valid_forward_transitions(self):
        """Test the standard canonical forward lifecycle path."""
        # DRAFT -> DOCUMENTS_PENDING
        ApplicationStateMachine.validate_transition(
            ApplicationStatus.DRAFT, ApplicationStatus.DOCUMENTS_PENDING
        )
        # DOCUMENTS_PENDING -> PROCESSING
        ApplicationStateMachine.validate_transition(
            ApplicationStatus.DOCUMENTS_PENDING, ApplicationStatus.PROCESSING
        )
        # PROCESSING -> FACTS_READY
        ApplicationStateMachine.validate_transition(
            ApplicationStatus.PROCESSING, ApplicationStatus.FACTS_READY
        )
        # FACTS_READY -> SCHEMES_IDENTIFIED
        ApplicationStateMachine.validate_transition(
            ApplicationStatus.FACTS_READY, ApplicationStatus.SCHEMES_IDENTIFIED
        )
        # SCHEMES_IDENTIFIED -> ELIGIBILITY_EVALUATED
        ApplicationStateMachine.validate_transition(
            ApplicationStatus.SCHEMES_IDENTIFIED, ApplicationStatus.ELIGIBILITY_EVALUATED
        )
        # ELIGIBILITY_EVALUATED -> READY_TO_APPLY (with guard)
        ApplicationStateMachine.validate_transition(
            ApplicationStatus.ELIGIBILITY_EVALUATED,
            ApplicationStatus.READY_TO_APPLY,
            context={"has_decision": True},
        )
        # READY_TO_APPLY -> COMPLETED
        ApplicationStateMachine.validate_transition(
            ApplicationStatus.READY_TO_APPLY,
            ApplicationStatus.COMPLETED,
            context={"is_ready": True},
        )

    def test_alternative_branches(self):
        """Test failure, review, and action required branch transitions."""
        # PROCESSING -> FAILED
        ApplicationStateMachine.validate_transition(
            ApplicationStatus.PROCESSING, ApplicationStatus.FAILED
        )
        # FAILED -> DRAFT (recovery retry)
        ApplicationStateMachine.validate_transition(
            ApplicationStatus.FAILED, ApplicationStatus.DRAFT
        )
        # FACTS_READY -> UNDER_REVIEW (conflicts)
        ApplicationStateMachine.validate_transition(
            ApplicationStatus.FACTS_READY, ApplicationStatus.UNDER_REVIEW
        )
        # UNDER_REVIEW -> FACTS_READY (resolved)
        ApplicationStateMachine.validate_transition(
            ApplicationStatus.UNDER_REVIEW, ApplicationStatus.FACTS_READY
        )
        # ELIGIBILITY_EVALUATED -> ACTION_REQUIRED
        ApplicationStateMachine.validate_transition(
            ApplicationStatus.ELIGIBILITY_EVALUATED, ApplicationStatus.ACTION_REQUIRED
        )
        # ACTION_REQUIRED -> PROCESSING
        ApplicationStateMachine.validate_transition(
            ApplicationStatus.ACTION_REQUIRED, ApplicationStatus.PROCESSING
        )

    def test_illegal_transitions_rejected(self):
        """Illegal transitions must be explicitly rejected with InvalidStateTransitionError."""
        # DRAFT -> COMPLETED is illegal
        with self.assertRaises(InvalidStateTransitionError):
            ApplicationStateMachine.validate_transition(
                ApplicationStatus.DRAFT, ApplicationStatus.COMPLETED
            )

        # PROCESSING -> READY_TO_APPLY is illegal
        with self.assertRaises(InvalidStateTransitionError):
            ApplicationStateMachine.validate_transition(
                ApplicationStatus.PROCESSING, ApplicationStatus.READY_TO_APPLY
            )

        # FAILED -> COMPLETED is illegal
        with self.assertRaises(InvalidStateTransitionError):
            ApplicationStateMachine.validate_transition(
                ApplicationStatus.FAILED, ApplicationStatus.COMPLETED
            )

        # DRAFT -> ELIGIBILITY_EVALUATED is illegal
        with self.assertRaises(InvalidStateTransitionError):
            ApplicationStateMachine.validate_transition(
                ApplicationStatus.DRAFT, ApplicationStatus.ELIGIBILITY_EVALUATED
            )

    def test_guard_condition_failures(self):
        """Guards should reject transition if prerequisite business context is missing."""
        # READY_TO_APPLY without evaluated decision
        with self.assertRaises(InvalidStateTransitionError):
            ApplicationStateMachine.validate_transition(
                ApplicationStatus.ELIGIBILITY_EVALUATED,
                ApplicationStatus.READY_TO_APPLY,
                context={"has_decision": False},
            )

        # COMPLETED without readiness
        with self.assertRaises(InvalidStateTransitionError):
            ApplicationStateMachine.validate_transition(
                ApplicationStatus.READY_TO_APPLY,
                ApplicationStatus.COMPLETED,
                context={"is_ready": False},
            )

    def test_self_transition(self):
        """Self-transition is a valid no-op."""
        ApplicationStateMachine.validate_transition(
            ApplicationStatus.PROCESSING, ApplicationStatus.PROCESSING
        )


if __name__ == "__main__":
    unittest.main()
