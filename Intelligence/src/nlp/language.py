"""
FIN Multi-Lingual Language Detection.
Classifies input queries into:
- English ('en')
- Hindi Devanagari ('hi')
- Gujarati ('gu')
- Hinglish Romanized Hindi ('hinglish')
- Tamil ('ta')
- Telugu ('te')
- Bengali ('bn')
- Marathi ('mr')
- Kannada ('kn')
- Malayalam ('ml')
- Punjabi ('pa')
"""

import re
from dataclasses import dataclass
from typing import Dict, Set, Tuple


# Common Romanized Hindi grammatical markers, pronouns, and governance lexemes
HINGLISH_MARKERS: Set[str] = {
    "mera", "meri", "mere", "mujhe", "mujhko", "main", "mein", "hum", "humara", "humari",
    "kaunsi", "kaunsa", "kaun", "yojana", "chahiye", "hai", "hain", "hoon", "tha", "thi",
    "kya", "kyu", "kyon", "aur", "ke", "liye", "paas", "zameen", "saal", "aay", "parivar",
    "batao", "bhi", "nahi", "milegi", "milega", "kisan", "chhatra", "yojna", "karo", "karna",
    "kaise", "mile", "wala", "wali", "wale", "khet", "ghar", "lagbhag", "rupae", "rupaye",
    "dastavez", "dastavej", "patra", "pramanpatra", "aavedan", "kripya", "sarkari", "laabh"
}

MARATHI_SPECIFIC_MARKERS: Set[str] = {
    "माझे", "माझी", "माझा", "मला", "आहे", "आहेत", "नाही", "कसे", "कशी", "मिळेल", "मिळणार",
    "करावे", "शासन", "कागदपत्रे", "कसा", "कोणती", "कोणत्या"
}

HINDI_SPECIFIC_MARKERS: Set[str] = {
    "है", "हैं", "नहीं", "मुझे", "चाहिए", "के बारे में", "क्या", "कौन", "कौनसी", "कौनसा",
    "का", "की", "के", "लिए", "बताओ", "मिलेगा", "मिलेगी", "आवेदन", "दस्तावेज"
}

SCRIPT_REGEXES: Dict[str, Tuple[re.Pattern, str]] = {
    "gu": (re.compile(r"[\u0A80-\u0AFF]"), "Gujarati"),
    "bn": (re.compile(r"[\u0980-\u09FF]"), "Bengali"),
    "ta": (re.compile(r"[\u0B80-\u0BFF]"), "Tamil"),
    "te": (re.compile(r"[\u0C00-\u0C7F]"), "Telugu"),
    "kn": (re.compile(r"[\u0C80-\u0CFF]"), "Kannada"),
    "ml": (re.compile(r"[\u0D00-\u0D7F]"), "Malayalam"),
    "pa": (re.compile(r"[\u0A00-\u0A7F]"), "Gurmukhi"),
}

DEVANAGARI_REGEX = re.compile(r"[\u0900-\u097F]")
LATIN_WORD_REGEX = re.compile(r"\b[a-zA-Z]{2,}\b")


@dataclass
class LanguageDetectionResult:
    language: str  # "en", "hi", "gu", "hinglish", "ta", "te", "bn", "mr", "kn", "ml", "pa", "unknown"
    confidence: float
    script: str  # "Devanagari", "Gujarati", "Tamil", "Latin", etc.


class LanguageDetector:
    """Multi-lingual deterministic language detector supporting Indian official languages, Hinglish, and English."""

    def detect(self, text: str) -> LanguageDetectionResult:
        if not text or not text.strip():
            return LanguageDetectionResult(language="unknown", confidence=0.0, script="Unknown")

        raw = text.strip()
        total_chars = len(re.findall(r"\w", raw))
        if total_chars == 0:
            return LanguageDetectionResult(language="unknown", confidence=0.0, script="Unknown")

        # 1. Non-Devanagari Indic scripts (Gujarati, Tamil, Bengali, Telugu, Kannada, Malayalam, Punjabi)
        for lang_code, (regex, script_name) in SCRIPT_REGEXES.items():
            script_chars = len(regex.findall(raw))
            if script_chars > 0 and (script_chars / total_chars) >= 0.12:
                conf = min(1.0, 0.75 + (script_chars / total_chars) * 0.25)
                return LanguageDetectionResult(language=lang_code, confidence=conf, script=script_name)

        # 2. Devanagari script (Hindi or Marathi)
        devanagari_chars = len(DEVANAGARI_REGEX.findall(raw))
        devanagari_ratio = devanagari_chars / total_chars

        if devanagari_ratio >= 0.15:
            conf = min(1.0, 0.7 + devanagari_ratio * 0.3)
            marathi_hits = sum(1 for m in MARATHI_SPECIFIC_MARKERS if m in raw)
            hindi_hits = sum(1 for h in HINDI_SPECIFIC_MARKERS if h in raw)

            if marathi_hits > hindi_hits and marathi_hits > 0:
                return LanguageDetectionResult(
                    language="mr",
                    confidence=conf,
                    script="Devanagari" if devanagari_ratio > 0.8 else "Mixed"
                )
            return LanguageDetectionResult(
                language="hi",
                confidence=conf,
                script="Devanagari" if devanagari_ratio > 0.8 else "Mixed"
            )

        # 3. Latin script: Distinguish English vs Hinglish
        grammatical_markers = {
            "mera", "meri", "mere", "mujhe", "mujhko", "main", "mein", "hum", "kaunsi",
            "kaunsa", "chahiye", "hai", "hain", "hoon", "tha", "thi", "kya",
            "aur", "ke", "liye", "paas", "batao", "nahi", "milegi", "milega", "kaise",
            "karo", "karna", "aay", "parivar", "lagbhag", "dastavez", "dastavej"
        }
        english_indicators = {
            "how", "what", "which", "to", "apply", "for", "scheme", "schemes", "online",
            "eligibility", "documents", "required", "benefit", "amount", "under", "status",
            "scholarship", "available", "criteria", "the", "is", "are", "can", "i", "tell",
            "me", "about", "application", "process", "program", "programme", "only", "of"
        }

        words = [w.lower() for w in LATIN_WORD_REGEX.findall(raw)]
        if not words:
            return LanguageDetectionResult(language="unknown", confidence=0.0, script="Unknown")

        grammatical_hits = sum(1 for w in words if w in grammatical_markers)
        all_hinglish_hits = sum(1 for w in words if w in HINGLISH_MARKERS)
        english_hits = sum(1 for w in words if w in english_indicators)

        # If standard English syntax indicators predominate, classify as English
        if english_hits >= 2 and english_hits >= grammatical_hits:
            return LanguageDetectionResult(language="en", confidence=0.95, script="Latin")

        # Hinglish requires either at least 1 strong grammatical marker or multiple Hinglish hits
        if grammatical_hits >= 1 or all_hinglish_hits >= 2:
            conf = min(1.0, 0.70 + (grammatical_hits / len(words)) * 0.30)
            return LanguageDetectionResult(language="hinglish", confidence=conf, script="Latin")

        return LanguageDetectionResult(language="en", confidence=0.92, script="Latin")
