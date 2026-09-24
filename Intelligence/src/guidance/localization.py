"""
Multilingual Guidance and Localization Engine.
Phase 11: Seamless English, Hindi, and Hinglish translation.
Preserves machine-stable identifiers (scheme IDs, URLs, doc types, rule IDs) intact.
"""

from typing import Any, Dict, List, Optional
from src.nlp.language import LanguageDetector

# Canonical phrase dictionary for core guidance components
LOCALIZED_PHRASES: Dict[str, Dict[str, str]] = {
    # Readiness
    "READY_TO_APPLY": {
        "en": "Ready to apply",
        "hi": "आवेदन करने के लिए तैयार",
        "hinglish": "Apply karne ke liye ready",
    },
    "ACTION_REQUIRED": {
        "en": "Action required before applying",
        "hi": "आवेदन करने से पहले कार्रवाई आवश्यक है",
        "hinglish": "Apply karne se pehle action required hai",
    },
    "READY_FOR_REVIEW": {
        "en": "Under administrative review",
        "hi": "प्रशासनिक समीक्षा के अधीन",
        "hinglish": "Administrative review ke under hai",
    },
    "NOT_READY": {
        "en": "Not ready to apply",
        "hi": "आवेदन करने के लिए तैयार नहीं",
        "hinglish": "Apply karne ke liye ready nahi",
    },
    # Decisions
    "PASS_SUMMARY": {
        "en": "Your profile satisfies the evaluated eligibility criteria for this scheme.",
        "hi": "आपकी प्रोफ़ाइल इस योजना के मूल्यांकन किए गए पात्रता मानदंडों को पूरा करती है।",
        "hinglish": "Aapki profile is scheme ke evaluated eligibility criteria ko satisfy karti hai.",
    },
    "FAIL_SUMMARY": {
        "en": "You are not eligible under statutory criteria for this scheme.",
        "hi": "आप इस योजना के वैधानिक मानदंडों के तहत पात्र नहीं हैं।",
        "hinglish": "Aap is scheme ke statutory criteria ke mutabiq eligible nahi hain.",
    },
    "UNKNOWN_SUMMARY": {
        "en": "Eligibility cannot be determined because mandatory information is missing.",
        "hi": "पात्रता निर्धारित नहीं की जा सकती क्योंकि अनिवार्य जानकारी अनुपलब्ध है।",
        "hinglish": "Eligibility determine nahi ki ja sakti kyunki mandatory information missing hai.",
    },
    "REVIEW_SUMMARY": {
        "en": "Your application requires human caseworker review due to conflicting or ambiguous evidence.",
        "hi": "विरोधाभासी या अस्पष्ट साक्ष्यों के कारण आपके आवेदन की मानव समीक्षा आवश्यक है।",
        "hinglish": "Conflicting ya ambiguous evidence ke chalte aapke application ko caseworker review chahiye.",
    },
    # Common Actions
    "UPLOAD_DOCUMENT_TITLE": {
        "en": "Upload Required Document",
        "hi": "आवश्यक दस्तावेज़ अपलोड करें",
        "hinglish": "Required Document upload karein",
    },
    "PROVIDE_INFORMATION_TITLE": {
        "en": "Provide Profile Information",
        "hi": "प्रोफ़ाइल जानकारी प्रदान करें",
        "hinglish": "Profile information provide karein",
    },
    "RESOLVE_CONFLICT_TITLE": {
        "en": "Resolve Conflicting Data",
        "hi": "विरोधाभासी डेटा का समाधान करें",
        "hinglish": "Conflicting data resolve karein",
    },
    "VISIT_OFFICIAL_PORTAL_TITLE": {
        "en": "Visit Official Government Scheme Portal",
        "hi": "आधिकारिक सरकारी योजना पोर्टल पर जाएं",
        "hinglish": "Official government scheme portal visit karein",
    },
}


class GuidanceLocalizer:
    """
    Translates guidance summaries and action titles into target language
    while maintaining absolute machine identifier stability.
    """

    def __init__(self):
        self.language_detector = LanguageDetector()

    def detect_language(self, query: Optional[str]) -> str:
        """Detects language from query text or defaults to 'en'."""
        if not query or not query.strip():
            return "en"
        res = self.language_detector.detect(query)
        if res.language in ("hi", "hinglish"):
            return res.language
        return "en"

    def get_phrase(self, key: str, language: str = "en") -> str:
        """Retrieves localized phrase template."""
        lang_key = language if language in ("en", "hi", "hinglish") else "en"
        if key in LOCALIZED_PHRASES:
            return LOCALIZED_PHRASES[key].get(lang_key, LOCALIZED_PHRASES[key]["en"])
        return key

    def localize_eligibility_summary(self, summary: str, decision: str, language: str = "en") -> str:
        """Translates eligibility summary template."""
        if language == "en":
            return summary
        key = f"{decision}_SUMMARY"
        return self.get_phrase(key, language)

    def localize_readiness_reason(self, readiness_status: str, language: str = "en") -> str:
        """Translates readiness display string."""
        return self.get_phrase(readiness_status, language)

    def localize_action_title(self, action_type: str, fallback_title: str, language: str = "en") -> str:
        """Translates standard action title."""
        if language == "en":
            return fallback_title
        key = f"{action_type}_TITLE"
        if key in LOCALIZED_PHRASES:
            return self.get_phrase(key, language)
        return fallback_title
