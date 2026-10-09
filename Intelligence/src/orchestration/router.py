"""
FIN Orchestration Request Router.
Maps Phase 18 CanonicalIntents and contextual markers to canonical RequestRoutes
without creating disjoint or competing intent taxonomies.
"""

import logging
import re
from typing import Optional

from src.query.models import CanonicalIntent, QueryUnderstandingResult
from .models import RequestRoute

logger = logging.getLogger("fin.orchestration.router")

WHY_PATTERNS = [
    r"^\s*why\??\s*$",
    r"\bwhy\s+not\b",
    r"\bwhy\s+am\s+i\s+not\s+eligible\b",
    r"\bwhy\s+did\s+you\s+say\b",
    r"\bwhy\s+was\s+i\s+rejected\b",
    r"\breason\s+(?:for\s+)?rejection\b",
    r"\bwhy\s+failed\b",
]

DOC_REQ_PATTERNS = [
    r"\bwhat\s+documents?\b",
    r"\bwhich\s+documents?\b",
    r"\brequired\s+documents?\b",
    r"\bdocuments?\s+(?:do\s+i\s+)?need\b",
    r"\bdocuments?\s+required\b",
    r"\bwhat\s+do\s+i\s+need\s+to\s+submit\b",
]

MISSING_INFO_PATTERNS = [
    r"\bmissing\s+information\b",
    r"\bwhat\s+is\s+missing\b",
    r"\bwhy\s+unknown\b",
    r"\bwhy\s+can\s+not\s+determine\b",
]

COMPARE_PATTERNS = [
    r"\bcompare\b",
    r"\bdifference\s+between\b",
    r"\bversus\b",
    r"\bvs\b",
]

CONFLICT_PATTERNS = [
    r"\bconflict\s+status\b",
    r"\breview\s+status\b",
    r"\bstatus\s+of\s+my\s+conflict\b",
]

BENEFIT_PATTERNS = [
    r"\bhow\s+much\s+(?:money|benefit|amount)\b",
    r"\bwhat\s+benefit\b",
    r"\bwhat\s+benefits\b",
    r"\bwhat\s+will\s+i\s+get\b",
]

PERSONAL_FACT_PATTERNS = [
    r"\bmy\s+(?:income|age|land|landholding|caste|category|residence|state|holding)\b",
    r"\bwhat\s+is\s+my\b",
    r"\btell\s+me\s+my\b",
    r"\bmeri\s+(?:aay|umar|jamin|jati)\b",
    r"\bmari\s+(?:aavak|umar|jamin|jati)\b",
    r"\bmera\s+",
    r"\bmaru\s+",
    r"મારી\s+આવક",
    r"मेरी\s+आय",
]


SCHEME_REC_PATTERNS = [
    r"\bwhat\s+schemes?\b",
    r"\bwhich\s+schemes?\b",
    r"\bschemes?\s+(?:are\s+)?available\b",
    r"\bschemes?\s+can\s+i\b",
    r"\bschemes?\s+for\s+me\b",
    r"\bavailable\s+schemes?\b",
    r"\bshow\s+schemes?\b",
    r"\bfind\s+schemes?\b",
]


class OrchestrationRouter:
    """
    Authoritative router translating semantic signals and context into an execution route.
    """

    def route(
        self,
        query_result: QueryUnderstandingResult,
        raw_message: str,
        active_scheme: Optional[str] = None,
        active_decision_id: Optional[str] = None,
    ) -> RequestRoute:
        text = (raw_message or "").lower().strip()

        # 0. Scheme Recommendation Queries
        if any(re.search(p, text) for p in SCHEME_REC_PATTERNS):
            return RequestRoute.SCHEME_RECOMMENDATION

        # 1. Specialized contextual patterns
        if any(re.search(p, text) for p in WHY_PATTERNS):
            return RequestRoute.DECISION_EXPLANATION

        if any(re.search(p, text) for p in DOC_REQ_PATTERNS):
            return RequestRoute.DOCUMENT_REQUIREMENTS

        if any(re.search(p, text) for p in MISSING_INFO_PATTERNS):
            return RequestRoute.MISSING_INFORMATION

        if any(re.search(p, text) for p in COMPARE_PATTERNS):
            return RequestRoute.SCHEME_COMPARISON

        if any(re.search(p, text) for p in CONFLICT_PATTERNS):
            return RequestRoute.CONFLICT_RESOLUTION_STATUS

        if any(re.search(p, text) for p in BENEFIT_PATTERNS):
            return RequestRoute.BENEFIT_QUERY

        if any(re.search(p, text) for p in PERSONAL_FACT_PATTERNS):
            return RequestRoute.PERSONAL_FACT_LOOKUP

        # 2. CanonicalIntent mappings
        intent = query_result.intent
        intent_val = intent.value if hasattr(intent, "value") else str(intent)
        if intent_val in ("PERSONAL_FACT_LOOKUP", "PERSONAL_FACT_QUERY"):
            return RequestRoute.PERSONAL_FACT_LOOKUP
        elif intent_val in ("DOCUMENT_QUERY", "DOCUMENT_EXTRACTION_QUERY"):
            return RequestRoute.DOCUMENT_QUERY
        elif intent_val in ("SCHEME_RECOMMENDATION", "SCHEME_DISCOVERY"):
            return RequestRoute.SCHEME_RECOMMENDATION
        elif intent_val in ("POLICY_INFORMATION", "SCHEME_DETAILS", "GENERAL_INFORMATION"):
            return RequestRoute.POLICY_INFORMATION
        elif intent_val in ("ELIGIBILITY_QUERY", "ELIGIBILITY_EVALUATION", "ELIGIBILITY_QUESTION"):
            return RequestRoute.ELIGIBILITY_QUERY
        elif intent_val in ("BENEFIT_QUERY", "BENEFIT_CALCULATION", "BENEFIT_QUESTION"):
            return RequestRoute.BENEFIT_QUERY
        elif intent_val in ("DOCUMENT_REQUIREMENTS", "APPLICATION_PROCESS"):
            return RequestRoute.DOCUMENT_REQUIREMENTS
        elif intent_val in ("DECISION_EXPLANATION",):
            return RequestRoute.DECISION_EXPLANATION
        elif intent_val in ("MISSING_INFORMATION",):
            return RequestRoute.MISSING_INFORMATION
        elif intent_val in ("COMPARISON", "SCHEME_COMPARISON"):
            return RequestRoute.SCHEME_COMPARISON
        elif intent_val in ("STATUS_TRACKING", "STATUS_QUERY"):
            return RequestRoute.CONFLICT_RESOLUTION_STATUS

        # 3. Fallback checks
        if "eligible" in text or "qualify" in text:
            return RequestRoute.ELIGIBILITY_QUERY
        if "document" in text or "certificate" in text:
            return RequestRoute.DOCUMENT_QUERY
        if "scheme" in text or "policy" in text or "available" in text:
            return RequestRoute.SCHEME_RECOMMENDATION

        return RequestRoute.GENERAL_FOLLOW_UP
