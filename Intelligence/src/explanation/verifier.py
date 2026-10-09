"""
FIN Phase 21 Grounding Verifier & Decision Immutability Guard.
Performs claim-level grounding verification, anti-hallucination checks,
and prompt injection defense. Enforces that LLM outputs cannot modify statutory decisions.
"""

from dataclasses import dataclass, field
from enum import Enum
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from src.rules.models import RuleStatus
from src.eligibility.decision import EligibilityDecision
from src.llm.safety import INJECTION_PATTERNS, PromptInjectionDetector

from .models import (
    ExplanationBundle,
    GroundingStatus,
    ReasonExplanation,
)

logger = logging.getLogger("fin.explanation.verifier")

# Claims of eligibility that must NOT appear if decision is not PASS
POSITIVE_ELIGIBILITY_PATTERNS = [
    re.compile(r"\b(?:you\s+are|applicant\s+is)\s+(?:fully\s+)?eligible\b", re.IGNORECASE),
    re.compile(r"\b(?:you\s+qualify|applicant\s+qualifies)\s+for\b", re.IGNORECASE),
    re.compile(r"\bmeets\s+all\s+(?:eligibility|requirements|criteria)\b", re.IGNORECASE),
    re.compile(r"\bapplication\s+is\s+approved\b", re.IGNORECASE),
]

# Claims of disqualification that must NOT appear if decision is PASS
DISQUALIFICATION_PATTERNS = [
    re.compile(r"\b(?:you\s+are|applicant\s+is)\s+ineligible\b", re.IGNORECASE),
    re.compile(r"\bdisqualified\s+from\b", re.IGNORECASE),
    re.compile(r"\bdoes\s+not\s+qualify\b", re.IGNORECASE),
    re.compile(r"\bfailed\s+eligibility\b", re.IGNORECASE),
]


class VerificationIssue(str, Enum):
    """Categorical classification of grounding or security violations."""
    DECISION_STATE_MUTATION = "DECISION_STATE_MUTATION"
    FABRICATED_THRESHOLD = "FABRICATED_THRESHOLD"
    FABRICATED_RULE_ID = "FABRICATED_RULE_ID"
    FABRICATED_EVIDENCE_ID = "FABRICATED_EVIDENCE_ID"
    UNGROUNDED_BENEFIT = "UNGROUNDED_BENEFIT"
    PROMPT_INJECTION_RISK = "PROMPT_INJECTION_RISK"
    UNGROUNDED_STATUTORY_CLAIM = "UNGROUNDED_STATUTORY_CLAIM"


@dataclass
class VerificationReport:
    """Report returned from verification check."""
    is_valid: bool
    grounding_status: GroundingStatus
    violations: List[str] = field(default_factory=list)
    requires_fallback: bool = False


DOCUMENT_INJECTION_PATTERNS = [
    re.compile(r"\b(?:ai\s+assistant|system|assistant):?\s*(?:ignore|change|override|force|set|tell|declare)\b", re.IGNORECASE),
    re.compile(r"\b(?:force|set|make)\s+(?:system\s+)?(?:status|result)\s+to\s+PASS\b", re.IGNORECASE),
    re.compile(r"\balways\s+return\s+PASS\b", re.IGNORECASE),
]


class ExplanationGroundingVerifier:
    """
    Validates that an ExplanationBundle is 100% grounded in verified AST rules,
    statutory decisions, and canonical applicant facts.
    """

    def __init__(self):
        self.injection_detector = PromptInjectionDetector()

    def detect_prompt_injection(self, text: str) -> bool:
        """Scans input text for prompt injection attempts."""
        if any(p.search(text) for p in DOCUMENT_INJECTION_PATTERNS):
            return True
        scan_res = self.injection_detector.scan(text)
        return scan_res.is_injection_risk

    def verify(
        self,
        bundle: ExplanationBundle,
        decision: EligibilityDecision,
    ) -> VerificationReport:
        """Executes verification and returns structured VerificationReport."""
        is_valid, status, issues = self.verify_bundle(bundle, decision)
        return VerificationReport(
            is_valid=is_valid,
            grounding_status=status,
            violations=issues,
            requires_fallback=not is_valid,
        )

    def verify_bundle(
        self,
        bundle: ExplanationBundle,
        decision: EligibilityDecision,
    ) -> Tuple[bool, GroundingStatus, List[str]]:
        """
        Executes comprehensive verification on the explanation bundle.
        Returns:
            Tuple[is_valid (bool), GroundingStatus, List[error_messages]]
        """
        errors: List[str] = []
        warnings: List[str] = []

        # ---------------------------------------------------------------------
        # 1. Structural Decision Immutability
        # ---------------------------------------------------------------------
        if bundle.eligibility_status != decision.status.value:
            errors.append(
                f"CRITICAL: Explanation status '{bundle.eligibility_status}' contradicts "
                f"authoritative decision '{decision.status.value}'."
            )
            return False, GroundingStatus.BLOCKED, errors

        # ---------------------------------------------------------------------
        # 2. Textual Semantic Contradiction Checks
        # ---------------------------------------------------------------------
        full_text = f"{bundle.headline} {bundle.summary} {' '.join(bundle.reasons)}"

        if decision.status != RuleStatus.PASS:
            # Non-PASS must NEVER claim applicant is eligible
            for pat in POSITIVE_ELIGIBILITY_PATTERNS:
                if pat.search(full_text):
                    errors.append(
                        f"CRITICAL: Non-PASS decision ({decision.status.value}) contains "
                        f"positive eligibility claim matching '{pat.pattern}'."
                    )
                    break

        if decision.status == RuleStatus.PASS:
            # PASS must NEVER claim applicant is ineligible
            for pat in DISQUALIFICATION_PATTERNS:
                if pat.search(full_text):
                    errors.append(
                        f"CRITICAL: PASS decision contains disqualification claim matching '{pat.pattern}'."
                    )
                    break

        # ---------------------------------------------------------------------
        # 3. Prompt Injection Defense
        # ---------------------------------------------------------------------
        scan_res = self.injection_detector.scan(full_text)
        if scan_res.is_injection_risk:
            errors.append(
                f"SECURITY: Prompt injection pattern detected in explanation text: {scan_res.detected_threats}"
            )
            return False, GroundingStatus.BLOCKED, errors

        # ---------------------------------------------------------------------
        # 4. AST Rule ID & Condition Grounding
        # ---------------------------------------------------------------------
        valid_rule_ids: Set[str] = {r.rule_id for r in decision.rule_results}
        valid_fields: Set[str] = {r.field for r in decision.rule_results}

        # Check all condition items in eligibility_explanation
        all_reasons: List[ReasonExplanation] = (
            bundle.eligibility_explanation.passed_conditions
            + bundle.eligibility_explanation.failed_conditions
            + bundle.eligibility_explanation.unknown_conditions
            + bundle.eligibility_explanation.review_conditions
        )

        rule_map = {r.rule_id: r for r in decision.rule_results}
        for r_item in all_reasons:
            if r_item.rule_id and r_item.rule_id not in valid_rule_ids:
                errors.append(
                    f"GROUNDING: Explanation cites fabricated rule ID '{r_item.rule_id}'. "
                    f"Valid rules: {sorted(list(valid_rule_ids))}."
                )
            elif r_item.rule_id and r_item.rule_id in rule_map:
                expected_in_ast = rule_map[r_item.rule_id].expected_value
                if r_item.expected_value != expected_in_ast:
                    errors.append(
                        f"Threshold mismatch on rule '{r_item.rule_id}': explanation cites "
                        f"{r_item.expected_value}, but rule AST requires {expected_in_ast}."
                    )

        # ---------------------------------------------------------------------
        # 5. Missing Fields Grounding
        # ---------------------------------------------------------------------
        valid_missing_fields: Set[str] = set(decision.missing_fields)
        for m in bundle.missing_information:
            if m.field not in valid_missing_fields:
                warnings.append(
                    f"Explanation guidance lists ungrounded missing field '{m.field}'."
                )

        # ---------------------------------------------------------------------
        # 6. Policy Citation Grounding
        # ---------------------------------------------------------------------
        for cit in bundle.policy_citations:
            if not cit.source_id or not cit.scheme_id:
                warnings.append(f"Citation '{cit.citation_id}' lacks source_id or scheme_id.")

        # Determine final status
        if errors:
            return False, GroundingStatus.BLOCKED, errors
        elif warnings:
            return True, GroundingStatus.PARTIAL, warnings
        return True, GroundingStatus.GROUNDED, []

    @classmethod
    def sanitize_or_fallback(
        cls,
        bundle: ExplanationBundle,
        decision: EligibilityDecision,
    ) -> ExplanationBundle:
        """
        If a bundle fails verification, resets to a pure deterministic fallback
        adhering strictly to decision state.
        """
        verifier = cls()
        is_valid, status, issues = verifier.verify_bundle(bundle, decision)
        if is_valid:
            bundle.grounding_status = status
            return bundle

        logger.warning(
            "ExplanationBundle failed verification (%s); enforcing deterministic fallback.",
            issues,
        )

        # Overwrite text with deterministic fallback
        bundle.eligibility_status = decision.status.value
        bundle.is_eligible = decision.eligible
        bundle.rule_version = decision.rule_version

        if decision.status == RuleStatus.PASS:
            bundle.headline = "Statutory Eligibility Criteria Satisfied (Deterministic Fallback)"
            bundle.summary = (
                f"Deterministic evaluation against policy version {decision.rule_version} confirms "
                f"all evaluated conditions for {decision.scheme_name or decision.scheme_id} are satisfied."
            )
        elif decision.status == RuleStatus.FAIL:
            bundle.headline = "Statutory Eligibility Criteria Not Satisfied (Deterministic Fallback)"
            bundle.summary = (
                f"Deterministic evaluation against policy version {decision.rule_version} identified "
                f"statutory disqualifications: {'; '.join(decision.disqualification_reasons[:2])}."
            )
        elif decision.status == RuleStatus.UNKNOWN:
            bundle.headline = "Information Incomplete (Deterministic Fallback)"
            bundle.summary = (
                f"Statutory eligibility could not be evaluated due to missing information: "
                f"{', '.join(decision.missing_fields)}."
            )
        else:
            bundle.headline = "Administrative Review Required (Deterministic Fallback)"
            bundle.summary = (
                f"Statutory evaluation requires administrative review: "
                f"{'; '.join(decision.review_reasons[:2])}."
            )

        bundle.grounding_status = GroundingStatus.GROUNDED
        bundle.generated_by = "DETERMINISTIC_SAFE_FALLBACK"
        return bundle
