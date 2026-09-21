"""
PolicySetu Multi-Lingual Intent Classifier.
Deterministic + LLM-assisted classification of citizen intents across English, Hindi, and Hinglish.
"""

import re
from typing import Optional, Tuple
import sys
from pathlib import Path

_CUR = Path(__file__).resolve()
while _CUR.name != "AI" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_AI_DIR = _CUR
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

try:
    from ..llm.models import UserIntent
except (ImportError, ValueError):
    from src.llm.models import UserIntent


# High-precision deterministic regular expressions for governance query intents
INTENT_PATTERNS = [
    (
        UserIntent.DOCUMENT_REQUIREMENTS,
        re.compile(
            r"\b(documents?|certificates?|proof|papers?|dastavej|kagaz|documents?\s+required|kya\s+document)\b|"
            r"(दस्तावेज़|कागजात|प्रमाणपत्र)",
            re.IGNORECASE
        ),
    ),
    (
        UserIntent.APPLICATION_PROCESS,
        re.compile(
            r"\b(how\s+to\s+apply|application\s+process|steps?\s+to\s+apply|registration|apply\s+online|"
            r"kaise\s+apply\s+kare|form\s+kaise\s+bhare|apply\s+karne\s+ka\s+tarika)\b|"
            r"(आवेदन\s+कैसे\s+करें|पंजीकरण|आवेदन\s+प्रक्रिया)",
            re.IGNORECASE
        ),
    ),
    (
        UserIntent.BENEFIT_QUESTION,
        re.compile(
            r"\b(how\s+much\s+(?:benefit|money|amount|grant|subsidy)|benefit\s+amount|financial\s+assistance|"
            r"kitna\s+(?:paisa|benefit|milega|amount)|subsidy\s+percentage)\b|"
            r"(कितना\s+(?:लाभ|पैसा|मिलेगा)|सहायता\s+राशि)",
            re.IGNORECASE
        ),
    ),
    (
        UserIntent.ELIGIBILITY_QUESTION,
        re.compile(
            r"\b(am\s+i\s+eligible|eligibility|can\s+i\s+(?:apply|get)|who\s+is\s+eligible|eligibility\s+criteria|"
            r"kya\s+(?:main|hum)\s+(?:bhi\s+)?eligible|mujhe\s+milegi\s+kya|kya\s+main\s+patra\s+hoon|patra\s+hoon|patrata)\b|"
            r"(पात्रता|पात्र\s*(?:हूँ|हैं|है|हो)?|क्या\s+मैं.*पात्र|कौन\s+पात्र\s+है)",
            re.IGNORECASE
        ),
    ),
    (
        UserIntent.STATUS_QUERY,
        re.compile(
            r"\b(status\s+of|track\s+(?:my\s+)?application|check\s+status|application\s+status|"
            r"status\s+kaise\s+check\s+kare)\b|"
            r"(स्थिति\s+जांचें|आवेदन\s+की\s+स्थिति)",
            re.IGNORECASE
        ),
    ),
    (
        UserIntent.COMPARISON,
        re.compile(
            r"\b(difference\s+between|compare|which\s+is\s+better|vs)\b|"
            r"(अंतर|तुलना)",
            re.IGNORECASE
        ),
    ),
    (
        UserIntent.SCHEME_DISCOVERY,
        re.compile(
            r"\b(scheme|schemes|yojana|yojna|scholarship|scholarships|subsidy|find|search|show\s+me|"
            r"list|options|kaunsi\s+yojana|yojana\s+batao|chahiye|milegi)\b|"
            r"(योजना|छात्रवृत्ति|योजनाएं|योजनाएँ|बताओ|चाहिए)",
            re.IGNORECASE
        ),
    ),
]


class IntentClassifier:
    """Classifies user intent using high-precision patterns with fallback to unknown/general."""

    def classify_intent(self, text: str) -> Tuple[UserIntent, Optional[UserIntent], float]:
        """
        Returns (primary_intent, secondary_intent, confidence).
        Deterministic, safe, offline.
        """
        if not text or not text.strip():
            return (UserIntent.UNKNOWN, None, 0.0)

        raw = text.strip()
        matched_intents = []

        for intent, pattern in INTENT_PATTERNS:
            if pattern.search(raw):
                matched_intents.append(intent)

        if not matched_intents:
            # If text has general query terms but no specific match
            if len(raw.split()) >= 3:
                return (UserIntent.GENERAL_INFORMATION, None, 0.50)
            return (UserIntent.UNKNOWN, None, 0.20)

        primary = matched_intents[0]
        secondary = matched_intents[1] if len(matched_intents) > 1 else None
        confidence = 0.95 if primary != UserIntent.GENERAL_INFORMATION else 0.60

        return (primary, secondary, confidence)