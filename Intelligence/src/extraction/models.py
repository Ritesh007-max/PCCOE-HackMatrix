"""
FIN Extraction Layer Data Models.
Defines canonical applicant profile fields, verification statuses, and fact representations.
"""

import dataclasses
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union


class FactVerificationStatus(str, Enum):
    """
    Verification states for an applicant fact.
    Enforces the hierarchy of trust and records conflict states.
    """
    SELF_REPORTED = "SELF_REPORTED"
    EXTRACTED = "EXTRACTED"
    USER_CONFIRMED = "USER_CONFIRMED"
    ISSUER_VERIFIED = "ISSUER_VERIFIED"
    CONFLICTED = "CONFLICTED"
    UNKNOWN = "UNKNOWN"


class ExtractionMethod(str, Enum):
    """Method by which a fact was extracted."""
    MANUAL_ENTRY = "MANUAL_ENTRY"
    EXTRACTED = "EXTRACTED"
    REGEX = "REGEX"
    NLP_MODEL = "NLP_MODEL"
    TABLE_PARSER = "TABLE_PARSER"
    FORM_FIELD = "FORM_FIELD"
    ISSUER_API = "ISSUER_API"
    SYSTEM_INFERRED = "SYSTEM_INFERRED"


# Authoritative dictionary of canonical applicant profile fields
CANONICAL_PROFILE_FIELDS: Dict[str, Dict[str, Any]] = {
    "age": {
        "data_type": "numeric",
        "description": "Chronological age in completed years",
        "min_value": 0,
        "max_value": 120,
    },
    "gender": {
        "data_type": "string",
        "description": "Legal gender identity",
        "allowed_values": ["Male", "Female", "Transgender"],
    },
    "state": {
        "data_type": "string",
        "description": "State or Union Territory of permanent domicile",
    },
    "is_permanent_resident": {
        "data_type": "boolean",
        "description": "Whether applicant is a permanent resident / domicile holder of the state",
    },
    "residency_years": {
        "data_type": "numeric",
        "description": "Continuous years of domicile residence",
        "min_value": 0,
        "max_value": 120,
    },
    "annual_family_income": {
        "data_type": "numeric",
        "description": "Total gross annual household income in INR",
        "min_value": 0,
    },
    "father_income": {
        "data_type": "numeric",
        "description": "Father's employment or wage income in INR",
        "min_value": 0,
    },
    "mother_income": {
        "data_type": "numeric",
        "description": "Mother's employment or business income in INR",
        "min_value": 0,
    },
    "other_income": {
        "data_type": "numeric",
        "description": "Other household income or agricultural earnings in INR",
        "min_value": 0,
    },
    "annual_income": {
        "data_type": "numeric",
        "description": "Individual personal annual income in INR",
        "min_value": 0,
    },
    "beneficiary_name": {
        "data_type": "string",
        "description": "Full legal name of the applicant/beneficiary",
    },
    "document_number": {
        "data_type": "string",
        "description": "Statutory registration or certificate reference number",
    },
    "date_of_birth": {
        "data_type": "string",
        "description": "Date of birth of the applicant",
    },
    "district": {
        "data_type": "string",
        "description": "District of domicile residence",
    },
    "bpl_card_holder": {
        "data_type": "boolean",
        "description": "Whether applicant possesses a Below Poverty Line card",
    },
    "social_category": {
        "data_type": "string",
        "description": "Constitutional social category",
        "allowed_values": ["General", "OBC", "SC", "ST", "EWS"],
    },
    "is_minority": {
        "data_type": "boolean",
        "description": "Whether applicant belongs to a notified religious minority community",
    },
    "is_disabled": {
        "data_type": "boolean",
        "description": "Whether applicant holds a Person with Disability (PwD) certificate",
    },
    "disability_percentage": {
        "data_type": "numeric",
        "description": "Certified benchmark disability percentage",
        "min_value": 0.0,
        "max_value": 100.0,
    },
    "is_student": {
        "data_type": "boolean",
        "description": "Whether applicant is currently enrolled as a student",
    },
    "enrolled_class": {
        "data_type": "string",
        "description": "Current educational grade or degree program",
    },
    "school_attendance_pct": {
        "data_type": "numeric",
        "description": "Recognized institutional attendance percentage",
        "min_value": 0.0,
        "max_value": 100.0,
    },
    "occupation": {
        "data_type": "string",
        "description": "Primary livelihood or occupational sector",
    },
    "owns_cultivable_land": {
        "data_type": "boolean",
        "description": "Whether applicant holds title to cultivable agricultural land",
    },
    "landholding_hectares": {
        "data_type": "numeric",
        "description": "Total agricultural landholding in hectares",
        "min_value": 0.0,
    },
    "has_bank_account": {
        "data_type": "boolean",
        "description": "Whether applicant has an active bank account linked with Aadhaar",
    },
    "is_taxpayer": {
        "data_type": "boolean",
        "description": "Whether applicant or spouse filed Income Tax in preceding assessment year",
    },
    "is_govt_employee": {
        "data_type": "boolean",
        "description": "Whether applicant or family member is employed in central/state government",
    },
    "monthly_pension_amount": {
        "data_type": "numeric",
        "description": "Existing monthly government pension received in INR",
        "min_value": 0,
    },
    "has_pucca_house": {
        "data_type": "boolean",
        "description": "Whether applicant household owns a pucca (all-weather permanent) dwelling",
    },
}


class FactSourceType(str, Enum):
    """Origin source type for an applicant fact."""
    DOCUMENT = "DOCUMENT"
    USER_INPUT = "USER_INPUT"
    PROFILE = "PROFILE"
    SYSTEM = "SYSTEM"
    DERIVED = "DERIVED"


@dataclass
class ApplicantFact:
    """
    Represents a single atomic extracted or declared applicant fact.
    Preserves exact verbatim source text, provenance, and verification state.
    """
    field: str
    value: Any
    normalized_value: Any
    data_type: str
    confidence: float
    source_document: str
    page_number: Optional[int] = None
    text_span: Optional[str] = None
    extraction_method: str = ExtractionMethod.EXTRACTED.value
    verification_status: FactVerificationStatus = FactVerificationStatus.EXTRACTED
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)
    id: Optional[str] = None
    applicant_id: Optional[str] = None
    document_id: Optional[str] = None
    source_type: FactSourceType = FactSourceType.DOCUMENT
    bounding_box: Optional[Dict[str, float]] = None
    extracted_at: Optional[str] = None
    fact_version: str = "1.0"
    conflict_group_id: Optional[str] = None

    def __post_init__(self):
        import uuid
        from datetime import datetime, timezone
        if not self.id:
            self.id = f"fact_{uuid.uuid4().hex[:12]}"
        if not self.extracted_at:
            self.extracted_at = datetime.now(timezone.utc).isoformat()
        # Ensure confidence is clamped between 0.0 and 1.0
        self.confidence = max(0.0, min(1.0, float(self.confidence)))
        if isinstance(self.verification_status, str):
            self.verification_status = FactVerificationStatus(self.verification_status)
        if isinstance(self.source_type, str):
            try:
                self.source_type = FactSourceType(self.source_type)
            except (ValueError, KeyError):
                self.source_type = FactSourceType.DOCUMENT

    @property
    def fact_key(self) -> str:
        """Alias for field."""
        return self.field

    @property
    def raw_value(self) -> Any:
        """Alias for raw extracted value."""
        return self.value

    @property
    def value_type(self) -> str:
        """Alias for data_type."""
        return self.data_type

    @property
    def source_reference(self) -> str:
        """Alias for source_document."""
        return self.source_document

    @property
    def is_conflicted(self) -> bool:
        return self.verification_status == FactVerificationStatus.CONFLICTED

    @property
    def is_unknown(self) -> bool:
        return (
            self.verification_status == FactVerificationStatus.UNKNOWN
            or self.normalized_value is None
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "applicant_id": self.applicant_id,
            "document_id": self.document_id,
            "field": self.field,
            "fact_key": self.field,
            "value": self.value,
            "raw_value": self.value,
            "normalized_value": self.normalized_value,
            "data_type": self.data_type,
            "value_type": self.data_type,
            "confidence": self.confidence,
            "source_type": self.source_type.value if hasattr(self.source_type, "value") else str(self.source_type),
            "source_document": self.source_document,
            "source_reference": self.source_document,
            "page_number": self.page_number,
            "text_span": self.text_span,
            "bounding_box": self.bounding_box,
            "extraction_method": self.extraction_method,
            "verification_status": self.verification_status.value,
            "extracted_at": self.extracted_at,
            "fact_version": self.fact_version,
            "conflict_group_id": self.conflict_group_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApplicantFact":
        field_name = data.get("field") or data.get("fact_key", "unknown")
        raw_val = data.get("raw_value") if "raw_value" in data else data.get("value")
        norm_val = data.get("normalized_value")
        data_type = data.get("data_type") or data.get("value_type", "string")
        source_doc = data.get("source_document") or data.get("source_reference", "unknown")

        source_type_val = data.get("source_type", FactSourceType.DOCUMENT.value)
        try:
            source_type = FactSourceType(source_type_val)
        except (ValueError, KeyError):
            source_type = FactSourceType.DOCUMENT

        status_val = data.get("verification_status", FactVerificationStatus.EXTRACTED.value)
        try:
            status = FactVerificationStatus(status_val)
        except (ValueError, KeyError):
            status = FactVerificationStatus.EXTRACTED

        return cls(
            id=data.get("id"),
            applicant_id=data.get("applicant_id"),
            document_id=data.get("document_id"),
            field=field_name,
            value=raw_val,
            normalized_value=norm_val,
            data_type=data_type,
            confidence=float(data.get("confidence", 1.0)),
            source_type=source_type,
            source_document=source_doc,
            page_number=data.get("page_number"),
            text_span=data.get("text_span"),
            bounding_box=data.get("bounding_box"),
            extraction_method=data.get("extraction_method", ExtractionMethod.EXTRACTED.value),
            verification_status=status,
            extracted_at=data.get("extracted_at"),
            fact_version=data.get("fact_version", "1.0"),
            conflict_group_id=data.get("conflict_group_id"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Evidence:
    """
    Canonical evidence record supporting an applicant fact.
    Answers: 'Why does FIN believe this fact?'
    """
    evidence_id: Optional[str] = None
    applicant_fact_id: Optional[str] = None
    applicant_id: Optional[str] = None
    document_id: Optional[str] = None
    source_type: FactSourceType = FactSourceType.DOCUMENT
    source_uri: Optional[str] = None
    page_number: Optional[int] = None
    text_span: Optional[str] = None
    bounding_box: Optional[Dict[str, float]] = None
    extraction_method: str = ExtractionMethod.EXTRACTED.value
    confidence: float = 1.0
    verification_status: FactVerificationStatus = FactVerificationStatus.EXTRACTED
    document_hash: Optional[str] = None
    created_at: Optional[str] = None
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def __post_init__(self):
        import uuid
        from datetime import datetime, timezone
        if not self.evidence_id:
            self.evidence_id = f"ev_{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if isinstance(self.verification_status, str):
            self.verification_status = FactVerificationStatus(self.verification_status)
        if isinstance(self.source_type, str):
            try:
                self.source_type = FactSourceType(self.source_type)
            except (ValueError, KeyError):
                self.source_type = FactSourceType.DOCUMENT
        self.confidence = max(0.0, min(1.0, float(self.confidence)))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "applicant_fact_id": self.applicant_fact_id,
            "applicant_id": self.applicant_id,
            "document_id": self.document_id,
            "source_type": self.source_type.value if hasattr(self.source_type, "value") else str(self.source_type),
            "source_uri": self.source_uri,
            "source_reference": self.source_uri,
            "page_number": self.page_number,
            "text_span": self.text_span,
            "bounding_box": self.bounding_box,
            "extraction_method": self.extraction_method,
            "confidence": self.confidence,
            "verification_status": self.verification_status.value if hasattr(self.verification_status, "value") else str(self.verification_status),
            "document_hash": self.document_hash,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Evidence":
        status_val = data.get("verification_status", FactVerificationStatus.EXTRACTED.value)
        try:
            status = FactVerificationStatus(status_val)
        except (ValueError, KeyError):
            status = FactVerificationStatus.EXTRACTED

        source_val = data.get("source_type", FactSourceType.DOCUMENT.value)
        try:
            source = FactSourceType(source_val)
        except (ValueError, KeyError):
            source = FactSourceType.DOCUMENT

        return cls(
            evidence_id=data.get("evidence_id"),
            applicant_fact_id=data.get("applicant_fact_id"),
            applicant_id=data.get("applicant_id"),
            document_id=data.get("document_id"),
            source_type=source,
            source_uri=data.get("source_uri") or data.get("source_reference"),
            page_number=data.get("page_number"),
            text_span=data.get("text_span"),
            bounding_box=data.get("bounding_box"),
            extraction_method=data.get("extraction_method", ExtractionMethod.EXTRACTED.value),
            confidence=float(data.get("confidence", 1.0)),
            verification_status=status,
            document_hash=data.get("document_hash"),
            created_at=data.get("created_at"),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_fact(cls, fact: ApplicantFact, document_hash: Optional[str] = None) -> "Evidence":
        return cls(
            applicant_fact_id=fact.id,
            applicant_id=fact.applicant_id,
            document_id=fact.document_id,
            source_type=fact.source_type,
            source_uri=fact.source_document,
            page_number=fact.page_number,
            text_span=fact.text_span,
            bounding_box=fact.bounding_box,
            extraction_method=fact.extraction_method,
            confidence=fact.confidence,
            verification_status=fact.verification_status,
            document_hash=document_hash or fact.metadata.get("document_hash"),
            metadata=dict(fact.metadata),
        )


@dataclass
class CanonicalApplicantProfile:
    """
    Canonical representation of applicant profile facts consolidated from evidence.
    Directly compatible with the Phase 3 RuleEvaluator and EligibilityEngine.
    """
    facts: Dict[str, ApplicantFact] = dataclasses.field(default_factory=dict)
    conflicted_fields: Set[str] = dataclasses.field(default_factory=set)

    def add_fact(self, fact: ApplicantFact) -> None:
        """Adds or updates a fact in the canonical profile."""
        self.facts[fact.field] = fact
        if fact.verification_status == FactVerificationStatus.CONFLICTED:
            self.conflicted_fields.add(fact.field)

    def get_value(self, field_name: str) -> Any:
        """Returns the normalized value if available, else None."""
        if field_name in self.conflicted_fields:
            return None
        fact = self.facts.get(field_name)
        return fact.normalized_value if fact else None

    def has_field(self, field_name: str) -> bool:
        fact = self.facts.get(field_name)
        return fact is not None and fact.normalized_value is not None

    def has_conflict(self, field_name: str) -> bool:
        return field_name in self.conflicted_fields

    def to_dict(self) -> Dict[str, Any]:
        """Converts to dictionary representation suitable for rules engine."""
        out: Dict[str, Any] = {}
        for k, f in self.facts.items():
            if k not in self.conflicted_fields:
                out[k] = f.normalized_value
        if self.conflicted_fields:
            out["_conflicts"] = sorted(list(self.conflicted_fields))
        return out
