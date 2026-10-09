"""
FIN Unified Intelligence Request and Response Models.
Provides canonical contracts for the central Intelligence orchestrator,
ensuring serializability, security (no credentials/secrets), and full provenance.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class RequestRoute(str, Enum):
    PERSONAL_FACT_LOOKUP = "PERSONAL_FACT_LOOKUP"
    DOCUMENT_QUERY = "DOCUMENT_QUERY"
    SCHEME_RECOMMENDATION = "SCHEME_RECOMMENDATION"
    ELIGIBILITY_QUERY = "ELIGIBILITY_QUERY"
    BENEFIT_QUERY = "BENEFIT_QUERY"
    POLICY_INFORMATION = "POLICY_INFORMATION"
    DOCUMENT_REQUIREMENTS = "DOCUMENT_REQUIREMENTS"
    MISSING_INFORMATION = "MISSING_INFORMATION"
    DECISION_EXPLANATION = "DECISION_EXPLANATION"
    SCHEME_COMPARISON = "SCHEME_COMPARISON"
    CONFLICT_RESOLUTION_STATUS = "CONFLICT_RESOLUTION_STATUS"
    GENERAL_FOLLOW_UP = "GENERAL_FOLLOW_UP"


@dataclass
class UnifiedIntelligenceRequest:
    """Canonical incoming request model for the unified intelligence engine."""
    applicant_id: str
    message: str
    conversation_id: Optional[str] = None
    request_id: str = field(default_factory=lambda: f"req_{uuid.uuid4().hex[:12]}")
    language: str = "en"
    scheme_id: Optional[str] = None
    document_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.applicant_id or not str(self.applicant_id).strip():
            raise ValueError("applicant_id is required.")
        if not self.conversation_id:
            self.conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
        if not self.language:
            self.language = "en"


@dataclass
class UnifiedIntelligenceResponse:
    """Canonical serializable response contract from the unified intelligence engine."""
    request_id: str
    applicant_id: str
    conversation_id: str
    intent: str
    route: str
    answer: str
    language: str = "en"
    eligibility: Optional[Dict[str, Any]] = None
    recommendations: List[Dict[str, Any]] = field(default_factory=list)
    explanation: Optional[Dict[str, Any]] = None
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)
    missing_information: List[Dict[str, Any]] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    next_actions: List[str] = field(default_factory=list)
    review: Optional[Dict[str, Any]] = None
    grounding_status: str = "GROUNDED"
    provenance: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    response_version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        """Safe serialization to dictionary without exposing sensitive internal secrets."""
        return {
            "request_id": self.request_id,
            "applicant_id": self.applicant_id,
            "conversation_id": self.conversation_id,
            "intent": self.intent,
            "route": self.route,
            "answer": self.answer,
            "language": self.language,
            "eligibility": self.eligibility,
            "recommendations": self.recommendations,
            "explanation": self.explanation,
            "evidence": self.evidence,
            "citations": self.citations,
            "missing_information": self.missing_information,
            "conflicts": self.conflicts,
            "next_actions": self.next_actions,
            "review": self.review,
            "grounding_status": self.grounding_status,
            "provenance": self.provenance,
            "timestamp": self.timestamp,
            "response_version": self.response_version,
        }
