"""
Decision Snapshot Domain Model.
Phase 10: Strict Immutability and Reproducible Audit Snapshots.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional

from .status import StatutoryDecision
from .exceptions import ImmutableSnapshotError


def generate_snapshot_id() -> str:
    """Generate a unique decision snapshot identifier using UUID4."""
    return f"snap_{uuid.uuid4().hex[:16]}"


def current_iso_timestamp() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


class DecisionSnapshot:
    """
    Immutable Decision Snapshot representing a statutory eligibility outcome.
    Guarantees:
        Policy Source + Rule AST + Applicant Facts = Reproducible Decision Context.
    
    Once initialized, mutating any attribute raises ImmutableSnapshotError.
    """

    def __init__(
        self,
        application_id: str,
        scheme_id: str,
        scheme_name: str = "",
        applicant_fact_snapshot: Optional[Dict[str, Any]] = None,
        policy_snapshot_version: str = "V1",
        rule_version: str = "1.0.0",
        decision_status: StatutoryDecision = StatutoryDecision.UNKNOWN,
        is_eligible: bool = False,
        matched_rules: Optional[List[Dict[str, Any]]] = None,
        failed_rules: Optional[List[Dict[str, Any]]] = None,
        unknown_rules: Optional[List[Dict[str, Any]]] = None,
        review_fields: Optional[List[str]] = None,
        benefit_result: Optional[Dict[str, Any]] = None,
        evidence_references: Optional[Dict[str, List[str]]] = None,
        snapshot_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        version_index: int = 1,
        reason_for_evaluation: str = "INITIAL_EVALUATION",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        # Internal storage during initialization
        super().__setattr__("_initialized", False)

        self.snapshot_id = snapshot_id or generate_snapshot_id()
        self.application_id = application_id
        self.scheme_id = scheme_id
        self.scheme_name = scheme_name
        self.applicant_fact_snapshot = dict(applicant_fact_snapshot or {})
        self.policy_snapshot_version = policy_snapshot_version
        self.rule_version = rule_version
        self.decision_status = decision_status if isinstance(decision_status, StatutoryDecision) else StatutoryDecision(str(decision_status))
        self.is_eligible = bool(is_eligible)
        self.matched_rules = list(matched_rules or [])
        self.failed_rules = list(failed_rules or [])
        self.unknown_rules = list(unknown_rules or [])
        self.review_fields = list(review_fields or [])
        self.benefit_result = dict(benefit_result) if benefit_result else None
        self.evidence_references = dict(evidence_references or {})
        self.timestamp = timestamp or current_iso_timestamp()
        self.version_index = int(version_index)
        self.reason_for_evaluation = reason_for_evaluation
        self.metadata = dict(metadata or {})

        # Freeze the snapshot
        super().__setattr__("_initialized", True)

    def __setattr__(self, name: str, value: Any) -> None:
        """Enforce strict immutability once object is initialized."""
        if getattr(self, "_initialized", False):
            raise ImmutableSnapshotError(
                snapshot_id=getattr(self, "snapshot_id", "unknown"),
                field_name=name,
            )
        super().__setattr__(name, value)

    def __delattr__(self, name: str) -> None:
        """Prevent deletion of snapshot attributes."""
        raise ImmutableSnapshotError(
            snapshot_id=getattr(self, "snapshot_id", "unknown"),
            field_name=name,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary for auditing or serialization."""
        return {
            "snapshot_id": self.snapshot_id,
            "application_id": self.application_id,
            "scheme_id": self.scheme_id,
            "scheme_name": self.scheme_name,
            "applicant_fact_snapshot": self.applicant_fact_snapshot,
            "policy_snapshot_version": self.policy_snapshot_version,
            "rule_version": self.rule_version,
            "decision_status": self.decision_status.value,
            "is_eligible": self.is_eligible,
            "matched_rules": self.matched_rules,
            "failed_rules": self.failed_rules,
            "unknown_rules": self.unknown_rules,
            "review_fields": self.review_fields,
            "benefit_result": self.benefit_result,
            "evidence_references": self.evidence_references,
            "timestamp": self.timestamp,
            "version_index": self.version_index,
            "reason_for_evaluation": self.reason_for_evaluation,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DecisionSnapshot":
        """Reconstruct immutable snapshot from serialized dict."""
        status_val = data.get("decision_status", StatutoryDecision.UNKNOWN.value)
        status_enum = StatutoryDecision(status_val) if status_val in StatutoryDecision.__members__ else StatutoryDecision.UNKNOWN
        return cls(
            snapshot_id=data.get("snapshot_id"),
            application_id=data["application_id"],
            scheme_id=data["scheme_id"],
            scheme_name=data.get("scheme_name", ""),
            applicant_fact_snapshot=data.get("applicant_fact_snapshot", {}),
            policy_snapshot_version=data.get("policy_snapshot_version", "V1"),
            rule_version=data.get("rule_version", "1.0.0"),
            decision_status=status_enum,
            is_eligible=data.get("is_eligible", False),
            matched_rules=data.get("matched_rules", []),
            failed_rules=data.get("failed_rules", []),
            unknown_rules=data.get("unknown_rules", []),
            review_fields=data.get("review_fields", []),
            benefit_result=data.get("benefit_result"),
            evidence_references=data.get("evidence_references", {}),
            timestamp=data.get("timestamp"),
            version_index=data.get("version_index", 1),
            reason_for_evaluation=data.get("reason_for_evaluation", "INITIAL_EVALUATION"),
            metadata=data.get("metadata", {}),
        )
