"""
FIN Audit Trail Logger.
Records immutable audit events for traceability:
- FACT_EXTRACTED
- FACT_NORMALIZED
- FACT_CONFLICT_DETECTED
- CONFLICT_OPENED
- CONFLICT_RESOLVED
- ELIGIBILITY_EVALUATED
- DECISION_CREATED
- EXPLANATION_GENERATED
- RECOMMENDATION_GENERATED
- HUMAN_REVIEW_REQUESTED
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import threading
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("fin.audit")


@dataclass
class AuditEvent:
    event_id: str
    applicant_id: str
    actor: str
    event_type: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    conversation_id: Optional[str] = None
    entity_id: Optional[str] = None
    old_state: Optional[Any] = None
    new_state: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "applicant_id": self.applicant_id,
            "actor": self.actor,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "conversation_id": self.conversation_id,
            "entity_id": self.entity_id,
            "old_state": self.old_state,
            "new_state": self.new_state,
            "metadata": self.metadata,
        }


class AuditLogger:
    """Thread-safe append-only audit event repository."""

    def __init__(self):
        self._lock = threading.Lock()
        self._events: List[AuditEvent] = []

    def log(
        self,
        event_type: str,
        applicant_id: str,
        actor: str = "SYSTEM",
        conversation_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        old_state: Optional[Any] = None,
        new_state: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            applicant_id=applicant_id,
            actor=actor,
            event_type=event_type,
            conversation_id=conversation_id,
            entity_id=entity_id,
            old_state=old_state,
            new_state=new_state,
            metadata=metadata or {},
        )
        with self._lock:
            self._events.append(event)
        logger.info(
            "Audit event %s for applicant %s: %s",
            event_type, applicant_id, entity_id or ""
        )
        return event

    def get_events_for_applicant(self, applicant_id: str) -> List[AuditEvent]:
        with self._lock:
            return [e for e in self._events if e.applicant_id == applicant_id]

    def get_events_by_type(self, event_type: str) -> List[AuditEvent]:
        with self._lock:
            return [e for e in self._events if e.event_type == event_type]

    def all_events(self) -> List[AuditEvent]:
        with self._lock:
            return list(self._events)
