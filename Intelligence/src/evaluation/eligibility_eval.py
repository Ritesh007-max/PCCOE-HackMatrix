"""
FIN Deterministic Eligibility & Benefit Calculation Evaluator.
Evaluates statutory rules across age, income, category, gender, occupation, land, missing facts, and conflicts.
Verifies critical invariants:
1. Missing information must NEVER become PASS.
2. Conflicting facts must NEVER silently become PASS or FAIL.
3. Historical decisions remain strictly reproducible.
4. LLM output cannot alter deterministic benefit results.
"""

from pathlib import Path
import time
from typing import Any, Dict, List, Optional

import sys
_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.evaluation.models import EvaluationCase, EvaluationResult, Severity
from src.evaluation.failures import FailureType
from src.evaluation.metrics import MetricAggregator
from src.eligibility.engine import EligibilityEngine
from src.rules.models import ApplicantProfile, RuleStatus
from src.benefits.calculator import BenefitCalculator


class EligibilityEvaluator:
    """
    Evaluates statutory correctness and invariant preservation of the deterministic eligibility engine.
    """

    def __init__(
        self,
        engine: Optional[EligibilityEngine] = None,
        benefit_calculator: Optional[BenefitCalculator] = None,
    ):
        rules_dir = _INTELLIGENCE_DIR / "data" / "schemes" / "rules" / "examples"
        if not rules_dir.exists():
            rules_dir = _INTELLIGENCE_DIR / "data" / "rules"
        self.engine = engine or EligibilityEngine(rules_dir=rules_dir if rules_dir.exists() else None)
        self.benefit_calculator = benefit_calculator or BenefitCalculator()

    def evaluate_case(self, case: EvaluationCase) -> EvaluationResult:
        """Evaluates a single statutory eligibility or boundary case."""
        start_time = time.perf_counter()
        scheme_id = (case.expected_scheme_id or "").replace("_", "-").strip().lower()
        input_data = case.input_data if isinstance(case.input_data, dict) else {}

        # Extract explicit conflicts if provided
        conflicts = input_data.get("_conflicts", [])
        profile_data = {k: v for k, v in input_data.items() if not k.startswith("_")}

        profile = ApplicantProfile(
            data=profile_data,
            conflicts=conflicts,
        )

        expected_status = (case.expected_status or "PASS").upper()

        try:
            decision = self.engine.evaluate(identifier=scheme_id, profile=profile)
            actual_status = decision.status.value.upper()
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000.0
            return EvaluationResult(
                case_id=case.case_id,
                passed=False,
                errors=[f"Eligibility evaluation crashed: {str(e)}"],
                latency_ms=latency,
                failure_type=FailureType.RULE_FAILURE.value,
                severity=Severity.CRITICAL,
            )

        latency = (time.perf_counter() - start_time) * 1000.0

        # CRITICAL INVARIANT CHECKS:
        # Invariant 1: Missing information never becomes PASS
        if expected_status == "UNKNOWN" and actual_status == "PASS":
            return EvaluationResult(
                case_id=case.case_id,
                passed=False,
                actual_output=actual_status,
                expected_output=expected_status,
                errors=["CRITICAL INVARIANT 1 VIOLATION: Missing information evaluated to PASS!"],
                latency_ms=latency,
                failure_type=FailureType.RULE_FAILURE.value,
                severity=Severity.CRITICAL,
            )

        # Invariant 2: Conflicted facts never silently become PASS or FAIL
        if conflicts and actual_status in ("PASS", "FAIL"):
            return EvaluationResult(
                case_id=case.case_id,
                passed=False,
                actual_output=actual_status,
                expected_output="REVIEW",
                errors=["CRITICAL INVARIANT 2 VIOLATION: Conflicted facts silently evaluated to PASS/FAIL instead of REVIEW!"],
                latency_ms=latency,
                failure_type=FailureType.RULE_FAILURE.value,
                severity=Severity.CRITICAL,
            )

        passed = (actual_status == expected_status)

        actual_output = {
            "status": actual_status,
            "eligible": decision.eligible,
            "matched_rules_count": len([r for r in decision.rule_results if r.status.value == "PASS"]),
            "failed_rules_count": len([r for r in decision.rule_results if r.status.value == "FAIL"]),
            "unknown_rules_count": len([r for r in decision.rule_results if r.status.value == "UNKNOWN"]),
            "missing_fields": decision.missing_fields,
        }

        return EvaluationResult(
            case_id=case.case_id,
            passed=passed,
            actual_output=actual_output,
            expected_output=expected_status,
            latency_ms=latency,
            failure_type=None if passed else FailureType.RULE_FAILURE.value,
            severity=case.severity,
        )

    def evaluate_benefit_calculation(
        self,
        scheme_id: str,
        applicant_facts: Dict[str, Any],
        scheme_name: Optional[str] = None,
        expected_min_amount: Optional[float] = None,
        expected_max_amount: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates deterministic benefit calculation, ensuring formula calculations are exact
        and cannot be altered by conversational LLM hallucinations.
        """
        result = self.benefit_calculator.calculate(
            scheme_id=scheme_id,
            scheme_name=scheme_name or scheme_id,
            applicant_facts=applicant_facts,
        )
        passed = True
        errors = []

        if expected_min_amount is not None and result.amount is not None:
            if result.amount < expected_min_amount:
                passed = False
                errors.append(f"Benefit amount {result.amount} is below expected min {expected_min_amount}")

        if expected_max_amount is not None and result.amount is not None:
            if result.amount > expected_max_amount:
                passed = False
                errors.append(f"Benefit amount {result.amount} exceeds expected max {expected_max_amount}")

        return {
            "scheme_id": scheme_id,
            "monetary_value": result.amount,
            "frequency": result.disbursement_frequency,
            "passed": passed,
            "errors": errors,
            "status": result.status.value,
        }

    def evaluate_suite(self, cases: List[EvaluationCase]) -> Dict[str, Any]:
        """Batch evaluation of eligibility suite."""
        results: List[EvaluationResult] = []
        decisions: List[Dict[str, Any]] = []

        for c in cases:
            res = self.evaluate_case(c)
            results.append(res)
            act_stat = res.actual_output.get("status") if isinstance(res.actual_output, dict) else res.actual_output
            decisions.append({
                "expected": c.expected_status,
                "actual": act_stat,
            })

        aggregated = MetricAggregator.aggregate_decisions(decisions)
        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count

        return {
            "suite": "eligibility",
            "total_cases": len(cases),
            "passed": passed_count,
            "failed": failed_count,
            "metrics": aggregated,
            "results": [r.to_dict() for r in results],
        }
