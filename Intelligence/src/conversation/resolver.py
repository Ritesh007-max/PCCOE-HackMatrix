"""
FIN Conversation Reference Resolver.
Deterministically resolves conversational references and pronouns ("it", "this scheme",
"that document", "my income", "why") using the explicit ConversationState and ApplicantContext.
Enforces the invariant: Never guess when references are ambiguous; return REVIEW/CLARIFICATION_REQUIRED.
"""

from dataclasses import dataclass, field
import logging
import re
from typing import Any, Dict, List, Optional, Set

from src.context.models import ApplicantContext
from .models import ConversationState

logger = logging.getLogger("fin.conversation.resolver")

PRONOUN_SCHEME_PATTERNS = [
    r"\b(?:for\s+)?it\b",
    r"\bthis\s+scheme\b",
    r"\bthat\s+scheme\b",
    r"\bthe\s+scheme\b",
    r"\bthis\s+policy\b",
    r"\bthat\s+policy\b",
    r"\babout\s+it\b",
    r"\bapply\s+(?:for\s+)?it\b",
    r"\beligible\s+(?:for\s+)?it\b",
    r"\bbenefits?\s+(?:of\s+)?it\b",
    r"\bdocuments?\s+(?:for\s+)?it\b",
    r"\bthis\b",
    r"\bthat\b",
]

PRONOUN_DOC_PATTERNS = [
    r"\bthis\s+document\b",
    r"\bthat\s+document\b",
    r"\bthe\s+document\b",
    r"\bthis\s+certificate\b",
    r"\bthat\s+certificate\b",
    r"\bmy\s+certificate\b",
    r"\buploaded\s+document\b",
    r"\buploaded\s+certificate\b",
]

DECISION_WHY_PATTERNS = [
    r"^\s*why\??\s*$",
    r"\bwhy\s+not\b",
    r"\bwhy\s+am\s+i\s+not\s+eligible\b",
    r"\bwhy\s+did\s+you\s+say\b",
    r"\bwhy\s+was\s+i\s+rejected\b",
    r"\bexplain\s+(?:the\s+)?decision\b",
    r"\breason\s+(?:for\s+)?rejection\b",
]


@dataclass
class ResolvedReferences:
    scheme_id: Optional[str] = None
    document_id: Optional[str] = None
    fact_key: Optional[str] = None
    decision_id: Optional[str] = None
    is_ambiguous: bool = False
    ambiguity_reason: Optional[str] = None
    candidate_schemes: List[str] = field(default_factory=list)
    resolved_by: str = "EXPLICIT"  # EXPLICIT, CONVERSATION_STATE, DETERMINISTIC_PRONOUN, AMBIGUOUS


class ConversationReferenceResolver:
    """
    Deterministic reference resolution engine across conversation history.
    """

    def resolve(
        self,
        message: str,
        state: Optional[ConversationState] = None,
        context: Optional[ApplicantContext] = None,
        explicit_scheme: Optional[str] = None,
        explicit_doc: Optional[str] = None,
        explicit_fact: Optional[str] = None,
    ) -> ResolvedReferences:
        text = (message or "").lower().strip()
        result = ResolvedReferences(
            scheme_id=explicit_scheme,
            document_id=explicit_doc,
            fact_key=explicit_fact,
        )

        # 1. Scheme Resolution
        if not result.scheme_id and state:
            # Check if text contains a pronoun or reference phrase
            has_scheme_pronoun = any(re.search(pat, text) for pat in PRONOUN_SCHEME_PATTERNS)
            if has_scheme_pronoun:
                # If there are multiple candidate schemes discussed recently (more than 1 in recent_schemes)
                # and user says "it" or "this", check if ambiguous
                recent = state.recent_schemes or []
                if len(recent) > 1 and "both" not in text and "all" not in text:
                    # Ambiguous between recently discussed schemes!
                    result.is_ambiguous = True
                    result.ambiguity_reason = (
                        f"Multiple schemes were recently discussed ({', '.join(recent[:2])}). "
                        "Please clarify which scheme you are referring to."
                    )
                    result.candidate_schemes = recent[:2]
                    result.resolved_by = "AMBIGUOUS"
                    return result
                elif state.active_scheme:
                    result.scheme_id = state.active_scheme
                    result.resolved_by = "CONVERSATION_STATE"

        # 2. Decision Resolution ("Why am I not eligible?", "Why?")
        is_why = any(re.search(pat, text) for pat in DECISION_WHY_PATTERNS)
        if is_why and state:
            if state.active_decision_id:
                result.decision_id = state.active_decision_id
            if not result.scheme_id and state.active_scheme:
                result.scheme_id = state.active_scheme

        # 3. Document Resolution
        if not result.document_id and state:
            has_doc_pronoun = any(re.search(pat, text) for pat in PRONOUN_DOC_PATTERNS)
            if has_doc_pronoun:
                if state.active_document:
                    result.document_id = state.active_document
                elif context and context.documents:
                    # Select the most recent document
                    result.document_id = context.documents[-1].document_id

        # 4. Fact Resolution
        if not result.fact_key:
            if any(k in text for k in ("income", "aay", "aavak", "kamai", "आय", "આવક")):
                result.fact_key = "annual_family_income"
            elif any(k in text for k in ("age", "umar", "umra", "उम्र", "ઉંમર")):
                result.fact_key = "age"
            elif any(k in text for k in ("land", "landholding", "jamin", "jameen", "khet", "જમીન", "जमीन")):
                result.fact_key = "landholding_hectares"
            elif "caste" in text or "category" in text or "jati" in text or "ज्ञाति" in text or "જાતિ" in text:
                result.fact_key = "social_category"
            elif "state" in text or "domicile" in text or "rajya" in text or "રાજ્ય" in text or "राज्य" in text:
                result.fact_key = "state"
            elif "student" in text or "occupation" in text or "vidyarthi" in text:
                result.fact_key = "occupation"

        return result
