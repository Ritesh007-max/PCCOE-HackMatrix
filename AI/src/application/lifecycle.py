"""
Application Lifecycle State Machine.
Phase 10: Strict state transition validation and guard checks.
"""

from typing import Dict, Set, Optional, Callable, Any
from .status import ApplicationStatus
from .exceptions import InvalidStateTransitionError


ALLOWED_TRANSITIONS: Dict[ApplicationStatus, Set[ApplicationStatus]] = {
    ApplicationStatus.DRAFT: {
        ApplicationStatus.DOCUMENTS_PENDING,
        ApplicationStatus.PROCESSING,
        ApplicationStatus.CANCELLED,
    },
    ApplicationStatus.DOCUMENTS_PENDING: {
        ApplicationStatus.PROCESSING,
        ApplicationStatus.ACTION_REQUIRED,
        ApplicationStatus.CANCELLED,
    },
    ApplicationStatus.PROCESSING: {
        ApplicationStatus.FACTS_READY,
        ApplicationStatus.UNDER_REVIEW,
        ApplicationStatus.FAILED,
    },
    ApplicationStatus.FACTS_READY: {
        ApplicationStatus.SCHEMES_IDENTIFIED,
        ApplicationStatus.ACTION_REQUIRED,
        ApplicationStatus.UNDER_REVIEW,
        ApplicationStatus.FAILED,
        ApplicationStatus.CANCELLED,
    },
    ApplicationStatus.SCHEMES_IDENTIFIED: {
        ApplicationStatus.ELIGIBILITY_EVALUATED,
        ApplicationStatus.ACTION_REQUIRED,
        ApplicationStatus.UNDER_REVIEW,
        ApplicationStatus.FAILED,
        ApplicationStatus.CANCELLED,
    },
    ApplicationStatus.ELIGIBILITY_EVALUATED: {
        ApplicationStatus.READY_TO_APPLY,
        ApplicationStatus.ACTION_REQUIRED,
        ApplicationStatus.UNDER_REVIEW,
        ApplicationStatus.COMPLETED,
        ApplicationStatus.FAILED,
        ApplicationStatus.CANCELLED,
    },
    ApplicationStatus.ACTION_REQUIRED: {
        ApplicationStatus.DOCUMENTS_PENDING,
        ApplicationStatus.PROCESSING,
        ApplicationStatus.READY_TO_APPLY,
        ApplicationStatus.UNDER_REVIEW,
        ApplicationStatus.CANCELLED,
    },
    ApplicationStatus.READY_TO_APPLY: {
        ApplicationStatus.COMPLETED,
        ApplicationStatus.ACTION_REQUIRED,
        ApplicationStatus.UNDER_REVIEW,
        ApplicationStatus.CANCELLED,
    },
    ApplicationStatus.UNDER_REVIEW: {
        ApplicationStatus.FACTS_READY,
        ApplicationStatus.ELIGIBILITY_EVALUATED,
        ApplicationStatus.READY_TO_APPLY,
        ApplicationStatus.ACTION_REQUIRED,
        ApplicationStatus.FAILED,
        ApplicationStatus.CANCELLED,
    },
    ApplicationStatus.COMPLETED: {
        # Allows re-evaluation upon new evidence/policy
        ApplicationStatus.PROCESSING,
    },
    ApplicationStatus.FAILED: {
        # Retry or recovery
        ApplicationStatus.DRAFT,
        ApplicationStatus.PROCESSING,
        ApplicationStatus.CANCELLED,
    },
    ApplicationStatus.CANCELLED: {
        # Re-opening a cancelled application
        ApplicationStatus.DRAFT,
    },
}


class ApplicationStateMachine:
    """
    Manages and validates lifecycle transitions for an application case.
    Prevents invalid shortcuts and enforces deterministic progression.
    """

    @classmethod
    def can_transition(cls, current_state: ApplicationStatus, target_state: ApplicationStatus) -> bool:
        """Check if a transition from current_state to target_state is structurally valid."""
        allowed = ALLOWED_TRANSITIONS.get(current_state, set())
        return target_state in allowed

    @classmethod
    def validate_transition(
        cls,
        current_state: ApplicationStatus,
        target_state: ApplicationStatus,
        reason: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Validate transition. Raises InvalidStateTransitionError if illegal.
        Also executes conditional guard logic if provided.
        """
        if current_state == target_state:
            # Self-transitions are no-ops or valid
            return

        if not cls.can_transition(current_state, target_state):
            raise InvalidStateTransitionError(
                current_state=current_state.value,
                target_state=target_state.value,
                reason=reason or f"Transition not permitted by lifecycle rules",
            )

        # Contextual guards
        if target_state == ApplicationStatus.READY_TO_APPLY and context:
            # Guard: Must have an evaluated decision
            has_decision = context.get("has_decision", False)
            if not has_decision:
                raise InvalidStateTransitionError(
                    current_state=current_state.value,
                    target_state=target_state.value,
                    reason="Cannot transition to READY_TO_APPLY without an evaluated eligibility decision",
                )

        if target_state == ApplicationStatus.COMPLETED and context:
            # Guard: Must be ready to apply or manually approved
            is_ready = context.get("is_ready", True)
            if not is_ready:
                raise InvalidStateTransitionError(
                    current_state=current_state.value,
                    target_state=target_state.value,
                    reason="Cannot complete an application that has unresolved required actions",
                )
