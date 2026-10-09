"""
FIN Review & Conflict Models.
Defines canonical conflict records, review statuses, and resolution actions
enforcing strict evidence preservation and historical immutability.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class ConflictStatus(str, Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"


@dataclass
class ConflictRecord:
    """
    Canonical record of a factual conflict between sources (e.g., Document vs User Input).
    Preserves all provenance evidence from both sides permanently.
    """
    conflict_id: str
    applicant_id: str
    field: str
    source_a: str
    value_a: Any
    evidence_a: Dict[str, Any] = field(default_factory=dict)
    source_b: str = ""
    value_b: Any = None
    evidence_b: Dict[str, Any] = field(default_factory=dict)
    status: ConflictStatus = ConflictStatus.OPEN
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolver_id: Optional[str] = None
    resolved_at: Optional[str] = None
    resolution_reason: Optional[str] = None
    authoritative_value: Optional[Any] = None
    selected_source: Optional[str] = None
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "applicant_id": self.applicant_id,
            "field": self.field,
            "source_a": self.source_a,
            "value_a": self.value_a,
            "evidence_a": self.evidence_a,
            "source_b": self.source_b,
            "value_b": self.value_b,
            "evidence_b": self.evidence_b,
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "detected_at": self.detected_at,
            "resolver_id": self.resolver_id,
            "resolved_at": self.resolved_at,
            "resolution_reason": self.resolution_reason,
            "authoritative_value": self.authoritative_value,
            "selected_source": self.selected_source,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConflictRecord":
        status_val = data.get("status", ConflictStatus.OPEN)
        if isinstance(status_val, str):
            try:
                status_val = ConflictStatus(status_val)
            except ValueError:
                status_val = ConflictStatus.OPEN
        return cls(
            conflict_id=data["conflict_id"],
            applicant_id=data["applicant_id"],
            field=data["field"],
            source_a=data.get("source_a", ""),
            value_a=data.get("value_a"),
            evidence_a=data.get("evidence_a", {}),
            source_b=data.get("source_b", ""),
            value_b=data.get("value_b"),
            evidence_b=data.get("evidence_b", {}),
            status=status_val,
            detected_at=data.get("detected_at", datetime.now(timezone.utc).isoformat()),
            resolver_id=data.get("resolver_id"),
            resolved_at=data.get("resolved_at"),
            resolution_reason=data.get("resolution_reason"),
            authoritative_value=data.get("authoritative_value"),
            selected_source=data.get("selected_source"),
            previous_state=data.get("previous_state"),
            new_state=data.get("new_state"),
            metadata=data.get("metadata", {}),
        )
