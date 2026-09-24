"""
Exceptions for Application Decision Workflow.
Phase 10: Case lifecycle and orchestration exceptions.
"""

class WorkflowError(Exception):
    """Base exception for all application workflow errors."""
    pass


class InvalidStateTransitionError(WorkflowError):
    """Raised when an illegal lifecycle state transition is attempted."""
    def __init__(self, current_state: str, target_state: str, reason: str = ""):
        self.current_state = current_state
        self.target_state = target_state
        self.reason = reason
        message = f"Invalid state transition from '{current_state}' to '{target_state}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class ImmutableSnapshotError(WorkflowError):
    """Raised when an attempt is made to mutate an immutable decision snapshot."""
    def __init__(self, snapshot_id: str, field_name: str = ""):
        self.snapshot_id = snapshot_id
        self.field_name = field_name
        message = f"Decision snapshot '{snapshot_id}' is immutable and cannot be modified"
        if field_name:
            message += f" (attempted mutation on '{field_name}')"
        super().__init__(message)


class ApplicationNotFoundError(WorkflowError):
    """Raised when an application case cannot be found."""
    def __init__(self, application_id: str):
        self.application_id = application_id
        super().__init__(f"Application case '{application_id}' not found")


class DocumentNotFoundError(WorkflowError):
    """Raised when a document reference cannot be found in the application."""
    def __init__(self, document_id: str, application_id: str):
        self.document_id = document_id
        self.application_id = application_id
        super().__init__(f"Document '{document_id}' not found in application '{application_id}'")
