"""
Application Guidance Domain Models and Structured Schemas.
Phase 11: Frontend-ready, stable guidance schemas with zero-hallucination guarantees.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ApplicationMode(str, Enum):
    """Authoritative submission mode for government schemes."""
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    BOTH = "BOTH"
    CSC = "CSC"
    DEPARTMENT_OFFICE = "DEPARTMENT_OFFICE"
    PORTAL = "PORTAL"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_string(cls, val: Any) -> "ApplicationMode":
        if not val:
            return cls.UNKNOWN
        s = str(val).strip().upper()
        if "ONLINE" in s and "OFFLINE" in s:
            return cls.BOTH
        if "ONLINE" in s or "PORTAL" in s:
            return cls.ONLINE
        if "OFFLINE" in s:
            return cls.OFFLINE
        if "CSC" in s:
            return cls.CSC
        if "DEPARTMENT" in s or "OFFICE" in s:
            return cls.DEPARTMENT_OFFICE
        return cls.UNKNOWN


class GuidanceWarningCode(str, Enum):
    """Categorical warning codes for risks, omissions, and ambiguities."""
    POLICY_INFORMATION_INCOMPLETE = "POLICY_INFORMATION_INCOMPLETE"
    OFFICIAL_LINK_UNAVAILABLE = "OFFICIAL_LINK_UNAVAILABLE"
    DOCUMENT_MISSING = "DOCUMENT_MISSING"
    DOCUMENT_CONFLICT = "DOCUMENT_CONFLICT"
    ELIGIBILITY_UNKNOWN = "ELIGIBILITY_UNKNOWN"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    BENEFIT_UNDETERMINED = "BENEFIT_UNDETERMINED"
    POLICY_SOURCE_CONFLICT = "POLICY_SOURCE_CONFLICT"


class WarningSeverity(str, Enum):
    """Severity tier for guidance warnings."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class StepSourceType(str, Enum):
    """Classification of procedure steps."""
    POLICY_SOURCED = "POLICY_SOURCED"
    GENERAL_PREPARATION = "GENERAL_PREPARATION"


class DeadlineStatus(str, Enum):
    """Status of scheme application window."""
    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass
class GuidanceWarning:
    """Structured, actionable warning for citizen or caseworker."""
    code: GuidanceWarningCode
    severity: WarningSeverity
    message: str
    related_field: Optional[str] = None
    related_scheme: Optional[str] = None
    evidence_reference: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code.value,
            "severity": self.severity.value,
            "message": self.message,
            "related_field": self.related_field,
            "related_scheme": self.related_scheme,
            "evidence_reference": self.evidence_reference,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GuidanceWarning":
        code_raw = data.get("code", GuidanceWarningCode.POLICY_INFORMATION_INCOMPLETE.value)
        sev_raw = data.get("severity", WarningSeverity.WARNING.value)
        code = GuidanceWarningCode(code_raw) if code_raw in GuidanceWarningCode.__members__ else GuidanceWarningCode.POLICY_INFORMATION_INCOMPLETE
        sev = WarningSeverity(sev_raw) if sev_raw in WarningSeverity.__members__ else WarningSeverity.WARNING
        return cls(
            code=code,
            severity=sev,
            message=data.get("message", ""),
            related_field=data.get("related_field"),
            related_scheme=data.get("related_scheme"),
            evidence_reference=data.get("evidence_reference"),
        )


@dataclass
class DocumentGuidanceItem:
    """Detailed guidance for a required or recommended certificate."""
    document_type: str
    display_name: str
    status: str  # AVAILABLE, MISSING, CONFLICTED, UNKNOWN, NOT_REQUIRED
    required: bool = True
    why_needed: str = ""
    already_provided: bool = False
    issuing_authority: str = "Not specified in available policy evidence."
    preparation_notes: str = "Ensure document is clear and all details match profile."
    source_reference: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_type": self.document_type,
            "display_name": self.display_name,
            "status": self.status,
            "required": self.required,
            "why_needed": self.why_needed,
            "already_provided": self.already_provided,
            "issuing_authority": self.issuing_authority,
            "preparation_notes": self.preparation_notes,
            "source_reference": self.source_reference,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentGuidanceItem":
        return cls(
            document_type=data["document_type"],
            display_name=data.get("display_name", data["document_type"]),
            status=data.get("status", "UNKNOWN"),
            required=bool(data.get("required", True)),
            why_needed=data.get("why_needed", ""),
            already_provided=bool(data.get("already_provided", False)),
            issuing_authority=data.get("issuing_authority", "Not specified in available policy evidence."),
            preparation_notes=data.get("preparation_notes", ""),
            source_reference=data.get("source_reference"),
        )


@dataclass
class ApplicationStep:
    """Ordered application step grounded in authoritative policy process or preparation rules."""
    step_number: int
    instruction: str
    source_type: StepSourceType = StepSourceType.POLICY_SOURCED
    source_reference: Optional[str] = None
    mandatory: bool = True
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "instruction": self.instruction,
            "source_type": self.source_type.value,
            "source_reference": self.source_reference,
            "mandatory": self.mandatory,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApplicationStep":
        stype_raw = data.get("source_type", StepSourceType.POLICY_SOURCED.value)
        stype = StepSourceType(stype_raw) if stype_raw in StepSourceType.__members__ else StepSourceType.POLICY_SOURCED
        return cls(
            step_number=int(data["step_number"]),
            instruction=data.get("instruction", ""),
            source_type=stype,
            source_reference=data.get("source_reference"),
            mandatory=bool(data.get("mandatory", True)),
            notes=data.get("notes", ""),
        )


@dataclass
class DeadlineGuidance:
    """Application opening and deadline dates."""
    status: DeadlineStatus = DeadlineStatus.UNKNOWN
    open_date: Optional[str] = None
    close_date: Optional[str] = None
    deadline_notes: str = "Deadlines not explicitly specified in the verified policy source."
    policy_snapshot_version: str = "V1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "open_date": self.open_date,
            "close_date": self.close_date,
            "deadline_notes": self.deadline_notes,
            "policy_snapshot_version": self.policy_snapshot_version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeadlineGuidance":
        st_raw = data.get("status", DeadlineStatus.UNKNOWN.value)
        st = DeadlineStatus(st_raw) if st_raw in DeadlineStatus.__members__ else DeadlineStatus.UNKNOWN
        return cls(
            status=st,
            open_date=data.get("open_date"),
            close_date=data.get("close_date"),
            deadline_notes=data.get("deadline_notes", ""),
            policy_snapshot_version=data.get("policy_snapshot_version", "V1"),
        )


@dataclass
class EligibilitySummary:
    """Citizen-readable explanation of deterministic statutory evaluation."""
    status: str  # PASS, FAIL, UNKNOWN, REVIEW
    summary: str
    criteria: List[Dict[str, Any]] = field(default_factory=list)
    satisfied_criteria: List[str] = field(default_factory=list)
    failed_criteria: List[str] = field(default_factory=list)
    unresolved_criteria: List[str] = field(default_factory=list)
    conflicting_evidence: List[str] = field(default_factory=list)
    missing_information: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "summary": self.summary,
            "criteria": self.criteria,
            "satisfied_criteria": self.satisfied_criteria,
            "failed_criteria": self.failed_criteria,
            "unresolved_criteria": self.unresolved_criteria,
            "conflicting_evidence": self.conflicting_evidence,
            "missing_information": self.missing_information,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EligibilitySummary":
        return cls(
            status=data.get("status", "UNKNOWN"),
            summary=data.get("summary", ""),
            criteria=data.get("criteria", []),
            satisfied_criteria=data.get("satisfied_criteria", []),
            failed_criteria=data.get("failed_criteria", []),
            unresolved_criteria=data.get("unresolved_criteria", []),
            conflicting_evidence=data.get("conflicting_evidence", []),
            missing_information=data.get("missing_information", []),
        )


@dataclass
class BenefitGuidance:
    """Transparent presentation of quantitative and qualitative benefits."""
    status: str  # CALCULATED, CONDITIONAL, CANNOT_DETERMINE
    benefit_type: str = "DIRECT_BENEFIT_TRANSFER"
    amount: Optional[float] = None
    currency: str = "INR"
    frequency: Optional[str] = None
    disbursement_structure: str = ""
    explanation: str = ""
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
            "evidence": self.evidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BenefitGuidance":
        return cls(
            status=data.get("status", "CANNOT_DETERMINE"),
            benefit_type=data.get("benefit_type", "DIRECT_BENEFIT_TRANSFER"),
            amount=data.get("amount"),
            currency=data.get("currency", "INR"),
            frequency=data.get("frequency"),
            disbursement_structure=data.get("disbursement_structure", ""),
            explanation=data.get("explanation", ""),
            evidence=data.get("evidence", []),
        )


@dataclass
class SourceCitation:
    """Authoritative provenance citation for grounding."""
    scheme_id: str
    scheme_name: str
    source_authority: str
    official_url: Optional[str] = None
    section: str = "general"
    chunk_id: Optional[str] = None
    policy_snapshot_version: str = "V1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scheme_id": self.scheme_id,
            "scheme_name": self.scheme_name,
            "source_authority": self.source_authority,
            "official_url": self.official_url,
            "section": self.section,
            "chunk_id": self.chunk_id,
            "policy_snapshot_version": self.policy_snapshot_version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceCitation":
        return cls(
            scheme_id=data["scheme_id"],
            scheme_name=data.get("scheme_name", ""),
            source_authority=data.get("source_authority", "Government Portal"),
            official_url=data.get("official_url"),
            section=data.get("section", "general"),
            chunk_id=data.get("chunk_id"),
            policy_snapshot_version=data.get("policy_snapshot_version", "V1"),
        )


@dataclass
class ApplicationGuidancePackage:
    """
    Authoritative Frontend-Ready Application Guidance Package.
    Enforces complete structural separation of concerns with zero hallucinations.
    """
    application_id: str
    scheme_id: str
    scheme_name: str
    statutory_decision: str
    readiness_status: str
    readiness: Dict[str, Any]
    eligibility: EligibilitySummary
    documents: Dict[str, Any]
    information: Dict[str, Any]
    benefit: BenefitGuidance
    application: Dict[str, Any]
    actions: List[Dict[str, Any]]
    warnings: List[GuidanceWarning]
    sources: List[SourceCitation]
    policy_snapshot_version: str
    rule_version: str
    language: str = "en"
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_deterministic_fallback: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "application_id": self.application_id,
            "scheme_id": self.scheme_id,
            "scheme_name": self.scheme_name,
            "statutory_decision": self.statutory_decision,
            "readiness_status": self.readiness_status,
            "readiness": self.readiness,
            "eligibility": self.eligibility.to_dict(),
            "documents": self.documents,
            "information": self.information,
            "benefit": self.benefit.to_dict(),
            "application": self.application,
            "actions": self.actions,
            "warnings": [w.to_dict() for w in self.warnings],
            "sources": [s.to_dict() for s in self.sources],
            "policy_snapshot_version": self.policy_snapshot_version,
            "rule_version": self.rule_version,
            "language": self.language,
            "generated_at": self.generated_at,
            "is_deterministic_fallback": self.is_deterministic_fallback,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApplicationGuidancePackage":
        elig = EligibilitySummary.from_dict(data.get("eligibility", {}))
        ben = BenefitGuidance.from_dict(data.get("benefit", {}))
        warns = [GuidanceWarning.from_dict(w) for w in data.get("warnings", [])]
        srcs = [SourceCitation.from_dict(s) for s in data.get("sources", [])]

        return cls(
            application_id=data["application_id"],
            scheme_id=data["scheme_id"],
            scheme_name=data.get("scheme_name", ""),
            statutory_decision=data.get("statutory_decision", "UNKNOWN"),
            readiness_status=data.get("readiness_status", "NOT_READY"),
            readiness=data.get("readiness", {}),
            eligibility=elig,
            documents=data.get("documents", {}),
            information=data.get("information", {}),
            benefit=ben,
            application=data.get("application", {}),
            actions=data.get("actions", []),
            warnings=warns,
            sources=srcs,
            policy_snapshot_version=data.get("policy_snapshot_version", "V1"),
            rule_version=data.get("rule_version", "1.0.0"),
            language=data.get("language", "en"),
            generated_at=data.get("generated_at", datetime.now(timezone.utc).isoformat()),
            is_deterministic_fallback=bool(data.get("is_deterministic_fallback", False)),
        )
