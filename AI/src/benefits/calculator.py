"""
PolicySetu Deterministic Benefit Calculator.
Evaluates quantitative financial values (subsidies, scholarships, direct benefit transfers)
and catalogs non-monetary provisions.

CRITICAL ARCHITECTURAL INVARIANTS:
1. ONLY executes already-structured rules.
2. NEVER performs runtime extraction of formulas from policy text via LLM or naive heuristics.
3. Schemes lacking pre-structured rules return CANNOT_DETERMINE or MANUAL_REVIEW_REQUIRED with verbatim text evidence.
4. Deterministic arithmetic only: zero hallucination, 100% reproducible.
"""

from dataclasses import dataclass, field
from enum import Enum
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("policysetu.benefits.calculator")


class BenefitType(str, Enum):
    """Categorical classification of government scheme benefits."""
    DIRECT_BENEFIT_TRANSFER = "DIRECT_BENEFIT_TRANSFER"
    SUBSIDY = "SUBSIDY"
    SCHOLARSHIP = "SCHOLARSHIP"
    FEE_CONCESSION = "FEE_CONCESSION"
    LOAN_INTEREST_SUBSIDY = "LOAN_INTEREST_SUBSIDY"
    IN_KIND = "IN_KIND"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_str(cls, val: Any) -> "BenefitType":
        if isinstance(val, BenefitType):
            return val
        if not val or not isinstance(val, str):
            return cls.UNKNOWN
        v = val.strip().upper()
        for item in cls:
            if item.value == v or item.name == v:
                return item
        if "DBT" in v or "CASH" in v or "TRANSFER" in v:
            return cls.DIRECT_BENEFIT_TRANSFER
        if "SUBSIDY" in v:
            return cls.SUBSIDY
        if "SCHOLARSHIP" in v:
            return cls.SCHOLARSHIP
        if "FEE" in v or "WAIVER" in v:
            return cls.FEE_CONCESSION
        if "LOAN" in v or "INTEREST" in v:
            return cls.LOAN_INTEREST_SUBSIDY
        if "KIND" in v or "FOOD" in v or "GRAIN" in v or "HOUSING" in v:
            return cls.IN_KIND
        return cls.UNKNOWN


class BenefitCalculationStatus(str, Enum):
    """Outcome status of benefit calculation."""
    CALCULATED = "CALCULATED"
    CONDITIONAL = "CONDITIONAL"
    CANNOT_DETERMINE = "CANNOT_DETERMINE"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


@dataclass
class BenefitResult:
    """Structured result of deterministic benefit calculation."""
    scheme_id: str
    scheme_name: str
    benefit_type: BenefitType
    amount: Optional[float] = None
    currency: str = "INR"
    disbursement_frequency: Optional[str] = None  # e.g., "ANNUAL", "MONTHLY", "ONE_TIME"
    formula_applied: Optional[str] = None
    status: BenefitCalculationStatus = BenefitCalculationStatus.CANNOT_DETERMINE
    reasoning: str = ""
    verbatim_policy_evidence: Optional[str] = None
    unstructured_note: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scheme_id": self.scheme_id,
            "scheme_name": self.scheme_name,
            "benefit_type": self.benefit_type.value,
            "amount": self.amount,
            "currency": self.currency,
            "disbursement_frequency": self.disbursement_frequency,
            "formula_applied": self.formula_applied,
            "status": self.status.value,
            "reasoning": self.reasoning,
            "verbatim_policy_evidence": self.verbatim_policy_evidence,
            "unstructured_note": self.unstructured_note,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BenefitResult":
        b_type = BenefitType.from_str(data.get("benefit_type", BenefitType.UNKNOWN.value))
        status_val = data.get("status", BenefitCalculationStatus.CANNOT_DETERMINE.value)
        try:
            status = BenefitCalculationStatus(status_val)
        except ValueError:
            status = BenefitCalculationStatus.CANNOT_DETERMINE

        return cls(
            scheme_id=data.get("scheme_id", ""),
            scheme_name=data.get("scheme_name", ""),
            benefit_type=b_type,
            amount=data.get("amount"),
            currency=data.get("currency", "INR"),
            disbursement_frequency=data.get("disbursement_frequency"),
            formula_applied=data.get("formula_applied"),
            status=status,
            reasoning=data.get("reasoning", ""),
            verbatim_policy_evidence=data.get("verbatim_policy_evidence"),
            unstructured_note=data.get("unstructured_note"),
        )


@dataclass
class StructuredBenefitRule:
    """Explicit, pre-compiled benefit calculation rule."""
    rule_id: str
    scheme_id: str
    benefit_type: BenefitType
    calculation_type: str  # "FLAT", "BRACKET", "PERCENTAGE_CAPPED"
    disbursement_frequency: str
    evaluator: Callable[[Dict[str, Any]], Tuple[Optional[float], str, BenefitCalculationStatus]]
    description: str = ""


# Static registry of pre-compiled, verified benefit rules
def _eval_pm_kisan(facts: Dict[str, Any]) -> Tuple[Optional[float], str, BenefitCalculationStatus]:
    """PM-KISAN: Rs. 6,000 per year payable in three equal four-monthly installments of Rs. 2,000."""
    return (
        6000.0,
        "Statutory fixed cash transfer of Rs 6,000 per year in 3 equal installments of Rs 2,000 each.",
        BenefitCalculationStatus.CALCULATED,
    )


def _eval_pm_awas_rural(facts: Dict[str, Any]) -> Tuple[Optional[float], str, BenefitCalculationStatus]:
    """PMAY-G: Rs 1,20,000 for plain areas; Rs 1,30,000 for hilly/difficult areas."""
    terrain = str(facts.get("terrain", facts.get("region_type", "plain"))).strip().lower()
    if terrain in ("hilly", "difficult", "northeastern", "himalayan"):
        return (
            130000.0,
            "Housing grant of Rs 1,30,000 for identified hilly / difficult / IAP areas.",
            BenefitCalculationStatus.CALCULATED,
        )
    return (
        120000.0,
        "Housing grant of Rs 1,20,000 for plain areas.",
        BenefitCalculationStatus.CALCULATED,
    )


def _eval_sc_post_matric_scholarship(facts: Dict[str, Any]) -> Tuple[Optional[float], str, BenefitCalculationStatus]:
    """Post-Matric Scholarship for SC Students: Maintenance allowance based on hosteller status."""
    is_hosteller = bool(facts.get("is_hosteller", facts.get("hosteller", False)))
    course_group = str(facts.get("course_group", "Group 1")).strip().upper()

    # Maintenance allowance tiers
    if is_hosteller:
        amount = 13500.0 if "GROUP 1" in course_group or "DEGREE" in course_group else 9500.0
        return (
            amount,
            f"Hosteller annual maintenance allowance tier: Rs {amount:,.0f} + full non-refundable compulsory fees.",
            BenefitCalculationStatus.CALCULATED,
        )
    else:
        amount = 7000.0 if "GROUP 1" in course_group or "DEGREE" in course_group else 4000.0
        return (
            amount,
            f"Day-scholar annual maintenance allowance tier: Rs {amount:,.0f} + full non-refundable compulsory fees.",
            BenefitCalculationStatus.CALCULATED,
        )


def _eval_pm_suraksha_bima(facts: Dict[str, Any]) -> Tuple[Optional[float], str, BenefitCalculationStatus]:
    """PMSBY: Accidental death/disability cover of Rs 2,00,000."""
    return (
        200000.0,
        "Risk coverage of Rs 2,00,000 for accidental death or full permanent disability (Annual premium: Rs 20).",
        BenefitCalculationStatus.CALCULATED,
    )


REGISTERED_BENEFIT_RULES: Dict[str, StructuredBenefitRule] = {
    "pm_kisan": StructuredBenefitRule(
        rule_id="RULE_PM_KISAN_2019",
        scheme_id="pm_kisan",
        benefit_type=BenefitType.DIRECT_BENEFIT_TRANSFER,
        calculation_type="FLAT",
        disbursement_frequency="ANNUAL",
        evaluator=_eval_pm_kisan,
        description="Rs. 6,000/year in three 4-monthly installments of Rs. 2,000",
    ),
    "pmay_g": StructuredBenefitRule(
        rule_id="RULE_PMAY_G_2016",
        scheme_id="pmay_g",
        benefit_type=BenefitType.SUBSIDY,
        calculation_type="BRACKET",
        disbursement_frequency="ONE_TIME",
        evaluator=_eval_pm_awas_rural,
        description="Rs 1,20,000 (plains) / Rs 1,30,000 (hilly/difficult)",
    ),
    "sc_post_matric_scholarship": StructuredBenefitRule(
        rule_id="RULE_SC_PMS_2020",
        scheme_id="sc_post_matric_scholarship",
        benefit_type=BenefitType.SCHOLARSHIP,
        calculation_type="BRACKET",
        disbursement_frequency="ANNUAL",
        evaluator=_eval_sc_post_matric_scholarship,
        description="Maintenance allowance + tuition waiver based on hosteller status",
    ),
    "pmsby": StructuredBenefitRule(
        rule_id="RULE_PMSBY_2015",
        scheme_id="pmsby",
        benefit_type=BenefitType.DIRECT_BENEFIT_TRANSFER,
        calculation_type="FLAT",
        disbursement_frequency="ANNUAL",
        evaluator=_eval_pm_suraksha_bima,
        description="Rs 2,00,000 accidental cover",
    ),
}


class BenefitCalculator:
    """
    Authoritative deterministic engine for calculating citizen benefits.
    Strictly forbids dynamic LLM formula synthesis.
    """

    def __init__(self, custom_rules: Optional[Dict[str, StructuredBenefitRule]] = None):
        self._rules = dict(REGISTERED_BENEFIT_RULES)
        if custom_rules:
            self._rules.update(custom_rules)

    def register_rule(self, rule: StructuredBenefitRule) -> None:
        self._rules[rule.scheme_id.lower().strip()] = rule

    def calculate(
        self,
        scheme_id: str,
        scheme_name: str,
        applicant_facts: Dict[str, Any],
        raw_benefit_text: Optional[str] = None,
        structured_metadata: Optional[Dict[str, Any]] = None,
    ) -> BenefitResult:
        """
        Calculates benefit deterministically.
        Order of evaluation:
          1. Pre-compiled registered rule in rule catalog.
          2. Explicit structured metadata fields (flat_amount, subsidy_percent, cap).
          3. Unstructured text ONLY -> Safe fallback (CANNOT_DETERMINE / MANUAL_REVIEW_REQUIRED).
             NO runtime formula parsing.
        """
        norm_id = scheme_id.lower().strip().replace("-", "_").replace(" ", "_")
        metadata = structured_metadata or {}

        # 1. Check registered static rule
        if norm_id in self._rules:
            rule = self._rules[norm_id]
            amount, reasoning, status = rule.evaluator(applicant_facts)
            return BenefitResult(
                scheme_id=scheme_id,
                scheme_name=scheme_name,
                benefit_type=rule.benefit_type,
                amount=amount,
                currency="INR",
                disbursement_frequency=rule.disbursement_frequency,
                formula_applied=rule.rule_id,
                status=status,
                reasoning=reasoning,
                verbatim_policy_evidence=raw_benefit_text,
            )

        # 2. Check explicit structured metadata
        if "benefit_amount" in metadata and isinstance(metadata["benefit_amount"], (int, float)):
            amt = float(metadata["benefit_amount"])
            b_type = BenefitType.from_str(metadata.get("benefit_type", "DIRECT_BENEFIT_TRANSFER"))
            freq = metadata.get("disbursement_frequency", "ONE_TIME")
            return BenefitResult(
                scheme_id=scheme_id,
                scheme_name=scheme_name,
                benefit_type=b_type,
                amount=amt,
                currency="INR",
                disbursement_frequency=freq,
                formula_applied="METADATA_DIRECT_AMOUNT",
                status=BenefitCalculationStatus.CALCULATED,
                reasoning=f"Computed from verified structured policy metadata: Rs {amt:,.2f} ({freq}).",
                verbatim_policy_evidence=raw_benefit_text,
            )

        if "subsidy_percentage" in metadata and isinstance(metadata["subsidy_percentage"], (int, float)):
            pct = float(metadata["subsidy_percentage"])
            cap = float(metadata.get("subsidy_cap", float("inf")))
            project_cost = float(applicant_facts.get("project_cost", applicant_facts.get("investment_cost", 0.0)))

            if project_cost > 0.0:
                raw_subsidy = (pct / 100.0) * project_cost
                final_amount = min(raw_subsidy, cap)
                return BenefitResult(
                    scheme_id=scheme_id,
                    scheme_name=scheme_name,
                    benefit_type=BenefitType.SUBSIDY,
                    amount=final_amount,
                    currency="INR",
                    disbursement_frequency="ONE_TIME",
                    formula_applied="METADATA_SUBSIDY_PERCENTAGE_CAPPED",
                    status=BenefitCalculationStatus.CALCULATED,
                    reasoning=(
                        f"Applied structured subsidy formula: {pct}% of Rs {project_cost:,.2f} = Rs {raw_subsidy:,.2f}"
                        + (f" (capped at statutory limit of Rs {cap:,.2f})." if raw_subsidy > cap else ".")
                    ),
                    verbatim_policy_evidence=raw_benefit_text,
                )
            else:
                return BenefitResult(
                    scheme_id=scheme_id,
                    scheme_name=scheme_name,
                    benefit_type=BenefitType.SUBSIDY,
                    amount=None,
                    currency="INR",
                    disbursement_frequency="ONE_TIME",
                    formula_applied="METADATA_SUBSIDY_PERCENTAGE_CAPPED",
                    status=BenefitCalculationStatus.CONDITIONAL,
                    reasoning=f"Requires project cost to calculate {pct}% subsidy (up to Rs {cap:,.2f}).",
                    verbatim_policy_evidence=raw_benefit_text,
                )

        # 3. Policy has only unstructured text: STRICTLY return CANNOT_DETERMINE / MANUAL_REVIEW
        # DO NOT use LLM or regex to extract new formulas!
        return BenefitResult(
            scheme_id=scheme_id,
            scheme_name=scheme_name,
            benefit_type=BenefitType.from_str(raw_benefit_text or "UNKNOWN"),
            amount=None,
            currency="INR",
            disbursement_frequency=None,
            formula_applied=None,
            status=BenefitCalculationStatus.CANNOT_DETERMINE,
            reasoning=(
                "No registered structured calculation rule exists for this scheme. "
                "Per system safety invariants, quantitative benefit formulas cannot be synthesized at runtime."
            ),
            verbatim_policy_evidence=raw_benefit_text,
            unstructured_note=raw_benefit_text,
        )
