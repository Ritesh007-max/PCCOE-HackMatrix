"""
Eligibility Explanation and Citizen Summary Builder.
Phase 11: Translates deterministic rule AST outcomes into transparent, citizen-readable explanations.
Guidance MUST NEVER change the statutory decision or soften disqualifications.
"""

from typing import Any, Dict, List, Optional
from src.application.status import StatutoryDecision
from src.application.decision import DecisionSnapshot
from src.application.case import SchemeEvaluation
from .models import EligibilitySummary


class EligibilitySummaryBuilder:
    """
    Builds transparent, unsoftened eligibility explanations directly from
    Phase 3/10 deterministic evaluation results.
    """

    @classmethod
    def build_summary(
        cls,
        evaluation: Optional[SchemeEvaluation] = None,
        snapshot: Optional[DecisionSnapshot] = None,
        scheme_name: str = "",
    ) -> EligibilitySummary:
        """
        Constructs an EligibilitySummary object.
        Preserves statutory decision strictly: PASS, FAIL, UNKNOWN, REVIEW.
        """
        # Determine status
        status_val = "UNKNOWN"
        if snapshot:
            status_val = snapshot.decision_status.value
            scheme_name = scheme_name or snapshot.scheme_name
            matched = snapshot.matched_rules
            failed = snapshot.failed_rules
            unknown = snapshot.unknown_rules
            conflicted = snapshot.review_fields
            missing = [r.get("field", "") for r in snapshot.unknown_rules if isinstance(r, dict)]
        elif evaluation:
            status_val = evaluation.decision_status.value
            scheme_name = scheme_name or evaluation.scheme_name
            matched = evaluation.matched_rules
            failed = evaluation.failed_rules
            unknown = evaluation.unknown_rules
            conflicted = evaluation.conflicted_fields
            missing = evaluation.missing_fields
        else:
            return EligibilitySummary(
                status="UNKNOWN",
                summary="Eligibility evaluation has not yet been executed for this application.",
            )

        name_display = scheme_name or "this government scheme"
        criteria_list: List[Dict[str, Any]] = []

        # 1. Process matched rules
        satisfied_crit: List[str] = []
        for r in matched:
            field_name = r.get("field", "Criteria") if isinstance(r, dict) else str(r)
            reason = r.get("reason", "Statutory condition satisfied") if isinstance(r, dict) else "Satisfied"
            ev = r.get("raw_text") if isinstance(r, dict) else None
            satisfied_crit.append(f"{field_name}: {reason}")
            criteria_list.append({
                "criterion": field_name,
                "satisfied": True,
                "status": "PASS",
                "reason": reason,
                "evidence": ev,
            })

        # 2. Process failed rules
        failed_crit: List[str] = []
        for r in failed:
            field_name = r.get("field", "Criteria") if isinstance(r, dict) else str(r)
            reason = r.get("reason", "Did not meet statutory requirement") if isinstance(r, dict) else "Failed"
            ev = r.get("raw_text") if isinstance(r, dict) else None
            failed_crit.append(f"{field_name}: {reason}")
            criteria_list.append({
                "criterion": field_name,
                "satisfied": False,
                "status": "FAIL",
                "reason": reason,
                "evidence": ev,
            })

        # 3. Process unknown rules
        unresolved_crit: List[str] = []
        for r in unknown:
            field_name = r.get("field", "Criteria") if isinstance(r, dict) else str(r)
            unresolved_crit.append(field_name)
            criteria_list.append({
                "criterion": field_name,
                "satisfied": False,
                "status": "UNKNOWN",
                "reason": f"Required applicant information for '{field_name}' is missing.",
            })

        # Build summary statement
        if status_val == StatutoryDecision.PASS.value:
            summary_text = (
                f"Your available profile information and verified documents satisfy the evaluated statutory "
                f"eligibility criteria for {name_display}."
            )
        elif status_val == StatutoryDecision.FAIL.value:
            reasons_str = "; ".join(failed_crit) if failed_crit else "statutory thresholds were not met"
            summary_text = (
                f"Based on evaluated statutory criteria for {name_display}, you are not eligible because: {reasons_str}. "
                f"Government guidelines strictly enforce these mandatory thresholds."
            )
        elif status_val == StatutoryDecision.REVIEW.value:
            summary_text = (
                f"Your application for {name_display} requires administrative caseworker review. Contradictory evidence "
                f"was detected across submitted documents, or the policy contains subjective conditions needing departmental verification."
            )
        else:  # UNKNOWN
            missing_str = ", ".join(missing or unresolved_crit) if (missing or unresolved_crit) else "profile fields"
            summary_text = (
                f"Statutory eligibility for {name_display} cannot be determined yet because mandatory information "
                f"is missing: {missing_str}. Please provide this information to complete your assessment."
            )

        return EligibilitySummary(
            status=status_val,
            summary=summary_text,
            criteria=criteria_list,
            satisfied_criteria=satisfied_crit,
            failed_criteria=failed_crit,
            unresolved_criteria=unresolved_crit,
            conflicting_evidence=list(conflicted),
            missing_information=list(missing),
        )
