"""
Status Enums and Constants for Application Decision Workflow.
Phase 10: Clear separation of Application Lifecycle, Statutory Eligibility, and Readiness.
"""

from enum import Enum


class ApplicationStatus(str, Enum):
    """
    Application lifecycle state machine states.
    NOTE: Lifecycle state is NOT statutory eligibility!
    """
    DRAFT = "DRAFT"
    DOCUMENTS_PENDING = "DOCUMENTS_PENDING"
    PROCESSING = "PROCESSING"
    FACTS_READY = "FACTS_READY"
    SCHEMES_IDENTIFIED = "SCHEMES_IDENTIFIED"
    ELIGIBILITY_EVALUATED = "ELIGIBILITY_EVALUATED"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    READY_TO_APPLY = "READY_TO_APPLY"
    UNDER_REVIEW = "UNDER_REVIEW"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class StatutoryDecision(str, Enum):
    """
    Statutory eligibility outcome (reused from Phase 3 contracts).
    Do NOT confuse this with ApplicationStatus or ReadinessStatus.
    """
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    REVIEW = "REVIEW"


class ReadinessStatus(str, Enum):
    """
    Application readiness states derived from fact/document completeness
    and statutory eligibility outcomes.
    """
    NOT_READY = "NOT_READY"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    READY_TO_APPLY = "READY_TO_APPLY"
    COMPLETED = "COMPLETED"


class DocumentRequirementStatus(str, Enum):
    """Status of a required scheme document."""
    AVAILABLE = "AVAILABLE"
    MISSING = "MISSING"
    CONFLICTED = "CONFLICTED"
    UNKNOWN = "UNKNOWN"


class FactCompletenessStatus(str, Enum):
    """Completeness status of an individual applicant profile field."""
    KNOWN = "KNOWN"
    MISSING = "MISSING"
    CONFLICTED = "CONFLICTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ActionType(str, Enum):
    """Deterministic next action types."""
    UPLOAD_DOCUMENT = "UPLOAD_DOCUMENT"
    PROVIDE_INFORMATION = "PROVIDE_INFORMATION"
    RESOLVE_CONFLICT = "RESOLVE_CONFLICT"
    REVIEW_ELIGIBILITY = "REVIEW_ELIGIBILITY"
    VIEW_BENEFIT = "VIEW_BENEFIT"
    CHECK_APPLICATION_STEPS = "CHECK_APPLICATION_STEPS"
    VISIT_OFFICIAL_PORTAL = "VISIT_OFFICIAL_PORTAL"
    READY_TO_APPLY = "READY_TO_APPLY"


class ActionPriority(str, Enum):
    """Priority level for next actions."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ReviewStatus(str, Enum):
    """Status of a human manual review case."""
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"


class ReviewReason(str, Enum):
    """Deterministic reasons triggering manual caseworker review."""
    FACT_CONFLICT = "FACT_CONFLICT"
    UNSTRUCTURED_RULE = "UNSTRUCTURED_RULE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    POLICY_SOURCE_CONFLICT = "POLICY_SOURCE_CONFLICT"
    DOCUMENT_AMBIGUITY = "DOCUMENT_AMBIGUITY"


class EventType(str, Enum):
    """Lifecycle history event types for immutable auditing."""
    APPLICATION_CREATED = "APPLICATION_CREATED"
    DOCUMENT_ADDED = "DOCUMENT_ADDED"
    DOCUMENT_PROCESSED = "DOCUMENT_PROCESSED"
    FACTS_UPDATED = "FACTS_UPDATED"
    CONFLICT_DETECTED = "CONFLICT_DETECTED"
    SCHEMES_RETRIEVED = "SCHEMES_RETRIEVED"
    ELIGIBILITY_EVALUATED = "ELIGIBILITY_EVALUATED"
    BENEFIT_CALCULATED = "BENEFIT_CALCULATED"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    READY_TO_APPLY = "READY_TO_APPLY"
    MANUAL_REVIEW_REQUESTED = "MANUAL_REVIEW_REQUESTED"
    APPLICATION_COMPLETED = "APPLICATION_COMPLETED"
    APPLICATION_CANCELLED = "APPLICATION_CANCELLED"
    APPLICATION_FAILED = "APPLICATION_FAILED"
    APPLICATION_REEVALUATED = "APPLICATION_REEVALUATED"
