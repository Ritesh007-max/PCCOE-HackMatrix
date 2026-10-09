"""
FIN ApplicantContext to RetrievalQuery Deterministic Bridge.
Transforms canonical applicant facts and query understanding signals into a
parameterized RetrievalQuery without fabricating filters or guessing missing values.

CRITICAL INVARIANTS:
1. Hard filters are applied ONLY for metadata fields natively supported by RetrievalQuery
   (state, social_category, beneficiary_type).
2. Conflicted facts are NEVER converted into hard retrieval filters.
3. Unsupported fields (age, income, landholding, disability) belong strictly to
   downstream compatibility analysis and deterministic eligibility evaluation.
4. User semantic intent is preserved; the query string is never replaced with fact tokens.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from src.context.models import ApplicantContext
from src.query.models import QueryUnderstandingResult
from src.rag.models import RetrievalQuery
from src.rag.filters import STATE_ALIASES, CATEGORY_KEYWORDS

logger = logging.getLogger("fin.recommendation.bridge")

# Beneficiary value mappings supported by retrieval corpus
BENEFICIARY_MAPPINGS = {
    "student": "Student",
    "students": "Student",
    "farmer": "Farmer",
    "farmers": "Farmer",
    "kisan": "Farmer",
    "cultivator": "Farmer",
    "women": "Women",
    "woman": "Women",
    "female": "Women",
    "artisan": "Artisans",
    "artisans": "Artisans",
    "weaver": "Artisans",
    "street vendor": "Street Vendors",
    "street vendors": "Street Vendors",
    "vendor": "Street Vendors",
    "senior citizen": "Senior Citizens",
    "senior": "Senior Citizens",
    "elderly": "Senior Citizens",
}

# Standardized Social Categories
CANONICAL_CATEGORIES = {
    "sc": "SC",
    "st": "ST",
    "obc": "OBC",
    "ews": "EWS",
    "general": "General",
    "gen": "General",
    "scheduled caste": "SC",
    "scheduled tribe": "ST",
    "other backward": "OBC",
    "other backward class": "OBC",
    "economically weaker section": "EWS",
}


class ContextRetrievalBridge:
    """
    Deterministic bridge from ApplicantContext + QueryUnderstandingResult
    to an authoritative RetrievalQuery.
    """

    @staticmethod
    def build_retrieval_query(
        applicant_context: Optional[ApplicantContext],
        user_query: str,
        query_understanding: Optional[QueryUnderstandingResult] = None,
        top_k: int = 10,
        language: str = "en",
        state_override: Optional[str] = None,
        category_override: Optional[str] = None,
    ) -> Tuple[RetrievalQuery, Dict[str, Any]]:
        """
        Constructs a RetrievalQuery with validated metadata filters.
        Returns:
            Tuple of (RetrievalQuery, applied_filters_audit_dict)
        """
        # 1. Determine query text preserving user semantic intent while enriching with demographic context
        if query_understanding and query_understanding.normalized_message:
            base_query = query_understanding.normalized_message
        else:
            base_query = " ".join(user_query.strip().split()) if user_query else "government schemes"

        # Enrich query text with applicant facts (e.g. "student", "SC") for RAG retrieval
        enrichments = []
        if applicant_context:
            raw_occ = applicant_context.get_value("occupation")
            if raw_occ and str(raw_occ).lower() not in base_query.lower():
                enrichments.append(str(raw_occ))
            raw_cat = applicant_context.get_value("social_category") or applicant_context.get_value("caste_category")
            if raw_cat and str(raw_cat).lower() not in base_query.lower():
                enrichments.append(str(raw_cat))

        generic_queries = (
            "schemes matching my profile",
            "schemes matching my profile and state",
            "schemes for me",
            "government schemes",
            "schemes",
            "my schemes",
        )
        if enrichments and base_query.lower().strip() in generic_queries:
            query_text = f"{base_query} {' '.join(enrichments)}".strip()
        else:
            query_text = base_query

        # 2. Bounded top_k
        clamped_top_k = max(1, min(50, top_k))

        # 3. Extract and validate candidate filters from ApplicantContext
        state_filter: Optional[str] = None
        category_filter: Optional[str] = None
        beneficiary_filter: Optional[str] = None

        applied_filters: Dict[str, Any] = {}
        ignored_conflicts: List[str] = []
        unsupported_facts_preserved: List[str] = []

        if applicant_context:
            conflicts = set(applicant_context.conflicts)

            # State Filter mapping
            if state_override:
                state_filter = state_override.strip()
                applied_filters["state_filter"] = {"value": state_filter, "source": "explicit_override"}
            elif "state" in conflicts:
                ignored_conflicts.append("state")
                logger.info("State fact is in conflict for %s; omitting from hard retrieval filter.", applicant_context.applicant_id)
            else:
                raw_state = applicant_context.get_value("state")
                if raw_state and isinstance(raw_state, str) and raw_state.strip():
                    cleaned_state = raw_state.strip()
                    lower_state = cleaned_state.lower()
                    canonical_state = STATE_ALIASES.get(lower_state, cleaned_state).title()
                    state_filter = canonical_state
                    applied_filters["state_filter"] = {"value": state_filter, "source": "applicant_context"}

            # Category Filter mapping (handles social category acronyms and explicit overrides)
            if category_override:
                cov = category_override.strip()
                cat_lower = cov.lower()
                category_filter = CANONICAL_CATEGORIES.get(cat_lower, cov)
                applied_filters["category_filter"] = {"value": category_filter, "source": "explicit_override"}
            elif "social_category" in conflicts:
                ignored_conflicts.append("social_category")
                logger.info("Social category fact is in conflict for %s; omitting from retrieval filter.", applicant_context.applicant_id)
            else:
                raw_cat = applicant_context.get_value("social_category") or applicant_context.get_value("caste_category")
                if raw_cat and isinstance(raw_cat, str) and raw_cat.strip():
                    cat_lower = raw_cat.strip().lower()
                    category_filter = CANONICAL_CATEGORIES.get(cat_lower, raw_cat.strip().upper())
                    applied_filters["category_filter"] = {"value": category_filter, "source": "applicant_context"}

            # Beneficiary Filter mapping
            # Beneficiary can be derived from is_student=True, occupation, or gender
            if "is_student" not in conflicts and applicant_context.get_value("is_student") is True:
                beneficiary_filter = "Student"
                applied_filters["beneficiary_filter"] = {"value": "Student", "source": "is_student_fact"}
            elif "occupation" not in conflicts:
                raw_occ = applicant_context.get_value("occupation")
                if raw_occ and isinstance(raw_occ, str):
                    occ_lower = raw_occ.strip().lower()
                    if occ_lower in BENEFICIARY_MAPPINGS:
                        beneficiary_filter = BENEFICIARY_MAPPINGS[occ_lower]
                        applied_filters["beneficiary_filter"] = {"value": beneficiary_filter, "source": "occupation_fact"}

            # Track unsupported facts preserved for downstream compatibility
            all_canonical = applicant_context.canonical_facts
            for field_name in all_canonical:
                if field_name not in ("state", "social_category", "occupation", "is_student"):
                    unsupported_facts_preserved.append(field_name)

        # 4. If query understanding detected an explicit state/category in the user's specific prompt,
        # and no filter is set yet, we can use it as a retrieval hint
        if query_understanding:
            if not state_filter and query_understanding.metadata.get("detected_state"):
                state_filter = query_understanding.metadata["detected_state"]
                applied_filters["state_filter"] = {"value": state_filter, "source": "query_understanding"}
            if not category_filter and query_understanding.metadata.get("detected_category"):
                category_filter = query_understanding.metadata["detected_category"]
                applied_filters["category_filter"] = {"value": category_filter, "source": "query_understanding"}

        retrieval_query = RetrievalQuery(
            query_text=query_text,
            language=language or "en",
            top_k=clamped_top_k,
            state_filter=state_filter,
            category_filter=category_filter,
            beneficiary_filter=beneficiary_filter,
        )

        filter_audit = {
            "applied_filters": applied_filters,
            "ignored_conflicts": ignored_conflicts,
            "unsupported_facts_preserved": unsupported_facts_preserved,
        }

        return retrieval_query, filter_audit
