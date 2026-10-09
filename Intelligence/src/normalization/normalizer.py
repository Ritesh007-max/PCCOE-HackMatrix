"""
FIN Data Normalization Engine.
Converts raw extracted strings and documents into standardized, typed values.
Strictly adheres to canonical standards and conservative parsing invariants.
"""

import re
from typing import Any, Dict, Optional, Union
import sys
from pathlib import Path

_CUR = Path(__file__).resolve()
while _CUR.name != "Intelligence" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_INTELLIGENCE_DIR = _CUR
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

try:
    from .validators import validate_field_value, ValidationError
except (ImportError, ValueError):
    from src.normalization.validators import validate_field_value, ValidationError

# Authoritative standard Indian States and Union Territories (28 States + 8 UTs)
INDIAN_STATES_AND_UTS = {
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    # Union Territories
    "Andaman and Nicobar Islands", "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Jammu and Kashmir",
    "Ladakh", "Lakshadweep", "Puducherry"
}

STATE_ALIASES: Dict[str, str] = {
    "orissa": "Odisha",
    "uttaranchal": "Uttarakhand",
    "pondicherry": "Puducherry",
    "nct of delhi": "Delhi",
    "new delhi": "Delhi",
    "delhi ncr": "Delhi",
    "daman and diu": "Dadra and Nagar Haveli and Daman and Diu",
    "dadra and nagar haveli": "Dadra and Nagar Haveli and Daman and Diu",
    "dadra & nagar haveli": "Dadra and Nagar Haveli and Daman and Diu",
    "jammu and kashmir": "Jammu and Kashmir",
    "jammu & kashmir": "Jammu and Kashmir",
    "j&k": "Jammu and Kashmir",
    "jk": "Jammu and Kashmir",
    "andaman and nicobar": "Andaman and Nicobar Islands",
    "andaman & nicobar": "Andaman and Nicobar Islands",
    "andaman & nicobar islands": "Andaman and Nicobar Islands",
    "a&n islands": "Andaman and Nicobar Islands",
    "all india": "All India",
    "pan india": "All India",
    "central": "All India",
}

# Precompile state lowercase lookup
_STATE_LOOKUP = {s.lower(): s for s in INDIAN_STATES_AND_UTS}
_STATE_LOOKUP.update(STATE_ALIASES)


def normalize_inr(value: Any) -> Optional[float]:
    """
    Normalizes Indian Rupee (INR) amounts.
    Supports currency symbols (₹, Rs., INR), commas (2,50,000),
    and Indian numeric denominations (lakh, lac, crore, k).
    Never invents values; returns None on unparseable inputs.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    raw = str(value).strip()
    if not raw or raw.lower() in ("null", "none", "na", "n/a"):
        return None

    # Clean currency symbols and delimiters
    # Matches symbols: ₹, Rs, Rs., INR, /-, and spaces
    cleaned = re.sub(r"[₹\u20b9]|(?:rs\.?|inr|/-)", "", raw, flags=re.IGNORECASE).strip()

    # Check for multiplier words
    multiplier = 1.0
    lower_raw = cleaned.lower()

    if re.search(r"(?:\bcrores?\b|\bcr\.?\b|(?<=\d)cr\.?\b|करोड़)", lower_raw):
        multiplier = 10_000_000.0
        cleaned = re.sub(r"(?:\bcrores?\b|\bcr\.?\b|(?<=\d)cr\.?\b|करोड़)", "", cleaned, flags=re.IGNORECASE).strip()
    elif re.search(r"(?:\blakhs?\b|\blacs?\b|(?<=\d)lakhs?\b|(?<=\d)lacs?\b|लाख)", lower_raw):
        multiplier = 100_000.0
        cleaned = re.sub(r"(?:\blakhs?\b|\blacs?\b|(?<=\d)lakhs?\b|(?<=\d)lacs?\b|लाख)", "", cleaned, flags=re.IGNORECASE).strip()
    elif re.search(r"(?:\bthousands?\b|(?<=\d)k\b|\bk\b|हज़ार|हजार)", lower_raw):
        multiplier = 1_000.0
        cleaned = re.sub(r"(?:\bthousands?\b|(?<=\d)k\b|\bk\b|हज़ार|हजार)", "", cleaned, flags=re.IGNORECASE).strip()
    elif re.search(r"(?:\bmillions?\b|(?<=\d)m\b|\bm\b)", lower_raw):
        multiplier = 1_000_000.0
        cleaned = re.sub(r"(?:\bmillions?\b|(?<=\d)m\b|\bm\b)", "", cleaned, flags=re.IGNORECASE).strip()

    # Remove commas and spaces
    cleaned = cleaned.replace(",", "").replace(" ", "")

    match = re.search(r"[-+]?\d*\.?\d+", cleaned)
    if not match:
        return None

    try:
        base_num = float(match.group(0))
        return round(base_num * multiplier, 2)
    except (ValueError, TypeError):
        return None


def normalize_age(value: Any) -> Optional[int]:
    """
    Normalizes chronological age into an integer.
    Supports formats like '25', '25 years', '25 yrs', 'age: 34', '34 years old'.
    """
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        return int(round(value))

    raw = str(value).strip()
    if not raw or raw.lower() in ("null", "none", "na", "n/a"):
        return None

    # Find number, supporting negative sign to allow validator to catch physical impossibility
    match = re.search(r"[-+]?\d+", raw)
    if not match:
        return None

    try:
        return int(match.group(0))
    except (ValueError, TypeError):
        return None


def normalize_gender(value: Any) -> Optional[str]:
    """
    Normalizes gender identity into canonical 'Male', 'Female', or 'Transgender'.
    """
    if value is None:
        return None
    raw = str(value).strip().lower()
    if not raw or raw in ("null", "none", "na", "n/a"):
        return None

    if raw in ("male", "m", "man", "boy", "gentleman", "purush"):
        return "Male"
    if raw in ("female", "f", "woman", "girl", "lady", "mahila", "stree"):
        return "Female"
    if raw in ("transgender", "trans", "t", "tg", "third gender", "other"):
        return "Transgender"

    return None


def normalize_state(value: Any) -> Optional[str]:
    """
    Normalizes Indian State or Union Territory name to authoritative standard.
    """
    if value is None:
        return None
    raw = str(value).strip()
    if not raw or raw.lower() in ("null", "none", "na", "n/a"):
        return None

    lower = raw.lower()
    # Strip prefixes like 'state of', 'ut of', 'govt of'
    lower = re.sub(r"^(?:state\s+of|ut\s+of|govt\s+of|government\s+of)\s+", "", lower).strip()

    if lower in _STATE_LOOKUP:
        return _STATE_LOOKUP[lower]

    return None


def normalize_social_category(value: Any) -> Optional[str]:
    """
    Normalizes constitutional social category to 'General', 'OBC', 'SC', 'ST', or 'EWS'.
    """
    if value is None:
        return None
    raw = str(value).strip().lower()
    if not raw or raw in ("null", "none", "na", "n/a"):
        return None

    if raw in ("general", "gen", "open", "ur", "unreserved", "oc"):
        return "General"
    if raw in ("obc", "other backward class", "other backward classes", "obc-ncl", "bc", "bc-a", "bc-b"):
        return "OBC"
    if raw in ("sc", "scheduled caste", "scheduled castes"):
        return "SC"
    if raw in ("st", "scheduled tribe", "scheduled tribes"):
        return "ST"
    if raw in ("ews", "economically weaker section", "economically weaker sections"):
        return "EWS"

    return None


def normalize_boolean(value: Any) -> Optional[bool]:
    """
    Normalizes truth values from multiple natural language and binary forms.
    Returns None for missing or unparseable values.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if value == 1:
            return True
        if value == 0:
            return False
        return None

    raw = str(value).strip().lower()
    if not raw or raw in ("null", "none", "na", "n/a", "unknown"):
        return None

    if raw in ("true", "yes", "y", "1", "t", "applicable", "eligible", "positive", "present", "active"):
        return True
    if raw in ("false", "no", "n", "0", "f", "not applicable", "ineligible", "negative", "absent", "inactive"):
        return False

    return None


def normalize_percentage(value: Any) -> Optional[float]:
    """
    Normalizes percentages to standard scale (0.0 - 100.0).
    Supports '45%', '45.5 %', '45.5', '0.45' (as ratio -> 45.0).
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        val = float(value)
        # If given as a decimal ratio between 0.0 and 1.0 (e.g. 0.75 -> 75.0)
        if 0.0 < val <= 1.0:
            val = val * 100.0
        return round(val, 2)

    raw = str(value).strip()
    if not raw or raw.lower() in ("null", "none", "na", "n/a"):
        return None

    has_percent_symbol = "%" in raw
    cleaned = raw.replace("%", "").replace("percent", "").replace("pct", "").strip()

    match = re.search(r"[-+]?\d*\.?\d+", cleaned)
    if not match:
        return None

    try:
        val = float(match.group(0))
        if not has_percent_symbol and 0.0 < val <= 1.0:
            val = val * 100.0
        return round(val, 2)
    except (ValueError, TypeError):
        return None


def normalize_landholding(value: Any) -> Optional[float]:
    """
    Normalizes agricultural landholding to standard hectares.
    Converts acres to hectares using standard conversion: 1 acre = 0.404686 hectares.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 4)

    raw = str(value).strip().lower()
    if not raw or raw in ("null", "none", "na", "n/a"):
        return None

    is_acre = bool(re.search(r"\b(?:acres?)\b", raw))
    cleaned = re.sub(r"\b(?:hectares?|ha|acres?)\b", "", raw).strip()

    match = re.search(r"[-+]?\d*\.?\d+", cleaned)
    if not match:
        return None

    try:
        num = float(match.group(0))
        if is_acre:
            num = num * 0.404686
        return round(num, 4)
    except (ValueError, TypeError):
        return None


def normalize_occupation(value: Any) -> Optional[str]:
    """
    Normalizes occupation titles and livelihood categories.
    """
    if value is None:
        return None
    raw = str(value).strip()
    if not raw or raw.lower() in ("null", "none", "na", "n/a"):
        return None

    lower = raw.lower()
    if lower in ("farmer", "kisan", "krishi"):
        return "Farmer"
    if lower in ("small farmer", "small / marginal farmer", "marginal farmer", "small and marginal farmer"):
        return "Small and Marginal Farmer"
    if lower in ("street vendor", "vendor", "hawker", "street-vendor"):
        return "Street Vendor"
    if lower in ("weaver", "bunkar", "handloom weaver"):
        return "Weaver"
    if lower in ("artisan", "craftsperson", "karigar"):
        return "Artisan"
    if lower in ("construction worker", "building worker"):
        return "Construction Worker"
    if lower in ("student", "learner"):
        return "Student"
    if lower in ("unemployed", "job seeker"):
        return "Unemployed"
    if lower in ("government employee", "govt employee", "public servant"):
        return "Government Employee"
    if lower in ("daily wage laborer", "laborer", "labourer", "daily wage earner"):
        return "Daily Wage Laborer"

    # Default: Title-case normalized string
    return " ".join(word.capitalize() for word in raw.split())


MONTH_NAMES = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12
}


def normalize_date(value: Any) -> Optional[str]:
    """
    Normalizes dates into canonical 'YYYY-MM-DD'.
    Handles 'YYYY-MM-DD', 'DD-MM-YYYY', 'DD/MM/YYYY', '12 August 2004', etc.
    """
    if value is None:
        return None
    raw = str(value).strip()
    if not raw or raw.lower() in ("null", "none", "na", "n/a"):
        return None

    m_iso = re.match(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$", raw)
    if m_iso:
        y, m, d = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
        return f"{y:04d}-{m:02d}-{d:02d}"

    m_dmy = re.match(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$", raw)
    if m_dmy:
        d, m, y = int(m_dmy.group(1)), int(m_dmy.group(2)), int(m_dmy.group(3))
        return f"{y:04d}-{m:02d}-{d:02d}"

    m_text = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", raw)
    if m_text:
        d = int(m_text.group(1))
        m_str = m_text.group(2).lower()
        y = int(m_text.group(3))
        if m_str in MONTH_NAMES:
            return f"{y:04d}-{MONTH_NAMES[m_str]:02d}-{d:02d}"

    m_text2 = re.search(r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", raw)
    if m_text2:
        m_str = m_text2.group(1).lower()
        d = int(m_text2.group(2))
        y = int(m_text2.group(3))
        if m_str in MONTH_NAMES:
            return f"{y:04d}-{MONTH_NAMES[m_str]:02d}-{d:02d}"

    return raw


def normalize_district(value: Any) -> Optional[str]:
    """
    Normalizes district names by stripping administrative suffixes.
    """
    if value is None:
        return None
    raw = str(value).strip()
    if not raw or raw.lower() in ("null", "none", "na", "n/a"):
        return None
    cleaned = re.sub(r"\b(?:district|dist\.?|city)\b", "", raw, flags=re.IGNORECASE).strip()
    return " ".join(word.capitalize() for word in cleaned.split()) if cleaned else raw.title()


def normalize_field_value(field: str, value: Any, validate: bool = True) -> Any:
    """
    Master normalization dispatcher.
    Routes raw field values to the appropriate normalizer and optionally validates.
    """
    if value is None:
        return None

    normalized: Any = None

    if field == "age":
        normalized = normalize_age(value)
    elif field in (
        "annual_family_income", "annual_income", "personal_income", "income", "family_income",
        "father_income", "mother_income", "other_income"
    ):
        normalized = normalize_inr(value)
    elif field == "gender":
        normalized = normalize_gender(value)
    elif field == "state":
        normalized = normalize_state(value)
    elif field in ("district", "city"):
        normalized = normalize_district(value)
    elif field in ("date_of_birth", "dob"):
        normalized = normalize_date(value)
    elif field == "social_category":
        normalized = normalize_social_category(value)
    elif field in (
        "is_permanent_resident", "bpl_card_holder", "is_minority",
        "is_disabled", "is_student", "owns_cultivable_land",
        "has_bank_account", "is_taxpayer", "is_govt_employee", "has_pucca_house"
    ) or field.startswith("is_") or field.startswith("has_") or field.startswith("owns_"):
        normalized = normalize_boolean(value)
    elif field in ("disability_percentage", "school_attendance_pct", "percentage"):
        normalized = normalize_percentage(value)
    elif field in ("landholding_hectares", "landholding"):
        normalized = normalize_landholding(value)
    elif field == "monthly_pension_amount":
        normalized = normalize_inr(value)
    elif field == "occupation":
        normalized = normalize_occupation(value)
    elif field == "residency_years":
        normalized = normalize_age(value)
    else:
        # Generic string fallback
        if isinstance(value, str):
            normalized = value.strip()
        else:
            normalized = value

    if validate and normalized is not None:
        validate_field_value(field, normalized)

    return normalized