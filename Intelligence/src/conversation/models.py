"""
FIN Conversation State & Memory Models.
Provides structured multi-turn conversation tracking, turn references, and contextual anchors
scoped strictly to an applicant and conversation session.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class TurnReference:
    """References identified or resolved within a conversation turn."""
    scheme_id: Optional[str] = None
    document_id: Optional[str] = None
    decision_id: Optional[str] = None
    fact_key: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scheme_id": self.scheme_id,
            "document_id": self.document_id,
            "decision_id": self.decision_id,
            "fact_key": self.fact_key,
            "metadata": self.metadata,
        }


@dataclass
class ConversationMessage:
    """Individual message in the multi-turn conversation log."""
    message_id: str
    role: MessageRole
    content: str
    intent: Optional[str] = None
    references: Optional[TurnReference] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "role": self.role.value if hasattr(self.role, "value") else str(self.role),
            "content": self.content,
            "intent": self.intent,
            "references": self.references.to_dict() if self.references else None,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class ConversationState:
    """
    Canonical multi-turn conversation context.
    Strictly isolated per applicant_id and conversation_id.
    Maintains active topic anchors (scheme, document, decision, fact),
    recent scheme history for deterministic pronoun resolution, and review flags.
    """
    conversation_id: str
    applicant_id: str
    messages: List[ConversationMessage] = field(default_factory=list)
    active_scheme: Optional[str] = None
    active_document: Optional[str] = None
    active_decision_id: Optional[str] = None
    active_fact_key: Optional[str] = None
    recent_schemes: List[str] = field(default_factory=list)
    unresolved_questions: List[str] = field(default_factory=list)
    pending_conflicts: List[str] = field(default_factory=list)
    language: str = "en"
    last_decision: Optional[Dict[str, Any]] = None
    last_explanation: Optional[Dict[str, Any]] = None
    version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def add_message(
        self,
        role: MessageRole,
        content: str,
        intent: Optional[str] = None,
        references: Optional[TurnReference] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationMessage:
        msg = ConversationMessage(
            message_id=f"msg_{uuid.uuid4().hex[:12]}",
            role=role,
            content=content,
            intent=intent,
            references=references,
            metadata=metadata or {},
        )
        self.messages.append(msg)
        if references:
            if references.scheme_id:
                self.set_active_scheme(references.scheme_id)
            if references.document_id:
                self.active_document = references.document_id
            if references.decision_id:
                self.active_decision_id = references.decision_id
            if references.fact_key:
                self.active_fact_key = references.fact_key
        self.version += 1
        self.updated_at = datetime.now(timezone.utc).isoformat()
        return msg

    def set_active_scheme(self, scheme_id: str) -> None:
        """Sets active scheme and updates recent_schemes fifo list."""
        if not scheme_id:
            return
        self.active_scheme = scheme_id
        if scheme_id in self.recent_schemes:
            self.recent_schemes.remove(scheme_id)
        self.recent_schemes.insert(0, scheme_id)
        if len(self.recent_schemes) > 5:
            self.recent_schemes = self.recent_schemes[:5]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "applicant_id": self.applicant_id,
            "messages": [m.to_dict() for m in self.messages],
            "active_scheme": self.active_scheme,
            "active_document": self.active_document,
            "active_decision_id": self.active_decision_id,
            "active_fact_key": self.active_fact_key,
            "recent_schemes": list(self.recent_schemes),
            "unresolved_questions": list(self.unresolved_questions),
            "pending_conflicts": list(self.pending_conflicts),
            "language": self.language,
            "last_decision": self.last_decision,
            "last_explanation": self.last_explanation,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
