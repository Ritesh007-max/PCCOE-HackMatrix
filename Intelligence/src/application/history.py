"""
Immutable Application Case Audit History.
Phase 10: Append-only event ledger tracking all lifecycle transitions and actions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional

from .status import EventType


def generate_event_id() -> str:
    """Generate unique event identifier."""
    return f"evt_{uuid.uuid4().hex[:14]}"


@dataclass(frozen=True)
class HistoryEvent:
    """
    Immutable audit log event.
    Tracks state transitions, fact mutations, evaluations, and actor actions.
    """
    event_id: str
    application_id: str
    event_type: EventType
    timestamp: str
    actor: str = "SYSTEM"
    old_state: Optional[str] = None
    new_state: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "application_id": self.application_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "old_state": self.old_state,
            "new_state": self.new_state,
            "request_id": self.request_id,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HistoryEvent":
        etype_raw = data["event_type"]
        etype = EventType(etype_raw) if etype_raw in EventType.__members__ else EventType.APPLICATION_CREATED
        return cls(
            event_id=data["event_id"],
            application_id=data["application_id"],
            event_type=etype,
            timestamp=data["timestamp"],
            actor=data.get("actor", "SYSTEM"),
            old_state=data.get("old_state"),
            new_state=data.get("new_state"),
            request_id=data.get("request_id"),
            metadata=dict(data.get("metadata", {})),
        )


class ApplicationHistoryManager:
    """
    Append-only repository ledger for application history events.
    Guarantees history cannot be modified or truncated.
    """

    def __init__(self):
        # Map: application_id -> List[HistoryEvent]
        self._ledger: Dict[str, List[HistoryEvent]] = {}

    def record_event(
        self,
        application_id: str,
        event_type: EventType,
        actor: str = "SYSTEM",
        old_state: Optional[str] = None,
        new_state: Optional[str] = None,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HistoryEvent:
        """Create and append an immutable event to the application's ledger."""
        event = HistoryEvent(
            event_id=generate_event_id(),
            application_id=application_id,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor=actor,
            old_state=old_state,
            new_state=new_state,
            request_id=request_id,
            metadata=dict(metadata or {}),
        )

        if application_id not in self._ledger:
            self._ledger[application_id] = []
        self._ledger[application_id].append(event)
        return event

    def get_history(self, application_id: str) -> List[HistoryEvent]:
        """Return a copy of the event ledger for a given application ID."""
        return list(self._ledger.get(application_id, []))

    def get_transitions(self, application_id: str) -> List[HistoryEvent]:
        """Return all state transition events for an application."""
        events = self._ledger.get(application_id, [])
        return [e for e in events if e.old_state is not None or e.new_state is not None]
