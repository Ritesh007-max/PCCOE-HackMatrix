"""
FIN Multi-Lingual Language Detection.
Classifies input queries into English ('en'), Hindi Devanagari ('hi'),
or Hinglish Romanized Hindi ('hinglish').
"""

import re
from dataclasses import dataclass
from typing import Set, Tuple


# Common Romanized Hindi grammatical markers, pronouns, and governance lexemes
HINGLISH_MARKERS: Set[str] = {
    "mera", "meri", "mere", "mujhe", "mujhko", "main", "mein", "hum", "humara", "humari",
    "kaunsi", "kaunsa", "kaun", "yojana", "chahiye", "hai", "hain", "hoon", "tha", "the", "thi",
    "kya", "kyu", "kyon", "aur", "ke", "liye", "paas", "zameen", "saal", "aay", "parivar",
    "batao", "bhi", "nahi", "milegi", "milega", "kisan", "chhatra", "yojna", "karo", "karna",
    "kaise", "mile", "wala", "wali", "wale", "khet", "ghar", "lagbhag", "rupae", "rupaye"
}

DEVANAGARI_REGEX = re.compile(r"[\u0900-\u097F]")
LATIN_WORD_REGEX = re.compile(r"\b[a-zA-Z]{2,}\b")


@dataclass
class LanguageDetectionResult:
    language: str  # "en", "hi", "hinglish", "unknown"
    confidence: float
    script: str  # "Devanagari", "Latin", "Mixed", "Unknown"


class LanguageDetector:
    """Lightweight deterministic language detector for English, Hindi, and Hinglish."""

    def detect(self, text: str) -> LanguageDetectionResult:
        if not text or not text.strip():
            return LanguageDetectionResult(language="unknown", confidence=0.0, script="Unknown")

        raw = text.strip()
        devanagari_chars = len(DEVANAGARI_REGEX.findall(raw))
        total_chars = len(re.findall(r"\w", raw))

        if total_chars == 0:
            return LanguageDetectionResult(language="unknown", confidence=0.0, script="Unknown")

        devanagari_ratio = devanagari_chars / total_chars

        # If significant Devanagari characters are present, it is Hindi
        if devanagari_ratio >= 0.15:
            conf = min(1.0, 0.7 + devanagari_ratio * 0.3)
            return LanguageDetectionResult(
                language="hi",
                confidence=conf,
                script="Devanagari" if devanagari_ratio > 0.8 else "Mixed"
            )

        # Distinct grammatical markers that indicate Hindi grammar in Roman script
        grammatical_markers = {
            "mera", "meri", "mere", "mujhe", "mujhko", "main", "mein", "hum", "kaunsi",
            "kaunsa", "chahiye", "hai", "hain", "hoon", "tha", "the", "thi", "kya",
            "aur", "ke", "liye", "paas", "batao", "nahi", "milegi", "milega", "kaise",
            "karo", "karna", "aay", "parivar", "lagbhag"
        }
        english_indicators = {
            "how", "what", "which", "to", "apply", "for", "scheme", "schemes", "online",
            "eligibility", "documents", "required", "benefit", "amount", "under", "status",
            "scholarship", "available", "criteria"
        }

        words = [w.lower() for w in LATIN_WORD_REGEX.findall(raw)]
        if not words:
            return LanguageDetectionResult(language="unknown", confidence=0.0, script="Unknown")

        grammatical_hits = sum(1 for w in words if w in grammatical_markers)
        all_hinglish_hits = sum(1 for w in words if w in HINGLISH_MARKERS)
        english_hits = sum(1 for w in words if w in english_indicators)

        # If English syntax indicators strongly predominate and no grammatical Hinglish markers exist, it's English
        if english_hits >= 2 and grammatical_hits == 0:
            return LanguageDetectionResult(language="en", confidence=0.92, script="Latin")

        # Hinglish requires either at least 1 strong grammatical marker or multiple Hinglish hits
        if grammatical_hits >= 1 or all_hinglish_hits >= 2:
            conf = min(1.0, 0.70 + (grammatical_hits / len(words)) * 0.30)
            return LanguageDetectionResult(language="hinglish", confidence=conf, script="Latin")

        # Default to English for Latin text
        return LanguageDetectionResult(language="en", confidence=0.90, script="Latin")
