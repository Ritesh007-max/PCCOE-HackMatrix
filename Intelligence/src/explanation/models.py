"""
FIN Phase 21 Explanation & Guidance Domain Models.
Defines canonical contracts for policy explanation, eligibility explanation,
evidence references, policy citations, missing-information guidance, next actions,
uncertainty explanation, human review guidance, and multi-scheme comparison.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class GroundingStatus(str, Enum):
    """Overall grounding verification status for an explanation."""
    GROUNDED = "GROUNDED"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"


class ActionPriority(str, Enum):
    """Deterministic priority ranking for citizen next actions."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ActionType(str, Enum):
    """Deterministic action categories derived from workflow state."""
    RESOLVE_CONFLICT = "RESOLVE_CONFLICT"
    PROVIDE_INFORMATION = "PROVIDE_INFORMATION"
    UPLOAD_DOCUMENT = "UPLOAD_DOCUMENT"
    REVIEW_ELIGIBILITY = "REVIEW_ELIGIBILITY"
    VIEW_POLICY_SOURCE = "VIEW_POLICY_SOURCE"
    VIEW_BENEFIT = "VIEW_BENEFIT"
    CHECK_APPLICATION_STEPS = "CHECK_APPLICATION_STEPS"
    VISIT_OFFICIAL_PORTAL = "VISIT_OFFICIAL_PORTAL"
    READY_TO_APPLY = "READY_TO_APPLY"


class ReviewReasonCode(str, Enum):
    """Categories of issues requiring human caseworker review."""
    FACT_CONFLICT = "FACT_CONFLICT"
    UNSTRUCTURED_RULE = "UNSTRUCTURED_RULE"
    STATUTORY_AMBIGUITY = "STATUTORY_AMBIGUITY"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    POLICY_SOURCE_CONFLICT = "POLICY_SOURCE_CONFLICT"


class SourceAuthorityTier(str, Enum):
    """Precedence hierarchy of policy sources (Phase 19/20 contract)."""
    PRIMARY_SCHEME = "PRIMARY_SCHEME"
    PRIMARY_FAQ = "PRIMARY_FAQ"
    SUPPLEMENTARY_SCHEME = "SUPPLEMENTARY_SCHEME"
    RAG_ARCHIVE = "RAG_ARCHIVE"
    EVALUATION_ONLY = "EVALUATION_ONLY"


@dataclass
class EvidenceReference:
    """Grounding reference tying an explanation claim to verified applicant facts/documents."""
    evidence_id: str
    field: str
    value: Any
    source_type: str = "DOCUMENT"
    source_document: Optional[str] = None
    source_page: Optional[int] = None
    confidence: float = 1.0
    verification_status: str = "EXTRACTED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "field": self.field,
            "value": self.value,
            "source_type": self.source_type,
            "source_document": self.source_document,
            "source_page": self.source_page,
            "confidence": self.confidence,
            "verification_status": self.verification_status,
        }


@dataclass
class PolicyCitation:
    """Structured statutory policy citation with verified authority tier."""
    citation_id: str
    scheme_id: str
    source_id: str
    source_type: str = "PRIMARY_SCHEME"
    source_authority: str = "PRIMARY_SCHEME"
    title: str = ""
    url: Optional[str] = None
    document_id: Optional[str] = None
    page: Optional[int] = None
    section: Optional[str] = None
    text_span: Optional[str] = None
    policy_version: str = "1.0.0"
    rule_id: Optional[str] = None
    retrieval_score: Optional[float] = None
    citation_confidence: float = 1.0
    grounding_state: str = "GROUNDED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "citation_id": self.citation_id,
            "scheme_id": self.scheme_id,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "source_authority": self.source_authority,
            "title": self.title,
            "url": self.url,
            "document_id": self.document_id,
            "page": self.page,
            "section": self.section,
            "text_span": self.text_span,
            "policy_version": self.policy_version,
            "rule_id": self.rule_id,
            "retrieval_score": self.retrieval_score,
            "citation_confidence": self.citation_confidence,
            "grounding_state": self.grounding_state,
        }


@dataclass
class ReasonExplanation:
    """Grounded explanation of an individual atomic rule result from AST execution."""
    rule_id: str
    field: str
    operator: str
    applicant_value: Any
    expected_value: Any
    status: str  # PASS, FAIL, UNKNOWN, REVIEW
    hard_constraint: bool
    human_text: str
    statutory_citation: str = ""
    rule_version: str = "1.0.0"
    policy_source_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "field": self.field,
            "operator": self.operator,
            "applicant_value": self.applicant_value,
            "expected_value": self.expected_value,
            "status": self.status,
            "hard_constraint": self.hard_constraint,
            "human_text": self.human_text,
            "statutory_citation": self.statutory_citation,
            "rule_version": self.rule_version,
            "policy_source_url": self.policy_source_url,
        }


@dataclass
class EligibilityExplanation:
    """Categorized explanation of all conditions checked during statutory evaluation."""
    what_was_checked: List[str] = field(default_factory=list)
    passed_conditions: List[ReasonExplanation] = field(default_factory=list)
    failed_conditions: List[ReasonExplanation] = field(default_factory=list)
    unknown_conditions: List[ReasonExplanation] = field(default_factory=list)
    review_conditions: List[ReasonExplanation] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "what_was_checked": self.what_was_checked,
            "passed_conditions": [c.to_dict() for c in self.passed_conditions],
            "failed_conditions": [c.to_dict() for c in self.failed_conditions],
            "unknown_conditions": [c.to_dict() for c in self.unknown_conditions],
            "review_conditions": [c.to_dict() for c in self.review_conditions],
        }


@dataclass
class MissingInformationGuidance:
    """Actionable guidance for missing applicant information required by statutory criteria."""
    field: str
    reason_required: str
    affected_rule_id: Optional[str] = None
    affected_scheme_id: Optional[str] = None
    suggested_evidence_type: str = "Declaration or Certificate"
    priority: ActionPriority = ActionPriority.HIGH
    user_input_satisfiable: bool = True
    official_verification_required: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "reason_required": self.reason_required,
            "affected_rule_id": self.affected_rule_id,
            "affected_scheme_id": self.affected_scheme_id,
            "suggested_evidence_type": self.suggested_evidence_type,
            "priority": self.priority.value if hasattr(self.priority, "value") else str(self.priority),
            "user_input_satisfiable": self.user_input_satisfiable,
            "official_verification_required": self.official_verification_required,
        }


@dataclass
class HumanReviewGuidance:
    """Caseworker and citizen review details for ambiguous or conflicting conditions."""
    review_id: str
    field: Optional[str]
    reason_code: ReviewReasonCode
    source_a: Optional[str] = None
    value_a: Optional[Any] = None
    source_b: Optional[str] = None
    value_b: Optional[Any] = None
    explanation: str = ""
    suggested_resolution: str = ""
    priority: ActionPriority = ActionPriority.HIGH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "review_id": self.review_id,
            "field": self.field,
            "reason_code": self.reason_code.value if hasattr(self.reason_code, "value") else str(self.reason_code),
            "source_a": self.source_a,
            "value_a": self.value_a,
            "source_b": self.source_b,
            "value_b": self.value_b,
            "explanation": self.explanation,
            "suggested_resolution": self.suggested_resolution,
            "priority": self.priority.value if hasattr(self.priority, "value") else str(self.priority),
        }


@dataclass
class NextAction:
    """Deterministic, policy-grounded actionable step for citizen or caseworker."""
    action_id: str
    action_type: ActionType
    priority: ActionPriority
    title: str
    explanation: str
    related_field: Optional[str] = None
    related_rule: Optional[str] = None
    related_document: Optional[str] = None
    related_scheme: Optional[str] = None
    evidence_reference: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value if hasattr(self.action_type, "value") else str(self.action_type),
            "priority": self.priority.value if hasattr(self.priority, "value") else str(self.priority),
            "title": self.title,
            "explanation": self.explanation,
            "related_field": self.related_field,
            "related_rule": self.related_rule,
            "related_document": self.related_document,
            "related_scheme": self.related_scheme,
            "evidence_reference": self.evidence_reference,
        }


@dataclass
class BenefitExplanation:
    """Deterministic financial or non-financial entitlement summary."""
    status: str  # CALCULATED, CONDITIONAL, CANNOT_DETERMINE
    benefit_type: str = "DIRECT_BENEFIT_TRANSFER"
    amount: Optional[float] = None
    currency: str = "INR"
    frequency: Optional[str] = None
    disbursement_structure: str = ""
    explanation: str = ""
    source_rule: Optional[str] = None
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "benefit_type": self.benefit_type,
            "amount": self.amount,
            "currency": self.currency,
            "frequency": self.frequency,
            "disbursement_structure": self.disbursement_structure,
            "explanation": self.explanation,
            "source_rule": self.source_rule,
            "evidence": self.evidence,
        }


@dataclass
class RecommendationExplanation:
    """Explains why a scheme was retrieved and its personal fact compatibility."""
    relevance_score: float
    compatibility_score: float
    retrieval_relevance_summary: str
    compatibility_summary: str
    evidence_availability_summary: str
    separation_notice: str = (
        "Retrieval relevance and personal compatibility scores indicate candidate alignment only. "
        "They do NOT constitute statutory eligibility, which is determined independently by deterministic rules."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relevance_score": round(self.relevance_score, 4),
            "compatibility_score": round(self.compatibility_score, 4),
            "retrieval_relevance_summary": self.retrieval_relevance_summary,
            "compatibility_summary": self.compatibility_summary,
            "evidence_availability_summary": self.evidence_availability_summary,
            "separation_notice": self.separation_notice,
        }


@dataclass
class UncertaintyExplanation:
    """Explains whether and why the determination contains residual uncertainty."""
    is_uncertain: bool
    uncertainty_type: str  # NONE, MISSING_FACTS, CONFLICTING_EVIDENCE, STATUTORY_AMBIGUITY
    explanation: str
    resolution_path: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_uncertain": self.is_uncertain,
            "uncertainty_type": self.uncertainty_type,
            "explanation": self.explanation,
            "resolution_path": self.resolution_path,
        }


@dataclass
class PolicyExplanation:
    """General grounded informational summary of a government scheme."""
    scheme_id: str
    scheme_slug: str
    scheme_name: str
    summary: str
    who_is_it_for: str
    what_does_it_provide: str
    key_eligibility_criteria: List[str] = field(default_factory=list)
    required_documents: List[str] = field(default_factory=list)
    official_portal_url: Optional[str] = None
    source_authority: str = "PRIMARY_SCHEME"
    policy_version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scheme_id": self.scheme_id,
            "scheme_slug": self.scheme_slug,
            "scheme_name": self.scheme_name,
            "summary": self.summary,
            "who_is_it_for": self.who_is_it_for,
            "what_does_it_provide": self.what_does_it_provide,
            "key_eligibility_criteria": self.key_eligibility_criteria,
            "required_documents": self.required_documents,
            "official_portal_url": self.official_portal_url,
            "source_authority": self.source_authority,
            "policy_version": self.policy_version,
        }


@dataclass
class ExplanationBundle:
    """
    Authoritative Master Explanation Bundle (Phase 21 data contract).
    Integrates recommendation, deterministic eligibility, rule trace, citations,
    missing-information guidance, and next actions without mutating statutory decisions.
    """
    explanation_id: str
    applicant_id: Optional[str]
    scheme_id: str
    scheme_name: str
    eligibility_status: str  # PASS, FAIL, UNKNOWN, REVIEW
    is_eligible: Optional[bool]
    rule_version: str
    rule_set_hash: Optional[str]
    decision_id: Optional[str]

    headline: str
    summary: str

    eligibility_explanation: EligibilityExplanation
    reasons: List[str]
    missing_information: List[MissingInformationGuidance]
    conflicts: List[HumanReviewGuidance]
    evidence: List[EvidenceReference]
    policy_citations: List[PolicyCitation]
    next_actions: List[NextAction]
    review_guidance: List[HumanReviewGuidance]
    benefit_information: Optional[BenefitExplanation]
    recommendation_explanation: Optional[RecommendationExplanation]
    uncertainty_explanation: UncertaintyExplanation
    source_metadata: List[Dict[str, Any]] = field(default_factory=list)

    generated_by: str = "DETERMINISTIC_EXPLANATION_BUILDER"
    grounding_status: GroundingStatus = GroundingStatus.GROUNDED
    language: str = "en"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "explanation_id": self.explanation_id,
            "applicant_id": self.applicant_id,
            "scheme_id": self.scheme_id,
            "scheme_name": self.scheme_name,
            "eligibility_status": self.eligibility_status,
            "is_eligible": self.is_eligible,
            "rule_version": self.rule_version,
            "rule_set_hash": self.rule_set_hash,
            "decision_id": self.decision_id,
            "headline": self.headline,
            "summary": self.summary,
            "eligibility_explanation": self.eligibility_explanation.to_dict(),
            "reasons": self.reasons,
            "missing_information": [m.to_dict() for m in self.missing_information],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "evidence": [e.to_dict() for e in self.evidence],
            "policy_citations": [c.to_dict() for c in self.policy_citations],
            "next_actions": [a.to_dict() for a in self.next_actions],
            "review_guidance": [g.to_dict() for g in self.review_guidance],
            "benefit_information": self.benefit_information.to_dict() if self.benefit_information else {},
            "recommendation_explanation": (
                self.recommendation_explanation.to_dict() if self.recommendation_explanation else None
            ),
            "uncertainty_explanation": self.uncertainty_explanation.to_dict(),
            "source_metadata": self.source_metadata,
            "generated_by": self.generated_by,
            "grounding_status": self.grounding_status.value if hasattr(self.grounding_status, "value") else str(self.grounding_status),
            "language": self.language,
            "created_at": self.created_at,
        }


@dataclass
class SchemeComparisonItem:
    """Individual scheme profile in a multi-scheme comparative analysis."""
    scheme_id: str
    scheme_slug: str
    scheme_name: str
    purpose: str
    relevance_score: float
    compatibility_score: float
    eligibility_status: str
    is_eligible: Optional[bool]
    benefit_summary: str
    key_differences: List[str] = field(default_factory=list)
    missing_fields_count: int = 0
    required_documents: List[str] = field(default_factory=list)
    official_application_route: str = "ONLINE"
    source_authority: str = "PRIMARY_SCHEME"
    rule_version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scheme_id": self.scheme_id,
            "scheme_slug": self.scheme_slug,
            "scheme_name": self.scheme_name,
            "purpose": self.purpose,
            "relevance_score": round(self.relevance_score, 4),
            "compatibility_score": round(self.compatibility_score, 4),
            "eligibility_status": self.eligibility_status,
            "is_eligible": self.is_eligible,
            "benefit_summary": self.benefit_summary,
            "key_differences": self.key_differences,
            "missing_fields_count": self.missing_fields_count,
            "required_documents": self.required_documents,
            "official_application_route": self.official_application_route,
            "source_authority": self.source_authority,
            "rule_version": self.rule_version,
        }


@dataclass
class SchemeComparisonResult:
    """Objective, side-by-side comparison across candidate government schemes."""
    comparison_id: str
    applicant_id: Optional[str]
    schemes: List[SchemeComparisonItem] = field(default_factory=list)
    summary_of_differences: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "comparison_id": self.comparison_id,
            "applicant_id": self.applicant_id,
            "schemes": [s.to_dict() for s in self.schemes],
            "summary_of_differences": self.summary_of_differences,
            "created_at": self.created_at,
        }
