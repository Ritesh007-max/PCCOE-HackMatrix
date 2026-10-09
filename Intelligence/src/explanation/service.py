"""
FIN Phase 21 Policy Explanation Service.
Coordinates deterministic explanation generation, optional LLM natural language phrasing,
grounding verification, multi-scheme comparison, and telemetry.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple

from src.rules.models import RuleStatus
from src.eligibility.decision import EligibilityDecision
from src.recommendation.models import SchemeRecommendationItem
from src.context.models import ApplicantContext
from src.llm.client import LLMClient
from src.llm.safety import DecisionImmutabilityGuard, PromptInjectionDetector

from .models import (
    ExplanationBundle,
    GroundingStatus,
    SchemeComparisonResult,
)
from .generator import ExplanationGenerator
from .verifier import ExplanationGroundingVerifier

logger = logging.getLogger("fin.explanation.service")


class PolicyExplanationService:
    """
    Authoritative Policy Explanation & Guidance Service.
    Guarantees:
    - Zero mutation of statutory eligibility decisions.
    - Zero hallucinated rules or thresholds.
    - Strict applicant isolation.
    - Deterministic fallback on any LLM or network failure.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        verifier: Optional[ExplanationGroundingVerifier] = None,
    ):
        self.llm_client = llm_client or LLMClient()
        self.verifier = verifier or ExplanationGroundingVerifier()
        # Safe in-memory cache keyed by (applicant_id, decision_id, rule_version, language)
        self._cache: Dict[Tuple[str, str, str, str], ExplanationBundle] = {}

    def explain_decision(
        self,
        decision: EligibilityDecision,
        recommendation: Optional[SchemeRecommendationItem] = None,
        context: Optional[ApplicantContext] = None,
        applicant_context: Optional[ApplicantContext] = None,
        query: Optional[str] = None,
        language: str = "en",
        use_llm_enhancement: bool = False,
    ) -> ExplanationBundle:
        """
        Generates an authoritative ExplanationBundle for an evaluated decision.
        """
        context = context or applicant_context
        app_id = decision.applicant_id or (context.applicant_id if context else "anonymous")
        cache_key = (
            str(app_id),
            str(decision.decision_id),
            str(decision.rule_version),
            str(language).lower(),
        )

        # 1. Check Cache
        if cache_key in self._cache:
            logger.debug("Cache hit for explanation %s", cache_key)
            return self._cache[cache_key]

        # 2. Build Base Deterministic Explanation
        bundle = ExplanationGenerator.generate_explanation_bundle(
            decision=decision,
            recommendation=recommendation,
            context=context,
            query=query,
            language=language,
        )

        # 3. Optional LLM Enhancement (Phrasing / Summarization ONLY)
        if use_llm_enhancement:
            try:
                bundle = self._enhance_with_llm(bundle, decision, language)
            except Exception as e:
                logger.warning(
                    "LLM enhancement failed (%s); using deterministic explanation.", e
                )
                bundle.generated_by = "DETERMINISTIC_EXPLANATION_BUILDER (LLM_FALLBACK)"

        # 4. Two-Tier Grounding Verification & Immutability Enforcement
        is_valid, status, issues = self.verifier.verify_bundle(bundle, decision)
        if not is_valid:
            logger.warning(
                "Explanation failed verification (%s); enforcing safe fallback.", issues
            )
            bundle = ExplanationGroundingVerifier.sanitize_or_fallback(bundle, decision)
        else:
            bundle.grounding_status = status

        # 5. Store in Cache
        self._cache[cache_key] = bundle

        # 6. PII-Safe Telemetry
        logger.info(
            "Generated explanation exp_id=%s scheme=%s status=%s version=%s grounding=%s",
            bundle.explanation_id,
            bundle.scheme_id,
            bundle.eligibility_status,
            bundle.rule_version,
            bundle.grounding_status.value,
        )

        return bundle

    def _enhance_with_llm(
        self,
        bundle: ExplanationBundle,
        decision: EligibilityDecision,
        language: str,
    ) -> ExplanationBundle:
        """
        Enhances natural language phrasing while strictly preserving decision status and numbers.
        """
        prompt = (
            f"Authoritative Statutory Decision: {decision.status.value}\n"
            f"Scheme Name: {decision.scheme_name}\n"
            f"Rule Version: {decision.rule_version}\n"
            f"Reasons: {'; '.join(bundle.reasons)}\n"
            f"Language: {language}\n\n"
            f"Please generate a concise, empathetic 2-sentence summary explaining this determination to the citizen. "
            f"CRITICAL RULES: Do NOT change the eligibility status. Do NOT invent new numbers or criteria."
        )

        resp = self.llm_client.generate(prompt=prompt, operation="explanation_summarize")
        text = resp.text.strip() if hasattr(resp, "text") else str(resp).strip()

        # Check for injection or contradiction in response
        is_compliant = DecisionImmutabilityGuard.check_explanation(text, decision.status)
        if is_compliant:
            bundle.summary = text
            bundle.generated_by = "HYBRID_LLM_GROUNDED"
        else:
            logger.warning("LLM summary contradicted decision status; rejected.")

        return bundle

    def compare_schemes(
        self,
        recommendations: List[SchemeRecommendationItem],
        decisions: Dict[str, EligibilityDecision],
    ) -> SchemeComparisonResult:
        """
        Generates an objective comparative analysis across multiple candidate schemes.
        """
        return ExplanationGenerator.compare_schemes(recommendations, decisions)

    def explain_historical_decision(
        self,
        decision: EligibilityDecision,
        context: Optional[ApplicantContext] = None,
        language: str = "en",
    ) -> ExplanationBundle:
        """
        Explains a historical decision using the exact pinned version and trace.
        Guaranteed: Never evaluates against current active rules.
        """
        return self.explain_decision(
            decision=decision,
            recommendation=None,
            context=context,
            language=language,
            use_llm_enhancement=False,  # Historical reproducibility requires 100% determinism
        )
