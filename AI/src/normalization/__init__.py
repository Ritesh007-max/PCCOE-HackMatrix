"""
PolicySetu Normalization Package.
Exports normalization functions, domain validators, and ValidationError.
"""

from .normalizer import (
    INDIAN_STATES_AND_UTS,
    STATE_ALIASES,
    normalize_inr,
    normalize_age,
    normalize_gender,
    normalize_state,
    normalize_social_category,
    normalize_boolean,
    normalize_percentage,
    normalize_landholding,
    normalize_occupation,
    normalize_field_value,
)
from .validators import (
    ValidationError,
    validate_age,
    validate_income,
    validate_percentage,
    validate_landholding,
    validate_residency_years,
    validate_pension,
    validate_field_value,
)

__all__ = [
    "INDIAN_STATES_AND_UTS",
    "STATE_ALIASES",
    "normalize_inr",
    "normalize_age",
    "normalize_gender",
    "normalize_state",
    "normalize_social_category",
    "normalize_boolean",
    "normalize_percentage",
    "normalize_landholding",
    "normalize_occupation",
    "normalize_field_value",
    "ValidationError",
    "validate_age",
    "validate_income",
    "validate_percentage",
    "validate_landholding",
    "validate_residency_years",
    "validate_pension",
    "validate_field_value",
]
