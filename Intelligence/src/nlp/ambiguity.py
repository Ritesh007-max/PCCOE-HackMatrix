"""
FIN Ambiguity Detection Engine.
Identifies approximate values, missing units, entity confusion,
and unverified residency claims in citizen statements.
"""

import re
from typing import List, Optional
import sys
from pathlib import Path

_CUR = Path(__file__).resolve()
while _CUR.name != "Intelligence" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_INTELLIGENCE_DIR = _CUR
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

try:
    from ..llm.models import AmbiguityRecord, AmbiguityType
except (ImportError, ValueError):
    from src.llm.models import AmbiguityRecord, AmbiguityType


APPROX_PATTERNS = [
    re.compile(r"\b(around|about|approx|approximately|nearly|almost|close to)\s+([\w\.\d]+)", re.IGNORECASE),
    re.compile(r"\b(lagbhag|aaspas|karib|kariban)\s+([\w\.\d]+)", re.IGNORECASE),
    re.compile(r"(लगभग|करीब|आसपास)\s*([\w\.\d]+)"),
]

LAND_WITHOUT_SIZE_PATTERNS = [
    re.compile(r"\b(i\s+own\s+land|have\s+land|own\s+property|own\s+agricultural\s+land)\b", re.IGNORECASE),
    re.compile(r"\b(mere\s+paas\s+zameen\s+hai|khet\s+hai|zameen\s+hai)\b", re.IGNORECASE),
    re.compile(r"(मेरे\s+पास\s+ज़मीन\s+है|खेत\s+है|भूमि\s+है)"),
]

THIRD_PARTY_PATTERNS = [
    re.compile(r"\b(my\s+(?:father|mother|brother|sister|spouse|husband|wife|son|daughter)\s+is\s+a?\s*([a-zA-Z]+))\b", re.IGNORECASE),
    re.compile(r"\b(mere\s+(?:pitaji|pita|mataji|bhai|pati|patni)\s+([a-zA-Z]+)\s+hain)\b", re.IGNORECASE),
    re.compile(r"(मेरे\s+(?:पिताजी|पिता|माताजी|भाई|पति|पत्नी)\s+([^\s]+)\s+हैं)"),
]

TEMPORARY_RESIDENCE_PATTERNS = [
    re.compile(r"\b(i\s+live\s+in|currently\s+staying\s+in|residing\s+in|staying\s+in)\s+([a-zA-Z\s]+)\b", re.IGNORECASE),
    re.compile(r"\b(main\s+abhi\s+([a-zA-Z]+)\s+mein\s+rehta\s+hoon)\b", re.IGNORECASE),
    re.compile(r"(मैं\s+अभी\s+([^\s]+)\s+में\s+रहता\s+हूँ)"),
]


class AmbiguityDetector:
    """Detects statutory, financial, and relational ambiguities in natural language."""

    def detect_ambiguities(self, text: str) -> List[AmbiguityRecord]:
        if not text or not text.strip():
            return []

        ambiguities: List[AmbiguityRecord] = []
        raw = text.strip()

        # 1. Approximate values
        for pat in APPROX_PATTERNS:
            match = pat.search(raw)
            if match:
                ambiguities.append(
                    AmbiguityRecord(
                        ambiguity_type=AmbiguityType.APPROXIMATE_VALUE,
                        raw_span=match.group(0),
                        description="Approximate or estimated value provided rather than certified amount.",
                        suggested_clarification="Please provide exact certified statutory amount or certificate value."
                    )
                )

        # 2. Land ownership declared without land size / unit
        for pat in LAND_WITHOUT_SIZE_PATTERNS:
            match = pat.search(raw)
            if match:
                # Check if numbers + units (acre/hectare/bigha) are actually present nearby
                has_units = bool(re.search(r"\b\d+\s*(?:acres?|hectares?|bigha|guntha)\b", raw, re.IGNORECASE))
                if not has_units:
                    ambiguities.append(
                        AmbiguityRecord(
                            ambiguity_type=AmbiguityType.MISSING_UNIT,
                            field="landholding_hectares",
                            raw_span=match.group(0),
                            description="Land ownership stated without specifying exact area or units.",
                            suggested_clarification="Please specify exact land area and measurement unit (e.g. 1.5 hectares or 2 acres)."
                        )
                    )

        # 3. Third-party family member attribute vs applicant attribute
        for pat in THIRD_PARTY_PATTERNS:
            match = pat.search(raw)
            if match:
                ambiguities.append(
                    AmbiguityRecord(
                        ambiguity_type=AmbiguityType.ENTITY_CONFUSION,
                        raw_span=match.group(0),
                        description="Family member's status stated instead of applicant's direct status.",
                        suggested_clarification="Please confirm if this attribute applies to the applicant or a family member."
                    )
                )

        # 4. Current residence vs Permanent domicile
        for pat in TEMPORARY_RESIDENCE_PATTERNS:
            match = pat.search(raw)
            if match:
                ambiguities.append(
                    AmbiguityRecord(
                        ambiguity_type=AmbiguityType.TEMPORARY_RESIDENCE,
                        field="state",
                        raw_span=match.group(0),
                        description="Current place of residence stated; does not prove permanent domicile.",
                        suggested_clarification="Please confirm if you hold a valid permanent domicile certificate for this state."
                    )
                )

        return ambiguities