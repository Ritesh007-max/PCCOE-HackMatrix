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

    def __post_init__(self):
        # Ensure confidence is clamped between 0.0 and 1.0
        self.confidence = max(0.0, min(1.0, float(self.confidence)))
        if isinstance(self.verification_status, str):
            self.verification_status = FactVerificationStatus(self.verification_status)

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
            "field": self.field,
            "value": self.value,
            "normalized_value": self.normalized_value,
            "data_type": self.data_type,
            "confidence": self.confidence,
            "source_document": self.source_document,
            "page_number": self.page_number,
            "text_span": self.text_span,
            "extraction_method": self.extraction_method,
            "verification_status": self.verification_status.value,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApplicantFact":
        return cls(
            field=data["field"],
            value=data.get("value"),
            normalized_value=data.get("normalized_value"),
            data_type=data.get("data_type", "string"),
            confidence=float(data.get("confidence", 1.0)),
            source_document=data.get("source_document", "unknown"),
            page_number=data.get("page_number"),
            text_span=data.get("text_span"),
            extraction_method=data.get("extraction_method", ExtractionMethod.EXTRACTED.value),
            verification_status=FactVerificationStatus(
                data.get("verification_status", FactVerificationStatus.EXTRACTED.value)
            ),
            metadata=data.get("metadata", {}),
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
