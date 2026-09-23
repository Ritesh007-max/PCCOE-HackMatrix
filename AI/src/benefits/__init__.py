"""
PolicySetu Benefits Module.
Calculates quantitative financial values (subsidies, scholarships, direct benefit transfers)
and catalogs non-monetary provisions via pre-compiled structured rules only.
"""

from .calculator import (
    BenefitCalculator,
    BenefitResult,
    BenefitType,
    BenefitCalculationStatus,
    StructuredBenefitRule,
    REGISTERED_BENEFIT_RULES,
)

__all__ = [
    "BenefitCalculator",
    "BenefitResult",
    "BenefitType",
    "BenefitCalculationStatus",
    "StructuredBenefitRule",
    "REGISTERED_BENEFIT_RULES",
]
