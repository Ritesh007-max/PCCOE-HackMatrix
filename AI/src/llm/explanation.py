"""
PolicySetu Grounded Explanation Generator.
Produces transparent, citation-backed explanations of Phase 3 deterministic rule evaluations.
CRITICAL INVARIANTS:
1. Decision immutability is STRUCTURAL: authoritatively wraps Phase 3 RuleStatus.
2. Contradictory explanations are REJECTED and fall back to auditable templates (no prose sanitizing).
3. Missing fields are derived from Phase 3 AST condition trees.
4. Factual claims are verified against retrieved Phase 5 chunks.
"""

import logging
from typing import Any, Dict, List, Optional
import sys
from pathlib import Path

logger = logging.getLogger("policysetu.llm.explanation")

# Ensure AI directory is on sys.path
_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

try:
    from .models import GroundedExplanation, FactualClaim, ClaimSupportStatus
    from .client import LLMClient
    from .prompts import SYSTEM_PROMPT_GROUNDED_EXPLANATION
    from .safety import DecisionImmutabilityGuard
    from .grounding import GroundingVerifier
    from .ast_analyzer import RuleASTMissingFieldAnalyzer
    from ..rules.models import SchemeRuleSet, ApplicantProfile, RuleStatus, RuleEvaluationResult
except (ImportError, ValueError):
    from src.llm.models import GroundedExplanation, FactualClaim, ClaimSupportStatus
    from src.llm.client import LLMClient
    from src.llm.prompts import SYSTEM_PROMPT_GROUNDED_EXPLANATION
    from src.llm.safety import DecisionImmutabilityGuard
    from src.llm.grounding import GroundingVerifier
    from src.llm.ast_analyzer import RuleASTMissingFieldAnalyzer
    from src.rules.models import SchemeRuleSet, ApplicantProfile, RuleStatus, RuleEvaluationResult


class GroundedExplanationGenerator:
    """Generates and verifies grounded natural-language explanations of eligibility outcomes."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        grounding_verifier: Optional[GroundingVerifier] = None,
        ast_analyzer: Optional[RuleASTMissingFieldAnalyzer] = None
    ):
        self.llm_client = llm_client or LLMClient()
        self.grounding_verifier = grounding_verifier or GroundingVerifier()
        self.ast_analyzer = ast_analyzer or RuleASTMissingFieldAnalyzer()

    def generate_explanation(
        self,
        ruleset: SchemeRuleSet,
        profile: ApplicantProfile,
        rule_status: RuleStatus,
        rule_results: List[RuleEvaluationResult],
        retrieved_chunks: Optional[List[Dict[str, Any]]] = None
    ) -> GroundedExplanation:
        """
        Builds a verified GroundedExplanation adhering to all immutability and grounding contracts.
        """
        chunks = retrieved_chunks or []
        passed_rules = [r.rule_id for r in rule_results if r.status == RuleStatus.PASS]
        failed_rules = [r.rule_id for r in rule_results if r.status == RuleStatus.FAIL]
        failed_reasons = [r.reason for r in rule_results if r.status == RuleStatus.FAIL]

        # Authoritative AST-derived missing fields (respecting AND/OR/NOT logic)
        missing_fields = self.ast_analyzer.find_missing_fields_for_pass(ruleset, profile)
        conflicts_set = getattr(profile, "_conflicts", None) or getattr(profile, "conflicts", None) or set()
        conflicted_fields = sorted(list(conflicts_set))

        # Context prompt summarizing the deterministic decision and retrieved evidence
        evidence_text = "\n".join(
            f"Chunk ID: {c.get('id') or c.get('chunk_id')}\nContent: {c.get('content')}\nURL: {c.get('source_url', '')}"
            for c in chunks[:5]
        )

        prompt = (
            f"Authoritative Rule Engine Decision: {rule_status.value}\n"
            f"Scheme ID: {ruleset.scheme_id} ({ruleset.scheme_name})\n"
            f"Passed Rules: {passed_rules}\n"
            f"Failed Rules: {failed_rules} ({'; '.join(failed_reasons)})\n"
            f"AST Missing Fields: {missing_fields}\n"
            f"Conflicted Fields: {conflicted_fields}\n\n"
            f"<POLICY_EVIDENCE_DATA>\n{evidence_text}\n</POLICY_EVIDENCE_DATA>\n\n"
            f"Generate an explanation of this deterministic decision."
        )

        # Call LLM client
        try:
            explanation = self.llm_client.generate_structured(
                prompt=prompt,
                schema_cls=GroundedExplanation,
                system_prompt=SYSTEM_PROMPT_GROUNDED_EXPLANATION,
                operation="grounded_explanation",
                authoritative_decision=rule_status.value,
                scheme_id=ruleset.scheme_id,
                retrieved_chunks=chunks,
                passed_rules=passed_rules,
                failed_rules=failed_rules,
                missing_fields=missing_fields,
                conflicted_fields=conflicted_fields,
            )
        except Exception as exc:
            logger.warning("LLM explanation generation failed (%s); using deterministic template explanation.", exc)
            fallback_text = DecisionImmutabilityGuard.generate_fallback_explanation(
                scheme_id=ruleset.scheme_id,
                phase3_status=rule_status,
                failed_rules=failed_reasons,
                missing_fields=missing_fields,
                conflicted_fields=conflicted_fields,
            )
            return GroundedExplanation(
                authoritative_decision=rule_status.value,
                scheme_id=ruleset.scheme_id,
                answer=fallback_text,
                passed_rules=passed_rules,
                failed_rules=failed_rules,
                missing_fields=missing_fields,
                conflicted_fields=conflicted_fields,
                review_required=(rule_status == RuleStatus.REVIEW),
                rejection_fallback_used=True,
            )

        # 1. Structural Decision Immutability: force authoritative decision
        explanation.authoritative_decision = rule_status.value
        explanation.scheme_id = ruleset.scheme_id
        explanation.passed_rules = passed_rules
        explanation.failed_rules = failed_rules
        explanation.missing_fields = missing_fields
        explanation.conflicted_fields = conflicted_fields
        explanation.review_required = (rule_status == RuleStatus.REVIEW)

        # 2. Contradiction Check: If LLM text contradicts Phase 3 status, REJECT and use template
        is_compliant = DecisionImmutabilityGuard.check_explanation(explanation.answer, rule_status)
        if not is_compliant:
            explanation.rejection_fallback_used = True
            explanation.answer = DecisionImmutabilityGuard.generate_fallback_explanation(
                scheme_id=ruleset.scheme_id,
                phase3_status=rule_status,
                failed_rules=failed_reasons,
                missing_fields=missing_fields,
                conflicted_fields=conflicted_fields,
            )

        # 3. Two-Tier Grounding Verification
        explanation = self.grounding_verifier.verify_explanation(explanation, chunks)

        return explanation
