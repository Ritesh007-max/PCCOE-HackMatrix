"""
FIN Phase 19 Scheme Recommendation Models.
Defines structured contracts for applicant-scheme compatibility, missing-field
gap analysis, policy evidence provenance, and ranked recommendations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class CompatibilityState(str, Enum):
    """
    Transparent four-state compatibility classification.
    CRITICAL INVARIANT: Compatibility is candidate relevance, NOT statutory eligibility.
    UNKNOWN is never collapsed into MATCH.
    """
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class MissingFieldCriticality(str, Enum):
    """Criticality level for missing applicant fields."""
    MANDATORY = "MANDATORY"
    OPTIONAL = "OPTIONAL"


@dataclass
class FactMatchDetail:
    """Diagnostic detail for an individual applicant fact comparison."""
    field: str
    applicant_value: Any
    expected_value: Any
    status: CompatibilityState
    reason: str
    source_type: Optional[str] = None
    has_conflict: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "applicant_value": self.applicant_value,
            "expected_value": self.expected_value,
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "reason": self.reason,
            "source_type": self.source_type,
            "has_conflict": self.has_conflict,
        }


@dataclass
class CompatibilityResult:
    """Deterministic compatibility analysis result for an applicant against a scheme."""
    overall_compatibility_score: float
    matched_facts: List[FactMatchDetail] = field(default_factory=list)
    unmatched_facts: List[FactMatchDetail] = field(default_factory=list)
    unknown_facts: List[FactMatchDetail] = field(default_factory=list)
    conflict_facts: List[FactMatchDetail] = field(default_factory=list)
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    explanation: List[str] = field(default_factory=list)
    target_group_match: CompatibilityState = CompatibilityState.NOT_APPLICABLE
    target_group_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_compatibility_score": round(self.overall_compatibility_score, 4),
            "matched_facts": [f.to_dict() for f in self.matched_facts],
            "unmatched_facts": [f.to_dict() for f in self.unmatched_facts],
            "unknown_facts": [f.to_dict() for f in self.unknown_facts],
            "conflict_facts": [f.to_dict() for f in self.conflict_facts],
            "score_breakdown": self.score_breakdown,
            "explanation": self.explanation,
            "target_group_match": self.target_group_match.value if hasattr(self.target_group_match, "value") else str(self.target_group_match),
            "target_group_name": self.target_group_name,
        }


@dataclass
class MissingField:
    """Represents a specific applicant fact missing for scheme evaluation."""
    field: str
    reason: str
    required_for: str = "eligibility"
    rule_id: Optional[str] = None
    criticality: MissingFieldCriticality = MissingFieldCriticality.MANDATORY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "reason": self.reason,
            "required_for": self.required_for,
            "rule_id": self.rule_id,
            "criticality": self.criticality.value if hasattr(self.criticality, "value") else str(self.criticality),
        }


@dataclass
class RecommendationEvidence:
    """Provenance and policy grounding for a recommended scheme."""
    source_tier: str
    source_dataset: Optional[str] = None
    source_url: Optional[str] = None
    snippets: List[str] = field(default_factory=list)
    chunk_ids: List[str] = field(default_factory=list)
    applicant_evidence_ids: List[str] = field(default_factory=list)
    provenance_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_tier": self.source_tier,
            "source_dataset": self.source_dataset,
            "source_url": self.source_url,
            "snippets": self.snippets,
            "chunk_ids": self.chunk_ids,
            "applicant_evidence_ids": self.applicant_evidence_ids,
            "provenance_metadata": self.provenance_metadata,
        }


@dataclass
class SchemeRecommendationItem:
    """
    Structured recommendation container for an individual scheme candidate.
    Preserves strict separation between:
    - relevance_score (retrieval relevance from HybridRetriever)
    - compatibility_score (deterministic personal fact alignment)
    - eligibility_status (PASS/FAIL/UNKNOWN/REVIEW from deterministic EligibilityEngine)
    - target_group_match (MATCH/MISMATCH/UNKNOWN/NOT_APPLICABLE)
    """
    scheme_id: str
    scheme_slug: str
    scheme_name: str
    relevance_score: float
    compatibility_score: float
    overall_match_score: float
    matched_facts: List[Dict[str, Any]] = field(default_factory=list)
    unmatched_facts: List[Dict[str, Any]] = field(default_factory=list)
    missing_fields: List[Dict[str, Any]] = field(default_factory=list)
    missing_fields_status: str = "UNKNOWN"
    conflict_fields: List[str] = field(default_factory=list)
    eligibility_status: Optional[str] = None
    is_eligible: Optional[bool] = None
    evidence: Optional[RecommendationEvidence] = None
    source_metadata: Dict[str, Any] = field(default_factory=dict)
    recommendation_reasons: List[str] = field(default_factory=list)
    target_group_match: Optional[str] = None
    target_group_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scheme_id": self.scheme_id,
            "scheme_slug": self.scheme_slug,
            "scheme_name": self.scheme_name,
            "relevance_score": round(self.relevance_score, 4),
            "compatibility_score": round(self.compatibility_score, 4),
            "overall_match_score": round(self.overall_match_score, 4),
            "matched_facts": self.matched_facts,
            "unmatched_facts": self.unmatched_facts,
            "missing_fields": self.missing_fields,
            "missing_fields_status": self.missing_fields_status,
            "conflict_fields": self.conflict_fields,
            "eligibility_status": self.eligibility_status,
            "is_eligible": self.is_eligible,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "source_metadata": self.source_metadata,
            "recommendation_reasons": self.recommendation_reasons,
            "target_group_match": self.target_group_match,
            "target_group_name": self.target_group_name,
        }


@dataclass
class SchemeRecommendationResult:
    """Authoritative recommendation result returned by SchemeRecommendationService."""
    applicant_id: str
    query: str
    total_candidates_retrieved: int
    recommendations: List[SchemeRecommendationItem] = field(default_factory=list)
    applied_filters: Dict[str, Any] = field(default_factory=dict)
    active_facts_summary: Dict[str, Any] = field(default_factory=dict)
    conflicts_detected: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "applicant_id": self.applicant_id,
            "query": self.query,
            "total_candidates_retrieved": self.total_candidates_retrieved,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "applied_filters": self.applied_filters,
            "active_facts_summary": self.active_facts_summary,
            "conflicts_detected": self.conflicts_detected,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Pydantic Schemas for API Layer (POST /v1/schemes/recommend)
# ---------------------------------------------------------------------------

class SchemeRecommendationRequest(BaseModel):
    """Payload for POST /v1/schemes/recommend."""
    applicant_id: str = Field(..., min_length=1, max_length=128, description="Citizen applicant identifier")
    query: str = Field(..., min_length=1, max_length=2000, description="Citizen recommendation or discovery query")
    language: str = Field("en", description="Query language code (en, hi, etc.)")
    top_k: int = Field(10, ge=1, le=50, description="Maximum number of recommendations to return")
    include_eligibility: bool = Field(True, description="Whether to evaluate deterministic eligibility where rules exist")
    include_missing_fields: bool = Field(True, description="Whether to compute missing-field gap analysis")
    state_override: Optional[str] = Field(None, description="Optional explicit state filter override")
    category_override: Optional[str] = Field(None, description="Optional explicit social category filter override")
    applicant_facts: Dict[str, Any] = Field(default_factory=dict, description="Authenticated applicant profile facts")
    document_facts: List[Dict[str, Any]] = Field(default_factory=list, description="Document-scoped extracted facts with provenance")


class SchemeRecommendationItemSchema(BaseModel):
    """API representation of a single ranked scheme recommendation."""
    scheme_id: str
    scheme_slug: str
    scheme_name: str
    relevance_score: float
    compatibility_score: float
    overall_match_score: float
    matched_facts: List[Dict[str, Any]] = []
    unmatched_facts: List[Dict[str, Any]] = []
    missing_fields: List[Dict[str, Any]] = []
    missing_fields_status: str = "UNKNOWN"
    conflict_fields: List[str] = []
    eligibility_status: Optional[str] = None
    is_eligible: Optional[bool] = None
    evidence: Optional[Dict[str, Any]] = None
    source_metadata: Dict[str, Any] = {}
    recommendation_reasons: List[str] = []


class SchemeRecommendationResponse(BaseModel):
    """API response envelope for POST /v1/schemes/recommend."""
    request_id: str
    applicant_id: str
    query: str
    total_candidates_retrieved: int
    recommendations: List[SchemeRecommendationItemSchema]
    applied_filters: Dict[str, Any] = {}
    active_facts_summary: Dict[str, Any] = {}
    conflicts_detected: List[str] = []
    metadata: Dict[str, Any] = {}
    created_at: str
