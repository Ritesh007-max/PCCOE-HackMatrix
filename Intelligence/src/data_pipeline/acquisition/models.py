"""
FIN Data Acquisition & Knowledge Base Entity Models.
Defines versioned, immutable, traceable schemas for multi-tier government policy acquisition.
Implements the 7-tier authority hierarchy and complete provenance metadata.
"""

from dataclasses import dataclass, field as dc_field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional
import hashlib
import json
import uuid


class AuthorityTierName(str, Enum):
    """
    Authoritative 7-Tier Hierarchy:
    TIER 0: Legal / Statutory Acts, Gazettes, Rules (egazette.gov.in, indiacode.nic.in)
    TIER 1: First-Party Ministry/Department Operational Portals
    TIER 2: myScheme Discovery & Normalization Platform
    TIER 3: National Official Government Portals (india.gov.in)
    TIER 4: Official Government Publications (PIB, press releases)
    TIER 5: Supplementary Datasets (HuggingFace, Kaggle, benchmarks - NEVER statutory truth)
    TIER 6: Untrusted External Sources / Blogs / Arbitrary Domains
    """
    TIER_0_LEGAL_STATUTORY = "TIER_0_LEGAL_STATUTORY"
    TIER_1_FIRST_PARTY_OPERATIONAL = "TIER_1_FIRST_PARTY_OPERATIONAL"
    TIER_2_MYSCHEME = "TIER_2_MYSCHEME"
    TIER_3_NATIONAL_OFFICIAL = "TIER_3_NATIONAL_OFFICIAL"
    TIER_4_OFFICIAL_PUBLICATION = "TIER_4_OFFICIAL_PUBLICATION"
    TIER_5_SUPPLEMENTARY = "TIER_5_SUPPLEMENTARY"
    TIER_6_UNTRUSTED = "TIER_6_UNTRUSTED"

    @property
    def rank(self) -> int:
        ranks = {
            AuthorityTierName.TIER_0_LEGAL_STATUTORY: 10,
            AuthorityTierName.TIER_1_FIRST_PARTY_OPERATIONAL: 8,
            AuthorityTierName.TIER_2_MYSCHEME: 6,
            AuthorityTierName.TIER_3_NATIONAL_OFFICIAL: 5,
            AuthorityTierName.TIER_4_OFFICIAL_PUBLICATION: 4,
            AuthorityTierName.TIER_5_SUPPLEMENTARY: 2,
            AuthorityTierName.TIER_6_UNTRUSTED: 0,
        }
        return ranks.get(self, 0)


class DetailStatus(str, Enum):
    FULL_DETAIL = "FULL_DETAIL"
    PARTIAL_DETAIL = "PARTIAL_DETAIL"
    CATALOG_ONLY = "CATALOG_ONLY"
    FAILED = "FAILED"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    REMOVED_ON_PORTAL = "REMOVED_ON_PORTAL"
    UNKNOWN = "UNKNOWN"


class ProvenanceStatus(str, Enum):
    LIVE_ACQUIRED = "LIVE_ACQUIRED"
    LIVE_REVALIDATED = "LIVE_REVALIDATED"
    REUSED_HISTORICAL = "REUSED_HISTORICAL"
    REUSED_BASELINE = "REUSED_BASELINE"
    NOT_LIVE_VERIFIED = "NOT_LIVE_VERIFIED"


class QueueStatus(str, Enum):
    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    DETAIL_FETCHED = "DETAIL_FETCHED"
    DETAIL_VALIDATED = "DETAIL_VALIDATED"
    PARTIAL_DETAIL = "PARTIAL_DETAIL"
    DOCUMENTS_FETCHED = "DOCUMENTS_FETCHED"
    FAQS_FETCHED = "FAQS_FETCHED"
    LANGUAGES_FETCHED = "LANGUAGES_FETCHED"
    NORMALIZED = "NORMALIZED"
    RAG_INDEXED = "RAG_INDEXED"
    COMPLETE = "COMPLETE"
    RETRY_PENDING = "RETRY_PENDING"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class EndpointType(str, Enum):
    CATALOGUE = "CATALOGUE"
    TAXONOMY = "TAXONOMY"
    DETAIL = "DETAIL"
    DOCUMENT = "DOCUMENT"
    FAQ = "FAQ"
    MULTILINGUAL = "MULTILINGUAL"
    OTHER = "OTHER"


class SchemeStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUPERSEDED = "SUPERSEDED"
    EXPIRED = "EXPIRED"
    REMOVED = "REMOVED"
    UNKNOWN = "UNKNOWN"


class RelationshipType(str, Enum):
    PARENT_OF = "PARENT_OF"
    COMPONENT_OF = "COMPONENT_OF"
    SUPERSEDES = "SUPERSEDED"
    SUPERSEDED_BY = "SUPERSEDED_BY"
    RENAMED_TO = "RENAMED_TO"
    MERGED_INTO = "MERGED_INTO"
    RELATED_TO = "RELATED_TO"


class ConflictResolutionStatus(str, Enum):
    RESOLVED = "RESOLVED"
    REVIEW = "REVIEW"
    CONFLICTED = "CONFLICTED"
    UNRESOLVED = "UNRESOLVED"


class ValidationSeverity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    REVIEW = "REVIEW"


@dataclass
class SourceEvidence:
    """Every extracted fact retains immutable evidence and provenance."""
    evidence_id: str
    source_id: str
    source_url: str
    source_domain: str
    authority_tier: str
    raw_text: str
    evidence_span: Optional[str] = None
    fetched_at: Optional[str] = None
    content_hash: Optional[str] = None
    extraction_confidence: float = 1.0


@dataclass
class EligibilityCriterion:
    """Statutory eligibility rule with both raw text and normalized condition."""
    criterion_id: str
    field: str
    operator: str
    value: Any
    unit: Optional[str] = None
    raw_text: str = ""
    normalized_condition: Dict[str, Any] = dc_field(default_factory=dict)
    source_id: str = "myscheme"
    source_url: str = ""
    authority_tier: str = AuthorityTierName.TIER_2_MYSCHEME.value
    effective_from: Optional[str] = None
    extraction_confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Benefit:
    """Structured benefit specification."""
    benefit_id: str
    benefit_type: str  # Cash, In-Kind, Subsidy, Composite
    raw_text: str
    monetary_benefit: Optional[float] = None
    percentage_subsidy: Optional[float] = None
    fixed_subsidy: Optional[float] = None
    benefit_frequency: Optional[str] = None
    benefit_duration: Optional[str] = None
    formula: Optional[str] = None
    caps: Optional[str] = None
    exclusions: Optional[str] = None
    source_url: str = ""
    authority_tier: str = AuthorityTierName.TIER_2_MYSCHEME.value

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RequiredDocument:
    """Identity or procedural supporting evidence document."""
    document_id: str
    document_name: str
    is_mandatory: bool = True
    document_type: str = "Certificate"
    issuing_authority: Optional[str] = None
    raw_text: str = ""
    source_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ApplicationStep:
    """Single step in the official application procedure."""
    step_number: int
    title: str
    description: str
    mode: str = "Online"
    url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FAQ:
    """Frequently asked question tied to scheme and section."""
    faq_id: str
    question: str
    answer: str
    language: str = "en"
    source_url: str = ""
    source_section: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SchemeRelationship:
    """Typed relationship in the umbrella / component scheme graph."""
    source_scheme_id: str
    target_scheme_id: str
    relationship_type: RelationshipType
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_scheme_id": self.source_scheme_id,
            "target_scheme_id": self.target_scheme_id,
            "relationship_type": self.relationship_type.value,
            "description": self.description,
        }


@dataclass
class SchemeAlias:
    """Acronym, alternate name, or translated identifier."""
    canonical_scheme_id: str
    alias: str
    alias_type: str  # "acronym", "former_name", "alternate_spelling", "translation"
    language: str = "en"


@dataclass
class Authority:
    """Government authority governing or implementing a scheme."""
    authority_id: str
    name: str
    level: str  # Central, State, UT, Local
    ministry: Optional[str] = None
    department: Optional[str] = None
    domain: Optional[str] = None
    authority_tier: str = AuthorityTierName.TIER_1_FIRST_PARTY_OPERATIONAL.value


@dataclass
class PolicyDocument:
    """First-party statutory document, gazette, guideline PDF, or circular."""
    document_url: str
    document_type: str  # "Guideline", "Gazette", "Circular", "Form", "FAQ"
    source_domain: str
    title: str
    fetched_at: str
    content_hash: str
    mime_type: str = "application/pdf"
    publication_date: Optional[str] = None
    effective_date: Optional[str] = None
    language: str = "en"
    scheme_id: Optional[str] = None
    authority_tier: str = AuthorityTierName.TIER_0_LEGAL_STATUTORY.value
    extraction_status: str = "DISCOVERED"  # DISCOVERED, DOWNLOADED, EXTRACTED, FAILED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LanguageVariant:
    """Multilingual manifestation of scheme metadata."""
    scheme_id: str
    language: str
    original_name: str
    original_text: str
    source_url: str
    fetched_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Scheme:
    """
    Exhaustive Normalized Government Scheme Entity.
    Retains complete provenance, full eligibility conditions, and statutory links.
    """
    # IDENTITY
    scheme_id: str
    canonical_slug: str
    scheme_name: str
    alternate_names: List[str] = dc_field(default_factory=list)
    local_names: Dict[str, str] = dc_field(default_factory=dict)
    scheme_type: str = "Central Sector"
    scheme_status: SchemeStatus = SchemeStatus.ACTIVE

    # AUTHORITY
    ministry: Optional[str] = None
    department: Optional[str] = None
    implementing_agency: Optional[str] = None
    central_or_state: str = "Central"
    state_or_ut: Optional[str] = None
    sponsoring_authority: Optional[str] = None
    nodal_department: Optional[str] = None

    # CLASSIFICATION
    category: str = "Social welfare & Empowerment"
    subcategory: Optional[str] = None
    tags: List[str] = dc_field(default_factory=list)
    sectors: List[str] = dc_field(default_factory=list)
    beneficiary_groups: List[str] = dc_field(default_factory=list)

    # CONTENT
    brief_description: str = ""
    detailed_description: str = ""

    # ELIGIBILITY
    eligibility_criteria: List[EligibilityCriterion] = dc_field(default_factory=list)
    raw_eligibility_text: str = ""

    # BENEFITS
    benefits: List[Benefit] = dc_field(default_factory=list)
    raw_benefits_text: str = ""

    # APPLICATION
    application_mode: List[str] = dc_field(default_factory=lambda: ["Online"])
    application_steps: List[ApplicationStep] = dc_field(default_factory=list)
    application_portal: Optional[str] = None
    application_url: Optional[str] = None
    implementing_office: Optional[str] = None
    submission_method: Optional[str] = None
    verification_process: Optional[str] = None
    approval_process: Optional[str] = None

    # DOCUMENTS
    required_documents: List[RequiredDocument] = dc_field(default_factory=list)
    raw_documents_text: str = ""

    # DEADLINES
    application_start: Optional[str] = None
    application_end: Optional[str] = None
    recurring_deadline: Optional[str] = None
    academic_year: Optional[str] = None
    financial_year: Optional[str] = None
    benefit_period: Optional[str] = None
    deadline_notes: Optional[str] = None

    # FAQS
    faqs: List[FAQ] = dc_field(default_factory=list)

    # SOURCE INFORMATION
    myscheme_url: Optional[str] = None
    official_scheme_url: Optional[str] = None
    official_application_url: Optional[str] = None
    official_guideline_url: Optional[str] = None
    official_pdf_urls: List[str] = dc_field(default_factory=list)
    gazette_url: Optional[str] = None
    notification_url: Optional[str] = None
    ministry_url: Optional[str] = None
    department_url: Optional[str] = None

    # TEMPORAL
    published_at: Optional[str] = None
    effective_from: Optional[str] = None
    effective_until: Optional[str] = None
    last_updated: Optional[str] = None
    fetched_at: str = ""
    source_last_updated: Optional[str] = None
    content_hash: str = ""

    # PROVENANCE
    source_id: str = "myscheme"
    source_url: str = ""
    source_domain: str = "www.myscheme.gov.in"
    authority_tier: str = AuthorityTierName.TIER_2_MYSCHEME.value
    extraction_method: str = "apisetu_rest"
    parser_version: str = "2.0.0"
    ingestion_version: str = "v1"
    snapshot_id: str = ""
    acquisition_run_id: str = ""
    detail_status: str = DetailStatus.CATALOG_ONLY.value
    provenance_status: str = ProvenanceStatus.NOT_LIVE_VERIFIED.value
    provenance_envelope: Optional[Dict[str, Any]] = None

    # RELATIONSHIPS & MULTILINGUAL
    relationships: List[SchemeRelationship] = dc_field(default_factory=list)
    language_variants: List[LanguageVariant] = dc_field(default_factory=list)

    def compute_content_hash(self) -> str:
        """Deterministic SHA256 of immutable scheme facts."""
        payload = {
            "slug": self.canonical_slug,
            "name": self.scheme_name,
            "ministry": self.ministry,
            "state": self.state_or_ut,
            "category": self.category,
            "eligibility": [c.to_dict() for c in self.eligibility_criteria],
            "benefits": [b.to_dict() for b in self.benefits],
            "documents": [d.to_dict() for d in self.required_documents],
        }
        raw = json.dumps(payload, sort_keys=True, default=str)
        self.content_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return self.content_hash

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["scheme_status"] = self.scheme_status.value
        data["relationships"] = [r.to_dict() for r in self.relationships]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Scheme":
        d = dict(data)
        st_val = d.get("scheme_status", SchemeStatus.ACTIVE.value)
        if isinstance(st_val, str):
            try:
                d["scheme_status"] = SchemeStatus(st_val)
            except Exception:
                d["scheme_status"] = SchemeStatus.ACTIVE
        if "required_documents" in d and isinstance(d["required_documents"], list):
            d["required_documents"] = [
                RequiredDocument(**rd) if isinstance(rd, dict) else rd
                for rd in d["required_documents"]
            ]
        if "benefits" in d and isinstance(d["benefits"], list):
            d["benefits"] = [
                Benefit(**b) if isinstance(b, dict) else b
                for b in d["benefits"]
            ]
        if "eligibility_criteria" in d and isinstance(d["eligibility_criteria"], list):
            d["eligibility_criteria"] = [
                EligibilityCriterion(**ec) if isinstance(ec, dict) else ec
                for ec in d["eligibility_criteria"]
            ]
        if "application_steps" in d and isinstance(d["application_steps"], list):
            d["application_steps"] = [
                ApplicationStep(**s) if isinstance(s, dict) else s
                for s in d["application_steps"]
            ]
        if "faqs" in d and isinstance(d["faqs"], list):
            d["faqs"] = [
                FAQ(**f) if isinstance(f, dict) else f
                for f in d["faqs"]
            ]
        d.pop("relationships", None)
        d.pop("language_variants", None)
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})



@dataclass
class Conflict:
    """Explicit cross-source conflict record preserving both sides."""
    conflict_id: str
    scheme_slug: str
    field_name: str
    source_a: str
    value_a: Any
    authority_a: str
    date_a: Optional[str]
    source_b: str
    value_b: Any
    authority_b: str
    date_b: Optional[str]
    conflicting_text: str
    resolution_status: ConflictResolutionStatus = ConflictResolutionStatus.CONFLICTED
    resolved_value: Any = None
    notes: Optional[str] = None
    detected_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["resolution_status"] = self.resolution_status.value
        return data


@dataclass
class CrawlFailure:
    """Auditable log of failed requests during acquisition."""
    url: str
    scheme_id: Optional[str]
    http_status: Optional[int]
    error_type: str
    retry_count: int
    first_failure: str
    latest_failure: str
    reason: str
    next_action: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HttpRequestRecord:
    """Instrumented network request log entry."""
    request_id: str
    endpoint: str
    method: str = "GET"
    run_id: str = ""
    scheme_id: Optional[str] = None
    slug: Optional[str] = None
    endpoint_type: str = EndpointType.OTHER.value
    batch_id: Optional[str] = None
    batch_size: int = 1
    page: Optional[int] = None
    language: str = "en"
    response_size: int = 0
    status_code: Optional[int] = None
    latency_ms: float = 0.0
    retry_count: int = 0
    success: bool = True
    timestamp: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LiveProvenanceEnvelope:
    """Exact scheme-level live provenance envelope."""
    acquisition_run_id: str
    scheme_id: str
    slug: str
    source: str = "myscheme"
    source_url: str = ""
    source_endpoint: str = ""
    acquisition_mode: str = "LIVE"
    retrieval_timestamp: str = ""
    http_status: int = 200
    response_hash: str = ""
    raw_artifact: str = ""
    normalization_version: str = "1.0"
    snapshot_id: str = ""
    detail_status: str = DetailStatus.FULL_DETAIL.value

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AcquisitionQueueItem:
    """Persistent queue/checkpoint entry for resumable scheme acquisition."""
    acquisition_id: str
    scheme_id: str
    slug: str
    status: str = QueueStatus.QUEUED.value
    attempts: int = 0
    last_attempt: Optional[str] = None
    next_retry: Optional[str] = None
    detail_status: str = DetailStatus.CATALOG_ONLY.value
    document_status: str = "NOT_AVAILABLE"
    faq_status: str = "NOT_AVAILABLE"
    language_status: str = "NOT_AVAILABLE"
    provenance_status: str = ProvenanceStatus.NOT_LIVE_VERIFIED.value
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SchemeAcquisitionEntry:
    """Detailed status entry for every scheme in the catalogue ledger."""
    scheme_id: str
    slug: str
    name: str = ""
    catalogue_status: str = "DISCOVERED"
    detail_status: str = DetailStatus.CATALOG_ONLY.value
    live_verified: bool = False
    detail_source: str = "myscheme"
    documents_status: str = "NOT_AVAILABLE"
    faq_status: str = "NOT_AVAILABLE"
    language_status: str = "NOT_AVAILABLE"
    normalized_status: str = "PENDING"
    rag_status: str = "NOT_INDEXED"
    source_url: str = ""
    acquisition_run_id: str = ""
    fetched_at: str = ""
    content_hash: str = ""
    provenance_status: str = ProvenanceStatus.NOT_LIVE_VERIFIED.value
    error: Optional[str] = None
    scheme_name: Optional[str] = None
    faqs_status: Optional[str] = None
    languages_status: Optional[str] = None

    def __post_init__(self):
        if self.scheme_name and not self.name:
            self.name = self.scheme_name
        elif self.name and not self.scheme_name:
            self.scheme_name = self.name

        if self.faqs_status and self.faq_status == "NOT_AVAILABLE":
            self.faq_status = self.faqs_status
        elif self.faq_status and not self.faqs_status:
            self.faqs_status = self.faq_status

        if self.languages_status and self.language_status == "NOT_AVAILABLE":
            self.language_status = self.languages_status
        elif self.language_status and not self.languages_status:
            self.languages_status = self.language_status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scheme_id": self.scheme_id,
            "slug": self.slug,
            "name": self.name or self.scheme_name or "",
            "scheme_name": self.name or self.scheme_name or "",
            "catalogue_status": self.catalogue_status,
            "detail_status": self.detail_status,
            "live_verified": self.live_verified,
            "detail_source": self.detail_source,
            "documents_status": self.documents_status,
            "faq_status": self.faq_status or self.faqs_status or "NOT_AVAILABLE",
            "faqs_status": self.faq_status or self.faqs_status or "NOT_AVAILABLE",
            "language_status": self.language_status or self.languages_status or "NOT_AVAILABLE",
            "languages_status": self.language_status or self.languages_status or "NOT_AVAILABLE",
            "normalized_status": self.normalized_status,
            "rag_status": self.rag_status,
            "source_url": self.source_url,
            "acquisition_run_id": self.acquisition_run_id,
            "fetched_at": self.fetched_at,
            "content_hash": self.content_hash,
            "provenance_status": self.provenance_status,
            "error": self.error,
        }


@dataclass
class CrawlJob:
    """Execution metadata and performance ledger for an acquisition run."""
    crawl_job_id: str
    started_at: str
    completed_at: Optional[str] = None
    portal_version: str = "myscheme-nextjs-v6"

    # Master Catalogue Metrics
    portal_catalogue_count: int = 5108
    catalogue_discovered_count: int = 5108
    portal_reported_scheme_count: int = 5108
    discovered_scheme_count: int = 5108

    # Explicit Detail Stage Metrics
    detail_discovered_count: int = 0
    detail_attempted_count: int = 0
    detail_success_count: int = 0
    detail_failed_count: int = 0
    detail_missing_count: int = 0
    full_detail_count: int = 0
    partial_detail_count: int = 0
    catalogue_only_count: int = 0

    # Sub-Resource Metrics
    documents_attempted_count: int = 0
    documents_success_count: int = 0
    faq_attempted_count: int = 0
    faq_success_count: int = 0
    multilingual_attempted_count: int = 0
    multilingual_success_count: int = 0

    # Normalized & Snapshot & RAG Metrics
    normalized_scheme_count: int = 0
    snapshot_scheme_count: int = 0
    rag_scheme_count: int = 0

    # General Numerical Ledger Fields
    successfully_fetched_count: int = 0
    failed_fetch_count: int = 0
    duplicate_count: int = 0
    categories_count: int = 0
    states_count: int = 0
    ministries_count: int = 0
    faqs_count: int = 0
    documents_count: int = 0
    application_links_count: int = 0
    official_source_links_count: int = 0
    languages_count: int = 0

    # Reconciled Conflict Metrics
    conflicts_detected: int = 0
    conflicts_resolved: int = 0
    conflicts_pending_review: int = 0
    conflicts_closed: int = 0
    conflicts_in_active_policy: int = 0
    unresolved_conflict_count: int = 0
    unresolved_conflicts: int = 0

    # Network Metrics
    total_requests: int = 0
    avg_latency_ms: float = 0.0
    retry_count: int = 0
    coverage_percentage: float = 0.0
    validation_errors: int = 0
    validation_warnings: int = 0
    unresolved_records: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PolicyVersion:
    """Immutable policy snapshot tracking point-in-time validity."""
    version_id: str
    snapshot_hash: str
    created_at: str
    effective_from: str
    effective_until: Optional[str] = None
    schemes_count: int = 0
    superseded_by: Optional[str] = None
    status: str = "ACTIVE"


@dataclass
class Source:
    """Registered source in the acquisition graph."""
    source_id: str
    name: str
    domain: str
    authority_tier: AuthorityTierName
    is_active: bool = True
    discovered_at: str = ""
    last_fetched_at: Optional[str] = None
