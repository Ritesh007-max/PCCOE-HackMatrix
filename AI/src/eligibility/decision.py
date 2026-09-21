"""
PolicySetu Eligibility Decision Model.
Encapsulates evaluation results, missing field diagnostics, and audit trails.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from src.rules.models import RuleStatus, RuleEvaluationResult

@dataclass
class EligibilityDecision:
    """Represents the final statutory eligibility decision for a government scheme."""
    scheme_id: str
    scheme_slug: str
    scheme_name: str
    status: RuleStatus
    eligible: Optional[bool]
    rule_results: List[RuleEvaluationResult] = field(default_factory=list)
    passed_rules: List[str] = field(default_factory=list)
    failed_rules: List[str] = field(default_factory=list)
    unknown_rules: List[str] = field(default_factory=list)
    review_rules: List[str] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    disqualification_reasons: List[str] = field(default_factory=list)
    confidence: float = 1.0
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_evaluation(
        cls,
        scheme_id: str,
        scheme_slug: str,
        scheme_name: str,
        overall_status: RuleStatus,
        rule_results: List[RuleEvaluationResult]
    ) -> "EligibilityDecision":
        """Builds an EligibilityDecision from rule evaluation results."""
        passed = [r.rule_id for r in rule_results if r.status == RuleStatus.PASS]
        failed = [r.rule_id for r in rule_results if r.status == RuleStatus.FAIL]
        unknown = [r.rule_id for r in rule_results if r.status == RuleStatus.UNKNOWN]
        review = [r.rule_id for r in rule_results if r.status == RuleStatus.REVIEW]

        missing_fields = sorted(list({r.field for r in rule_results if r.status == RuleStatus.UNKNOWN}))

        disqualification_reasons = [
            f"Violated statutory criteria '{r.field}': {r.reason} (Statute: \"{r.raw_text}\")"
            for r in rule_results if r.status == RuleStatus.FAIL and r.hard_constraint
        ]

        # Invariant: eligible boolean is True ONLY for PASS, False for FAIL, None for UNKNOWN/REVIEW
        if overall_status == RuleStatus.PASS:
            eligible = True
        elif overall_status == RuleStatus.FAIL:
            eligible = False
        else:
            eligible = None

        audit_trail = [r.to_dict() for r in rule_results]

        # Calculate confidence as average rule confidence
        conf = 1.0
        if rule_results:
            confs = [getattr(r.rule, "confidence", 1.0) for r in rule_results if r.rule]
            conf = round(sum(confs) / len(confs), 3) if confs else 1.0

        return cls(
            scheme_id=scheme_id,
            scheme_slug=scheme_slug,
            scheme_name=scheme_name,
            status=overall_status,
            eligible=eligible,
            rule_results=rule_results,
            passed_rules=passed,
            failed_rules=failed,
            unknown_rules=unknown,
            review_rules=review,
            missing_fields=missing_fields,
            disqualification_reasons=disqualification_reasons,
            confidence=conf,
            audit_trail=audit_trail
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scheme_id": self.scheme_id,
            "scheme_slug": self.scheme_slug,
            "scheme_name": self.scheme_name,
            "status": self.status.value,
            "eligible": self.eligible,
            "passed_rules": self.passed_rules,
            "failed_rules": self.failed_rules,
            "unknown_rules": self.unknown_rules,
            "review_rules": self.review_rules,
            "missing_fields": self.missing_fields,
            "disqualification_reasons": self.disqualification_reasons,
            "confidence": self.confidence,
            "audit_trail": self.audit_trail
        }
