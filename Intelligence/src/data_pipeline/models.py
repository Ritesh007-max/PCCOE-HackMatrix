"""
FIN Phase 7 Data Pipeline Models and Enums.
Provides authoritative schemas for source registry, change detection,
content hashing, lineage, policy/rule versioning, freshness, snapshots, and synchronization audit.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class SourceType(str, Enum):
    """Supported data ingestion source types."""
    LOCAL_BASELINE = "LOCAL_BASELINE"
    LOCAL_BILINGUAL_DATASET = "LOCAL_BILINGUAL_DATASET"
    HUGGINGFACE_DATASET = "HUGGINGFACE_DATASET"
    WEB_PAGE = "WEB_PAGE"
    SITEMAP = "SITEMAP"
    PDF = "PDF"
    CSV = "CSV"
    JSON = "JSON"
    ZIP = "ZIP"


class AuthorityTier(str, Enum):
    """
    Source authority hierarchy.
    TIER_0_LEGAL_STATUTORY > TIER_1_FIRST_PARTY_OPERATIONAL > TIER_2_MYSCHEME >
    TIER_3_NATIONAL_OFFICIAL > TIER_4_OFFICIAL_PUBLICATION > TIER_5_SUPPLEMENTARY > TIER_6_UNTRUSTED
    """
    # Authoritative 7-tier statutory hierarchy
    TIER_0_LEGAL_STATUTORY = "TIER_0_LEGAL_STATUTORY"          # Legal / statutory acts, gazettes, rules (egazette.gov.in, indiacode.nic.in)
    TIER_1_FIRST_PARTY_OPERATIONAL = "TIER_1_FIRST_PARTY_OPERATIONAL" # First-party ministry/department portal
    TIER_2_MYSCHEME = "TIER_2_MYSCHEME"                        # myScheme discovery platform
    TIER_3_NATIONAL_OFFICIAL = "TIER_3_NATIONAL_OFFICIAL"      # National official portals (india.gov.in)
    TIER_4_OFFICIAL_PUBLICATION = "TIER_4_OFFICIAL_PUBLICATION"# PIB, official press releases
    TIER_5_SUPPLEMENTARY = "TIER_5_SUPPLEMENTARY"              # HuggingFace, Kaggle, research datasets
    TIER_6_UNTRUSTED = "TIER_6_UNTRUSTED"                      # Unverified external blogs, arbitrary domains

    # Backward compatibility aliases
    PRIMARY_OFFICIAL = "PRIMARY_OFFICIAL"              # Score 8: First-party ministry/department portals & gazettes
    PRIMARY_CANONICALIZED = "PRIMARY_CANONICALIZED"    # Score 6: schemes.csv & schemes_faqs.csv baseline
    SUPPLEMENTARY = "SUPPLEMENTARY"                    # Score 2: updated_data.csv, BharatSchemes, HuggingFace datasets
    ARCHIVE = "ARCHIVE"                                # Score 2: Historical archive text corpora (archive.zip)
    EVALUATION_ONLY = "EVALUATION_ONLY"                # Score 1: Synthetic/evaluation benchmark datasets
    UNTRUSTED = "UNTRUSTED"                            # Score 0: Unverified external, blog, or rejected sources

    @property
    def priority(self) -> int:
        priorities = {
            AuthorityTier.TIER_0_LEGAL_STATUTORY: 10,
            AuthorityTier.TIER_1_FIRST_PARTY_OPERATIONAL: 8,
            AuthorityTier.PRIMARY_OFFICIAL: 8,
            AuthorityTier.TIER_2_MYSCHEME: 6,
            AuthorityTier.PRIMARY_CANONICALIZED: 6,
            AuthorityTier.TIER_3_NATIONAL_OFFICIAL: 5,
            AuthorityTier.TIER_4_OFFICIAL_PUBLICATION: 4,
            AuthorityTier.TIER_5_SUPPLEMENTARY: 2,
            AuthorityTier.SUPPLEMENTARY: 2,
            AuthorityTier.ARCHIVE: 2,
            AuthorityTier.EVALUATION_ONLY: 1,
            AuthorityTier.TIER_6_UNTRUSTED: 0,
            AuthorityTier.UNTRUSTED: 0,
        }
        return priorities.get(self, 0)


class FreshnessStatus(str, Enum):
    """Freshness health states for registered sources."""
    FRESH = "FRESH"
    AGING = "AGING"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class ChangeType(str, Enum):
    """Categorized diff outcomes for change detection."""
    UNCHANGED = "UNCHANGED"
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    REMOVED = "REMOVED"
    FAILED_FETCH = "FAILED_FETCH"


class ChangeImpactType(str, Enum):
    """Fine-grained semantic impact classification for detected differences."""
    NO_CHANGE = "NO_CHANGE"
    SCHEME_ADDED = "SCHEME_ADDED"
    SCHEME_REMOVED = "SCHEME_REMOVED"
    SCHEME_UPDATED = "SCHEME_UPDATED"
    ELIGIBILITY_CHANGED = "ELIGIBILITY_CHANGED"
    BENEFIT_CHANGED = "BENEFIT_CHANGED"
    DOCUMENT_REQUIREMENT_CHANGED = "DOCUMENT_REQUIREMENT_CHANGED"
    APPLICATION_STEP_CHANGED = "APPLICATION_STEP_CHANGED"
    DEADLINE_CHANGED = "DEADLINE_CHANGED"
    SOURCE_URL_CHANGED = "SOURCE_URL_CHANGED"
    METADATA_CHANGED = "METADATA_CHANGED"
    FAQ_CHANGED = "FAQ_CHANGED"
    SUPPLEMENTARY_ONLY_CHANGE = "SUPPLEMENTARY_ONLY_CHANGE"
    RULE_AFFECTING_CHANGE = "RULE_AFFECTING_CHANGE"
    CONFLICT_DETECTED = "CONFLICT_DETECTED"


class PolicyStatus(str, Enum):
    """Statutory policy lifecycle status."""
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    WITHDRAWN = "WITHDRAWN"
    UNKNOWN = "UNKNOWN"


class ConflictResolution(str, Enum):
    """Resolution outcome for overlapping conflicting sources."""
    PRIMARY_CONFIRMED = "PRIMARY_CONFIRMED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    UNRESOLVED = "UNRESOLVED"


class SyncStatus(str, Enum):
    """Execution status of synchronization runs."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DRY_RUN = "DRY_RUN"
    SUCCEEDED = "SUCCEEDED"
    SUCCESS = "SUCCESS"  # Backward compatibility alias
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"  # Backward compatibility alias
    REJECTED = "REJECTED"
    ROLLED_BACK = "ROLLED_BACK"


@dataclass
class SourceDefinition:
    """
    Authoritative definition of an ingested source.
    Dynamic freshness does not equal statutory authority.
    """
    source_id: str
    source_name: str
    source_type: SourceType
    authority_tier: AuthorityTier
    canonical: bool = False
    url: Optional[str] = None
    fetch_method: str = "local"  # "local", "http_get", "sitemap", "huggingface"
    format: str = "csv"          # "csv", "parquet", "json", "html", "pdf", "zip"
    update_frequency_hours: int = 168  # 7 days default
    enabled: bool = True
    parser: str = "default"      # "default", "myscheme", "faq", "bharatschemes", "eligibility_eval"
    last_successful_fetch: Optional[str] = None
    last_content_hash: Optional[str] = None
    stale_after_days: int = 30
    first_party_url_field: Optional[str] = "source_url"
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "source_type": self.source_type.value,
            "authority_tier": self.authority_tier.value,
            "canonical": self.canonical,
            "url": self.url,
            "fetch_method": self.fetch_method,
            "format": self.format,
            "update_frequency_hours": self.update_frequency_hours,
            "enabled": self.enabled,
            "parser": self.parser,
            "last_successful_fetch": self.last_successful_fetch,
            "last_content_hash": self.last_content_hash,
            "stale_after_days": self.stale_after_days,
            "first_party_url_field": self.first_party_url_field,
            "notes": self.notes,
        }


@dataclass
class FieldDiff:
    """Represents an atomic field-level difference."""
    field_name: str
    old_value: Any
    new_value: Any
    is_threshold_changed: bool = False
    description: Optional[str] = None


@dataclass
class RecordDiff:
    """Represents a scheme-level difference between versions."""
    scheme_slug: str
    change_type: ChangeType
    field_diffs: List[FieldDiff] = field(default_factory=list)
    impact_flags: List[ChangeImpactType] = field(default_factory=list)
    rule_recompile_required: bool = False
    source_id: str = ""
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None

    @property
    def has_eligibility_change(self) -> bool:
        """Determines if eligibility criteria or statutory limits changed."""
        eligibility_fields = {"eligibility", "annual_family_income", "age", "exclusions", "level", "state"}
        return any(d.field_name in eligibility_fields for d in self.field_diffs)

    @property
    def has_benefits_only_change(self) -> bool:
        """Determines if only benefit descriptions or non-eligibility fields changed."""
        return len(self.field_diffs) > 0 and not self.has_eligibility_change


@dataclass
class ConflictRecord:
    """Records conflicting policy facts between overlapping sources."""
    scheme_slug: str
    field_name: str
    source_a: str
    value_a: Any
    tier_a: AuthorityTier
    source_b: str
    value_b: Any
    tier_b: AuthorityTier
    detected_at: str
    resolution_status: ConflictResolution = ConflictResolution.UNRESOLVED
    resolved_value: Any = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scheme_slug": self.scheme_slug,
            "field_name": self.field_name,
            "source_a": self.source_a,
            "value_a": self.value_a,
            "tier_a": self.tier_a.value,
            "source_b": self.source_b,
            "value_b": self.value_b,
            "tier_b": self.tier_b.value,
            "detected_at": self.detected_at,
            "resolution_status": self.resolution_status.value,
            "resolved_value": self.resolved_value,
            "notes": self.notes,
        }


@dataclass
class PolicyVersionMetadata:
    """Content/source revision version metadata for canonical schemes."""
    policy_version_id: str          # e.g., policy_9a4f21bc_20260922
    source_revision: str            # SHA256 or commit hash of source snapshot
    content_hash: str               # SHA256 of canonical scheme record
    created_at: str
    valid_from: str
    valid_until: Optional[str] = None
    published_at: Optional[str] = None
    retrieved_at: Optional[str] = None
    supersedes_version: Optional[str] = None
    status: PolicyStatus = PolicyStatus.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_version_id": self.policy_version_id,
            "source_revision": self.source_revision,
            "content_hash": self.content_hash,
            "created_at": self.created_at,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "published_at": self.published_at,
            "retrieved_at": self.retrieved_at,
            "supersedes_version": self.supersedes_version,
            "status": self.status.value,
        }


@dataclass
class RuleVersionMetadata:
    """Tracks rule AST versions tied directly to policy source versions."""
    rule_version_id: str            # e.g., rules_v1_9a4f21bc
    policy_version_id: str
    scheme_slug: str
    rule_hash: str                  # SHA256 of compiled SchemeRuleSet JSON
    extraction_timestamp: str
    source_url: Optional[str] = None
    raw_source_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_version_id": self.rule_version_id,
            "policy_version_id": self.policy_version_id,
            "scheme_slug": self.scheme_slug,
            "rule_hash": self.rule_hash,
            "extraction_timestamp": self.extraction_timestamp,
            "source_url": self.source_url,
            "raw_source_text": self.raw_source_text,
        }


@dataclass
class SyncRunMetadata:
    """Immutable audit trail for every synchronization execution."""
    sync_run_id: str
    started_at: str
    completed_at: Optional[str] = None
    status: SyncStatus = SyncStatus.DRY_RUN
    sources_attempted: List[str] = field(default_factory=list)
    sources_succeeded: List[str] = field(default_factory=list)
    sources_failed: List[str] = field(default_factory=list)
    records_added: int = 0
    records_modified: int = 0
    records_removed: int = 0
    records_unchanged: int = 0
    conflicts_detected: int = 0
    validation_failures: int = 0
    activated_version: Optional[str] = None
    rollback_version: Optional[str] = None
    dry_run: bool = False
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sync_run_id": self.sync_run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status.value,
            "sources_attempted": self.sources_attempted,
            "sources_succeeded": self.sources_succeeded,
            "sources_failed": self.sources_failed,
            "records_added": self.records_added,
            "records_modified": self.records_modified,
            "records_removed": self.records_removed,
            "records_unchanged": self.records_unchanged,
            "conflicts_detected": self.conflicts_detected,
            "validation_failures": self.validation_failures,
            "activated_version": self.activated_version,
            "rollback_version": self.rollback_version,
            "dry_run": self.dry_run,
            "notes": self.notes,
        }


@dataclass
class SyncJob:
    """Detailed operational sync job representation."""
    sync_id: str
    source_id: Optional[str] = None
    started_at: str = ""
    completed_at: Optional[str] = None
    status: SyncStatus = SyncStatus.PENDING
    previous_version: Optional[str] = None
    candidate_version: Optional[str] = None
    records_seen: int = 0
    records_added: int = 0
    records_updated: int = 0
    records_removed: int = 0
    records_unchanged: int = 0
    validation_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    activation_status: str = "PENDING"
    error_summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sync_id": self.sync_id,
            "source_id": self.source_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status.value,
            "previous_version": self.previous_version,
            "candidate_version": self.candidate_version,
            "records_seen": self.records_seen,
            "records_added": self.records_added,
            "records_updated": self.records_updated,
            "records_removed": self.records_removed,
            "records_unchanged": self.records_unchanged,
            "validation_errors": self.validation_errors,
            "warnings": self.warnings,
            "conflicts": self.conflicts,
            "activation_status": self.activation_status,
            "error_summary": self.error_summary,
        }
