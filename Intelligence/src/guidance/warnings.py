"""
Guidance Warnings Generator.
Phase 11: Deterministic risk, compliance, and ambiguity warnings.
"""

from typing import Any, Dict, List, Optional
from src.application.case import ApplicationCase, SchemeEvaluation
from src.application.decision import DecisionSnapshot
from src.application.status import StatutoryDecision, ReadinessStatus
from .models import GuidanceWarning, GuidanceWarningCode, WarningSeverity


class WarningGenerator:
    """
    Generates structured risk and compliance warnings directly from
    application state, decision results, document audits, and source metadata.
    """

    @classmethod
    def generate_warnings(
        cls,
        case: ApplicationCase,
        evaluation: Optional[SchemeEvaluation] = None,
        snapshot: Optional[DecisionSnapshot] = None,
        official_portal_url: Optional[str] = None,
        missing_documents: Optional[List[str]] = None,
        benefit_status: Optional[str] = None,
        scheme_id: Optional[str] = None,
    ) -> List[GuidanceWarning]:
        """
        Synthesizes deterministic warnings.
        """
        warnings: List[GuidanceWarning] = []
        target_scheme = scheme_id or (evaluation.scheme_id if evaluation else case.selected_scheme_id)

        # 1. Document Missing Warning
        if missing_documents:
            warnings.append(
                GuidanceWarning(
                    code=GuidanceWarningCode.DOCUMENT_MISSING,
                    severity=WarningSeverity.CRITICAL if case.readiness == ReadinessStatus.ACTION_REQUIRED else WarningSeverity.WARNING,
                    message=f"Mandatory documents are missing: {', '.join(missing_documents)}. Application cannot be submitted without them.",
                    related_scheme=target_scheme,
                )
            )

        # 2. Document / Fact Conflict Warning
        conflicts = set(case.facts.conflicted_fields)
        if evaluation:
            conflicts.update(evaluation.conflicted_fields)
        if snapshot:
            conflicts.update(snapshot.review_fields)

        if conflicts:
            conf_str = ", ".join(sorted(conflicts))
            warnings.append(
                GuidanceWarning(
                    code=GuidanceWarningCode.DOCUMENT_CONFLICT,
                    severity=WarningSeverity.CRITICAL,
                    message=f"Contradictory evidence detected for field(s): {conf_str}. Case requires resolution before proceeding.",
                    related_field=conf_str,
                    related_scheme=target_scheme,
                )
            )

        # 3. Eligibility Unknown Warning
        decision_val = snapshot.decision_status.value if snapshot else (evaluation.decision_status.value if evaluation else "UNKNOWN")
        if decision_val == StatutoryDecision.UNKNOWN.value:
            missing_facts = case.facts.missing_fields
            if evaluation:
                missing_facts = evaluation.missing_fields or missing_facts
            mf_str = ", ".join(missing_facts) if missing_facts else "mandatory profile fields"
            warnings.append(
                GuidanceWarning(
                    code=GuidanceWarningCode.ELIGIBILITY_UNKNOWN,
                    severity=WarningSeverity.WARNING,
                    message=f"Eligibility could not be determined because required applicant information is missing: {mf_str}.",
                    related_scheme=target_scheme,
                )
            )

        # 4. Human Review Required Warning
        if decision_val == StatutoryDecision.REVIEW.value or case.readiness == ReadinessStatus.READY_FOR_REVIEW:
            warnings.append(
                GuidanceWarning(
                    code=GuidanceWarningCode.HUMAN_REVIEW_REQUIRED,
                    severity=WarningSeverity.CRITICAL,
                    message="Application requires administrative caseworker review due to ambiguous criteria or discordant documentation.",
                    related_scheme=target_scheme,
                )
            )

        # 5. Official Link Unavailable Warning
        if not official_portal_url:
            warnings.append(
                GuidanceWarning(
                    code=GuidanceWarningCode.OFFICIAL_LINK_UNAVAILABLE,
                    severity=WarningSeverity.WARNING,
                    message="Official application portal link is not available in verified policy sources. Beware of phishing or unverified third-party websites.",
                    related_scheme=target_scheme,
                )
            )

        # 6. Benefit Undetermined Warning
        if benefit_status == "CANNOT_DETERMINE":
            warnings.append(
                GuidanceWarning(
                    code=GuidanceWarningCode.BENEFIT_UNDETERMINED,
                    severity=WarningSeverity.INFO,
                    message="Exact statutory financial benefit amount could not be determined deterministically from current policy guidelines.",
                    related_scheme=target_scheme,
                )
            )

        return warnings
