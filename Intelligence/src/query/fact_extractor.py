"""
FIN User Fact Extraction Engine.
Extracts candidate applicant facts from conversational citizen utterances.
Enforces:
1. source_type is strictly FactSourceType.USER_INPUT.
2. verification_status is strictly FactVerificationStatus.SELF_REPORTED.
3. Raw values are preserved verbatim alongside deterministic normalized values.
4. Semantic safety: Never infers unstated facts (e.g. 'I am a student' -> status only, no age/income).
5. Distinguishes personal income ('I earn 21 lakh') from family income ('My family income is...').
"""

import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from src.extraction.models import (
    ApplicantFact,
    Evidence,
    FactSourceType,
    FactVerificationStatus,
    CANONICAL_PROFILE_FIELDS,
)
from src.normalization.normalizer import normalize_field_value
from src.normalization.normalizer import INDIAN_STATES_AND_UTS, STATE_ALIASES


class UserFactExtractor:
    """
    Extracts structured statutory facts declared by the citizen in natural-language chat.
    Uses Phase 17 canonical models and deterministic normalizers.
    """

    def __init__(self):
        # Build states lookup regex
        sorted_states = sorted(
            list(INDIAN_STATES_AND_UTS) + list(STATE_ALIASES.keys()),
            key=len,
            reverse=True
        )
        self.state_pattern = re.compile(
            r"\b(?:in|live\s+in|reside\s+in|from|demicile\s+in|state\s+is\s+)?(" +
            "|".join(re.escape(s) for s in sorted_states) + r")\b",
            re.IGNORECASE
        )

    def extract_user_facts(
        self,
        text: str,
        applicant_id: str = "default_applicant",
    ) -> List[ApplicantFact]:
        """
        Extracts candidate facts from conversational input.
        Does NOT invent information not present in the text.
        """
        if not text or not text.strip():
            return []

        raw = text.strip()
        extracted: List[ApplicantFact] = []

        # 1. Age extraction
        # e.g., "I am 19", "my age is 19", "19 years old", "age: 19", "meri age 19"
        age_match = re.search(
            r"\b(?:i\s+am|my\s+age\s+is|age\s*[:=]|meri\s+age\s*[:=]?)\s*(\d{1,3})\b|"
            r"\b(\d{1,3})\s*(?:years?\s+old|saal|वर्ष)\b|"
            r"\bi\s+am\s+(\d{1,3})\b",
            raw,
            re.IGNORECASE
        )
        if age_match:
            raw_age = age_match.group(1) or age_match.group(2) or age_match.group(3)
            # Ensure it's not a currency number or other quantity
            if raw_age and int(raw_age) <= 120:
                normalized = normalize_field_value("age", raw_age, validate=False)
                fact = ApplicantFact(
                    id=f"ufact_{uuid.uuid4().hex[:12]}",
                    applicant_id=applicant_id,
                    field="age",
                    value=raw_age,
                    normalized_value=normalized,
                    data_type="numeric",
                    confidence=0.95,
                    source_type=FactSourceType.USER_INPUT,
                    source_document="user_dialogue",
                    text_span=age_match.group(0),
                    extraction_method="CONVERSATIONAL_EXTRACTION",
                    verification_status=FactVerificationStatus.SELF_REPORTED,
                    metadata={"raw_span": age_match.group(0)},
                )
                extracted.append(fact)

        # 2. Income extraction: Explicit distinction between personal income and family income
        # A. Explicit family income: "my family income is 800000", "family's income is 4.2 lakh"
        family_inc_match = re.search(
            r"(?:family(?:'s)?\s+income|annual\s+family\s+income|household\s+income|parivar\s+ki\s+aay)\s*"
            r"(?:is|=|:)?\s*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?\s*(?:lakhs?|lacs?|crores?|cr|k)?)|"
            r"(?:my\s+family\s+earns?\s*)(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?\s*(?:lakhs?|lacs?|crores?|cr|k)?)",
            raw,
            re.IGNORECASE
        )

        # B. Personal individual income: "I earn 21 lakh", "my personal income is 21 lakh", "my salary is 50000"
        personal_inc_match = re.search(
            r"(?:i\s+earn|my\s+personal\s+income|my\s+salary|personal\s+income)\s*"
            r"(?:is|=|:)?\s*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?\s*(?:lakhs?|lacs?|crores?|cr|k)?)",
            raw,
            re.IGNORECASE
        )

        # C. General income utterance: "my income is 21 lakhs", "income is 420000"
        general_inc_match = re.search(
            r"(?:my\s+income|annual\s+income|income)\s*(?:is|=|:)?\s*(?:₹|rs\.?|inr)?\s*"
            r"([\d,]+(?:\.\d+)?\s*(?:lakhs?|lacs?|crores?|cr|k)?)|"
            r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?\s*(?:lakhs?|lacs?|crores?|cr|k)?)\s+(?:income|annual\s+income)",
            raw,
            re.IGNORECASE
        )

        if family_inc_match:
            raw_val = (family_inc_match.group(1) or family_inc_match.group(2)).strip()
            norm_val = normalize_field_value("annual_family_income", raw_val, validate=False)
            fact = ApplicantFact(
                id=f"ufact_{uuid.uuid4().hex[:12]}",
                applicant_id=applicant_id,
                field="annual_family_income",
                value=raw_val,
                normalized_value=norm_val,
                data_type="numeric",
                confidence=0.95,
                source_type=FactSourceType.USER_INPUT,
                source_document="user_dialogue",
                text_span=family_inc_match.group(0),
                extraction_method="CONVERSATIONAL_EXTRACTION",
                verification_status=FactVerificationStatus.SELF_REPORTED,
                metadata={"income_type": "family_income", "raw_span": family_inc_match.group(0)},
            )
            extracted.append(fact)
        elif personal_inc_match:
            raw_val = personal_inc_match.group(1).strip()
            norm_val = normalize_field_value("annual_income", raw_val, validate=False)
            fact = ApplicantFact(
                id=f"ufact_{uuid.uuid4().hex[:12]}",
                applicant_id=applicant_id,
                field="annual_income",
                value=raw_val,
                normalized_value=norm_val,
                data_type="numeric",
                confidence=0.95,
                source_type=FactSourceType.USER_INPUT,
                source_document="user_dialogue",
                text_span=personal_inc_match.group(0),
                extraction_method="CONVERSATIONAL_EXTRACTION",
                verification_status=FactVerificationStatus.SELF_REPORTED,
                metadata={"income_type": "personal_income", "raw_span": personal_inc_match.group(0)},
            )
            extracted.append(fact)
        elif general_inc_match:
            raw_val = (general_inc_match.group(1) or general_inc_match.group(2)).strip()
            norm_val = normalize_field_value("annual_income", raw_val, validate=False)
            fact = ApplicantFact(
                id=f"ufact_{uuid.uuid4().hex[:12]}",
                applicant_id=applicant_id,
                field="annual_income",
                value=raw_val,
                normalized_value=norm_val,
                data_type="numeric",
                confidence=0.90,
                source_type=FactSourceType.USER_INPUT,
                source_document="user_dialogue",
                text_span=general_inc_match.group(0),
                extraction_method="CONVERSATIONAL_EXTRACTION",
                verification_status=FactVerificationStatus.SELF_REPORTED,
                metadata={"income_type": "general_income", "raw_span": general_inc_match.group(0)},
            )
            extracted.append(fact)

        # 3. State extraction
        # e.g., "I live in Gujarat", "from Maharashtra", "state is Rajasthan"
        state_match = re.search(
            r"\b(?:i\s+live\s+in|live\s+in|reside\s+in|from|state\s+(?:is|=|:))\s+([a-zA-Z\s]+)\b|"
            r"\b(?:in\s+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
            raw,
            re.IGNORECASE
        )
        if state_match:
            candidate_state = (state_match.group(1) or state_match.group(2) or "").strip()
            # Clean trailing punctuation
            candidate_state = re.sub(r"[^\w\s]", "", candidate_state).strip()
            # Check if it matches known state / alias
            norm_state = normalize_field_value("state", candidate_state, validate=False)
            if norm_state in INDIAN_STATES_AND_UTS:
                fact = ApplicantFact(
                    id=f"ufact_{uuid.uuid4().hex[:12]}",
                    applicant_id=applicant_id,
                    field="state",
                    value=candidate_state,
                    normalized_value=norm_state,
                    data_type="string",
                    confidence=0.95,
                    source_type=FactSourceType.USER_INPUT,
                    source_document="user_dialogue",
                    text_span=state_match.group(0),
                    extraction_method="CONVERSATIONAL_EXTRACTION",
                    verification_status=FactVerificationStatus.SELF_REPORTED,
                    metadata={"raw_span": state_match.group(0)},
                )
                extracted.append(fact)

        # 4. Social Category extraction
        # e.g. "my category is OBC", "I belong to SC", "category: General"
        cat_match = re.search(
            r"\b(?:category|caste|social\s+category|jati)\s*(?:is|=|:)?\s*(general|obc|sc|st|ews)\b|"
            r"\b(?:belong\s+to\s+)(general|obc|sc|st|ews)\b",
            raw,
            re.IGNORECASE
        )
        if cat_match:
            raw_cat = (cat_match.group(1) or cat_match.group(2)).strip().upper()
            norm_cat = normalize_field_value("social_category", raw_cat, validate=False)
            fact = ApplicantFact(
                id=f"ufact_{uuid.uuid4().hex[:12]}",
                applicant_id=applicant_id,
                field="social_category",
                value=raw_cat,
                normalized_value=norm_cat,
                data_type="string",
                confidence=0.95,
                source_type=FactSourceType.USER_INPUT,
                source_document="user_dialogue",
                text_span=cat_match.group(0),
                extraction_method="CONVERSATIONAL_EXTRACTION",
                verification_status=FactVerificationStatus.SELF_REPORTED,
                metadata={"raw_span": cat_match.group(0)},
            )
            extracted.append(fact)

        # 5. Student declaration
        # e.g., "I'm a student", "I am a student"
        # CRITICAL SAFETY INVARIANT: Only extracts student status. Never infers age or income!
        if re.search(r"\b(?:i\s+am\s+a\s+student|i['’]m\s+a\s+student|main\s+student\s+hoon)\b", raw, re.IGNORECASE):
            fact = ApplicantFact(
                id=f"ufact_{uuid.uuid4().hex[:12]}",
                applicant_id=applicant_id,
                field="is_student",
                value=True,
                normalized_value=True,
                data_type="boolean",
                confidence=0.95,
                source_type=FactSourceType.USER_INPUT,
                source_document="user_dialogue",
                text_span="student",
                extraction_method="CONVERSATIONAL_EXTRACTION",
                verification_status=FactVerificationStatus.SELF_REPORTED,
                metadata={"declared_status": "student"},
            )
            extracted.append(fact)

        # 6. Occupation declaration
        # e.g. "I am a farmer", "I am a driver"
        occ_match = re.search(
            r"\b(?:i\s+am\s+a\s+|main\s+)(farmer|kisan|artisan|weaver|laborer|driver|teacher)\b",
            raw,
            re.IGNORECASE
        )
        if occ_match:
            raw_occ = occ_match.group(1).strip()
            norm_occ = normalize_field_value("occupation", raw_occ, validate=False)
            fact = ApplicantFact(
                id=f"ufact_{uuid.uuid4().hex[:12]}",
                applicant_id=applicant_id,
                field="occupation",
                value=raw_occ,
                normalized_value=norm_occ,
                data_type="string",
                confidence=0.90,
                source_type=FactSourceType.USER_INPUT,
                source_document="user_dialogue",
                text_span=occ_match.group(0),
                extraction_method="CONVERSATIONAL_EXTRACTION",
                verification_status=FactVerificationStatus.SELF_REPORTED,
                metadata={"raw_span": occ_match.group(0)},
            )
            extracted.append(fact)

        return extracted
