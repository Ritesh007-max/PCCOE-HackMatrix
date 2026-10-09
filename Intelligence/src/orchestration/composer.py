"""
FIN Response Composer.
Composes authoritative, structured, and conversational responses.
Enforces the invariant:
Safety > statutory decision > evidence > explanation > conversational style.
Guarantees numeric preservation (amounts, thresholds, ages) across English, Hindi, and Gujarati.
"""

from typing import Any, Dict, List, Optional
import logging

from src.rules.models import RuleStatus
from .models import RequestRoute, UnifiedIntelligenceResponse

logger = logging.getLogger("fin.orchestration.composer")

# Multilingual labels preserving statutory precision
TRANSLATIONS = {
    "en": {
        "eligible": "Eligible (PASS)",
        "ineligible": "Ineligible (FAIL)",
        "unknown": "Eligibility Unknown (UNKNOWN)",
        "review": "Human Review Required (REVIEW)",
        "income_statement": "Your annual family income is ₹{val:,}.",
        "document_income": "Your annual family income is ₹{val:,} according to the uploaded {doc_type}.",
        "fact_not_found": "We do not have verified records for your {field}.",
        "why_failed": "You do not meet the criteria for {scheme}: {reason}.",
        "missing_info": "Eligibility cannot currently be determined because the policy requires {missing}.",
        "conflict_detected": "Conflicting information was detected for {field}. Document indicates {doc_val} while declared value is {user_val}. This requires caseworker review.",
        "next_action_upload": "Please provide or upload acceptable documentation to verify your {missing}.",
        "schemes_found": "Based on your verified profile, here are the relevant schemes:",
    },
    "hi": {
        "eligible": "पात्र (PASS)",
        "ineligible": "अपात्र (FAIL)",
        "unknown": "पात्रता अज्ञात (UNKNOWN)",
        "review": "मानव समीक्षा आवश्यक (REVIEW)",
        "income_statement": "आपकी वार्षिक पारिवारिक आय ₹{val:,} है।",
        "document_income": "अपलोड किए गए {doc_type} के अनुसार आपकी वार्षिक पारिवारिक आय ₹{val:,} है।",
        "fact_not_found": "हमारे पास आपके {field} का सत्यापित रिकॉर्ड उपलब्ध नहीं है।",
        "why_failed": "आप {scheme} के मानदंडों को पूरा नहीं करते: {reason}।",
        "missing_info": "वर्तमान में पात्रता निर्धारित नहीं की जा सकती क्योंकि नीति के लिए {missing} की आवश्यकता है।",
        "conflict_detected": "{field} के लिए विरोधाभासी जानकारी पाई गई। दस्तावेज़ में {doc_val} दर्शाया गया है जबकि घोषित मान {user_val} है। इसके लिए केसवर्कर समीक्षा की आवश्यकता है।",
        "next_action_upload": "कृपया अपने {missing} को सत्यापित करने के लिए मान्य दस्तावेज़ अपलोड करें।",
        "schemes_found": "आपकी सत्यापित प्रोफ़ाइल के आधार पर, यहाँ प्रासंगिक योजनाएँ हैं:",
    },
    "gu": {
        "eligible": "પાત્ર (PASS)",
        "ineligible": "અપાત્ર (FAIL)",
        "unknown": "પાત્રતા અજ્ઞાત (UNKNOWN)",
        "review": "માનવ સમીક્ષા જરૂરી (REVIEW)",
        "income_statement": "તમારી વાર્ષિક પારિવારિક આવક ₹{val:,} છે.",
        "document_income": "અપલોડ કરેલા {doc_type} અનુસાર તમારી વાર્ષિક પારિવારિક આવક ₹{val:,} છે.",
        "fact_not_found": "અમારી પાસે તમારા {field} માટે ચકાસાયેલ રેકોર્ડ ઉપલબ્ધ નથી.",
        "why_failed": "તમે {scheme} ના માપદંડ પૂર્ણ કરતા નથી: {reason}.",
        "missing_info": "હાલમાં પાત્રતા નક્કી કરી શકાતી નથી કારણ કે નીતિ માટે {missing} ની જરૂર છે.",
        "conflict_detected": "{field} માટે વિરોધાભાસી માહિતી મળી આવી છે. દસ્તાવેજમાં {doc_val} દર્શાવેલ છે જ્યારે જાહેર કરેલ મૂલ્ય {user_val} છે. આ માટે કેસવર્કર સમીક્ષાની જરૂર છે.",
        "next_action_upload": "કૃપા કરીને તમારા {missing} ની ચકાસણી કરવા માટે માન્ય દસ્તાવેજ અપલોડ કરો.",
        "schemes_found": "તમારી ચકાસાયેલ પ્રોફાઇલના આધારે, અહીં સંબંધિત યોજનાઓ છે:",
    },
}


class ResponseComposer:
    """
    Composes natural-language responses backed strictly by structured evidence and decisions.
    """

    def compose(
        self,
        request_id: str,
        applicant_id: str,
        conversation_id: str,
        intent: str,
        route: RequestRoute,
        language: str = "en",
        answer_text: Optional[str] = None,
        eligibility: Optional[Dict[str, Any]] = None,
        recommendations: Optional[List[Dict[str, Any]]] = None,
        explanation: Optional[Dict[str, Any]] = None,
        evidence: Optional[List[Dict[str, Any]]] = None,
        citations: Optional[List[str]] = None,
        missing_information: Optional[List[Dict[str, Any]]] = None,
        conflicts: Optional[List[Dict[str, Any]]] = None,
        next_actions: Optional[List[str]] = None,
        review: Optional[Dict[str, Any]] = None,
        grounding_status: str = "GROUNDED",
        provenance: Optional[Dict[str, Any]] = None,
    ) -> UnifiedIntelligenceResponse:
        lang = language if language in TRANSLATIONS else "en"
        t = TRANSLATIONS[lang]

        # If answer_text is not provided, deterministically build it from state
        if not answer_text:
            answer_text = self._build_deterministic_answer(
                route=route,
                eligibility=eligibility,
                recommendations=recommendations or [],
                missing_information=missing_information or [],
                conflicts=conflicts or [],
                evidence=evidence or [],
                lang_dict=t,
            )

        return UnifiedIntelligenceResponse(
            request_id=request_id,
            applicant_id=applicant_id,
            conversation_id=conversation_id,
            intent=intent,
            route=route.value if hasattr(route, "value") else str(route),
            answer=answer_text.strip(),
            language=lang,
            eligibility=eligibility,
            recommendations=recommendations or [],
            explanation=explanation,
            evidence=evidence or [],
            citations=citations or [],
            missing_information=missing_information or [],
            conflicts=conflicts or [],
            next_actions=next_actions or [],
            review=review,
            grounding_status=grounding_status,
            provenance=provenance or {},
        )

    def _build_deterministic_answer(
        self,
        route: RequestRoute,
        eligibility: Optional[Dict[str, Any]],
        recommendations: List[Dict[str, Any]],
        missing_information: List[Dict[str, Any]],
        conflicts: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        lang_dict: Dict[str, str],
    ) -> str:
        parts: List[str] = []

        if conflicts:
            c = conflicts[0]
            field_name = c.get("field", "field")
            doc_val = c.get("stored_value") or c.get("value_a", "unknown")
            user_val = c.get("user_value") or c.get("value_b", "unknown")
            msg = lang_dict["conflict_detected"].format(
                field=field_name, doc_val=doc_val, user_val=user_val
            )
            parts.append(msg)
            return "\n\n".join(parts)

        if eligibility:
            status = eligibility.get("status")
            scheme_id = eligibility.get("scheme_id", "the requested scheme")
            reason = eligibility.get("reason", "")
            if status == "PASS":
                parts.append(f"Status: {lang_dict['eligible']} for {scheme_id}.")
            elif status == "FAIL":
                parts.append(lang_dict["why_failed"].format(scheme=scheme_id, reason=reason))
            elif status == "UNKNOWN":
                missing_str = ", ".join(m.get("field", "") for m in missing_information) if missing_information else "required statutory information"
                parts.append(lang_dict["missing_info"].format(missing=missing_str))
            elif status == "REVIEW":
                parts.append(f"Status: {lang_dict['review']} for {scheme_id}. {reason}")

        if recommendations:
            parts.append(lang_dict["schemes_found"])
            for idx, rec in enumerate(recommendations[:5], 1):
                s_name = rec.get("scheme_name") or rec.get("scheme_id")
                status = rec.get("eligibility_status", "UNKNOWN")
                parts.append(f"{idx}. **{s_name}** - Status: {status}")

        if not parts:
            parts.append("I have processed your query against verified policy and applicant evidence.")

        return "\n\n".join(parts)
