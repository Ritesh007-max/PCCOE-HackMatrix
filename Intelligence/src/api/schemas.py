"""
FIN API Request & Response Schemas.
Pydantic v2 schemas defining strict API contracts for the AI microservice.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Common / Meta Schemas
# ---------------------------------------------------------------------------

class ApiErrorDetail(BaseModel):
    """Detailed error object returned on client or server failure."""
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error explanation")
    request_id: Optional[str] = Field(None, description="Correlation request ID")
    details: Optional[Any] = Field(None, description="Optional diagnostic details")


class ApiErrorResponse(BaseModel):
    """Standardized top-level API error envelope."""
    error: ApiErrorDetail


class HealthResponse(BaseModel):
    """Liveness check response."""
    status: str = Field(default="ok", examples=["ok"])
    service: str = Field(default="fin-ai", examples=["fin-ai"])


class ReadinessResponse(BaseModel):
    """Readiness probe response with local dependency health checks."""
    status: str = Field(default="ready", examples=["ready"])
    checks: Dict[str, str] = Field(
        ...,
        examples=[{"config": "ok", "rag": "ok", "corpus": "ok", "rules": "ok"}]
    )


class VersionResponse(BaseModel):
    """Service build and pipeline version metadata."""
    service: str = Field(default="fin-ai", examples=["fin-ai"])
    api_version: str = Field(default="v1", examples=["v1"])
    pipeline_version: str = Field(default="phase-9", examples=["phase-9"])
    llm_provider_mode: str = Field(default="auto", examples=["auto"])
    knowledge_base_version: str = Field(..., examples=["snapshot_20260921_193823"])


# ---------------------------------------------------------------------------
# Document Ingestion Endpoint Schemas
# ---------------------------------------------------------------------------

class ProcessedDocumentItem(BaseModel):
    """Processed document summary container."""
    document_id: str
    file_name: str
    document_type: str
    status: str
    page_count: int
    extraction_method: str
    sha256: str
    error_message: Optional[str] = None
    extracted_text: Optional[str] = None
    extracted_fields: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = 0.95


class DocumentProcessResponse(BaseModel):
    """Response returned by /v1/documents/process."""
    request_id: str
    document_count: int
    documents: List[ProcessedDocumentItem]


# ---------------------------------------------------------------------------
# Application Analysis Endpoint Schemas
# ---------------------------------------------------------------------------

class ApplicationAnalyzeResponse(BaseModel):
    """Comprehensive response for /v1/applications/analyze (Phase 8 21-step pipeline)."""
    request_id: str
    application_id: str
    steps_completed: int = 21
    processing_status: str
    documents_processed: List[Dict[str, Any]]
    applicant_profile: Dict[str, Any]
    conflicts_detected: List[str]
    query_intent: Optional[Dict[str, Any]] = None
    retrieved_schemes: List[Dict[str, Any]] = []
    eligibility_decision: Dict[str, Any]
    benefit_calculation: Optional[Dict[str, Any]] = None
    missing_information: Dict[str, Any]
    explanation: Dict[str, Any]
    security_audit: Dict[str, Any]
    telemetry: Dict[str, Any]


# ---------------------------------------------------------------------------
# Scheme Search Endpoint Schemas
# ---------------------------------------------------------------------------

class SchemeSearchRequest(BaseModel):
    """Payload for POST /v1/schemes/search."""
    query: str = Field(..., min_length=1, max_length=1000, description="Citizen search query")
    language: str = Field("en", description="Search query language (en, hi, etc.)")
    state: Optional[str] = Field(None, description="Optional state or union territory filter")
    social_category: Optional[str] = Field(None, description="Optional category filter (SC, ST, OBC, General)")
    beneficiary_type: Optional[str] = Field(None, description="Optional beneficiary filter (student, farmer, etc.)")
    top_k: int = Field(10, ge=1, le=50, description="Maximum number of schemes to return")


class SchemeSearchResultItem(BaseModel):
    """Individual ranked scheme search result."""
    scheme_id: str
    scheme_name: str
    relevance_score: float
    source_authority: Optional[str] = None
    source_url: Optional[str] = None
    evidence_snippets: List[str] = []
    state: Optional[str] = None
    details: Dict[str, Any] = {}


class SchemeSearchResponse(BaseModel):
    """Response payload for POST /v1/schemes/search."""
    request_id: str
    query: str
    total_results: int
    results: List[SchemeSearchResultItem]


# ---------------------------------------------------------------------------
# Deterministic Eligibility Check Endpoint Schemas
# ---------------------------------------------------------------------------

class EligibilityCheckRequest(BaseModel):
    """Payload for POST /v1/eligibility/check (100% deterministic, zero LLM)."""
    applicant_facts: Dict[str, Any] = Field(default_factory=dict, description="Normalized applicant facts dictionary")
    scheme_ids: List[str] = Field(..., min_length=1, description="List of target scheme IDs or slugs")
    applicant_id: Optional[str] = Field(None, description="Optional applicant ID to resolve facts from context")
    rule_version: Optional[str] = Field(None, description="Optional rule version to pin evaluation to")
    evidence_references: Optional[Dict[str, Any]] = Field(None, description="Optional provenance citations")


class RuleEvaluationItem(BaseModel):
    """Result of evaluating a single rule AST condition."""
    rule_id: str
    field: str
    operator: str
    status: str
    applicant_value: Any
    expected_value: Any
    hard_constraint: bool
    reason: str


class SchemeEligibilityItem(BaseModel):
    """Deterministic evaluation for an individual scheme."""
    scheme_id: str
    scheme_name: str
    status: str  # PASS, FAIL, UNKNOWN, REVIEW
    is_eligible: bool
    rule_version: Optional[str] = None
    decision_id: Optional[str] = None
    rule_set_hash: Optional[str] = None
    rules_evaluated: List[RuleEvaluationItem] = []
    matched_rules: List[str] = []
    failed_rules: List[str] = []
    missing_fields: List[str] = []
    conflicted_fields: List[str] = []
    disqualification_reasons: List[str] = []
    review_reasons: List[str] = []
    evidence: List[Dict[str, Any]] = []


class EligibilityCheckResponse(BaseModel):
    """Response payload for POST /v1/eligibility/check."""
    request_id: str
    evaluated_schemes_count: int
    evaluations: List[SchemeEligibilityItem]



# ---------------------------------------------------------------------------
# Grounded Chat Endpoint Schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """Payload for POST /v1/chat (grounded RAG query answering)."""
    query: str = Field(..., min_length=1, max_length=2000, description="Citizen query message")
    conversation_id: Optional[str] = Field(None, description="Optional client conversation ID")
    applicant_id: Optional[str] = Field(None, description="Optional citizen identifier for personalized context")
    language: str = Field("en", description="Target response language")
    applicant_facts: Optional[Dict[str, Any]] = Field(None, description="Optional pre-extracted applicant facts")
    documents: Optional[List[Dict[str, Any]]] = Field(None, description="Complete uploaded documents data including extracted fields and text")
    applications: Optional[List[Dict[str, Any]]] = Field(None, description="Submitted welfare applications and support tickets")
    conversation_history: Optional[List[Dict[str, str]]] = Field(None, description="Optional conversational message history")


class ChatCitationItem(BaseModel):
    """Source provenance citation for a claim in chat."""
    chunk_id: str
    scheme_id: str
    url: Optional[str] = None
    excerpt: str


class ChatResponse(BaseModel):
    """Response payload for POST /v1/chat."""
    request_id: str
    conversation_id: Optional[str] = None
    answer: str
    intent: Optional[str] = None
    detected_language: Optional[str] = "en"
    citations: List[ChatCitationItem] = []
    suggested_schemes: List[Dict[str, Any]] = []
    query_understanding: Optional[Dict[str, Any]] = None
    provider_telemetry: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Scheme Recommendation Endpoint Schemas (Phase 19)
# ---------------------------------------------------------------------------

from src.recommendation.models import (
    SchemeRecommendationRequest,
    SchemeRecommendationResponse,
    SchemeRecommendationItemSchema,
)


# ---------------------------------------------------------------------------
# Phase 21 Policy Explanation Endpoint Schemas
# ---------------------------------------------------------------------------

class ExplanationRequest(BaseModel):
    """Payload for POST /v1/explanation/generate."""
    scheme_id: str = Field(..., min_length=1, description="Target scheme slug or ID")
    applicant_id: Optional[str] = Field(None, description="Optional applicant ID to load facts from context")
    applicant_facts: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional manual applicant facts")
    decision_id: Optional[str] = Field(None, description="Optional historical decision ID to explain")
    rule_version: Optional[str] = Field(None, description="Optional rule version to pin explanation to")
    language: str = Field("en", description="Target language (en, hi, gu)")
    query: Optional[str] = Field(None, description="Citizen query context")
    use_llm: bool = Field(False, description="Whether to request LLM natural phrasing enhancement")


class ExplanationResponse(BaseModel):
    """Response payload for POST /v1/explanation/generate."""
    request_id: str
    explanation: Dict[str, Any]


class SchemeComparisonRequest(BaseModel):
    """Payload for POST /v1/explanation/compare."""
    scheme_ids: List[str] = Field(..., min_length=2, max_length=10, description="List of scheme slugs/IDs to compare")
    applicant_id: Optional[str] = Field(None, description="Optional citizen ID to contextualize comparison")
    applicant_facts: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional manual facts")
    language: str = Field("en", description="Target language (en, hi, gu)")


class SchemeComparisonResponse(BaseModel):
    """Response payload for POST /v1/explanation/compare."""
    request_id: str
    comparison: Dict[str, Any]

