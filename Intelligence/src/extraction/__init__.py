"""
FIN Extraction Layer Package.
Exports canonical data models, verification statuses, and JSON schemas.
"""

from .models import (
    FactVerificationStatus,
    ExtractionMethod,
    FactSourceType,
    ApplicantFact,
    Evidence,
    CanonicalApplicantProfile,
    CANONICAL_PROFILE_FIELDS,
)
from .schema import (
    APPLICANT_FACT_SCHEMA,
    EVIDENCE_COLLECTION_SCHEMA,
    APPLICANT_PROFILE_SCHEMA,
    validate_applicant_fact_dict,
    validate_evidence_collection_dict,
    validate_applicant_profile_dict,
)

__all__ = [
    "FactVerificationStatus",
    "ExtractionMethod",
    "FactSourceType",
    "ApplicantFact",
    "Evidence",
    "CanonicalApplicantProfile",
    "CANONICAL_PROFILE_FIELDS",
    "APPLICANT_FACT_SCHEMA",
    "EVIDENCE_COLLECTION_SCHEMA",
    "APPLICANT_PROFILE_SCHEMA",
    "validate_applicant_fact_dict",
    "validate_evidence_collection_dict",
    "validate_applicant_profile_dict",
]
