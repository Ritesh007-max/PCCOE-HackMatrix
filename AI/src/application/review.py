"""
Manual Review Domain Model and Management.
Phase 10: Structured human-in-the-loop review cases for ambiguous or conflicted claims.
Caseworker manual review is NOT an LLM decision.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional

from .status import ReviewStatus, ReviewReason


def generate_review_id() -> str:
    """Generate unique review case identifier."""
    return f"rev_{uuid.uuid4().hex[:12]}"


def current_iso_timestamp() -> str:
    """Return current UTC ISO timestamp."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ReviewCase:
    """
    Structured case for human caseworker review.
    Initiated when deterministic rules encounter conflicts, ambiguous wording,
    or policy requirements needing manual departmental verification.
    """
    review_id: str
    application_id: str
    reason: ReviewReason
    scheme_id: Optional[str] = None
    conflicting_fields: List[str] = field(default_factory=list)
    unresolved_rules: List[str] = field(default_factory=list)
    supporting_documents: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    status: ReviewStatus = ReviewStatus.OPEN
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None
    created_at: str = field(default_factory=current_iso_timestamp)
    updated_at: str = field(default_factory=current_iso_timestamp)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "review_id": self.review_id,
            "application_id": self.application_id,
            "scheme_id": self.scheme_id,
            "reason": self.reason.value,
            "conflicting_fields": self.conflicting_fields,
            "unresolved_rules": self.unresolved_rules,
            "supporting_documents": self.supporting_documents,
            "evidence": self.evidence,
            "status": self.status.value,
            "assigned_to": self.assigned_to,
            "resolution_notes": self.resolution_notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReviewCase":
        reason_raw = data["reason"]
        reason_enum = ReviewReason(reason_raw) if reason_raw in ReviewReason.__members__ else ReviewReason.UNSTRUCTURED_RULE
        status_raw = data.get("status", ReviewStatus.OPEN.value)
        status_enum = ReviewStatus(status_raw) if status_raw in ReviewStatus.__members__ else ReviewStatus.OPEN

        return cls(
            review_id=data["review_id"],
            application_id=data["application_id"],
            reason=reason_enum,
            scheme_id=data.get("scheme_id"),
            conflicting_fields=data.get("conflicting_fields", []),
            unresolved_rules=data.get("unresolved_rules", []),
            supporting_documents=data.get("supporting_documents", []),
            evidence=data.get("evidence", {}),
            status=status_enum,
            assigned_to=data.get("assigned_to"),
            resolution_notes=data.get("resolution_notes"),
            created_at=data.get("created_at", current_iso_timestamp()),
            updated_at=data.get("updated_at", current_iso_timestamp()),
        )


class ReviewManager:
    """Manages review case creation, querying, and caseworker status updates."""

    def __init__(self):
        # Map: review_id -> ReviewCase
        self._reviews: Dict[str, ReviewCase] = {}

    def create_review(
        self,
        application_id: str,
        reason: ReviewReason,
        scheme_id: Optional[str] = None,
        conflicting_fields: Optional[List[str]] = None,
        unresolved_rules: Optional[List[str]] = None,
        supporting_documents: Optional[List[str]] = None,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> ReviewCase:
        """Create a new manual review case."""
        case = ReviewCase(
            review_id=generate_review_id(),
            application_id=application_id,
            reason=reason,
            scheme_id=scheme_id,
            conflicting_fields=list(conflicting_fields or []),
            unresolved_rules=list(unresolved_rules or []),
            supporting_documents=list(supporting_documents or []),
            evidence=dict(evidence or {}),
            status=ReviewStatus.OPEN,
            created_at=current_iso_timestamp(),
            updated_at=current_iso_timestamp(),
        )
        self._reviews[case.review_id] = case
        return case

    def get_review(self, review_id: str) -> Optional[ReviewCase]:
        return self._reviews.get(review_id)

    def list_reviews_for_application(self, application_id: str) -> List[ReviewCase]:
        return [r for r in self._reviews.values() if r.application_id == application_id]

    def update_status(
        self,
        review_id: str,
        status: ReviewStatus,
        assigned_to: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> ReviewCase:
        case = self._reviews.get(review_id)
        if not case:
            raise KeyError(f"Review case '{review_id}' not found")
        case.status = status
        if assigned_to:
            case.assigned_to = assigned_to
        if notes:
            case.resolution_notes = notes
        case.updated_at = current_iso_timestamp()
        return case
