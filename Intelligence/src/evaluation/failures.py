"""
FIN Phase 13 Failure Taxonomy.
Categorizes every evaluation and red-team defect into deterministic failure categories.
"""

from enum import Enum
from typing import Dict, Any, Optional

try:
    from .models import Severity
except (ImportError, ValueError):
    from src.evaluation.models import Severity


class FailureType(str, Enum):
    """The 15 authoritative defect categories for FIN red-teaming and evaluation."""
    RETRIEVAL_FAILURE = "RETRIEVAL_FAILURE"                    # Target scheme/FAQ missing from top-K
    EXTRACTION_FAILURE = "EXTRACTION_FAILURE"                  # Document fact extraction missed or erroneous
    NORMALIZATION_FAILURE = "NORMALIZATION_FAILURE"            # Data format, unit, or type normalization error
    RULE_FAILURE = "RULE_FAILURE"                              # Statutory PASS/FAIL/UNKNOWN/REVIEW logic mismatch
    GROUNDING_FAILURE = "GROUNDING_FAILURE"                    # Claim unsupported by retrieved evidence
    HALLUCINATION_FAILURE = "HALLUCINATION_FAILURE"            # Invented scheme, benefit, deadline, or URL
    AUTHORITY_FAILURE = "AUTHORITY_FAILURE"                    # Supplementary source overrode primary official
    TEMPORAL_FAILURE = "TEMPORAL_FAILURE"                      # Stale source or temporal validity misinterpretation
    SECURITY_FAILURE = "SECURITY_FAILURE"                      # Unauthorized access, path traversal, or resource abuse
    INJECTION_FAILURE = "INJECTION_FAILURE"                    # Prompt injection executed or altered state
    POLICY_POISONING_FAILURE = "POLICY_POISONING_FAILURE"      # Unsafe candidate policy bypassed activation gates
    API_SECURITY_FAILURE = "API_SECURITY_FAILURE"              # API secret leakage, unauthenticated mutation, or PII leak
    MULTILINGUAL_FAILURE = "MULTILINGUAL_FAILURE"              # Language barrier altered eligibility or intent
    GUIDANCE_FAILURE = "GUIDANCE_FAILURE"                      # Contradictory steps, softened advice, or missing checklist
    VERSIONING_FAILURE = "VERSIONING_FAILURE"                  # Historical decision mutation or snapshot mismatch


DEFAULT_SEVERITY_MAPPING: Dict[FailureType, Severity] = {
    FailureType.INJECTION_FAILURE: Severity.CRITICAL,
    FailureType.POLICY_POISONING_FAILURE: Severity.CRITICAL,
    FailureType.VERSIONING_FAILURE: Severity.CRITICAL,
    FailureType.API_SECURITY_FAILURE: Severity.CRITICAL,
    FailureType.AUTHORITY_FAILURE: Severity.HIGH,
    FailureType.HALLUCINATION_FAILURE: Severity.HIGH,
    FailureType.RULE_FAILURE: Severity.HIGH,
    FailureType.GROUNDING_FAILURE: Severity.HIGH,
    FailureType.EXTRACTION_FAILURE: Severity.HIGH,
    FailureType.SECURITY_FAILURE: Severity.HIGH,
    FailureType.RETRIEVAL_FAILURE: Severity.MEDIUM,
    FailureType.MULTILINGUAL_FAILURE: Severity.MEDIUM,
    FailureType.GUIDANCE_FAILURE: Severity.MEDIUM,
    FailureType.NORMALIZATION_FAILURE: Severity.MEDIUM,
    FailureType.TEMPORAL_FAILURE: Severity.MEDIUM,
}


def classify_failure(
    failure_type: FailureType,
    details: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Formats a structured failure record with severity and diagnostic context."""
    return {
        "failure_type": failure_type.value,
        "severity": DEFAULT_SEVERITY_MAPPING.get(failure_type, Severity.MEDIUM).value,
        "details": details,
        "context": context or {},
    }
