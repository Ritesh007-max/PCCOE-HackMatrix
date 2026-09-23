"""
PolicySetu Application Decision Workflow Package.
Phase 10: Case lifecycle orchestration around Phase 8 AI decision engine.
"""

from .exceptions import (
    WorkflowError,
    InvalidStateTransitionError,
    ImmutableSnapshotError,
    ApplicationNotFoundError,
    DocumentNotFoundError,
)

from .status import (
    ApplicationStatus,
    StatutoryDecision,
    ReadinessStatus,
    DocumentRequirementStatus,
    FactCompletenessStatus,
    ActionType,
    ActionPriority,
    ReviewStatus,
    ReviewReason,
    EventType,
)

from .case import (
    ApplicationCase,
    DocumentReference,
    FactSnapshot,
    SchemeEvaluation,
    generate_application_id,
)

from .decision import (
    DecisionSnapshot,
    generate_snapshot_id,
)

from .lifecycle import (
    ApplicationStateMachine,
    ALLOWED_TRANSITIONS,
)

from .readiness import (
    ApplicationReadinessEvaluator,
    DocumentCompletenessReport,
    FactCompletenessReport,
    ApplicationChecklist,
)

from .actions import (
    NextAction,
    NextActionEngine,
    generate_action_id,
)

from .history import (
    HistoryEvent,
    ApplicationHistoryManager,
    generate_event_id,
)

from .review import (
    ReviewCase,
    ReviewManager,
    generate_review_id,
)

from .repository import (
    ApplicationRepository,
    InMemoryApplicationRepository,
)

from .service import (
    ApplicationWorkflowService,
)

__all__ = [
    # Exceptions
    "WorkflowError",
    "InvalidStateTransitionError",
    "ImmutableSnapshotError",
    "ApplicationNotFoundError",
    "DocumentNotFoundError",
    # Statuses & Enums
    "ApplicationStatus",
    "StatutoryDecision",
    "ReadinessStatus",
    "DocumentRequirementStatus",
    "FactCompletenessStatus",
    "ActionType",
    "ActionPriority",
    "ReviewStatus",
    "ReviewReason",
    "EventType",
    # Domain Models
    "ApplicationCase",
    "DocumentReference",
    "FactSnapshot",
    "SchemeEvaluation",
    "DecisionSnapshot",
    "NextAction",
    "HistoryEvent",
    "ReviewCase",
    "DocumentCompletenessReport",
    "FactCompletenessReport",
    "ApplicationChecklist",
    # State Machine & Engines
    "ApplicationStateMachine",
    "ALLOWED_TRANSITIONS",
    "ApplicationReadinessEvaluator",
    "NextActionEngine",
    "ApplicationHistoryManager",
    "ReviewManager",
    # Repositories & Services
    "ApplicationRepository",
    "InMemoryApplicationRepository",
    "ApplicationWorkflowService",
    # ID Generators
    "generate_application_id",
    "generate_snapshot_id",
    "generate_action_id",
    "generate_event_id",
    "generate_review_id",
]
