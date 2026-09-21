"""
PolicySetu Query Normalization and Metadata Filtering.
Extracts retrieval hints without making eligibility decisions, and builds
metadata filter predicates for vector and sparse search.
"""

import re
from typing import Any, Callable, Dict, List, Optional
import sys
from pathlib import Path

_CUR = Path(__file__).resolve()
while _CUR.name != "AI" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_AI_DIR = _CUR
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

try:
    from .models import RetrievalIntent, RetrievalQuery
except (ImportError, ValueError):
    from src.rag.models import RetrievalIntent, RetrievalQuery

# Re-use Indian States and Social Categories
INDIAN_STATES_KEYWORDS = {
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
    "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka",
    "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram",
    "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu",
    "telangana", "tripura", "uttar pradesh", "uttarakhand", "west bengal",
    "delhi", "jammu and kashmir", "ladakh", "puducherry", "chandigarh"
}

STATE_ALIASES = {
    "orissa": "odisha",
    "uttaranchal": "uttarakhand",
    "pondicherry": "puducherry",
    "new delhi": "delhi",
    "j&k": "jammu and kashmir",
    "up": "uttar pradesh",
    "mp": "madhya pradesh",
}

CATEGORY_KEYWORDS = {
    "sc": "SC",
    "st": "ST",
    "obc": "OBC",
    "ews": "EWS",
    "general": "General",
    "scheduled caste": "SC",
    "scheduled tribe": "ST",
    "other backward": "OBC",
}

BENEFICIARY_KEYWORDS = {
    "student": "Student",
    "students": "Student",
    "farmer": "Farmer",
    "farmers": "Farmer",
    "kisan": "Farmer",
    "woman": "Women",
    "women": "Women",
    "girl": "Women",
    "mahila": "Women",
    "disabled": "Persons with Disabilities",
    "pwd": "Persons with Disabilities",
    "artisan": "Artisans",
    "artisans": "Artisans",
    "vendor": "Street Vendors",
    "vendors": "Street Vendors",
    "street vendor": "Street Vendors",
    "street vendors": "Street Vendors",
    "hawker": "Street Vendors",
    "hawkers": "Street Vendors",
    "senior citizen": "Senior Citizens",
    "senior citizens": "Senior Citizens",
    "elderly": "Senior Citizens",
}

POLICY_INTENT_TERMS = [
    "scholarship", "subsidy", "pension", "loan", "grant", "training",
    "allowance", "housing", "insurance", "financial assistance", "stipend"
]


def detect_language(text: str) -> str:
    """
    Detects language hint: 'hi' (Hindi / Devanagari), 'hi-en' (code-mixed / Hinglish), or 'en'.
    """
    if not text:
        return "en"
    has_devanagari = bool(re.search(r"[\u0900-\u097F]", text))
    has_latin = bool(re.search(r"[a-zA-Z]", text))

    if has_devanagari and not has_latin:
        return "hi"
    elif has_devanagari and has_latin:
        return "hi-en"
    
    # Check for common Hinglish transliteration markers (e.g. 'chahiye', 'yojana', 'kaise', 'milega')
    hinglish_markers = ["chahiye", "yojana", "kaise", "milega", "karen", "mujhe", "ke liye", "kya hai"]
    lower = text.lower()
    if any(m in lower for m in hinglish_markers):
        return "hi-en"

    return "en"


def normalize_query_intent(query_text: str) -> RetrievalIntent:
    """
    Analyzes user query to extract retrieval hints without making eligibility decisions.
    Missing attributes remain None.
    """
    raw = query_text.strip()
    lower = raw.lower()
    lang = detect_language(raw)

    detected_state: Optional[str] = None
    detected_category: Optional[str] = None
    detected_beneficiary: Optional[str] = None
    matched_intents: List[str] = []

    # State matching
    for alias, canonical in STATE_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", lower):
            detected_state = canonical.title()
            break
    if not detected_state:
        for state in INDIAN_STATES_KEYWORDS:
            if re.search(rf"\b{re.escape(state)}\b", lower):
                detected_state = state.title()
                break

    # Category matching
    for cat_kw, cat_canonical in CATEGORY_KEYWORDS.items():
        if re.search(rf"\b{re.escape(cat_kw)}\b", lower):
            detected_category = cat_canonical
            break

    # Beneficiary matching
    for ben_kw, ben_canonical in BENEFICIARY_KEYWORDS.items():
        if re.search(rf"\b{re.escape(ben_kw)}\b", lower):
            detected_beneficiary = ben_canonical
            break

    # Intent terms
    for term in POLICY_INTENT_TERMS:
        if term in lower:
            matched_intents.append(term)

    return RetrievalIntent(
        raw_query=raw,
        normalized_query=lower,
        language=lang,
        detected_state=detected_state,
        detected_category=detected_category,
        detected_beneficiary_type=detected_beneficiary,
        intent_terms=matched_intents
    )


def build_metadata_filter(query: RetrievalQuery) -> Optional[Callable[[Dict[str, Any]], bool]]:
    """
    Constructs a metadata predicate function based on user filter specification.
    Returns None if no filters are active.
    """
    filters = []

    if query.state_filter:
        req_state = query.state_filter.strip().lower()
        # State match allows state-specific matches OR national/central (All India) schemes
        filters.append(lambda m: (
            m.get("state") is None or
            str(m.get("state")).strip().lower() in (req_state, "all india", "central", "all")
        ))

    if query.category_filter:
        req_cat = query.category_filter.strip().lower()
        filters.append(lambda m: (
            m.get("category") is None or
            req_cat in str(m.get("category")).strip().lower() or
            "all" in str(m.get("category")).strip().lower()
        ))

    if query.beneficiary_filter:
        req_ben = query.beneficiary_filter.strip().lower()
        filters.append(lambda m: (
            m.get("beneficiary_type") is None or
            req_ben in str(m.get("beneficiary_type")).strip().lower()
        ))

    if query.content_type_filter:
        req_ct = query.content_type_filter.strip().lower()
        filters.append(lambda m: (
            str(m.get("content_type", "")).strip().lower() == req_ct
        ))

    if not filters:
        return None

    return lambda meta: all(f(meta) for f in filters)