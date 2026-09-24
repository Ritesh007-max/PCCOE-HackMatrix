"""
Application Case Domain Models.
Phase 10: Citizen application representation, document references, fact snapshots,
and candidate scheme evaluations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional

from .status import ApplicationStatus, ReadinessStatus, StatutoryDecision
from .exceptions import DocumentNotFoundError


def generate_application_id() -> str:
    """Generate a unique application identifier using UUID4."""
    return f"app_{uuid.uuid4().hex[:16]}"


def current_iso_timestamp() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class DocumentReference:
    """
    Metadata reference to an uploaded document.
    CRITICAL: Never stores raw file bytes to preserve memory and privacy.
    """
    document_id: str
    filename: str
    document_type: str = "UNKNOWN"
    sha256_hash: str = ""
    processing_status: str = "PENDING"  # PENDING, PROCESSED, FAILED
    provenance_refs: List[Dict[str, Any]] = field(default_factory=list)
    facts_extracted: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=current_iso_timestamp)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "document_type": self.document_type,
            "sha256_hash": self.sha256_hash,
            "processing_status": self.processing_status,
            "provenance_refs": self.provenance_refs,
            "facts_extracted": self.facts_extracted,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentReference":
        return cls(
            document_id=data["document_id"],
            filename=data["filename"],
            document_type=data.get("document_type", "UNKNOWN"),
            sha256_hash=data.get("sha256_hash", ""),
            processing_status=data.get("processing_status", "PENDING"),
            provenance_refs=data.get("provenance_refs", []),
            facts_extracted=data.get("facts_extracted", []),
            created_at=data.get("created_at", current_iso_timestamp()),
            metadata=data.get("metadata", {}),
        )


@dataclass
class FactSnapshot:
    """
    Snapshot of applicant profile facts used during evaluation.
    Answers: 'What applicant information was actually used for this decision?'
    """
    facts: Dict[str, Any] = field(default_factory=dict)
    verification_status: Dict[str, str] = field(default_factory=dict)
    evidence_references: Dict[str, List[str]] = field(default_factory=dict)
    conflicted_fields: List[str] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    snapshot_timestamp: str = field(default_factory=current_iso_timestamp)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "facts": self.facts,
            "verification_status": self.verification_status,
            "evidence_references": self.evidence_references,
            "conflicted_fields": self.conflicted_fields,
            "missing_fields": self.missing_fields,
            "snapshot_timestamp": self.snapshot_timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FactSnapshot":
        return cls(
            facts=data.get("facts", {}),
            verification_status=data.get("verification_status", {}),
            evidence_references=data.get("evidence_references", {}),
            conflicted_fields=data.get("conflicted_fields", []),
            missing_fields=data.get("missing_fields", []),
            snapshot_timestamp=data.get("snapshot_timestamp", current_iso_timestamp()),
        )


@dataclass
class SchemeEvaluation:
    """
    Candidate scheme evaluation maintaining strict separation between
    retrieval relevance and statutory eligibility outcome.
    """
    scheme_id: str
    scheme_name: str = ""
    retrieval_relevance_score: float = 0.0
    retrieval_rank: Optional[int] = None
    decision_status: StatutoryDecision = StatutoryDecision.UNKNOWN
    is_eligible: bool = False
    matched_rules: List[Dict[str, Any]] = field(default_factory=list)
    failed_rules: List[Dict[str, Any]] = field(default_factory=list)
    unknown_rules: List[Dict[str, Any]] = field(default_factory=list)
    conflicted_fields: List[str] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    benefit_summary: Optional[Dict[str, Any]] = None
    policy_snapshot_version: str = "V1"
    rule_version: str = "1.0.0"
    evaluated_at: str = field(default_factory=current_iso_timestamp)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scheme_id": self.scheme_id,
            "scheme_name": self.scheme_name,
            "retrieval_relevance_score": self.retrieval_relevance_score,
            "retrieval_rank": self.retrieval_rank,
            "decision_status": self.decision_status.value if isinstance(self.decision_status, StatutoryDecision) else str(self.decision_status),
            "is_eligible": self.is_eligible,
            "matched_rules": self.matched_rules,
            "failed_rules": self.failed_rules,
            "unknown_rules": self.unknown_rules,
            "conflicted_fields": self.conflicted_fields,
            "missing_fields": self.missing_fields,
            "benefit_summary": self.benefit_summary,
            "policy_snapshot_version": self.policy_snapshot_version,
            "rule_version": self.rule_version,
            "evaluated_at": self.evaluated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SchemeEvaluation":
        decision_raw = data.get("decision_status", StatutoryDecision.UNKNOWN.value)
        decision_enum = StatutoryDecision(decision_raw) if decision_raw in StatutoryDecision.__members__ else StatutoryDecision.UNKNOWN
        return cls(
            scheme_id=data["scheme_id"],
            scheme_name=data.get("scheme_name", ""),
            retrieval_relevance_score=float(data.get("retrieval_relevance_score", 0.0)),
            retrieval_rank=data.get("retrieval_rank"),
            decision_status=decision_enum,
            is_eligible=bool(data.get("is_eligible", False)),
            matched_rules=data.get("matched_rules", []),
            failed_rules=data.get("failed_rules", []),
            unknown_rules=data.get("unknown_rules", []),
            conflicted_fields=data.get("conflicted_fields", []),
            missing_fields=data.get("missing_fields", []),
            benefit_summary=data.get("benefit_summary"),
            policy_snapshot_version=data.get("policy_snapshot_version", "V1"),
            rule_version=data.get("rule_version", "1.0.0"),
            evaluated_at=data.get("evaluated_at", current_iso_timestamp()),
        )


@dataclass
class ApplicationCase:
    """
    Authoritative Application Case Aggregate Root for Phase 10.
    Coordinates document references, profile facts, evaluated candidate schemes,
    readiness signals, and active decision snapshot references.
    """
    application_id: str = field(default_factory=generate_application_id)
    citizen_reference: Optional[str] = None
    current_status: ApplicationStatus = ApplicationStatus.DRAFT
    documents: Dict[str, DocumentReference] = field(default_factory=dict)
    facts: FactSnapshot = field(default_factory=FactSnapshot)
    candidate_schemes: Dict[str, SchemeEvaluation] = field(default_factory=dict)
    selected_scheme_id: Optional[str] = None
    active_decision_snapshot_id: Optional[str] = None
    readiness: ReadinessStatus = ReadinessStatus.NOT_READY
    next_actions: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=current_iso_timestamp)
    updated_at: str = field(default_factory=current_iso_timestamp)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def attach_document(self, doc_ref: DocumentReference) -> None:
        """Attach a document reference to the case."""
        self.documents[doc_ref.document_id] = doc_ref
        self.updated_at = current_iso_timestamp()

    def get_document(self, document_id: str) -> DocumentReference:
        """Retrieve a document reference by ID or raise DocumentNotFoundError."""
        if document_id not in self.documents:
            raise DocumentNotFoundError(document_id, self.application_id)
        return self.documents[document_id]

    def select_scheme(self, scheme_id: str) -> None:
        """Select a scheme for targeted processing."""
        self.selected_scheme_id = scheme_id
        self.updated_at = current_iso_timestamp()

    def get_selected_evaluation(self) -> Optional[SchemeEvaluation]:
        """Return evaluation for selected scheme, or the first evaluated candidate."""
        if self.selected_scheme_id and self.selected_scheme_id in self.candidate_schemes:
            return self.candidate_schemes[self.selected_scheme_id]
        if self.candidate_schemes:
            return next(iter(self.candidate_schemes.values()))
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "application_id": self.application_id,
            "citizen_reference": self.citizen_reference,
            "current_status": self.current_status.value if isinstance(self.current_status, ApplicationStatus) else str(self.current_status),
            "documents": {k: v.to_dict() for k, v in self.documents.items()},
            "facts": self.facts.to_dict(),
            "candidate_schemes": {k: v.to_dict() for k, v in self.candidate_schemes.items()},
            "selected_scheme_id": self.selected_scheme_id,
            "active_decision_snapshot_id": self.active_decision_snapshot_id,
            "readiness": self.readiness.value if isinstance(self.readiness, ReadinessStatus) else str(self.readiness),
            "next_actions": self.next_actions,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApplicationCase":
        status_raw = data.get("current_status", ApplicationStatus.DRAFT.value)
        status_enum = ApplicationStatus(status_raw) if status_raw in ApplicationStatus.__members__ else ApplicationStatus.DRAFT

        readiness_raw = data.get("readiness", ReadinessStatus.NOT_READY.value)
        readiness_enum = ReadinessStatus(readiness_raw) if readiness_raw in ReadinessStatus.__members__ else ReadinessStatus.NOT_READY

        docs = {
            k: DocumentReference.from_dict(v)
            for k, v in data.get("documents", {}).items()
        }

        schemes = {
            k: SchemeEvaluation.from_dict(v)
            for k, v in data.get("candidate_schemes", {}).items()
        }

        facts = FactSnapshot.from_dict(data.get("facts", {}))

        return cls(
            application_id=data["application_id"],
            citizen_reference=data.get("citizen_reference"),
            current_status=status_enum,
            documents=docs,
            facts=facts,
            candidate_schemes=schemes,
            selected_scheme_id=data.get("selected_scheme_id"),
            active_decision_snapshot_id=data.get("active_decision_snapshot_id"),
            readiness=readiness_enum,
            next_actions=data.get("next_actions", []),
            created_at=data.get("created_at", current_iso_timestamp()),
            updated_at=data.get("updated_at", current_iso_timestamp()),
            metadata=data.get("metadata", {}),
        )
