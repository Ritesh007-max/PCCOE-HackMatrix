"""
PolicySetu LLM Safety & Decision Immutability Guardrails.
Enforces non-destructive prompt injection detection and structural decision immutability.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import sys
from pathlib import Path

# Ensure AI directory is on sys.path
_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

try:
    from ..rules.models import RuleStatus
except (ImportError, ValueError):
    from src.rules.models import RuleStatus

from .errors import DecisionContradictionError


# Signatures indicative of prompt injection, instruction overrides, or jailbreaks
INJECTION_PATTERNS = [
    re.compile(r"\bignore\s+(?:all\s+)?(?:previous|prior|system)\s+instructions\b", re.IGNORECASE),
    re.compile(r"\boverride\s+(?:system|rules|safety|instructions)\b", re.IGNORECASE),
    re.compile(r"\b(?:mark|declare|make)\s+(?:applicant|me|user)\s+(?:eligible|pass|approved)\b", re.IGNORECASE),
    re.compile(r"\bbypass\s+(?:eligibility|verification|rules|checks)\b", re.IGNORECASE),
    re.compile(r"\byou\s+are\s+now\s+in\s+developer\s+mode\b", re.IGNORECASE),
    re.compile(r"\bdisregard\s+(?:the\s+)?(?:rules|context|prompt)\b", re.IGNORECASE),
    re.compile(r"\boutput\s+only\s+PASS\b", re.IGNORECASE),
    re.compile(r"<\s*system\s*>", re.IGNORECASE),
]

# Patterns indicating claim of statutory eligibility in natural language
ELIGIBLE_CLAIM_PATTERNS = [
    re.compile(r"\b(?:you\s+are|applicant\s+is)\s+eligible\b", re.IGNORECASE),
    re.compile(r"\b(?:you\s+qualify|applicant\s+qualifies)\s+for\b", re.IGNORECASE),
    re.compile(r"\bmeets\s+all\s+(?:eligibility|requirements|criteria)\b", re.IGNORECASE),
    re.compile(r"\b(?:aap|tum)\s+eligible\s+ho\b", re.IGNORECASE),
    re.compile(r"\b(?:aap|tum)\s+patra\s+hain\b", re.IGNORECASE),
    re.compile(r"(आप\s+पात्र\s+हैं|पात्रता\s+पूरी\s+होती\s+है)", re.IGNORECASE),
]


@dataclass
class SafetyScanResult:
    """Audit result of safety inspection on untrusted text."""
    is_safe: bool
    is_injection_risk: bool
    detected_threats: List[str] = field(default_factory=list)
    raw_text: str = ""  # Strictly preserved verbatim without mutation


class PromptInjectionDetector:
    """
    Non-destructive prompt injection detection.
    Detects and flags malicious instruction overrides without modifying or truncating the raw text.
    """

    def scan(self, text: str) -> SafetyScanResult:
        if not text or not text.strip():
            return SafetyScanResult(is_safe=True, is_injection_risk=False, raw_text=text or "")

        detected: List[str] = []
        for pat in INJECTION_PATTERNS:
            match = pat.search(text)
            if match:
                detected.append(match.group(0))

        is_risk = len(detected) > 0
        return SafetyScanResult(
            is_safe=not is_risk,
            is_injection_risk=is_risk,
            detected_threats=detected,
            raw_text=text  # Untouched verbatim text preserved for audit
        )

    @staticmethod
    def wrap_untrusted_input(text: str) -> str:
        """
        Wraps untrusted user or document text in strict XML isolation boundaries
        for safe LLM consumption.
        """
        # Escape any rogue closing tags to prevent escaping the boundary
        sanitized = text.replace("</UNTRUSTED_USER_INPUT>", "<\\/UNTRUSTED_USER_INPUT>")
        return f"<UNTRUSTED_USER_INPUT>\n{sanitized}\n</UNTRUSTED_USER_INPUT>"


class DecisionImmutabilityGuard:
    """
    Programmatic invariant enforcer for statutory decisions.
    THE LLM MUST NEVER OVERRIDE PHASE 3 DECISIONS.
    If generated text contradicts the authoritative Phase 3 outcome, the explanation
    is REJECTED (not rewritten) and a safe deterministic template is used instead.
    """

    @classmethod
    def check_explanation(cls, explanation_text: str, phase3_status: RuleStatus) -> bool:
        """
        Validates whether explanation prose respects the authoritative Phase 3 decision.
        Returns True if compliant, False if contradictory.
        """
        if not explanation_text:
            return True

        # Invariant 1: If Phase 3 says FAIL, explanation must NEVER state applicant is eligible
        if phase3_status == RuleStatus.FAIL:
            for pat in ELIGIBLE_CLAIM_PATTERNS:
                if pat.search(explanation_text):
                    return False

        # Invariant 2: If Phase 3 says UNKNOWN, explanation must not declare definitive eligibility
        if phase3_status == RuleStatus.UNKNOWN:
            for pat in ELIGIBLE_CLAIM_PATTERNS:
                if pat.search(explanation_text):
                    return False

        # Invariant 3: If Phase 3 says REVIEW, explanation must not declare definitive eligibility
        if phase3_status == RuleStatus.REVIEW:
            for pat in ELIGIBLE_CLAIM_PATTERNS:
                if pat.search(explanation_text):
                    return False

        return True

    @classmethod
    def generate_fallback_explanation(
        cls,
        scheme_id: str,
        phase3_status: RuleStatus,
        failed_rules: List[str],
        missing_fields: List[str],
        conflicted_fields: List[str]
    ) -> str:
        """
        Generates an auditable, deterministic fallback explanation when LLM prose
        is rejected due to decision contradiction or unavailable provider.
        """
        if phase3_status == RuleStatus.PASS:
            return (
                f"Statutory Evaluation: PASS. The applicant satisfies all required eligibility criteria "
                f"for scheme '{scheme_id}'. Please refer to the official portal for application steps."
            )
        elif phase3_status == RuleStatus.FAIL:
            reasons = ", ".join(failed_rules) if failed_rules else "statutory criteria not met"
            return (
                f"Statutory Evaluation: FAIL. The applicant does not meet one or more mandatory eligibility "
                f"requirements for scheme '{scheme_id}'. Specific disqualified condition(s): {reasons}."
            )
        elif phase3_status == RuleStatus.UNKNOWN:
            missing = ", ".join(missing_fields) if missing_fields else "required applicant data"
            return (
                f"Statutory Evaluation: UNKNOWN. Eligibility for scheme '{scheme_id}' cannot be determined "
                f"because essential information is missing: {missing}. Please provide these details."
            )
        elif phase3_status == RuleStatus.REVIEW:
            conflicts = ", ".join(conflicted_fields) if conflicted_fields else "evidence inconsistency"
            return (
                f"Statutory Evaluation: REVIEW. Eligibility for scheme '{scheme_id}' requires manual review "
                f"due to conflicting evidence across submitted documents for: {conflicts}."
            )
        return f"Statutory Evaluation: {phase3_status.value} for scheme '{scheme_id}'."
