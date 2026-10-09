"""
FIN Phase 21 Deterministic Policy Explanation and Guidance Generator.
Converts ApplicantContext, QueryIntent, SchemeRecommendation, and EligibilityDecision
into comprehensive, fully grounded ExplanationBundles with zero LLM decision mutation.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from src.rules.models import RuleStatus
from src.eligibility.decision import EligibilityDecision
from src.recommendation.models import SchemeRecommendationItem
from src.context.models import ApplicantContext
from src.guidance.benefit_summary import BenefitSummaryBuilder

from .models import (
    ActionPriority,
    ActionType,
    BenefitExplanation,
    EligibilityExplanation,
    EvidenceReference,
    ExplanationBundle,
    GroundingStatus,
    HumanReviewGuidance,
    MissingInformationGuidance,
    NextAction,
    PolicyCitation,
    ReasonExplanation,
    RecommendationExplanation,
    ReviewReasonCode,
    SchemeComparisonItem,
    SchemeComparisonResult,
    SourceAuthorityTier,
    UncertaintyExplanation,
)

logger = logging.getLogger("fin.explanation.generator")


class ExplanationGenerator:
    """
    Deterministic Explanation and Guidance Engine.
    Guarantees:
    1. Authoritative Decision Immutability: EligibilityDecision is strictly read-only.
    2. Zero Hallucinated Thresholds: Rules and statutory thresholds are strictly quoted from AST.
    3. Grounded Evidence: Every factual condition is bound to verified applicant facts or statutes.
    4. Deterministic Actions: Prioritized next actions are derived directly from workflow state.
    """

    # Localized text dictionaries preserving exact numbers and statuses
    _LOCALIZED_HEADLINES = {
        "en": {
            "PASS": "Statutory Eligibility Criteria Satisfied",
            "FAIL": "Statutory Eligibility Criteria Not Satisfied",
            "UNKNOWN": "Information Incomplete to Determine Statutory Eligibility",
            "REVIEW": "Administrative or Evidence Review Required",
        },
        "hi": {
            "PASS": "वैधानिक पात्रता मानदंड पूरे हुए (PASS)",
            "FAIL": "वैधानिक पात्रता मानदंड पूरे नहीं हुए (FAIL)",
            "UNKNOWN": "पात्रता निर्धारित करने के लिए जानकारी अधूरी है (UNKNOWN)",
            "REVIEW": "प्रशासनिक या साक्ष्य समीक्षा आवश्यक है (REVIEW)",
        },
        "gu": {
            "PASS": "કાયદાકીય પાત્રતાના માપદંડો પૂર્ણ થયા (PASS)",
            "FAIL": "કાયદાકીય પાત્રતાના માપદંડો પૂર્ણ થયા નથી (FAIL)",
            "UNKNOWN": "પાત્રતા નક્કી કરવા માટે માહિતી અધૂરી છે (UNKNOWN)",
            "REVIEW": "વહીવટી અથવા પુરાવાની સમીક્ષા જરૂરી છે (REVIEW)",
        },
    }

    @classmethod
    def generate_explanation_bundle(
        cls,
        decision: EligibilityDecision,
        recommendation: Optional[SchemeRecommendationItem] = None,
        context: Optional[ApplicantContext] = None,
        query: Optional[str] = None,
        language: str = "en",
    ) -> ExplanationBundle:
        """
        Builds the authoritative ExplanationBundle for an evaluated scheme decision.
        """
        lang = language.lower() if language and language.lower() in ("hi", "gu") else "en"
        scheme_id = decision.scheme_id
        scheme_slug = decision.scheme_slug
        scheme_name = decision.scheme_name or scheme_slug
        status_val = decision.status.value

        # 1. Decision immutability check
        is_eligible = decision.eligible
        rule_version = decision.rule_version or "1.0.0"
        rule_set_hash = decision.rule_set_hash
        decision_id = decision.decision_id

        # 2. Extract and format atomic rule results
        eligibility_expl = cls._build_eligibility_explanation(decision)

        # 3. Build headline & summary based on four-state semantics
        headline, summary = cls._build_headline_and_summary(
            decision, scheme_name, rule_version, lang
        )

        # 4. Build missing information guidance
        missing_info_guidance = cls._build_missing_info_guidance(decision)

        # 5. Build human review and conflict guidance
        review_guidance = cls._build_review_guidance(decision, context)

        # 6. Extract evidence references
        evidence_refs = cls._build_evidence_references(decision, context)

        # 7. Extract policy citations
        policy_citations = cls._build_policy_citations(decision, recommendation)

        # 8. Deterministic next action generation
        next_actions = cls._build_next_actions(
            decision, missing_info_guidance, review_guidance, policy_citations, lang
        )

        # 9. Benefit explanation
        benefit_expl = cls._build_benefit_explanation(decision, recommendation, scheme_name)

        # 10. Recommendation context (if candidate came through Phase 19)
        rec_expl = None
        if recommendation:
            rec_expl = cls._build_recommendation_explanation(recommendation)

        # 11. Uncertainty analysis
        uncertainty = cls._build_uncertainty_explanation(decision)

        # 12. Reasons list
        reasons_list = cls._build_reasons_list(decision)

        # Source metadata list
        source_meta = []
        if recommendation and recommendation.source_metadata:
            source_meta.append(recommendation.source_metadata)

        return ExplanationBundle(
            explanation_id=f"exp_{uuid.uuid4().hex[:12]}",
            applicant_id=decision.applicant_id or (context.applicant_id if context else None),
            scheme_id=scheme_id,
            scheme_name=scheme_name,
            eligibility_status=status_val,
            is_eligible=is_eligible,
            rule_version=rule_version,
            rule_set_hash=rule_set_hash,
            decision_id=decision_id,
            headline=headline,
            summary=summary,
            eligibility_explanation=eligibility_expl,
            reasons=reasons_list,
            missing_information=missing_info_guidance,
            conflicts=[g for g in review_guidance if g.reason_code == ReviewReasonCode.FACT_CONFLICT],
            evidence=evidence_refs,
            policy_citations=policy_citations,
            next_actions=next_actions,
            review_guidance=review_guidance,
            benefit_information=benefit_expl,
            recommendation_explanation=rec_expl,
            uncertainty_explanation=uncertainty,
            source_metadata=source_meta,
            generated_by="DETERMINISTIC_EXPLANATION_BUILDER",
            grounding_status=GroundingStatus.GROUNDED,
            language=lang,
        )

    # -------------------------------------------------------------------------
    # Helper: Build Rule Explanations
    # -------------------------------------------------------------------------
    @classmethod
    def _build_eligibility_explanation(
        cls, decision: EligibilityDecision
    ) -> EligibilityExplanation:
        what_checked: List[str] = []
        passed: List[ReasonExplanation] = []
        failed: List[ReasonExplanation] = []
        unknown: List[ReasonExplanation] = []
        review: List[ReasonExplanation] = []

        for r in decision.rule_results:
            field_name = r.field
            what_checked.append(f"{field_name} ({r.operator} {r.expected_value})")

            # Translate operator and outcome to natural phrasing
            human_text = cls._format_rule_human_text(r)
            statute = r.raw_text or ""
            source_url = r.rule.source_url if r.rule else None

            reason_item = ReasonExplanation(
                rule_id=r.rule_id,
                field=r.field,
                operator=r.operator,
                applicant_value=r.applicant_value,
                expected_value=r.expected_value,
                status=r.status.value,
                hard_constraint=r.hard_constraint,
                human_text=human_text,
                statutory_citation=statute,
                rule_version=decision.rule_version,
                policy_source_url=source_url,
            )

            if r.status == RuleStatus.PASS:
                passed.append(reason_item)
            elif r.status == RuleStatus.FAIL:
                failed.append(reason_item)
            elif r.status == RuleStatus.UNKNOWN:
                unknown.append(reason_item)
            elif r.status == RuleStatus.REVIEW:
                review.append(reason_item)

        return EligibilityExplanation(
            what_was_checked=sorted(list(set(what_checked))),
            passed_conditions=passed,
            failed_conditions=failed,
            unknown_conditions=unknown,
            review_conditions=review,
        )

    @staticmethod
    def _format_rule_human_text(r: Any) -> str:
        f = r.field.replace("_", " ").title()
        op = r.operator.lower()
        val = r.applicant_value
        exp = r.expected_value
        st = r.status

        if st == RuleStatus.PASS:
            if op in (">=", ">"):
                return f"Your recorded {f} ({val}) satisfies the requirement of at least {exp}."
            elif op in ("<=", "<"):
                return f"Your recorded {f} ({val}) satisfies the requirement of at most {exp}."
            elif op in ("=", "=="):
                return f"Your recorded {f} matches the statutory requirement ('{exp}')."
            elif op == "between":
                min_v = exp.get("min") if isinstance(exp, dict) else exp[0]
                max_v = exp.get("max") if isinstance(exp, dict) else exp[1]
                return f"Your recorded {f} ({val}) falls within the required range [{min_v} to {max_v}]."
            elif op in ("is_true", "is_false"):
                return f"Verified that {f} matches the required policy condition."
            elif op in ("in", "contains"):
                return f"Your recorded {f} ('{val}') is an eligible category."
            return f"Your recorded {f} satisfies statutory criterion: {r.reason}"

        elif st == RuleStatus.FAIL:
            if op in (">=", ">"):
                return f"Your recorded {f} ({val}) does not meet the minimum requirement of {exp}."
            elif op in ("<=", "<"):
                return f"Your recorded {f} ({val}) exceeds the maximum allowable limit of {exp}."
            elif op in ("=", "=="):
                return f"Your recorded {f} ('{val}') does not match the required value ('{exp}')."
            elif op == "between":
                min_v = exp.get("min") if isinstance(exp, dict) else exp[0]
                max_v = exp.get("max") if isinstance(exp, dict) else exp[1]
                return f"Your recorded {f} ({val}) is outside the required range [{min_v} to {max_v}]."
            elif op in ("is_false",):
                return f"You are disqualified due to exclusion criteria for {f}."
            return f"Your profile does not satisfy statutory criterion for {f}: {r.reason}"

        elif st == RuleStatus.UNKNOWN:
            return f"Your profile is missing required information for '{f}'. Statutory criterion ({op} {exp}) could not be verified."

        elif st == RuleStatus.REVIEW:
            return f"Criterion for '{f}' requires administrative casework verification: {r.reason}"

        return str(r.reason or "")

    # -------------------------------------------------------------------------
    # Helper: Headlines & Summaries
    # -------------------------------------------------------------------------
    @classmethod
    def _build_headline_and_summary(
        cls, decision: EligibilityDecision, scheme_name: str, rule_version: str, lang: str
    ) -> Tuple[str, str]:
        status_key = decision.status.value
        headline = cls._LOCALIZED_HEADLINES.get(lang, cls._LOCALIZED_HEADLINES["en"]).get(
            status_key, f"Scheme Evaluation: {status_key}"
        )

        if decision.status == RuleStatus.PASS:
            if lang == "hi":
                summary = (
                    f"पंजीकृत नीति संस्करण {rule_version} के तहत, आपके द्वारा दर्ज किए गए तथ्य {scheme_name} के "
                    f"सभी वैधानिक पात्रता मानदंडों को पूरा करते हैं। ध्यान दें: यह मूल्यांकन पंजीकृत वैधानिक नियमों और "
                    f"उपलब्ध साक्ष्यों पर आधारित है; अंतिम लाभ स्वीकृति संबंधित सरकारी विभाग द्वारा सत्यापन के अधीन है।"
                )
            elif lang == "gu":
                summary = (
                    f"નોંધાયેલ નીતિ આવૃત્તિ {rule_version} હેઠળ, તમારા નોંધાયેલા તથ્યો {scheme_name} ના "
                    f"તમામ કાયદાકીય પાત્રતાના માપદંડોને પૂર્ણ કરે છે. નોંધ: આ મૂલ્યાંકન નોંધાયેલા કાયદાકીય નિયમો અને "
                    f"ઉપલબ્ધ પુરાવા પર આધારિત છે; અંતિમ લાભ મંજૂરી સંબંધિત સરકારી વિભાગ દ્વારા ચકાસણીને આધીન છે."
                )
            else:
                summary = (
                    f"Based on registered policy version {rule_version}, your recorded facts satisfy all evaluated "
                    f"statutory criteria for {scheme_name}. Note: This determination reflects deterministic rule evaluation "
                    f"against available evidence; formal benefit sanction is subject to final administrative verification by the competent authority."
                )

        elif decision.status == RuleStatus.FAIL:
            disq_text = "; ".join(decision.disqualification_reasons[:2])
            if lang == "hi":
                summary = (
                    f"पंजीकृत नीति संस्करण {rule_version} के तहत, आपका आवेदन {scheme_name} के लिए पात्र नहीं है। "
                    f"अस्वीकृति का मुख्य कारण: {disq_text}।"
                )
            elif lang == "gu":
                summary = (
                    f"નોંધાયેલ નીતિ આવૃત્તિ {rule_version} હેઠળ, તમારી પ્રોફાઇલ {scheme_name} માટે પાત્ર નથી. "
                    f"અસ્વીકારનું મુખ્ય કારણ: {disq_text}."
                )
            else:
                summary = (
                    f"Based on registered policy version {rule_version}, your recorded profile does not satisfy statutory "
                    f"criteria for {scheme_name}. Primary disqualifying condition(s): {disq_text}."
                )

        elif decision.status == RuleStatus.UNKNOWN:
            missing_fields_str = ", ".join(decision.missing_fields[:3])
            if lang == "hi":
                summary = (
                    f"{scheme_name} के लिए पात्रता का पूर्ण निर्धारण नहीं किया जा सका क्योंकि आवश्यक जानकारी अधूरी है "
                    f"({missing_fields_str})। पात्रता जांच पूरी करने के लिए कृपया आवश्यक विवरण या दस्तावेज प्रदान करें।"
                )
            elif lang == "gu":
                summary = (
                    f"{scheme_name} માટે પાત્રતા સંપૂર્ણપણે નક્કી કરી શકાઈ નથી કારણ કે આવશ્યક માહિતી ખૂટે છે "
                    f"({missing_fields_str}). પાત્રતા ચકાસણી પૂર્ણ કરવા માટે કૃપા કરીને જરૂરી વિગતો અથવા દસ્તાવેજો પ્રદાન કરો."
                )
            else:
                summary = (
                    f"Eligibility for {scheme_name} could not be conclusively determined because essential statutory facts "
                    f"are missing from your profile: {missing_fields_str}. Please provide the required information to complete evaluation."
                )

        else:  # REVIEW
            review_text = "; ".join(decision.review_reasons[:2]) or "Contradictory evidence or casework clause detected."
            if lang == "hi":
                summary = (
                    f"{scheme_name} के लिए स्वचालित निर्धारण अपर्याप्त है और प्रशासनिक समीक्षा की आवश्यकता है। कारण: {review_text}।"
                )
            elif lang == "gu":
                summary = (
                    f"{scheme_name} માટે સ્વચાલિત નિર્ણય અપર્યાપ્ત છે અને વહીવટી સમીક્ષા જરૂરી છે. કારણ: {review_text}."
                )
            else:
                summary = (
                    f"Automated eligibility determination for {scheme_name} requires administrative review. "
                    f"Reason: {review_text}."
                )

        return headline, summary

    # -------------------------------------------------------------------------
    # Helper: Missing Info Guidance
    # -------------------------------------------------------------------------
    @classmethod
    def _build_missing_info_guidance(
        cls, decision: EligibilityDecision
    ) -> List[MissingInformationGuidance]:
        guidance_items: List[MissingInformationGuidance] = []
        for field in decision.missing_fields:
            # Locate the rule that needed this field
            matching_rule = next(
                (r for r in decision.rule_results if r.field == field and r.status == RuleStatus.UNKNOWN),
                None
            )
            rule_id = matching_rule.rule_id if matching_rule else None
            reason = (
                f"Required by statutory rule '{rule_id}' to evaluate eligibility condition."
                if rule_id
                else "Required by policy criteria to evaluate eligibility."
            )

            # Suggest evidence based on field name
            evidence_type = "Self-Declaration or Document"
            user_sat = True
            off_ver = False
            if "income" in field:
                evidence_type = "Income Certificate or ITR"
                off_ver = True
            elif "land" in field:
                evidence_type = "RoR (Record of Rights / 7/12 Extract) or Land Ownership Certificate"
                off_ver = True
            elif "bank" in field:
                evidence_type = "Bank Account Passbook / Statement"
            elif "category" in field or "caste" in field:
                evidence_type = "Caste / Category Certificate"
                off_ver = True
            elif "age" in field or "dob" in field:
                evidence_type = "Aadhaar Card, Birth Certificate, or School Leaving Certificate"

            item = MissingInformationGuidance(
                field=field,
                reason_required=reason,
                affected_rule_id=rule_id,
                affected_scheme_id=decision.scheme_id,
                suggested_evidence_type=evidence_type,
                priority=ActionPriority.HIGH,
                user_input_satisfiable=user_sat,
                official_verification_required=off_ver,
            )
            guidance_items.append(item)

        return guidance_items

    # -------------------------------------------------------------------------
    # Helper: Human Review & Conflict Guidance
    # -------------------------------------------------------------------------
    @classmethod
    def _build_review_guidance(
        cls, decision: EligibilityDecision, context: Optional[ApplicantContext]
    ) -> List[HumanReviewGuidance]:
        guidance: List[HumanReviewGuidance] = []

        # 1. Fact conflicts across documents
        for field in decision.conflicted_fields:
            sources = []
            if context:
                ev_records = context.get_evidence(field)
                for e in ev_records:
                    doc = getattr(e, "source_document", None) or getattr(e, "source_type", "Source")
                    val = getattr(e, "raw_value", getattr(e, "value", "Recorded"))
                    sources.append(f"{doc}: {val}")
                if not sources:
                    c_facts = context.conflict_details.get(field) or [f for f in context.all_facts if f.field == field]
                    for cf in c_facts:
                        doc = getattr(cf, "source_document", None) or getattr(cf, "source_type", "Source")
                        val = getattr(cf, "value", getattr(cf, "normalized_value", "Recorded"))
                        sources.append(f"{doc}: {val}")

            src_a = sources[0] if len(sources) > 0 else "Source 1"
            src_b = sources[1] if len(sources) > 1 else "Source 2"

            guidance.append(
                HumanReviewGuidance(
                    review_id=f"rev_conf_{uuid.uuid4().hex[:8]}",
                    field=field,
                    reason_code=ReviewReasonCode.FACT_CONFLICT,
                    source_a=src_a,
                    source_b=src_b,
                    explanation=(
                        f"Discordant evidence detected across documents for '{field}'. "
                        f"System refuses to arbitrarily pick one value over another."
                    ),
                    suggested_resolution="Submit authoritative official gazette or revised certificate to resolve conflict.",
                    priority=ActionPriority.HIGH,
                )
            )

        # 2. Casework statutory clauses requiring review
        for r in decision.rule_results:
            if r.status == RuleStatus.REVIEW and r.field not in decision.conflicted_fields:
                guidance.append(
                    HumanReviewGuidance(
                        review_id=f"rev_rule_{uuid.uuid4().hex[:8]}",
                        field=r.field,
                        reason_code=ReviewReasonCode.UNSTRUCTURED_RULE,
                        explanation=f"Clause requires official manual review: {r.reason}",
                        suggested_resolution="Administrative caseworker must inspect supporting documents.",
                        priority=ActionPriority.MEDIUM,
                    )
                )

        return guidance

    # -------------------------------------------------------------------------
    # Helper: Evidence References
    # -------------------------------------------------------------------------
    @classmethod
    def _build_evidence_references(
        cls, decision: EligibilityDecision, context: Optional[ApplicantContext]
    ) -> List[EvidenceReference]:
        refs: List[EvidenceReference] = []
        seen = set()

        if context:
            for fact in context.all_facts:
                fid = fact.field
                if fid in seen:
                    continue
                seen.add(fid)
                ref = EvidenceReference(
                    evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
                    field=fid,
                    value=fact.normalized_value or fact.value,
                    source_type=fact.source_type.value if hasattr(fact.source_type, "value") else str(fact.source_type),
                    source_document=fact.source_document,
                    source_page=getattr(fact, "page_number", getattr(fact, "source_page", None)),
                    confidence=fact.confidence,
                    verification_status=(
                        fact.verification_status.value
                        if hasattr(fact.verification_status, "value")
                        else str(fact.verification_status)
                    ),
                )
                refs.append(ref)

        return refs

    # -------------------------------------------------------------------------
    # Helper: Policy Citations
    # -------------------------------------------------------------------------
    @classmethod
    def _build_policy_citations(
        cls,
        decision: EligibilityDecision,
        recommendation: Optional[SchemeRecommendationItem],
    ) -> List[PolicyCitation]:
        citations: List[PolicyCitation] = []
        seen_rules = set()

        # From decision evidence
        for ev in decision.evidence:
            rid = ev.get("rule_id", "rule_general")
            if rid in seen_rules:
                continue
            seen_rules.add(rid)

            cit = PolicyCitation(
                citation_id=f"cit_{uuid.uuid4().hex[:8]}",
                scheme_id=decision.scheme_id,
                source_id=ev.get("source_document") or "statute",
                source_type=SourceAuthorityTier.PRIMARY_SCHEME.value,
                source_authority=SourceAuthorityTier.PRIMARY_SCHEME.value,
                title=f"Statutory Provision ({rid})",
                url=ev.get("source_url"),
                document_id=ev.get("source_document"),
                page=ev.get("source_page"),
                section=ev.get("source_section"),
                text_span=ev.get("raw_text"),
                policy_version=decision.rule_version,
                rule_id=rid,
                citation_confidence=1.0,
                grounding_state="GROUNDED",
            )
            citations.append(cit)

        # From recommendation snippets
        if recommendation and recommendation.evidence:
            rev_ev = recommendation.evidence
            for idx, snip in enumerate(rev_ev.snippets[:2]):
                cit = PolicyCitation(
                    citation_id=f"cit_rec_{idx}_{uuid.uuid4().hex[:6]}",
                    scheme_id=decision.scheme_id,
                    source_id=rev_ev.source_dataset or "retrieval_corpus",
                    source_type=rev_ev.source_tier,
                    source_authority=rev_ev.source_tier,
                    title="Policy Description Extract",
                    url=rev_ev.source_url,
                    text_span=snip,
                    policy_version=decision.rule_version,
                    retrieval_score=recommendation.relevance_score,
                    citation_confidence=0.9,
                    grounding_state="GROUNDED",
                )
                citations.append(cit)

        return citations

    # -------------------------------------------------------------------------
    # Helper: Next Actions
    # -------------------------------------------------------------------------
    @classmethod
    def _build_next_actions(
        cls,
        decision: EligibilityDecision,
        missing_guidance: List[MissingInformationGuidance],
        review_guidance: List[HumanReviewGuidance],
        citations: List[PolicyCitation],
        lang: str,
    ) -> List[NextAction]:
        actions: List[NextAction] = []

        # 1. Resolve Conflicts (HIGH)
        for rev in review_guidance:
            if rev.reason_code == ReviewReasonCode.FACT_CONFLICT:
                actions.append(
                    NextAction(
                        action_id=f"act_{uuid.uuid4().hex[:8]}",
                        action_type=ActionType.RESOLVE_CONFLICT,
                        priority=ActionPriority.HIGH,
                        title=f"Resolve conflicting records for {rev.field}",
                        explanation=f"Documents contain discordant values ({rev.source_a} vs {rev.source_b}). Upload a verified certificate to resolve.",
                        related_field=rev.field,
                        related_scheme=decision.scheme_id,
                    )
                )

        # 2. Provide Missing Facts (HIGH)
        for m in missing_guidance:
            act_type = (
                ActionType.UPLOAD_DOCUMENT
                if m.official_verification_required
                else ActionType.PROVIDE_INFORMATION
            )
            actions.append(
                NextAction(
                    action_id=f"act_{uuid.uuid4().hex[:8]}",
                    action_type=act_type,
                    priority=m.priority,
                    title=f"Provide {m.field.replace('_', ' ').title()}",
                    explanation=f"Required for statutory eligibility check. Suggested: {m.suggested_evidence_type}.",
                    related_field=m.field,
                    related_rule=m.affected_rule_id,
                    related_scheme=decision.scheme_id,
                )
            )

        # 3. Ready to Apply (HIGH if PASS)
        if decision.status == RuleStatus.PASS:
            portal_url = citations[0].url if citations and citations[0].url else "https://www.myscheme.gov.in"
            actions.append(
                NextAction(
                    action_id=f"act_{uuid.uuid4().hex[:8]}",
                    action_type=ActionType.READY_TO_APPLY,
                    priority=ActionPriority.HIGH,
                    title="Proceed to Application Submission",
                    explanation=f"Your profile satisfies evaluated statutory criteria. You can proceed with the formal application.",
                    related_scheme=decision.scheme_id,
                )
            )
            actions.append(
                NextAction(
                    action_id=f"act_{uuid.uuid4().hex[:8]}",
                    action_type=ActionType.VISIT_OFFICIAL_PORTAL,
                    priority=ActionPriority.MEDIUM,
                    title="Visit Official Scheme Portal",
                    explanation=f"Access verified online portal: {portal_url}",
                    related_scheme=decision.scheme_id,
                )
            )

        # 4. View Benefits (LOW/MEDIUM)
        actions.append(
            NextAction(
                action_id=f"act_{uuid.uuid4().hex[:8]}",
                action_type=ActionType.VIEW_BENEFIT,
                priority=ActionPriority.LOW,
                title="Review Scheme Entitlements & Benefits",
                explanation="Check structured DBT disbursements, subsidies, and assistance schedules.",
                related_scheme=decision.scheme_id,
            )
        )

        return actions

    # -------------------------------------------------------------------------
    # Helper: Benefit Explanation
    # -------------------------------------------------------------------------
    @classmethod
    def _build_benefit_explanation(
        cls,
        decision: EligibilityDecision,
        recommendation: Optional[SchemeRecommendationItem],
        scheme_name: str,
    ) -> BenefitExplanation:
        # Check if recommendation or decision metadata contains benefit info
        benefit_data = None
        if recommendation and recommendation.source_metadata:
            benefit_data = recommendation.source_metadata.get("benefit_summary")

        bg = BenefitSummaryBuilder.build_guidance(benefit_data, scheme_name)
        return BenefitExplanation(
            status=bg.status,
            benefit_type=bg.benefit_type,
            amount=bg.amount,
            currency=bg.currency,
            frequency=bg.frequency,
            disbursement_structure=bg.disbursement_structure,
            explanation=bg.explanation,
            evidence=bg.evidence,
        )

    # -------------------------------------------------------------------------
    # Helper: Recommendation Explanation
    # -------------------------------------------------------------------------
    @classmethod
    def _build_recommendation_explanation(
        cls, recommendation: SchemeRecommendationItem
    ) -> RecommendationExplanation:
        rel_summary = (
            f"Retrieved with search relevance score {recommendation.relevance_score:.2f} "
            f"based on semantic keyword and BM25 statutory retrieval."
        )
        comp_summary = (
            f"Personal profile compatibility evaluated at {recommendation.compatibility_score:.2f} "
            f"across {len(recommendation.matched_facts)} matching attributes."
        )
        ev_summary = (
            f"Grounded in verified policy documentation (Source Tier: "
            f"{recommendation.evidence.source_tier if recommendation.evidence else 'PRIMARY_SCHEME'})."
        )
        return RecommendationExplanation(
            relevance_score=recommendation.relevance_score,
            compatibility_score=recommendation.compatibility_score,
            retrieval_relevance_summary=rel_summary,
            compatibility_summary=comp_summary,
            evidence_availability_summary=ev_summary,
        )

    # -------------------------------------------------------------------------
    # Helper: Uncertainty Explanation
    # -------------------------------------------------------------------------
    @classmethod
    def _build_uncertainty_explanation(
        cls, decision: EligibilityDecision
    ) -> UncertaintyExplanation:
        if decision.status == RuleStatus.PASS:
            return UncertaintyExplanation(
                is_uncertain=False,
                uncertainty_type="NONE",
                explanation="All registered statutory conditions were evaluated deterministically without ambiguity.",
                resolution_path="Profile ready for application submission.",
            )
        elif decision.status == RuleStatus.UNKNOWN:
            return UncertaintyExplanation(
                is_uncertain=True,
                uncertainty_type="MISSING_FACTS",
                explanation=f"Missing {len(decision.missing_fields)} required attribute(s): {', '.join(decision.missing_fields)}.",
                resolution_path="Supply missing applicant facts to complete evaluation.",
            )
        elif decision.status == RuleStatus.REVIEW:
            u_type = (
                "CONFLICTING_EVIDENCE"
                if decision.conflicted_fields
                else "STATUTORY_AMBIGUITY"
            )
            return UncertaintyExplanation(
                is_uncertain=True,
                uncertainty_type=u_type,
                explanation="Evaluation encountered conflicting facts across documents or a manual casework clause.",
                resolution_path="Requires manual caseworker review or submission of authoritative clarifying documents.",
            )
        else:  # FAIL
            return UncertaintyExplanation(
                is_uncertain=False,
                uncertainty_type="NONE",
                explanation="Disqualification was evaluated deterministically against statutory hard constraints.",
                resolution_path="Check alternative schemes where criteria align with your profile.",
            )

    # -------------------------------------------------------------------------
    # Helper: Reasons List
    # -------------------------------------------------------------------------
    @classmethod
    def _build_reasons_list(cls, decision: EligibilityDecision) -> List[str]:
        if decision.status == RuleStatus.PASS:
            return [
                f"Criterion '{r.field}' satisfied: {r.reason}"
                for r in decision.rule_results if r.status == RuleStatus.PASS
            ]
        elif decision.status == RuleStatus.FAIL:
            return decision.disqualification_reasons or ["Violates statutory hard constraint."]
        elif decision.status == RuleStatus.UNKNOWN:
            return [f"Missing required field: {f}" for f in decision.missing_fields]
        else:
            return decision.review_reasons or ["Requires administrative casework verification."]

    # -------------------------------------------------------------------------
    # Objective Multi-Scheme Comparison
    # -------------------------------------------------------------------------
    @classmethod
    def compare_schemes(
        cls,
        recommendations: List[SchemeRecommendationItem],
        decisions: Dict[str, EligibilityDecision],
    ) -> SchemeComparisonResult:
        """
        Generates an objective, side-by-side comparative analysis across multiple candidate schemes.
        Guaranteed: Presents objective differences without declaring a subjective 'winner'.
        """
        items: List[SchemeComparisonItem] = []
        differences: List[str] = []

        for rec in recommendations:
            slug = rec.scheme_slug
            dec = decisions.get(slug) or decisions.get(rec.scheme_id)
            if not dec:
                continue

            # Key differences
            key_diffs = []
            if dec.status == RuleStatus.PASS:
                key_diffs.append("All statutory conditions currently satisfied (PASS)")
            elif dec.status == RuleStatus.UNKNOWN:
                key_diffs.append(f"Requires {len(dec.missing_fields)} additional fact(s) (UNKNOWN)")
            elif dec.status == RuleStatus.FAIL:
                key_diffs.append("Disqualified by statutory hard constraint (FAIL)")
            elif dec.status == RuleStatus.REVIEW:
                key_diffs.append("Requires administrative evidence review (REVIEW)")

            # Benefits summary
            b_summary = "Statutory assistance / grant as per official portal guidelines."
            if rec.source_metadata and rec.source_metadata.get("benefit_summary"):
                b_info = rec.source_metadata["benefit_summary"]
                if b_info.get("amount"):
                    b_summary = f"₹{b_info['amount']:,.0f} ({b_info.get('frequency', 'One-time')})"

            items.append(
                SchemeComparisonItem(
                    scheme_id=rec.scheme_id,
                    scheme_slug=rec.scheme_slug,
                    scheme_name=rec.scheme_name,
                    purpose=rec.source_metadata.get("purpose", f"Welfare scheme for {rec.scheme_name}"),
                    relevance_score=rec.relevance_score,
                    compatibility_score=rec.compatibility_score,
                    eligibility_status=dec.status.value,
                    is_eligible=dec.eligible,
                    benefit_summary=b_summary,
                    key_differences=key_diffs,
                    missing_fields_count=len(dec.missing_fields),
                    required_documents=rec.source_metadata.get("required_documents", ["Identity Document"]),
                    official_application_route="ONLINE" if rec.source_metadata.get("online_application", True) else "OFFLINE",
                    source_authority=(
                        rec.evidence.source_tier if rec.evidence else SourceAuthorityTier.PRIMARY_SCHEME.value
                    ),
                    rule_version=dec.rule_version,
                )
            )

        if len(items) >= 2:
            differences.append(
                f"Evaluated {len(items)} schemes. Differences observed in eligibility readiness: "
                + ", ".join(f"{i.scheme_name} ({i.eligibility_status})" for i in items)
            )

        return SchemeComparisonResult(
            comparison_id=f"cmp_{uuid.uuid4().hex[:12]}",
            applicant_id=items[0].scheme_id if items else None,
            schemes=items,
            summary_of_differences=differences,
        )
