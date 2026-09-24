"""
Benefit Presentation and Explanation Builder.
Phase 11: Derives transparent benefit guidance from deterministic BenefitCalculator results.
LLMs must NEVER calculate or invent benefits.
"""

from typing import Any, Dict, List, Optional
from .models import BenefitGuidance


class BenefitSummaryBuilder:
    """
    Builds transparent citizen benefit guidance directly from deterministic
    BenefitCalculator and SchemeEvaluation results.
    """

    @classmethod
    def build_guidance(
        cls,
        benefit_data: Optional[Dict[str, Any]] = None,
        scheme_name: str = "",
    ) -> BenefitGuidance:
        """
        Constructs BenefitGuidance without runtime formula synthesis.
        """
        if not benefit_data:
            return BenefitGuidance(
                status="CANNOT_DETERMINE",
                benefit_type="UNKNOWN",
                amount=None,
                currency="INR",
                frequency=None,
                disbursement_structure="Not specified in verified policy evidence.",
                explanation="Benefit entitlement details are not specified in the verified policy source for this scheme.",
                evidence=[],
            )

        status = str(benefit_data.get("status", "CANNOT_DETERMINE"))
        b_type = str(benefit_data.get("benefit_type") or benefit_data.get("type", "DIRECT_BENEFIT_TRANSFER"))
        amount = benefit_data.get("amount")
        amount_val = float(amount) if amount is not None else None
        freq = benefit_data.get("disbursement_frequency") or benefit_data.get("frequency")
        reasoning = str(benefit_data.get("reasoning", ""))
        evidence_raw = benefit_data.get("verbatim_policy_evidence") or benefit_data.get("evidence")
        evidence_list = [evidence_raw] if isinstance(evidence_raw, str) else list(evidence_raw or [])

        # Construct explanation
        if status == "CALCULATED" and amount_val is not None:
            freq_str = f" payable {freq.lower().replace('_', ' ')}" if freq else ""
            explanation = (
                f"Under {scheme_name or 'this scheme'}, you are entitled to an estimated statutory benefit of "
                f"₹{amount_val:,.0f}{freq_str}. {reasoning}"
            ).strip()
            disbursement_structure = f"Direct transfer via Aadhaar-linked bank account ({freq or 'Standard schedule'})."
        elif status == "CONDITIONAL":
            explanation = (
                f"Benefit calculation is conditional upon institutional verification or variable factors: {reasoning}"
            ).strip()
            disbursement_structure = "Determined upon departmental sanction."
        else:
            explanation = (
                "Benefit amount cannot be determined deterministically from the available policy text. "
                "Official guidelines indicate variable grants, fee concessions, or departmental discretion."
            )
            disbursement_structure = "Subject to departmental processing."

        return BenefitGuidance(
            status=status,
            benefit_type=b_type,
            amount=amount_val,
            currency="INR",
            frequency=freq,
            disbursement_structure=disbursement_structure,
            explanation=explanation,
            evidence=evidence_list,
        )
