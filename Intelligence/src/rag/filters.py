"""
FIN Query Normalization and Metadata Filtering.
Extracts retrieval hints without making eligibility decisions, and builds
metadata filter predicates for vector and sparse search.
"""

import re
from typing import Any, Callable, Dict, List, Optional
import sys
from pathlib import Path

_CUR = Path(__file__).resolve()
while _CUR.name != "Intelligence" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_INTELLIGENCE_DIR = _CUR
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

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
        # Schemes with no explicit state are allowed ONLY if they are not explicitly marked as State-level
        def _matches_state(m):
            st = m.get("state")
            if st is not None and str(st).strip().lower() not in ("none", "nan", ""):
                return str(st).strip().lower() in (req_state, "all india", "central", "all", "pan india")
            lvl = str(m.get("level") or (m.get("metadata") or {}).get("level") or "").strip().lower()
            return lvl not in ("state", "state government")
        filters.append(_matches_state)


    if query.category_filter:
        req_cat = query.category_filter.strip().lower()
        is_social_cat = req_cat in ("sc", "st", "obc", "ews", "general", "all")

        def _matches_category(m: Dict[str, Any]) -> bool:
            cat_val = str(m.get("category") or "").strip().lower()
            soc_val = str(m.get("social_category") or (m.get("metadata") or {}).get("social_category") or "").strip().lower()
            target_val = str(m.get("target_beneficiaries") or "").strip().lower()
            desc_val = str(m.get("description") or "").strip().lower()

            if is_social_cat:
                # If social category filter (e.g. SC, OBC):
                # Matches if scheme category/soc is open/all, or explicitly includes applicant's category
                if not soc_val or soc_val in ("all", "all categories", "any", "general", "none", "", "nan"):
                    return True
                return req_cat in soc_val or req_cat in cat_val or req_cat in target_val or req_cat in desc_val
            else:
                return not cat_val or cat_val in ("all", "none", "", "nan") or req_cat in cat_val

        filters.append(_matches_category)

    if query.beneficiary_filter:
        req_ben = query.beneficiary_filter.strip().lower()
        # An individual citizen/student matches schemes for Individual, Family, All, or matching target_beneficiaries
        filters.append(lambda m: (
            m.get("beneficiary_type") is None or
            str(m.get("beneficiary_type")).strip().lower() in ("individual", "family", "all", "citizens", "citizen", "none", "nan") or
            req_ben in str(m.get("beneficiary_type")).strip().lower() or
            req_ben in str(m.get("target_beneficiaries", "")).strip().lower()
        ))

    if query.content_type_filter:
        req_ct = query.content_type_filter.strip().lower()
        filters.append(lambda m: (
            str(m.get("content_type", "")).strip().lower() == req_ct
        ))

    if not filters:
        return None

    return lambda meta: all(f(meta) for f in filters)