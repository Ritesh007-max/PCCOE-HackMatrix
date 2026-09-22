"""
PolicySetu Phase 6 LLM / NLP Data Models & Schemas.
Defines structured contracts for query understanding, candidate fact extraction,
two-tier grounding verification, and grounded explanation generation.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import sys
from pathlib import Path

# Ensure AI directory is on sys.path
_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

try:
    from ..extraction.models import FactVerificationStatus
except (ImportError, ValueError):
    from src.extraction.models import FactVerificationStatus


class UserIntent(str, Enum):
    """Enumeration of user intent categories."""
    SCHEME_DISCOVERY = "SCHEME_DISCOVERY"
    ELIGIBILITY_QUESTION = "ELIGIBILITY_QUESTION"
    BENEFIT_QUESTION = "BENEFIT_QUESTION"
    APPLICATION_PROCESS = "APPLICATION_PROCESS"
    DOCUMENT_REQUIREMENTS = "DOCUMENT_REQUIREMENTS"
    STATUS_QUERY = "STATUS_QUERY"
    COMPARISON = "COMPARISON"
    GENERAL_INFORMATION = "GENERAL_INFORMATION"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_str(cls, val: Any) -> "UserIntent":
        if isinstance(val, UserIntent):
            return val
        if not val or not isinstance(val, str):
            return cls.UNKNOWN
        v = val.strip().upper()
        for item in cls:
            if item.value == v or item.name == v:
                return item
        if any(s in v for s in ("SCHEME", "SEARCH", "FIND", "DISCOVERY", "EXPLORE", "SCHOLARSHIP")):
            return cls.SCHEME_DISCOVERY
        if "ELIGIB" in v or "QUALIF" in v:
            return cls.ELIGIBILITY_QUESTION
        if "BENEFIT" in v or "SUBSIDY" in v or "MONEY" in v:
            return cls.BENEFIT_QUESTION
        if "APPLY" in v or "APPLICATION" in v or "PROCESS" in v:
            return cls.APPLICATION_PROCESS
        if "DOC" in v:
            return cls.DOCUMENT_REQUIREMENTS
        if "STATUS" in v or "TRACK" in v:
            return cls.STATUS_QUERY
        if "COMPARE" in v or "COMPARISON" in v:
            return cls.COMPARISON
        if "INFO" in v:
            return cls.GENERAL_INFORMATION
        return cls.UNKNOWN


class ExtractionConfidence(str, Enum):
    """Categorical confidence for fact extraction."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_str(cls, val: Any) -> "ExtractionConfidence":
        if isinstance(val, ExtractionConfidence):
            return val
        if not val or not isinstance(val, str):
            return cls.UNKNOWN
        v = val.strip().upper()
        for item in cls:
            if item.value == v or item.name == v:
                return item
        if "HIGH" in v:
            return cls.HIGH
        if "MED" in v:
            return cls.MEDIUM
        if "LOW" in v:
            return cls.LOW
        return cls.UNKNOWN


class AmbiguityType(str, Enum):
    """Taxonomy of detected ambiguities in citizen inputs."""
    APPROXIMATE_VALUE = "APPROXIMATE_VALUE"
    MISSING_UNIT = "MISSING_UNIT"
    ENTITY_CONFUSION = "ENTITY_CONFUSION"
    TEMPORARY_RESIDENCE = "TEMPORARY_RESIDENCE"
    UNVERIFIED_STATUS = "UNVERIFIED_STATUS"
    CONTRADICTORY_STATEMENT = "CONTRADICTORY_STATEMENT"
    MULTIPLE_VALUES = "MULTIPLE_VALUES"


class ClaimSupportStatus(str, Enum):
    """Grounding verification status of individual factual claims."""
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    UNVERIFIED_CITATION = "UNVERIFIED_CITATION"


@dataclass
class AmbiguityRecord:
    """Represents a specific ambiguity detected in user input."""
    ambiguity_type: AmbiguityType
    field: Optional[str] = None
    raw_span: str = ""
    description: str = ""
    suggested_clarification: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ambiguity_type": self.ambiguity_type.value,
            "field": self.field,
            "raw_span": self.raw_span,
            "description": self.description,
            "suggested_clarification": self.suggested_clarification,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AmbiguityRecord":
        return cls(
            ambiguity_type=AmbiguityType(data.get("ambiguity_type", AmbiguityType.APPROXIMATE_VALUE.value)),
            field=data.get("field"),
            raw_span=data.get("raw_span", ""),
            description=data.get("description", ""),
            suggested_clarification=data.get("suggested_clarification", ""),
        )


@dataclass
class QueryIntent:
    """
    Structured query understanding result.
    CRITICAL CONTRACT: Fields here are RETRIEVAL HINTS ONLY.
    They must NEVER automatically become ApplicantFacts unless the user explicitly
    states the attribute about themselves in the first person.
    """
    original_query: str
    normalized_query: str
    language: str  # "en", "hi", "hinglish", "unknown"
    intent: UserIntent
    secondary_intent: Optional[UserIntent] = None
    state: Optional[str] = None
    social_category: Optional[str] = None
    beneficiary_type: Optional[str] = None
    policy_domain: Optional[str] = None
    benefit_type: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    confidence: float = 1.0
    ambiguities: List[AmbiguityRecord] = field(default_factory=list)
    is_search_hint_only: bool = True

    def __post_init__(self):
        self.confidence = max(0.0, min(1.0, float(self.confidence)))
        self.intent = UserIntent.from_str(self.intent)
        if self.secondary_intent is not None:
            self.secondary_intent = UserIntent.from_str(self.secondary_intent)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_query": self.original_query,
            "normalized_query": self.normalized_query,
            "language": self.language,
            "intent": self.intent.value,
            "secondary_intent": self.secondary_intent.value if self.secondary_intent else None,
            "state": self.state,
            "social_category": self.social_category,
            "beneficiary_type": self.beneficiary_type,
            "policy_domain": self.policy_domain,
            "benefit_type": self.benefit_type,
            "keywords": self.keywords,
            "confidence": self.confidence,
            "ambiguities": [a.to_dict() for a in self.ambiguities],
            "is_search_hint_only": self.is_search_hint_only,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueryIntent":
        ambiguities = [
            AmbiguityRecord.from_dict(a) if isinstance(a, dict) else a
            for a in data.get("ambiguities", [])
        ]
        return cls(
            original_query=data.get("original_query", ""),
            normalized_query=data.get("normalized_query", ""),
            language=data.get("language", "unknown"),
            intent=UserIntent.from_str(data.get("intent", UserIntent.UNKNOWN.value)),
            secondary_intent=UserIntent.from_str(data["secondary_intent"]) if data.get("secondary_intent") else None,
            state=data.get("state"),
            social_category=data.get("social_category"),
            beneficiary_type=data.get("beneficiary_type"),
            policy_domain=data.get("policy_domain"),
            benefit_type=data.get("benefit_type"),
            keywords=data.get("keywords", []),
            confidence=float(data.get("confidence", 1.0)),
            ambiguities=ambiguities,
            is_search_hint_only=data.get("is_search_hint_only", True),
        )


@dataclass
class ApplicantFactCandidate:
    """
    Extracted candidate applicant fact.
    CRITICAL CONTRACT:
    1. Holds ONLY raw_value. Phase 4 exclusively owns normalization.
    2. suggested_verification_status defaults strictly to SELF_REPORTED.
    """
    field: str
    raw_value: Any
    data_type: str = "string"
    confidence: float = 1.0
    evidence_text: str = ""
    extraction_source: str = "user_text"
    ambiguity: Optional[str] = None
    needs_confirmation: bool = False
    suggested_verification_status: FactVerificationStatus = FactVerificationStatus.SELF_REPORTED

    def __post_init__(self):
        self.confidence = max(0.0, min(1.0, float(self.confidence)))
        if isinstance(self.suggested_verification_status, str):
            self.suggested_verification_status = FactVerificationStatus(self.suggested_verification_status)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "raw_value": self.raw_value,
            "data_type": self.data_type,
            "confidence": self.confidence,
            "evidence_text": self.evidence_text,
            "extraction_source": self.extraction_source,
            "ambiguity": self.ambiguity,
            "needs_confirmation": self.needs_confirmation,
            "suggested_verification_status": self.suggested_verification_status.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApplicantFactCandidate":
        status_raw = data.get("suggested_verification_status")
        try:
            status = FactVerificationStatus(status_raw) if status_raw else FactVerificationStatus.SELF_REPORTED
        except (ValueError, KeyError):
            status = FactVerificationStatus.SELF_REPORTED

        field_raw = data.get("field") or data.get("fact_type") or data.get("field_name") or "unknown"
        f_lower = str(field_raw).strip().lower()
        canonical_map = {
            "family_income": "annual_family_income",
            "annual_income": "annual_family_income",
            "income": "annual_family_income",
            "age": "age",
            "state": "state",
            "state_of_residence": "state",
            "gender": "gender",
            "social_category": "social_category",
            "caste": "social_category",
            "disability_percentage": "disability_percentage",
            "disability": "disability_percentage",
            "occupation": "occupation",
            "marital_status": "marital_status",
            "landholding_acres": "landholding_acres",
        }
        field = canonical_map.get(f_lower, f_lower)

        return cls(
            field=field,
            raw_value=data.get("raw_value") or data.get("value"),
            data_type=data.get("data_type", "string"),
            confidence=float(data.get("confidence", 1.0)),
            evidence_text=data.get("evidence_text", ""),
            extraction_source=data.get("extraction_source", "user_text"),
            ambiguity=data.get("ambiguity"),
            needs_confirmation=bool(data.get("needs_confirmation", False)),
            suggested_verification_status=status,
        )


@dataclass
class FactExtractionResult:
    """Result of applicant fact extraction from natural-language text."""
    facts: List[ApplicantFactCandidate] = field(default_factory=list)
    candidate_missing_fields: List[str] = field(default_factory=list)
    ambiguities: List[AmbiguityRecord] = field(default_factory=list)
    extraction_confidence: ExtractionConfidence = ExtractionConfidence.HIGH
    source_text: str = ""
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "facts": [f.to_dict() for f in self.facts],
            "candidate_missing_fields": self.candidate_missing_fields,
            "ambiguities": [a.to_dict() for a in self.ambiguities],
            "extraction_confidence": self.extraction_confidence.value,
            "source_text": self.source_text,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FactExtractionResult":
        raw_list = data.get("facts") or data.get("extracted_facts") or []
        facts = [
            ApplicantFactCandidate.from_dict(f) if isinstance(f, dict) else f
            for f in raw_list
        ]
        ambiguities = [
            AmbiguityRecord.from_dict(a) if isinstance(a, dict) else a
            for a in data.get("ambiguities", [])
        ]
        return cls(
            facts=facts,
            candidate_missing_fields=data.get("candidate_missing_fields", []),
            ambiguities=ambiguities,
            extraction_confidence=ExtractionConfidence.from_str(
                data.get("extraction_confidence", ExtractionConfidence.HIGH.value)
            ),
            source_text=data.get("source_text", ""),
            warnings=data.get("warnings", []),
        )


@dataclass
class FactualClaim:
    """A factual claim made in an explanation, with its grounding provenance."""
    statement: str
    cited_chunk_ids: List[str] = field(default_factory=list)
    cited_urls: List[str] = field(default_factory=list)
    support_status: ClaimSupportStatus = ClaimSupportStatus.UNVERIFIED_CITATION
    support_score: float = 0.0
    evidence_excerpt: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "statement": self.statement,
            "cited_chunk_ids": self.cited_chunk_ids,
            "cited_urls": self.cited_urls,
            "support_status": self.support_status.value,
            "support_score": self.support_score,
            "evidence_excerpt": self.evidence_excerpt,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FactualClaim":
        return cls(
            statement=data.get("statement", ""),
            cited_chunk_ids=data.get("cited_chunk_ids", []),
            cited_urls=data.get("cited_urls", []),
            support_status=ClaimSupportStatus(
                data.get("support_status", ClaimSupportStatus.UNVERIFIED_CITATION.value)
            ),
            support_score=float(data.get("support_score", 0.0)),
            evidence_excerpt=data.get("evidence_excerpt"),
        )


@dataclass
class GroundedExplanation:
    """
    Grounded explanation of Phase 3 eligibility evaluation.
    CRITICAL CONTRACT:
    authoritative_decision wraps Phase 3 RuleStatus and cannot be altered by LLM text.
    If generated text contradicts the decision, the text is rejected and template fallback is used.
    """
    authoritative_decision: str  # Must match Phase 3 RuleStatus: PASS, FAIL, UNKNOWN, REVIEW
    scheme_id: str
    answer: str
    claims: List[FactualClaim] = field(default_factory=list)
    supporting_chunk_ids: List[str] = field(default_factory=list)
    supporting_source_urls: List[str] = field(default_factory=list)
    decision_reference: Dict[str, Any] = field(default_factory=dict)
    passed_rules: List[str] = field(default_factory=list)
    failed_rules: List[str] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)  # Authoritatively AST-derived
    conflicted_fields: List[str] = field(default_factory=list)
    uncertainty_notes: List[str] = field(default_factory=list)
    review_required: bool = False
    rejection_fallback_used: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "authoritative_decision": self.authoritative_decision,
            "scheme_id": self.scheme_id,
            "answer": self.answer,
            "claims": [c.to_dict() for c in self.claims],
            "supporting_chunk_ids": self.supporting_chunk_ids,
            "supporting_source_urls": self.supporting_source_urls,
            "decision_reference": self.decision_reference,
            "passed_rules": self.passed_rules,
            "failed_rules": self.failed_rules,
            "missing_fields": self.missing_fields,
            "conflicted_fields": self.conflicted_fields,
            "uncertainty_notes": self.uncertainty_notes,
            "review_required": self.review_required,
            "rejection_fallback_used": self.rejection_fallback_used,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GroundedExplanation":
        claims = [
            FactualClaim.from_dict(c) if isinstance(c, dict) else c
            for c in data.get("claims", [])
        ]
        return cls(
            authoritative_decision=data.get("authoritative_decision", "UNKNOWN"),
            scheme_id=data.get("scheme_id", ""),
            answer=data.get("answer", ""),
            claims=claims,
            supporting_chunk_ids=data.get("supporting_chunk_ids", []),
            supporting_source_urls=data.get("supporting_source_urls", []),
            decision_reference=data.get("decision_reference", {}),
            passed_rules=data.get("passed_rules", []),
            failed_rules=data.get("failed_rules", []),
            missing_fields=data.get("missing_fields", []),
            conflicted_fields=data.get("conflicted_fields", []),
            uncertainty_notes=data.get("uncertainty_notes", []),
            review_required=bool(data.get("review_required", False)),
            rejection_fallback_used=bool(data.get("rejection_fallback_used", False)),
        )


@dataclass
class LLMMetadata:
    """Operational telemetry and auditing metadata for LLM calls."""
    provider: str
    model: str
    operation: str
    latency_ms: float
    success: bool = True
    tokens_used: Optional[int] = None
    error_code: Optional[str] = None
    request_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "operation": self.operation,
            "latency_ms": self.latency_ms,
            "success": self.success,
            "tokens_used": self.tokens_used,
            "error_code": self.error_code,
            "request_id": self.request_id,
        }
