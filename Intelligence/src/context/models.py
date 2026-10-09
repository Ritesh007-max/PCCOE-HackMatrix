"""
FIN Canonical Applicant and Document Context Models.
Represents the unified, evidence-backed applicant state consumed by
downstream Intelligence layers (Retrieval, Rules, Benefit Calculation, Chat).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Union
import uuid
import re

from src.extraction.models import (
    ApplicantFact,
    Evidence,
    FactSourceType,
    FactVerificationStatus,
    ExtractionMethod,
    CANONICAL_PROFILE_FIELDS,
)
from src.rules.models import ApplicantProfile
from src.documents.models import DocumentContent


@dataclass
class DocumentContext:
    """
    Structured understanding of an individual ingested citizen document.
    Binds the physical file, OCR blocks, extracted facts, and provenance evidence.
    """
    document_id: str
    applicant_id: str
    document_type: str
    document_hash: str
    file_name: str
    file_path: Optional[str] = None
    mime_type: Optional[str] = None
    page_count: int = 1
    extraction_status: str = "VALID"
    is_scanned: bool = False
    extraction_method: str = "NATIVE_PDF"
    extracted_facts: List[ApplicantFact] = field(default_factory=list)
    evidence: List[Evidence] = field(default_factory=list)
    raw_text: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    version: str = "1.0"

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "applicant_id": self.applicant_id,
            "document_type": self.document_type,
            "document_hash": self.document_hash,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "mime_type": self.mime_type,
            "page_count": self.page_count,
            "extraction_status": self.extraction_status,
            "is_scanned": self.is_scanned,
            "extraction_method": self.extraction_method,
            "extracted_facts": [f.to_dict() for f in self.extracted_facts],
            "evidence": [e.to_dict() for e in self.evidence],
            "raw_text": self.raw_text[:4000] if self.raw_text else None,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentContext":
        facts = [
            ApplicantFact.from_dict(f) if isinstance(f, dict) else f
            for f in data.get("extracted_facts", [])
        ]
        evidence = [
            Evidence.from_dict(e) if isinstance(e, dict) else e
            for e in data.get("evidence", [])
        ]
        return cls(
            document_id=data["document_id"],
            applicant_id=data.get("applicant_id", "default_applicant"),
            document_type=data.get("document_type", "UNKNOWN_DOCUMENT"),
            document_hash=data.get("document_hash") or data.get("sha256", ""),
            file_name=data.get("file_name", "unnamed_document"),
            file_path=data.get("file_path"),
            mime_type=data.get("mime_type"),
            page_count=int(data.get("page_count", 1)),
            extraction_status=data.get("extraction_status") or data.get("status", "VALID"),
            is_scanned=bool(data.get("is_scanned", False)),
            extraction_method=data.get("extraction_method", "NATIVE_PDF"),
            extracted_facts=facts,
            evidence=evidence,
            raw_text=data.get("raw_text"),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at"),
            version=data.get("version", "1.0"),
        )

    @classmethod
    def from_document_content(
        cls,
        doc_content: DocumentContent,
        applicant_id: str,
        facts: Optional[List[ApplicantFact]] = None,
        evidence: Optional[List[Evidence]] = None,
    ) -> "DocumentContext":
        """Converts an ingested DocumentContent into a structured DocumentContext."""
        doc_type = (
            doc_content.document_type.value
            if hasattr(doc_content.document_type, "value")
            else str(doc_content.document_type)
        )
        ext_method = (
            doc_content.extraction_method.value
            if hasattr(doc_content.extraction_method, "value")
            else str(doc_content.extraction_method)
        )
        status_val = (
            doc_content.status.value
            if hasattr(doc_content.status, "value")
            else str(doc_content.status)
        )
        return cls(
            document_id=doc_content.document_id,
            applicant_id=applicant_id,
            document_type=doc_type,
            document_hash=doc_content.sha256,
            file_name=doc_content.file_name,
            file_path=doc_content.file_path,
            mime_type=doc_content.mime_type,
            page_count=doc_content.page_count,
            extraction_status=status_val,
            is_scanned=doc_content.is_scanned,
            extraction_method=ext_method,
            extracted_facts=facts or [],
            evidence=evidence or [],
            raw_text=doc_content.get_full_text(),
            metadata=dict(doc_content.metadata),
        )


SYSTEM_METADATA_KEYS = {
    "id", "user_id", "applicant_id",
    "created_at", "updated_at", "uploaded_at",
    "createdAt", "updatedAt", "uploadedAt",
    "status", "verification_status", "role",
    "password_hash", "email_confirmed_at",
}


@dataclass
class ApplicantContext:
    """
    Canonical consolidated context of an applicant.
    Aggregates profile, document-extracted, user-provided, and system-inferred facts.
    Maintains full provenance ledger, conflict states, and deterministic bridge to RuleEvaluator.
    """
    applicant_id: str
    canonical_facts: Dict[str, ApplicantFact] = field(default_factory=dict)
    all_facts: List[ApplicantFact] = field(default_factory=list)
    evidence: List[Evidence] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    conflict_details: Dict[str, List[ApplicantFact]] = field(default_factory=dict)
    documents: List[DocumentContext] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    version: str = "1.0"

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        # Auto-reconcile facts if all_facts is provided and canonical_facts is empty
        if self.all_facts and not self.canonical_facts:
            self._reconcile_all_facts()

    def add_fact(self, fact: ApplicantFact, evidence_record: Optional[Evidence] = None) -> None:
        """Adds a fact and associated evidence, triggering conflict detection."""
        if not fact.field or fact.field in SYSTEM_METADATA_KEYS:
            return
        fact.applicant_id = self.applicant_id
        if fact.source_type == FactSourceType.PROFILE:
            # Latest authoritative profile declaration supersedes prior profile records and informal user inputs
            self.all_facts = [
                f for f in self.all_facts
                if not (f.field == fact.field and f.source_type in (FactSourceType.PROFILE, FactSourceType.USER_INPUT))
            ]
        self.all_facts.append(fact)
        if evidence_record:
            evidence_record.applicant_id = self.applicant_id
            evidence_record.applicant_fact_id = fact.id
            self.evidence.append(evidence_record)
        self._reconcile_field(fact.field)

    def _reconcile_all_facts(self) -> None:
        """Reconciles all fields from the full fact list."""
        fields: Set[str] = {f.field for f in self.all_facts if f.field not in SYSTEM_METADATA_KEYS}
        for f in fields:
            self._reconcile_field(f)

    def _reconcile_field(self, field_name: str) -> None:
        """
        Reconciles facts for a single field across documents and sources.
        Enforces:
        - Discordant normalized values -> CONFLICTED status (never guess or average).
        - Corroborating normalized values -> highest verification tier chosen.
        """
        if not field_name or field_name in SYSTEM_METADATA_KEYS:
            self.canonical_facts.pop(field_name, None)
            if field_name in self.conflicts:
                self.conflicts.remove(field_name)
            self.conflict_details.pop(field_name, None)
            return

        facts = [f for f in self.all_facts if f.field == field_name]
        if not facts:
            self.canonical_facts.pop(field_name, None)
            if field_name in self.conflicts:
                self.conflicts.remove(field_name)
            self.conflict_details.pop(field_name, None)
            return

        # Check if there is an explicit human resolution fact
        resolved_facts = [
            f for f in facts 
            if f.metadata and (f.metadata.get("resolved_from_conflict") or f.metadata.get("is_authoritative"))
        ]
        if resolved_facts:
            authoritative = resolved_facts[-1]
            if field_name in self.conflicts:
                self.conflicts.remove(field_name)
            self.conflict_details.pop(field_name, None)
            self.canonical_facts[field_name] = authoritative
            return

        # If an authoritative authenticated PROFILE declaration exists and there are no DOCUMENT facts,
        # the profile declaration is authoritative over informal user inputs.
        has_profile = any(f.source_type == FactSourceType.PROFILE for f in facts)
        has_document = any(f.source_type == FactSourceType.DOCUMENT for f in facts)
        if has_profile and not has_document:
            profile_facts = [f for f in facts if f.source_type == FactSourceType.PROFILE]
            self.canonical_facts[field_name] = profile_facts[-1]
            if field_name in self.conflicts:
                self.conflicts.remove(field_name)
            self.conflict_details.pop(field_name, None)
            return

        # Check for explicit conflicted status
        distinct_values: List[Any] = []
        for f in facts:
            val = f.normalized_value
            if val is not None:
                matches = any(self._values_match(val, existing) for existing in distinct_values)
                if not matches:
                    distinct_values.append(val)

        if len(distinct_values) > 1:
            # Discordant evidence -> CONFLICT
            if field_name not in self.conflicts:
                self.conflicts.append(field_name)
            self.conflicts.sort()
            for f in facts:
                f.verification_status = FactVerificationStatus.CONFLICTED
            self.conflict_details[field_name] = facts

            # Build a consolidated representation marked CONFLICTED
            first = facts[0]
            consolidated = ApplicantFact(
                id=f"conflict_{field_name}",
                applicant_id=self.applicant_id,
                field=field_name,
                value=[f.value for f in facts],
                normalized_value=None,
                data_type=first.data_type,
                confidence=min(f.confidence for f in facts),
                source_document=", ".join(sorted({f.source_document for f in facts})),
                page_number=None,
                text_span=None,
                extraction_method="MULTI_SOURCE_CONSOLIDATION",
                verification_status=FactVerificationStatus.CONFLICTED,
                metadata={"conflicting_values": [f.to_dict() for f in facts]},
            )
            self.canonical_facts[field_name] = consolidated
        else:
            # Consistent or single-fact evidence
            if field_name in self.conflicts:
                self.conflicts.remove(field_name)
            self.conflict_details.pop(field_name, None)

            # Verification hierarchy: ISSUER_VERIFIED (4) > USER_CONFIRMED (3) > EXTRACTED (2) > SELF_REPORTED (1) > UNKNOWN (0)
            tier_weights = {
                FactVerificationStatus.UNKNOWN: 0,
                FactVerificationStatus.SELF_REPORTED: 1,
                FactVerificationStatus.EXTRACTED: 2,
                FactVerificationStatus.USER_CONFIRMED: 3,
                FactVerificationStatus.ISSUER_VERIFIED: 4,
            }
            # Pick highest verification tier, then highest confidence
            sorted_facts = sorted(
                facts,
                key=lambda f: (
                    tier_weights.get(f.verification_status, 0),
                    f.confidence
                ),
                reverse=True
            )
            self.canonical_facts[field_name] = sorted_facts[0]

    @staticmethod
    def _values_match(v1: Any, v2: Any) -> bool:
        """Compares normalized statutory values with floating-point tolerance and numeric normalization."""
        if v1 == v2:
            return True
        if v1 is None or v2 is None:
            return False
        # Try numeric comparison (handles 200000 vs "200000" vs 200000.0 vs "2,00,000")
        try:
            n1 = float(str(v1).replace(",", "").strip())
            n2 = float(str(v2).replace(",", "").strip())
            return abs(n1 - n2) < 1e-4
        except (ValueError, TypeError):
            pass
        if isinstance(v1, str) and isinstance(v2, str):
            s1 = v1.strip().lower()
            s2 = v2.strip().lower()
            if s1 == s2:
                return True
            # Support name formatting differences without creating false conflicts (e.g. "Dhruv" vs "Dhruv Ozha")
            t1 = [w for w in re.split(r"[\s,.\-_]+", s1) if w]
            t2 = [w for w in re.split(r"[\s,.\-_]+", s2) if w]
            if t1 and t2:
                if (all(w in t2 for w in t1) or all(w in t1 for w in t2)) and t1[0] == t2[0]:
                    return True
            return False
        return False

    def get_fact(self, field_name: str) -> Optional[ApplicantFact]:
        """Returns the canonical fact for a field, or None if missing or conflicted."""
        if field_name in self.conflicts:
            return None
        return self.canonical_facts.get(field_name)

    def get_raw_fact(self, field_name: str) -> Optional[ApplicantFact]:
        """Returns the canonical fact even if currently in conflict."""
        return self.canonical_facts.get(field_name)

    def get_value(self, field_name: str) -> Any:
        """Returns normalized value if available and not conflicted, else None."""
        fact = self.get_fact(field_name)
        return fact.normalized_value if fact else None

    def get_raw_value(self, field_name: str) -> Any:
        """Returns raw verbatim extracted value."""
        fact = self.canonical_facts.get(field_name)
        return fact.value if fact else None

    def get_evidence(self, field_name: str) -> List[Evidence]:
        """Returns all evidence records supporting a given fact field."""
        # Find fact ids associated with this field
        matching_fact_ids = {f.id for f in self.all_facts if f.field == field_name}
        return [
            e for e in self.evidence
            if e.applicant_fact_id in matching_fact_ids or (e.metadata.get("field") == field_name)
        ]

    def has_conflict(self, field_name: str) -> bool:
        """Returns True if the field is in conflict."""
        return field_name in self.conflicts

    def get_facts_by_source(self, source_type: Union[FactSourceType, str]) -> List[ApplicantFact]:
        """Filters facts by their origin source type (DOCUMENT, USER_INPUT, PROFILE, etc.)."""
        target = source_type.value if hasattr(source_type, "value") else str(source_type)
        return [
            f for f in self.all_facts
            if (f.source_type.value if hasattr(f.source_type, "value") else str(f.source_type)) == target
        ]

    def to_applicant_profile(self) -> ApplicantProfile:
        """
        Bridges canonical applicant context directly to the Phase 3 RuleEvaluator.
        CRITICAL INVARIANTS:
        1. Conflicted fields are omitted from profile data and recorded in `_conflicts`,
           causing RuleEvaluator to return REVIEW (never PASS).
        2. Missing fields remain omitted, evaluating to UNKNOWN (never PASS, never FAIL).
        3. Valid canonical facts supply their deterministic normalized_value.
        """
        profile_data: Dict[str, Any] = {}
        for field_name, fact in self.canonical_facts.items():
            if field_name not in self.conflicts and fact.normalized_value is not None:
                profile_data[field_name] = fact.normalized_value

        return ApplicantProfile(
            data=profile_data,
            conflicts=sorted(list(self.conflicts))
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "applicant_id": self.applicant_id,
            "canonical_facts": {k: f.to_dict() for k, f in self.canonical_facts.items()},
            "all_facts": [f.to_dict() for f in self.all_facts],
            "evidence": [e.to_dict() for e in self.evidence],
            "conflicts": sorted(list(self.conflicts)),
            "conflict_details": {
                k: [f.to_dict() for f in fl] for k, fl in self.conflict_details.items()
            },
            "documents": [d.to_dict() for d in self.documents],
            "metadata": self.metadata,
            "created_at": self.created_at,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApplicantContext":
        all_facts = [
            ApplicantFact.from_dict(f) if isinstance(f, dict) else f
            for f in data.get("all_facts", [])
        ]
        evidence = [
            Evidence.from_dict(e) if isinstance(e, dict) else e
            for e in data.get("evidence", [])
        ]
        documents = [
            DocumentContext.from_dict(d) if isinstance(d, dict) else d
            for d in data.get("documents", [])
        ]
        canonical_facts: Dict[str, ApplicantFact] = {}
        for k, v in data.get("canonical_facts", {}).items():
            canonical_facts[k] = ApplicantFact.from_dict(v) if isinstance(v, dict) else v

        conflicts = list(data.get("conflicts", []))

        return cls(
            applicant_id=data.get("applicant_id", "default_applicant"),
            canonical_facts=canonical_facts,
            all_facts=all_facts,
            evidence=evidence,
            conflicts=conflicts,
            documents=documents,
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at"),
            version=data.get("version", "1.0"),
        )
