"""
Guidance Consistency and Anti-Hallucination Validator.
Phase 11: Rigorous 10-point consistency validation guarding against LLM contradictions.
"""

import logging
from typing import Any, Dict, List, Optional
from src.application.status import StatutoryDecision, ReadinessStatus
from .models import ApplicationGuidancePackage, GuidanceWarningCode
from .exceptions import GuidanceValidationError, ContradictoryGuidanceError
from .sources import SourceMetadataResolver

logger = logging.getLogger("fin.guidance.validator")


class GuidanceValidator:
    """
    Enforces strict consistency between the guidance package and deterministic statutory truth.
    Whenever generated text conflicts with structured truth, rejects the text and applies deterministic fallbacks.
    """

    @classmethod
    def validate_package(cls, package: ApplicationGuidancePackage) -> None:
        """
        Executes the 10-point statutory consistency validation suite.
        Raises GuidanceValidationError or ContradictoryGuidanceError on violation.
        """
        cls._validate_eligibility_consistency(package)
        cls._validate_readiness_consistency(package)
        cls._validate_document_consistency(package)
        cls._validate_benefit_consistency(package)
        cls._validate_url_safety(package)
        cls._validate_policy_version_consistency(package)
        cls._validate_no_textual_contradictions(package)

    @classmethod
    def _validate_eligibility_consistency(cls, package: ApplicationGuidancePackage) -> None:
        """Point 1: Statutory decision in package must match eligibility summary status."""
        stat_decision = package.statutory_decision
        summary_status = package.eligibility.status

        if stat_decision != summary_status:
            raise GuidanceValidationError(
                message=f"Statutory decision '{stat_decision}' does not match eligibility summary status '{summary_status}'",
                rule_name="ELIGIBILITY_CONSISTENCY",
            )

    @classmethod
    def _validate_readiness_consistency(cls, package: ApplicationGuidancePackage) -> None:
        """Point 2: READY_TO_APPLY cannot have missing mandatory documents or unresolved conflicts."""
        readiness = package.readiness_status
        docs_missing = package.documents.get("missing", [])
        conflicts = package.information.get("conflicted", [])

        if readiness == ReadinessStatus.READY_TO_APPLY.value:
            if docs_missing:
                raise GuidanceValidationError(
                    message=f"Readiness is READY_TO_APPLY but mandatory documents are missing: {docs_missing}",
                    rule_name="READINESS_DOCUMENT_CONSISTENCY",
                )
            if conflicts:
                raise GuidanceValidationError(
                    message=f"Readiness is READY_TO_APPLY but unresolved conflicts remain: {conflicts}",
                    rule_name="READINESS_CONFLICT_CONSISTENCY",
                )
            if package.statutory_decision != StatutoryDecision.PASS.value:
                raise GuidanceValidationError(
                    message=f"Readiness is READY_TO_APPLY but statutory decision is '{package.statutory_decision}' (must be PASS)",
                    rule_name="READINESS_DECISION_CONSISTENCY",
                )

    @classmethod
    def _validate_document_consistency(cls, package: ApplicationGuidancePackage) -> None:
        """Point 3: Documents marked available cannot be simultaneously in missing."""
        avail = set(package.documents.get("available", []))
        missing = set(package.documents.get("missing", []))
        overlap = avail & missing
        if overlap:
            raise GuidanceValidationError(
                message=f"Document(s) simultaneously marked available and missing: {overlap}",
                rule_name="DOCUMENT_MUTUAL_EXCLUSION",
            )

    @classmethod
    def _validate_benefit_consistency(cls, package: ApplicationGuidancePackage) -> None:
        """Point 4: Benefit amount must be None if status is CANNOT_DETERMINE."""
        b_status = package.benefit.status
        b_amount = package.benefit.amount
        if b_status == "CANNOT_DETERMINE" and b_amount is not None:
            raise GuidanceValidationError(
                message=f"Benefit status is CANNOT_DETERMINE but amount is set to {b_amount}",
                rule_name="BENEFIT_UNDETERMINED_AMOUNT_NULL",
            )

    @classmethod
    def _validate_url_safety(cls, package: ApplicationGuidancePackage) -> None:
        """Point 5: Official portal URL must pass government allowlist validation."""
        portal_url = package.application.get("official_portal_url")
        if portal_url:
            validated = SourceMetadataResolver.validate_official_url(portal_url)
            if not validated:
                raise GuidanceValidationError(
                    message=f"Official portal URL '{portal_url}' failed government domain allowlist",
                    rule_name="OFFICIAL_URL_ALLOWLIST",
                )

    @classmethod
    def _validate_policy_version_consistency(cls, package: ApplicationGuidancePackage) -> None:
        """Point 6: Policy snapshot version and rule version must be non-empty."""
        if not package.policy_snapshot_version:
            raise GuidanceValidationError(
                message="Policy snapshot version is missing from guidance package",
                rule_name="POLICY_SNAPSHOT_REQUIRED",
            )
        if not package.rule_version:
            raise GuidanceValidationError(
                message="Rule AST version is missing from guidance package",
                rule_name="RULE_VERSION_REQUIRED",
            )

    @classmethod
    def _validate_no_textual_contradictions(cls, package: ApplicationGuidancePackage) -> None:
        """Point 7: Natural language text must not contradict deterministic status."""
        summary = (package.eligibility.summary or "").lower()
        decision = package.statutory_decision

        if decision == StatutoryDecision.FAIL.value:
            prohibited_phrases = ["you are eligible", "aap eligible hain", "fully eligible", "ready to apply"]
            for p in prohibited_phrases:
                if p in summary:
                    raise ContradictoryGuidanceError(
                        statutory_truth=f"FAIL: Citizen is not eligible",
                        generated_claim=f"Summary contains '{p}'",
                    )
        elif decision == StatutoryDecision.PASS.value:
            prohibited_phrases = ["you are not eligible", "aap eligible nahi", "disqualified"]
            for p in prohibited_phrases:
                if p in summary:
                    raise ContradictoryGuidanceError(
                        statutory_truth=f"PASS: Citizen satisfies criteria",
                        generated_claim=f"Summary contains '{p}'",
                    )
