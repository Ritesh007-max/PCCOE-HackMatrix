"""
FIN JSON Schemas for Applicant Facts, Evidence Collections, and Applicant Profiles.
Validates structural integrity and typing of fact layers.
"""

from typing import Any, Dict
import jsonschema

APPLICANT_FACT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "ApplicantFact",
    "description": "Represents an atomic applicant fact with provenance and verification status.",
    "type": "object",
    "required": ["field", "data_type", "source_document", "verification_status"],
    "properties": {
        "field": {
            "type": "string",
            "minLength": 1,
            "description": "Canonical or scheme-specific field key."
        },
        "value": {
            "description": "Raw extracted or stated value before normalization."
        },
        "normalized_value": {
            "description": "Normalized typed value (null if unknown or unparseable)."
        },
        "data_type": {
            "type": "string",
            "enum": ["numeric", "string", "boolean"]
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "default": 1.0
        },
        "source_document": {
            "type": "string",
            "minLength": 1,
            "description": "Originating document name or citation identifier."
        },
        "page_number": {
            "type": ["integer", "null"],
            "minimum": 1
        },
        "text_span": {
            "type": ["string", "null"],
            "description": "Exact verbatim text segment extracted from document."
        },
        "extraction_method": {
            "type": "string",
            "enum": [
                "MANUAL_ENTRY",
                "EXTRACTED",
                "REGEX",
                "NLP_MODEL",
                "TABLE_PARSER",
                "FORM_FIELD",
                "ISSUER_API",
                "SYSTEM_INFERRED"
            ]
        },
        "verification_status": {
            "type": "string",
            "enum": [
                "SELF_REPORTED",
                "EXTRACTED",
                "USER_CONFIRMED",
                "ISSUER_VERIFIED",
                "CONFLICTED",
                "UNKNOWN"
            ]
        },
        "metadata": {
            "type": "object"
        }
    },
    "additionalProperties": True
}

EVIDENCE_COLLECTION_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "EvidenceCollection",
    "description": "Multi-document evidence container aggregating applicant facts.",
    "type": "object",
    "required": ["facts"],
    "properties": {
        "applicant_id": {
            "type": "string"
        },
        "facts": {
            "type": "array",
            "items": APPLICANT_FACT_SCHEMA
        },
        "conflicts": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of field keys with contradictory evidence."
        },
        "source_documents": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "additionalProperties": True
}

APPLICANT_PROFILE_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "ApplicantProfile",
    "description": "Canonical applicant profile consumed by the FIN eligibility engine.",
    "type": "object",
    "properties": {
        "age": {
            "type": "integer",
            "minimum": 0,
            "maximum": 120
        },
        "gender": {
            "type": "string",
            "enum": ["Male", "Female", "Transgender"]
        },
        "state": {
            "type": "string"
        },
        "is_permanent_resident": {
            "type": "boolean"
        },
        "residency_years": {
            "type": "number",
            "minimum": 0,
            "maximum": 120
        },
        "annual_family_income": {
            "type": "number",
            "minimum": 0
        },
        "bpl_card_holder": {
            "type": "boolean"
        },
        "social_category": {
            "type": "string",
            "enum": ["General", "OBC", "SC", "ST", "EWS"]
        },
        "is_minority": {
            "type": "boolean"
        },
        "is_disabled": {
            "type": "boolean"
        },
        "disability_percentage": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 100.0
        },
        "is_student": {
            "type": "boolean"
        },
        "enrolled_class": {
            "type": "string"
        },
        "school_attendance_pct": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 100.0
        },
        "occupation": {
            "type": "string"
        },
        "owns_cultivable_land": {
            "type": "boolean"
        },
        "landholding_hectares": {
            "type": "number",
            "minimum": 0.0
        },
        "has_bank_account": {
            "type": "boolean"
        },
        "is_taxpayer": {
            "type": "boolean"
        },
        "is_govt_employee": {
            "type": "boolean"
        },
        "monthly_pension_amount": {
            "type": "number",
            "minimum": 0
        },
        "has_pucca_house": {
            "type": "boolean"
        },
        "_conflicts": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of fields where evidence was contradictory."
        }
    },
    "additionalProperties": True
}


def validate_applicant_fact_dict(data: Dict[str, Any]) -> None:
    """Validates a dictionary against the ApplicantFact JSON schema."""
    jsonschema.validate(instance=data, schema=APPLICANT_FACT_SCHEMA)


def validate_evidence_collection_dict(data: Dict[str, Any]) -> None:
    """Validates a dictionary against the EvidenceCollection JSON schema."""
    jsonschema.validate(instance=data, schema=EVIDENCE_COLLECTION_SCHEMA)


def validate_applicant_profile_dict(data: Dict[str, Any]) -> None:
    """Validates a dictionary against the ApplicantProfile JSON schema."""
    jsonschema.validate(instance=data, schema=APPLICANT_PROFILE_SCHEMA)
