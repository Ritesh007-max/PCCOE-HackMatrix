"""
FIN Query Reference and Entity Resolution Engine.
Resolves:
1. Explicit and pronoun/follow-up scheme references (e.g., 'What is PMJAY?' -> 'Am I eligible for it?').
2. Document references against ApplicantContext.documents.
3. Personal fact key references and ambiguity detection (e.g. personal vs family income).
4. Missing required statutory facts detection.
"""

import re
from typing import Any, Dict, List, Optional, Tuple, Set

from src.context.models import ApplicantContext, DocumentContext
from src.extraction.models import ApplicantFact


# Well-known Indian central and state welfare scheme acronyms & slugs
KNOWN_SCHEME_PATTERNS = [
    (r"\b(?:pmjay|ayushman\s+bharat|pm-jay)\b", "PMJAY"),
    (r"\b(?:pmegp|prime\s+minister\s+employment\s+generation\s+programme)\b", "PMEGP"),
    (r"\b(?:mudra|pm\s+mudra|pm-mudra)\b", "MUDRA"),
    (r"\b(?:pm-kisan|pm\s+kisan|pmkisan)\b", "PM-KISAN"),
    (r"\b(?:pm-awas|pm\s+awas|pmawasyojana|pmay)\b", "PMAY"),
    (r"\b(?:nsp|national\s+scholarship\s+portal)\b", "NSP"),
    (r"\b(?:post\s+matric\s+scholarship|pms)\b", "POST_MATRIC_SCHOLARSHIP"),
    (r"\b(?:sukanya\s+samriddhi|ssy)\b", "SUKANYA_SAMRIDDHI"),
    (r"\b(?:stand\s+up\s+india)\b", "STAND_UP_INDIA"),
]


class ReferenceResolver:
    """
    Resolves entity references across conversational turns, document attachments,
    and the canonical ApplicantContext snapshot.
    """

    def resolve_scheme_reference(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Extracts scheme reference from message or resolves follow-up pronouns ('it', 'this scheme').
        Returns (resolved_scheme, ambiguity_dict).
        """
        raw = message.strip()

        # 1. Direct match in message
        for pattern, scheme_id in KNOWN_SCHEME_PATTERNS:
            if re.search(pattern, raw, re.IGNORECASE):
                return (scheme_id, None)

        # Generic capitalized alphanumeric scheme code detection (e.g., "PMEGP", "PMJAY")
        cap_match = re.search(r"\b([A-Z]{3,10}(?:-[A-Z0-9]+)?)\b", raw)
        if cap_match and cap_match.group(1) not in ("THE", "AND", "FOR", "WHAT", "HOW", "WHY", "CAN", "ARE", "NOT"):
            return (cap_match.group(1), None)

        # 2. Check for follow-up pronoun referring to antecedent in conversation history
        # e.g., "Am I eligible for it?", "Tell me more about it", "Can I apply for this scheme?"
        pronoun_match = re.search(r"\b(?:for\s+it|about\s+it|this\s+scheme|that\s+scheme|the\s+scheme)\b", raw, re.IGNORECASE)
        if pronoun_match and conversation_history:
            found_schemes: List[str] = []
            for turn in reversed(conversation_history):
                content = str(turn.get("content") or turn.get("message") or turn.get("query") or "")
                for pattern, scheme_id in KNOWN_SCHEME_PATTERNS:
                    if re.search(pattern, content, re.IGNORECASE) and scheme_id not in found_schemes:
                        found_schemes.append(scheme_id)

            if len(found_schemes) == 1:
                return (found_schemes[0], None)
            elif len(found_schemes) > 1:
                # Multiple antecedents: Flag ambiguity rather than guessing!
                return (None, {
                    "type": "AMBIGUOUS_SCHEME_REFERENCE",
                    "options": found_schemes,
                    "message": f"Ambiguous follow-up reference: multiple schemes mentioned ({', '.join(found_schemes)})"
                })

        return (None, None)

    def resolve_document_reference(
        self,
        message: str,
        applicant_context: Optional[ApplicantContext] = None,
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Resolves document reference from message against documents in ApplicantContext.
        Returns (resolved_document_id_or_type, ambiguity_dict).
        """
        raw = message.strip().lower()

        doc_type_map = {
            "income certificate": "INCOME_CERTIFICATE",
            "income proof": "INCOME_CERTIFICATE",
            "salary slip": "INCOME_CERTIFICATE",
            "caste certificate": "CASTE_CERTIFICATE",
            "community certificate": "CASTE_CERTIFICATE",
            "domicile certificate": "DOMICILE_CERTIFICATE",
            "residence certificate": "DOMICILE_CERTIFICATE",
            "aadhaar": "AADHAAR_CARD",
            "aadhar": "AADHAAR_CARD",
            "pan": "PAN_CARD",
            "pan card": "PAN_CARD",
            "disability certificate": "DISABILITY_CERTIFICATE",
            "pwd certificate": "DISABILITY_CERTIFICATE",
        }

        # Strip negative instructions so "Do not show my uploaded documents" does not register as ANY_UPLOADED_DOCUMENT
        neg_pattern = (
            r"\b(?:do\s+not|don['\u2019]?t|dont|never|without|exclude|avoid|stop)\s+"
            r"(?:to\s+)?(?:show|display|use|utilize|search|check|inspect|look\s+at|include|refer\s+to|mention|rely\s+on)?\s*"
            r"[^.!?\n;]*(?:documents?|files?|certificates?|tickets?|applications?|vault|profile|records?)[^.!?\n;]*"
        )
        cleaned_raw = re.sub(neg_pattern, " ", raw, flags=re.IGNORECASE).strip()

        matched_types: List[str] = []
        for phrase, doc_type in doc_type_map.items():
            if phrase in cleaned_raw:
                matched_types.append(doc_type)

        if not matched_types:
            if "uploaded document" in cleaned_raw or "my document" in cleaned_raw or "the document" in cleaned_raw or "the pdf" in cleaned_raw:
                matched_types.append("ANY_UPLOADED_DOCUMENT")

        if not matched_types:
            return (None, None)

        if not applicant_context or not applicant_context.documents:
            return (matched_types[0], None)

        # Match against actual ingested documents
        matching_docs: List[DocumentContext] = []
        for doc in applicant_context.documents:
            if "ANY_UPLOADED_DOCUMENT" in matched_types or doc.document_type in matched_types:
                matching_docs.append(doc)

        if len(matching_docs) == 1:
            return (matching_docs[0].document_id, None)
        elif len(matching_docs) > 1:
            return (None, {
                "type": "AMBIGUOUS_DOCUMENT_REFERENCE",
                "matching_document_ids": [d.document_id for d in matching_docs],
                "message": f"Multiple matching documents found ({len(matching_docs)})"
            })
        else:
            return (matched_types[0], None)

    def resolve_personal_fact_reference(
        self,
        message: str,
        applicant_context: Optional[ApplicantContext] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[List[str], Optional[Dict[str, Any]]]:
        """
        Resolves personal fact keys referenced in an inquiry (e.g. 'What is my personal annual income?').
        Detects ambiguity if both personal income and family income exist in context.
        Supports multi-turn clarification when resolving follow-up replies ('personal' or 'family').
        Returns:
            (referenced_fact_keys, ambiguity_dict)
        """
        raw = message.strip().lower()

        # Check multi-turn clarification context from recent assistant message
        is_clarification_turn = False
        if conversation_history:
            for prev in reversed(conversation_history[-3:]):
                if prev.get("role") in ("assistant", "model", "system"):
                    p_content = prev.get("content", "").lower()
                    if "which one would you like to review" in p_content or ("personal" in p_content and "family" in p_content and "income" in p_content):
                        is_clarification_turn = True
                        break

        # Check explicit personal vs family tokens
        is_personal = bool(re.search(r"\b(?:personal|individual|my\s+salary|salary|own)\b", raw))
        is_family = bool(re.search(r"\b(?:family|household|parivar|total\s+family|gross\s+family)\b", raw))

        # Handle multi-turn clarification replies (e.g., user simply replies "personal" or "family")
        if is_clarification_turn or raw in ("personal", "personal income", "personal one", "my personal", "family", "family income", "household", "family one"):
            if is_personal and not is_family:
                return (["annual_income"], None)
            if is_family and not is_personal:
                return (["annual_family_income"], None)

        # Component-level income queries (Strict Income Semantics)
        if re.search(r"\b(?:father(?:\x27s|\'s)?\s+income|father\s+wage)\b", raw):
            return (["father_income"], None)
        if re.search(r"\b(?:mother(?:\x27s|\'s)?\s+income|mother\s+craft)\b", raw):
            return (["mother_income"], None)
        if re.search(r"\b(?:other\s+family\s+income|other\s+income)\b", raw):
            return (["other_income"], None)

        # 1. Income query
        if re.search(r"\b(?:income|aay|earnings|salary)\b", raw):
            # If the query specifically targets a page (e.g. "Page 2 including income assessment"),
            # it is a document-scoped retrieval request and must not trigger generic profile fact ambiguity.
            if re.search(r"\bpage\s+\d+\b", raw, re.IGNORECASE):
                return (["annual_family_income"], None)

            # Explicit Personal Income Query
            if is_personal and not is_family:
                return (["annual_income"], None)

            # Explicit Family / Household Income Query
            if is_family and not is_personal:
                return (["annual_family_income"], None)

            # Explicit query mentioning both
            if is_personal and is_family:
                return (["annual_income", "annual_family_income"], None)

            # Generic income query (e.g. "What is my income?")
            # Check ApplicantContext to see what exists
            if applicant_context:
                has_family = "annual_family_income" in applicant_context.canonical_facts
                has_personal = "annual_income" in applicant_context.canonical_facts

                if has_family and has_personal:
                    f_val = str(applicant_context.canonical_facts["annual_family_income"].value).replace("₹", "").replace(",", "").strip()
                    p_val = str(applicant_context.canonical_facts["annual_income"].value).replace("₹", "").replace(",", "").strip()
                    if f_val == p_val or not f_val or not p_val:
                        return (["annual_family_income"], None)

                    # BOTH EXIST WITH DIFFERENT VALUES: AMBIGUITY!
                    return (
                        ["annual_income", "annual_family_income"],
                        {
                            "type": "AMBIGUOUS_INCOME_REFERENCE",
                            "candidate_keys": ["annual_income", "annual_family_income"],
                            "message": (
                                "Both personal annual income and family annual income are available in your records. "
                                "Which one would you like to review?"
                            )
                        }
                    )
                elif has_personal and not has_family:
                    return (["annual_income"], None)
                elif has_family and not has_personal:
                    return (["annual_family_income"], None)
                else:
                    return (["annual_family_income"], None)
            return (["annual_family_income"], None)

        # 2. Identity Queries: Full Name, Certificate Number, Date of Birth, District
        if re.search(r"\b(?:full\s+name|applicant\s+name|beneficiary\s+name|my\s+name|naam)\b", raw):
            return (["beneficiary_name"], None)

        if re.search(r"\b(?:certificate\s+(?:number|no\.?)|cert\s+no|doc(?:ument)?\s+(?:number|no\.?)|registration\s+no)\b", raw):
            return (["document_number"], None)

        if re.search(r"\b(?:date\s+of\s+birth|dob|birth\s+date|janma\s+tarikh)\b", raw):
            return (["date_of_birth"], None)

        if re.search(r"\b(?:district|jilla|zila)\b", raw):
            return (["district"], None)

        if re.search(r"\b(?:pan(?:\s+card)?(?:\s+number)?)\b", raw, re.IGNORECASE):
            return (["pan_number"], None)

        if re.search(r"\b(?:aadhaar(?:\s+card)?(?:\s+number)?)\b", raw, re.IGNORECASE):
            return (["aadhaar_number"], None)

        # 3. Age query
        if re.search(r"\b(?:age|how\s+old|umr|उम्र)\b", raw):
            return (["age"], None)

        # 4. State query
        if re.search(r"\b(?:state|domicile|residence|live\s+in|rajya)\b", raw):
            return (["state"], None)

        # 5. Category query
        if re.search(r"\b(?:category|caste|social\s+category|jati)\b", raw):
            return (["social_category"], None)

        # 6. Student query
        if re.search(r"\b(?:student|school|college|class)\b", raw):
            return (["is_student"], None)

        # 7. Occupation query
        if re.search(r"\b(?:occupation|profession|job|work)\b", raw):
            return (["occupation"], None)

        return ([], None)

    def check_missing_required_facts(
        self,
        message: str,
        referenced_scheme: Optional[str],
        applicant_context: Optional[ApplicantContext],
    ) -> List[str]:
        """
        Determines if a query depends on facts that are missing in the applicant's context.
        e.g., 'Am I eligible based on my income?' when no income exists in context.
        """
        missing: List[str] = []
        raw = message.strip().lower()

        if not applicant_context:
            return missing

        # User asks about eligibility based on income
        if "based on my income" in raw or "with my income" in raw:
            has_inc = (
                applicant_context.get_fact("annual_family_income") is not None or
                applicant_context.get_fact("annual_income") is not None
            )
            if not has_inc:
                missing.append("annual_family_income")

        # User asks about eligibility based on age
        if "based on my age" in raw:
            if applicant_context.get_fact("age") is None:
                missing.append("age")

        # User asks general missing information
        if "missing" in raw or "what information are you missing" in raw:
            # Report core standard fields absent from context
            core_fields = ["age", "state", "annual_family_income", "social_category"]
            for f in core_fields:
                if applicant_context.get_fact(f) is None:
                    missing.append(f)

        return missing
