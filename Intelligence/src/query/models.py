"""
FIN Query Understanding Models and Canonical Data Contracts.
Defines structured schemas for query classification, candidate fact extraction,
reference resolution, and downstream Phase 19 routing.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from src.llm.models import UserIntent
from src.extraction.models import ApplicantFact, Evidence, FactSourceType


# Canonical Phase 18 Intent Aliases
CanonicalIntent = UserIntent


class DownstreamRoute(str, Enum):
    """Routing targets for Phase 18 query understanding."""
    PERSONAL_FACT_SERVICE = "PERSONAL_FACT_SERVICE"
    DOCUMENT_CONTEXT_SERVICE = "DOCUMENT_CONTEXT_SERVICE"
    SCHEME_RECOMMENDATION_PIPELINE = "SCHEME_RECOMMENDATION_PIPELINE"
    ELIGIBILITY_PIPELINE = "ELIGIBILITY_PIPELINE"
    BENEFIT_PIPELINE = "BENEFIT_PIPELINE"
    POLICY_RAG = "POLICY_RAG"
    DOCUMENT_GUIDANCE = "DOCUMENT_GUIDANCE"
    COMPLETENESS_SERVICE = "COMPLETENESS_SERVICE"
    EXPLANATION_SERVICE = "EXPLANATION_SERVICE"
    CLARIFICATION_HANDLER = "CLARIFICATION_HANDLER"
    UNKNOWN_HANDLER = "UNKNOWN_HANDLER"


@dataclass
class QueryUnderstandingResult:
    """
    Authoritative query understanding contract produced by Phase 18.
    Consumed by downstream Intelligence pipelines (Phase 19 scheme retrieval,
    rule evaluator, benefit calculator, and grounded chat).
    """
    applicant_id: str
    raw_message: str
    normalized_message: str
    intent: CanonicalIntent
    intent_confidence: float
    route: DownstreamRoute
    routing_reason: str
    referenced_scheme: Optional[str] = None
    referenced_document: Optional[str] = None
    referenced_fact_keys: List[str] = field(default_factory=list)
    requested_fact: Optional[str] = None
    candidate_facts: List[ApplicantFact] = field(default_factory=list)
    missing_information: List[str] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    ambiguity: Optional[Dict[str, Any]] = None
    applicant_context_available: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if isinstance(self.intent, str):
            self.intent = CanonicalIntent.from_str(self.intent)
        if isinstance(self.route, str):
            try:
                self.route = DownstreamRoute(self.route)
            except ValueError:
                self.route = DownstreamRoute.UNKNOWN_HANDLER

    def to_dict(self) -> Dict[str, Any]:
        return {
            "applicant_id": self.applicant_id,
            "raw_message": self.raw_message,
            "normalized_message": self.normalized_message,
            "intent": self.intent.value,
            "intent_confidence": round(self.intent_confidence, 4),
            "route": self.route.value,
            "routing_reason": self.routing_reason,
            "referenced_scheme": self.referenced_scheme,
            "referenced_document": self.referenced_document,
            "referenced_fact_keys": self.referenced_fact_keys,
            "requested_fact": self.requested_fact,
            "candidate_facts": [f.to_dict() for f in self.candidate_facts],
            "missing_information": self.missing_information,
            "conflicts": self.conflicts,
            "ambiguity": self.ambiguity,
            "applicant_context_available": self.applicant_context_available,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueryUnderstandingResult":
        facts = [
            ApplicantFact.from_dict(f) if isinstance(f, dict) else f
            for f in data.get("candidate_facts", [])
        ]
        return cls(
            applicant_id=data.get("applicant_id", "default_applicant"),
            raw_message=data.get("raw_message", ""),
            normalized_message=data.get("normalized_message", ""),
            intent=CanonicalIntent.from_str(data.get("intent", CanonicalIntent.UNKNOWN.value)),
            intent_confidence=float(data.get("intent_confidence", 0.0)),
            route=DownstreamRoute(data.get("route", DownstreamRoute.UNKNOWN_HANDLER.value)),
            routing_reason=data.get("routing_reason", ""),
            referenced_scheme=data.get("referenced_scheme"),
            referenced_document=data.get("referenced_document"),
            referenced_fact_keys=data.get("referenced_fact_keys", []),
            requested_fact=data.get("requested_fact"),
            candidate_facts=facts,
            missing_information=data.get("missing_information", []),
            conflicts=data.get("conflicts", []),
            ambiguity=data.get("ambiguity"),
            applicant_context_available=bool(data.get("applicant_context_available", False)),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at"),
        )


@dataclass
class QueryContext:
    """
    Combined snapshot of applicant context and the current conversational turn.
    Ensures single-read consistency for downstream reasoning.
    """
    applicant_id: str
    understanding: QueryUnderstandingResult
    active_facts: Dict[str, Any] = field(default_factory=dict)
    unresolved_conflicts: List[str] = field(default_factory=list)
    document_summaries: List[Dict[str, Any]] = field(default_factory=list)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "applicant_id": self.applicant_id,
            "understanding": self.understanding.to_dict(),
            "active_facts": self.active_facts,
            "unresolved_conflicts": self.unresolved_conflicts,
            "document_summaries": self.document_summaries,
            "conversation_history": self.conversation_history,
            "created_at": self.created_at,
        }
