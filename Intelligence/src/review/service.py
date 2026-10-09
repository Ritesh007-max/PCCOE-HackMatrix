"""
FIN Conflict Resolution & Human Review Service.
Manages conflicting applicant evidence, provides caseworker resolution workflows,
enforces evidence preservation, and updates ApplicantContext without mutating historical decisions.
"""

from datetime import datetime, timezone
import logging
import threading
from typing import Any, Dict, List, Optional
import uuid

from src.context.models import ApplicantContext
from src.context.service import ApplicantContextService
from src.extraction.models import (
    ApplicantFact,
    Evidence,
    FactSourceType,
    FactVerificationStatus,
)
from .models import ConflictRecord, ConflictStatus
from .audit import AuditLogger

logger = logging.getLogger("fin.review.service")


class ConflictResolutionService:
    """
    Caseworker-authorized conflict resolution service.
    Enforces the invariant:
    No conflict is automatically resolved by guessing or recency.
    Historical decisions remain immutable; resolution generates a NEW decision version.
    """

    def __init__(
        self,
        context_service: Optional[ApplicantContextService] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        self.context_service = context_service or ApplicantContextService()
        self.audit_logger = audit_logger or AuditLogger()
        self._lock = threading.Lock()
        # Key: conflict_id -> ConflictRecord
        self._conflicts: Dict[str, ConflictRecord] = {}

    def record_conflict(
        self,
        applicant_id: str,
        field: str,
        source_a: str,
        value_a: Any,
        evidence_a: Optional[Dict[str, Any]] = None,
        source_b: str = "",
        value_b: Any = None,
        evidence_b: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConflictRecord:
        """Records an open conflict between two sources."""
        conflict_id = f"cnf_{uuid.uuid4().hex[:12]}"
        conflict = ConflictRecord(
            conflict_id=conflict_id,
            applicant_id=applicant_id,
            field=field,
            source_a=source_a,
            value_a=value_a,
            evidence_a=evidence_a or {},
            source_b=source_b,
            value_b=value_b,
            evidence_b=evidence_b or {},
            status=ConflictStatus.OPEN,
            metadata=metadata or {},
        )
        with self._lock:
            self._conflicts[conflict_id] = conflict

        self.audit_logger.log(
            event_type="FACT_CONFLICT_DETECTED",
            applicant_id=applicant_id,
            actor="SYSTEM",
            entity_id=conflict_id,
            new_state="OPEN",
            metadata={"field": field, "source_a": source_a, "source_b": source_b},
        )
        return conflict

    def list_conflicts(
        self,
        applicant_id: Optional[str] = None,
        status: Optional[ConflictStatus] = None,
    ) -> List[ConflictRecord]:
        with self._lock:
            records = list(self._conflicts.values())
        if applicant_id:
            records = [r for r in records if r.applicant_id == applicant_id]
        if status:
            records = [r for r in records if r.status == status]
        return records

    def get_conflict(self, conflict_id: str) -> Optional[ConflictRecord]:
        with self._lock:
            return self._conflicts.get(conflict_id)

    def resolve_conflict(
        self,
        conflict_id: str,
        resolver_id: str,
        selected_source: str,
        reason: str,
        authoritative_value: Optional[Any] = None,
    ) -> ConflictRecord:
        """
        Caseworker resolution of a conflict.
        Selects authoritative source or provides verified value.
        Updates ApplicantContext with resolved fact without destroying historical evidence.
        """
        if not resolver_id or not resolver_id.strip():
            raise ValueError("Authenticated resolver_id is required to resolve conflicts.")
        if not reason or not reason.strip():
            raise ValueError("A documented resolution reason is mandatory.")

        with self._lock:
            conflict = self._conflicts.get(conflict_id)
            if not conflict:
                raise KeyError(f"Conflict {conflict_id} not found.")

            if conflict.status == ConflictStatus.RESOLVED:
                logger.warning("Conflict %s is already resolved.", conflict_id)
                return conflict

            prev_state = conflict.status.value

            # Determine authoritative value
            if authoritative_value is not None:
                final_val = authoritative_value
            elif selected_source == conflict.source_a:
                final_val = conflict.value_a
            elif selected_source == conflict.source_b:
                final_val = conflict.value_b
            else:
                final_val = authoritative_value if authoritative_value is not None else conflict.value_a

            norm_val = final_val
            if isinstance(final_val, str):
                try:
                    if "." in final_val:
                        norm_val = float(final_val)
                    else:
                        norm_val = float(int(final_val))
                except (ValueError, TypeError):
                    norm_val = final_val
            elif isinstance(final_val, (int, float)):
                norm_val = float(final_val)

            final_val = norm_val

            conflict.status = ConflictStatus.RESOLVED
            conflict.resolver_id = resolver_id
            conflict.resolved_at = datetime.now(timezone.utc).isoformat()
            conflict.resolution_reason = reason
            conflict.selected_source = selected_source
            conflict.authoritative_value = final_val
            conflict.previous_state = prev_state
            conflict.new_state = ConflictStatus.RESOLVED.value

        # Update canonical ApplicantContext via repository
        if self.context_service and hasattr(self.context_service, "repository") and self.context_service.repository:
            resolved_fact = ApplicantFact(
                id=f"fact_resolved_{uuid.uuid4().hex[:8]}",
                applicant_id=conflict.applicant_id,
                field=conflict.field,
                value=final_val,
                normalized_value=final_val,
                data_type="numeric" if isinstance(final_val, (int, float)) else "string",
                confidence=1.0,
                source_document=f"Resolved by {resolver_id}: {reason}",
                extraction_method="MANUAL_ENTRY",
                verification_status=FactVerificationStatus.USER_CONFIRMED,
                source_type=FactSourceType.USER_INPUT if "USER" in selected_source.upper() else FactSourceType.DOCUMENT,
                metadata={"resolved_from_conflict": conflict_id, "reason": reason, "is_authoritative": True},
            )
            self.context_service.repository.save_fact(resolved_fact)

        self.audit_logger.log(
            event_type="CONFLICT_RESOLVED",
            applicant_id=conflict.applicant_id,
            actor=resolver_id,
            entity_id=conflict_id,
            old_state=prev_state,
            new_state=ConflictStatus.RESOLVED.value,
            metadata={
                "field": conflict.field,
                "selected_source": selected_source,
                "authoritative_value": final_val,
                "reason": reason,
            },
        )
        return conflict

    def reject_conflict(
        self,
        conflict_id: str,
        resolver_id: str,
        reason: str,
    ) -> ConflictRecord:
        """Rejects a conflict (e.g. invalid conflict report)."""
        with self._lock:
            conflict = self._conflicts.get(conflict_id)
            if not conflict:
                raise KeyError(f"Conflict {conflict_id} not found.")
            prev_state = conflict.status.value
            conflict.status = ConflictStatus.REJECTED
            conflict.resolver_id = resolver_id
            conflict.resolved_at = datetime.now(timezone.utc).isoformat()
            conflict.resolution_reason = reason
            conflict.previous_state = prev_state
            conflict.new_state = ConflictStatus.REJECTED.value

        self.audit_logger.log(
            event_type="CONFLICT_REJECTED",
            applicant_id=conflict.applicant_id,
            actor=resolver_id,
            entity_id=conflict_id,
            old_state=prev_state,
            new_state=ConflictStatus.REJECTED.value,
            metadata={"reason": reason},
        )
        return conflict

    def escalate_conflict(
        self,
        conflict_id: str,
        resolver_id: str,
        reason: str,
    ) -> ConflictRecord:
        """Escalates conflict to supervisory review."""
        with self._lock:
            conflict = self._conflicts.get(conflict_id)
            if not conflict:
                raise KeyError(f"Conflict {conflict_id} not found.")
            prev_state = conflict.status.value
            conflict.status = ConflictStatus.ESCALATED
            conflict.resolver_id = resolver_id
            conflict.resolution_reason = reason
            conflict.previous_state = prev_state
            conflict.new_state = ConflictStatus.ESCALATED.value

        self.audit_logger.log(
            event_type="CONFLICT_ESCALATED",
            applicant_id=conflict.applicant_id,
            actor=resolver_id,
            entity_id=conflict_id,
            old_state=prev_state,
            new_state=ConflictStatus.ESCALATED.value,
            metadata={"reason": reason},
        )
        return conflict
