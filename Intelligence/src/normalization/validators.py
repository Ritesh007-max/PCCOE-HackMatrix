"""
FIN Validation Layer.
Detects and rejects impossible physical and domain values for applicant facts.
"""

from typing import Any, Optional


class ValidationError(ValueError):
    """Raised when an applicant fact value violates physical or domain constraints."""
    def __init__(self, field: str, value: Any, message: str):
        self.field = field
        self.value = value
        self.message = message
        super().__init__(f"Validation failed for field '{field}' with value '{value}': {message}")


def validate_age(age: Optional[int]) -> Optional[int]:
    """Validates applicant age. Must be between 0 and 120 years."""
    if age is None:
        return None
    if not isinstance(age, (int, float)):
        raise ValidationError("age", age, "Age must be a numeric integer.")
    if age < 0:
        raise ValidationError("age", age, "Age cannot be negative.")
    if age > 120:
        raise ValidationError("age", age, "Age cannot exceed 120 years.")
    return int(age)


def validate_income(income: Optional[float]) -> Optional[float]:
    """Validates annual family income. Cannot be negative."""
    if income is None:
        return None
    if not isinstance(income, (int, float)):
        raise ValidationError("annual_family_income", income, "Income must be a numeric value.")
    if income < 0:
        raise ValidationError("annual_family_income", income, "Income cannot be negative.")
    return float(income)


def validate_percentage(pct: Optional[float], field_name: str = "percentage") -> Optional[float]:
    """Validates percentages (e.g. disability_percentage, school_attendance_pct). Must be in [0.0, 100.0]."""
    if pct is None:
        return None
    if not isinstance(pct, (int, float)):
        raise ValidationError(field_name, pct, "Percentage must be a numeric value.")
    if pct < 0.0 or pct > 100.0:
        raise ValidationError(field_name, pct, f"{field_name} must be between 0.0 and 100.0.")
    return float(pct)


def validate_landholding(ha: Optional[float]) -> Optional[float]:
    """Validates landholding in hectares. Cannot be negative."""
    if ha is None:
        return None
    if not isinstance(ha, (int, float)):
        raise ValidationError("landholding_hectares", ha, "Landholding must be a numeric value.")
    if ha < 0.0:
        raise ValidationError("landholding_hectares", ha, "Landholding hectares cannot be negative.")
    return float(ha)


def validate_residency_years(years: Optional[float]) -> Optional[float]:
    """Validates continuous residency years. Must be between 0 and 120."""
    if years is None:
        return None
    if not isinstance(years, (int, float)):
        raise ValidationError("residency_years", years, "Residency years must be numeric.")
    if years < 0.0 or years > 120.0:
        raise ValidationError("residency_years", years, "Residency years must be between 0 and 120.")
    return float(years)


def validate_pension(amount: Optional[float]) -> Optional[float]:
    """Validates monthly pension amount. Cannot be negative."""
    if amount is None:
        return None
    if not isinstance(amount, (int, float)):
        raise ValidationError("monthly_pension_amount", amount, "Pension amount must be numeric.")
    if amount < 0.0:
        raise ValidationError("monthly_pension_amount", amount, "Pension amount cannot be negative.")
    return float(amount)


def validate_field_value(field: str, value: Any) -> Any:
    """
    Dispatches validation for a specific canonical field.
    Raises ValidationError on physical impossibility.
    """
    if value is None:
        return None

    if field == "age":
        return validate_age(value)
    elif field in ("annual_family_income", "family_income", "income"):
        return validate_income(value)
    elif field in ("disability_percentage", "school_attendance_pct", "percentage"):
        return validate_percentage(value, field_name=field)
    elif field in ("landholding_hectares", "landholding"):
        return validate_landholding(value)
    elif field == "residency_years":
        return validate_residency_years(value)
    elif field == "monthly_pension_amount":
        return validate_pension(value)
    
    return value
