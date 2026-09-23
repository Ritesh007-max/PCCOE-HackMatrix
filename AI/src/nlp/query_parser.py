"""
PolicySetu Query Entity & Search Hint Extractor.
Parses multi-lingual text to extract search intent hints (states, categories, domains, beneficiaries).
CRITICAL INVARIANT: QueryIntent entities are RETRIEVAL HINTS ONLY.
They must NEVER automatically become ApplicantFacts unless the user explicitly makes
a first-person self-declaration.
"""

import re
from typing import Any, Dict, List, Optional, Tuple, Set

# Indian States and UTs dictionary (English, Devanagari, and transliterated)
STATES_MAP: Dict[str, str] = {
    "andhra pradesh": "Andhra Pradesh", "arunachal pradesh": "Arunachal Pradesh", "assam": "Assam",
    "bihar": "Bihar", "chhattisgarh": "Chhattisgarh", "goa": "Goa", "gujarat": "Gujarat",
    "haryana": "Haryana", "himachal pradesh": "Himachal Pradesh", "jharkhand": "Jharkhand",
    "karnataka": "Karnataka", "kerala": "Kerala", "madhya pradesh": "Madhya Pradesh",
    "maharashtra": "Maharashtra", "manipur": "Manipur", "meghalaya": "Meghalaya", "mizoram": "Mizoram",
    "nagaland": "Nagaland", "odisha": "Odisha", "punjab": "Punjab", "rajasthan": "Rajasthan",
    "sikkim": "Sikkim", "tamil nadu": "Tamil Nadu", "telangana": "Telangana", "tripura": "Tripura",
    "uttar pradesh": "Uttar Pradesh", "uttarakhand": "Uttarakhand", "west bengal": "West Bengal",
    "delhi": "Delhi", "jammu and kashmir": "Jammu and Kashmir", "ladakh": "Ladakh",
    # Hindi Devanagari mappings
    "गुजरात": "Gujarat", "महाराष्ट्र": "Maharashtra", "राजस्थान": "Rajasthan",
    "उत्तर प्रदेश": "Uttar Pradesh", "मध्य प्रदेश": "Madhya Pradesh", "बिहार": "Bihar",
    "पंजाब": "Punjab", "हरियाणा": "Haryana", "कर्नाटक": "Karnataka", "दिल्ली": "Delhi",
    "पश्चिम बंगाल": "West Bengal", "केरल": "Kerala", "तमिलनाडु": "Tamil Nadu",
}

# Social Category mappings
CATEGORIES_MAP: Dict[str, str] = {
    "sc": "SC", "scheduled caste": "SC", "अनुसूचित जाति": "SC", "एससी": "SC", "एस.सी.": "SC",
    "st": "ST", "scheduled tribe": "ST", "अनुसूचित जनजाति": "ST", "एसटी": "ST", "एस.टी.": "ST",
    "obc": "OBC", "other backward class": "OBC", "अन्य पिछड़ा वर्ग": "OBC", "पिछड़ा वर्ग": "OBC", "ओबीसी": "OBC", "ओ.बी.सी.": "OBC",
    "ews": "EWS", "economically weaker section": "EWS", "आर्थिक रूप से कमजोर": "EWS", "ईडब्ल्यूएस": "EWS",
    "general": "General", "gen": "General", "सामान्य": "General", "खुला": "General",
}

# Beneficiary Type mappings
BENEFICIARY_MAP: Dict[str, str] = {
    "student": "student", "students": "student", "छात्र": "student", "छात्रों": "student",
    "vidyarthi": "student", "chhatra": "student", "scholarship": "student", "छात्रवृत्ति": "student", "matric": "student",
    "farmer": "farmer", "farmers": "farmer", "किसान": "farmer", "kisan": "farmer",
    "kheti": "farmer", "krishi": "farmer",
    "woman": "woman", "women": "woman", "महिला": "woman", "महिलाओं": "woman", "mahila": "woman",
    "senior citizen": "senior_citizen", "elderly": "senior_citizen", "वरिष्ठ नागरिक": "senior_citizen",
    "buzurg": "senior_citizen", "vriddha": "senior_citizen",
    "disabled": "disabled", "disability": "disabled", "दिव्यांग": "disabled",
    "विकलांग": "disabled", "pwd": "disabled", "viklang": "disabled",
    "artisan": "artisan", "weavers": "artisan", "कारीगर": "artisan", "bunkar": "artisan",
}

# Policy Domain mappings
DOMAIN_MAP: Dict[str, str] = {
    "scholarship": "Education & Learning", "छात्रवृत्ति": "Education & Learning",
    "education": "Education & Learning", "padhai": "Education & Learning",
    "agriculture": "Agriculture & Rural", "kisan": "Agriculture & Rural",
    "farming": "Agriculture & Rural", "krishi": "Agriculture & Rural",
    "housing": "Housing & Shelter", "आवास": "Housing & Shelter", "awas": "Housing & Shelter",
    "health": "Health & Family Welfare", "swasthya": "Health & Family Welfare",
    "hospital": "Health & Family Welfare", "ayushman": "Health & Family Welfare",
    "pension": "Social Welfare & Security", "पेंशन": "Social Welfare & Security",
}

# Self-reference markers indicating first-person applicant facts
SELF_DECLARATION_MARKERS = [
    re.compile(r"\b(i am|my age|my income|my family|i live|i have|i own|i hold)\b", re.IGNORECASE),
    re.compile(r"\b(मेरी उम्र|मेरी आय|मेरा परिवार|मैं|मेरे पास|मेरी जाति|मेरे पिता)\b"),
    re.compile(r"\b(meri age|meri income|mera parivar|main|mere paas|meri aay|mera naam)\b", re.IGNORECASE),
]


class QueryParser:
    """Extracts structured search hints and intent entities from query text."""

    @staticmethod
    def is_self_declaration(text: str) -> bool:
        """Determines if the text contains first-person declarations of applicant status."""
        for pattern in SELF_DECLARATION_MARKERS:
            if pattern.search(text):
                return True
        return False

    @classmethod
    def extract_search_hints(cls, text: str) -> Dict[str, Any]:
        """
        Extracts state, social category, beneficiary type, policy domain, and keywords.
        Returns a dictionary of retrieval hints.
        """
        lower = text.lower()
        hints: Dict[str, Any] = {
            "state": None,
            "social_category": None,
            "beneficiary_type": None,
            "policy_domain": None,
            "keywords": [],
        }

        # 1. State extraction
        for name, standard_state in STATES_MAP.items():
            if name.isascii():
                if re.search(r"\b" + re.escape(name) + r"\b", lower):
                    hints["state"] = standard_state
                    break
            elif name in text:
                hints["state"] = standard_state
                break

        # 2. Social category extraction
        for cat_term, std_cat in CATEGORIES_MAP.items():
            if cat_term.isascii():
                if re.search(r"\b" + re.escape(cat_term) + r"\b", lower):
                    hints["social_category"] = std_cat
                    break
            elif cat_term in text:
                hints["social_category"] = std_cat
                break

        # 3. Beneficiary type extraction
        for ben_term, std_ben in BENEFICIARY_MAP.items():
            if ben_term.isascii():
                if re.search(r"\b" + re.escape(ben_term) + r"\b", lower):
                    hints["beneficiary_type"] = std_ben
                    break
            elif ben_term in text:
                hints["beneficiary_type"] = std_ben
                break

        # 4. Policy domain extraction
        for dom_term, std_dom in DOMAIN_MAP.items():
            if dom_term.isascii():
                if re.search(r"\b" + re.escape(dom_term) + r"\b", lower):
                    hints["policy_domain"] = std_dom
                    break
            elif dom_term in text:
                hints["policy_domain"] = std_dom
                break

        # 5. Extract significant content keywords
        stopwords = {
            "the", "a", "an", "for", "in", "to", "of", "and", "is", "me", "my", "i", "are",
            "what", "how", "which", "show", "tell", "available", "scheme", "yojana", "ke",
            "liye", "hai", "kaunsi", "chahiye", "kya", "mein", "ko", "ki"
        }
        words = re.findall(r"[\w\u0900-\u097F]+", text.lower())
        keywords = [w for w in words if len(w) > 2 and w not in stopwords]
        hints["keywords"] = list(dict.fromkeys(keywords))[:8]

        return hints
