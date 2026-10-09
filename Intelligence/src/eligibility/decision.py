"""
FIN Eligibility Decision Model.
Encapsulates deterministic evaluation results, audit trace, missing field diagnostics,
rule version pinning, and provenance citations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional
import uuid

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.rules.models import RuleEvaluationResult, RuleStatus


@dataclass
class EligibilityDecision:
    """
    Represents the final statutory eligibility decision for a government scheme.
    Pinned immutably to a specific rule version, audit trace, and source provenance.
    """
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
    conflicted_fields: List[str] = field(default_factory=list)
    disqualification_reasons: List[str] = field(default_factory=list)
    review_reasons: List[str] = field(default_factory=list)
    confidence: float = 1.0
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)

    # Phase 20 enhancements: immutable version pinning, trace, and provenance
    decision_id: str = field(default_factory=lambda: f"dec_{uuid.uuid4().hex[:12]}")
    applicant_id: Optional[str] = None
    rule_set_id: Optional[str] = None
    rule_version: str = "1.0.0"
    rule_set_hash: Optional[str] = None
    evaluated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    rule_trace: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    completeness: str = "COMPLETE"

    @classmethod
    def from_evaluation(
        cls,
        scheme_id: str,
        scheme_slug: str,
        scheme_name: str,
        overall_status: RuleStatus,
        rule_results: List[RuleEvaluationResult],
        rule_version: str = "1.0.0",
        rule_set_hash: Optional[str] = None,
        applicant_id: Optional[str] = None,
        completeness: str = "COMPLETE",
    ) -> "EligibilityDecision":
        """Builds an EligibilityDecision from rule evaluation results with complete trace and versioning."""
        passed = [r.rule_id for r in rule_results if r.status == RuleStatus.PASS]
        failed = [r.rule_id for r in rule_results if r.status == RuleStatus.FAIL]
        unknown = [r.rule_id for r in rule_results if r.status == RuleStatus.UNKNOWN]
        review = [r.rule_id for r in rule_results if r.status == RuleStatus.REVIEW]

        missing_fields = sorted(list({r.field for r in rule_results if r.status == RuleStatus.UNKNOWN}))
        conflicted_fields = sorted(list({r.field for r in rule_results if r.status == RuleStatus.REVIEW and "contradictory" in r.reason.lower()}))

        disqualification_reasons = [
            f"Violated statutory criteria '{r.field}': {r.reason} (Statute: \"{r.raw_text}\")"
            for r in rule_results if r.status == RuleStatus.FAIL and r.hard_constraint
        ]

        review_reasons = [
            f"Requires review for '{r.field}': {r.reason}"
            for r in rule_results if r.status == RuleStatus.REVIEW
        ]

        # Invariant: eligible boolean is True ONLY for PASS, False for FAIL, None for UNKNOWN/REVIEW
        if overall_status == RuleStatus.PASS:
            eligible = True
        elif overall_status == RuleStatus.FAIL:
            eligible = False
        else:
            eligible = None

        audit_trail = [r.to_dict() for r in rule_results]

        # Build detailed node-level rule trace
        rule_trace = [
            {
                "rule_id": r.rule_id,
                "field": r.field,
                "operator": r.operator,
                "expected": r.expected_value,
                "actual": r.applicant_value,
                "result": r.status.value,
                "hard_constraint": r.hard_constraint,
                "deterministic": True,
                "reason": r.reason,
                "raw_text": r.raw_text,
            }
            for r in rule_results
        ]

        # Build source evidence list
        evidence_list: List[Dict[str, Any]] = []
        for r in rule_results:
            if r.rule:
                ev_item = {
                    "rule_id": r.rule_id,
                    "field": r.field,
                    "source_url": r.rule.source_url,
                    "source_document": r.rule.source_document,
                    "source_page": r.rule.source_page,
                    "source_section": r.rule.source_section,
                    "raw_text": r.raw_text,
                    "provenance": r.rule.provenance,
                }
                evidence_list.append(ev_item)

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
            conflicted_fields=conflicted_fields,
            disqualification_reasons=disqualification_reasons,
            review_reasons=review_reasons,
            confidence=conf,
            audit_trail=audit_trail,
            applicant_id=applicant_id,
            rule_set_id=scheme_id,
            rule_version=rule_version,
            rule_set_hash=rule_set_hash,
            rule_trace=rule_trace,
            evidence=evidence_list,
            completeness=completeness,
        )

    def to_dict(self, include_metadata: bool = False) -> Dict[str, Any]:
        """
        Returns dictionary representation of evaluation result.
        Deterministic across identical evaluations (omits execution timestamps and UUIDs
        unless include_metadata is True).
        """
        d = {
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
            "audit_trail": self.audit_trail,
        }
        if include_metadata:
            d.update({
                "decision_id": self.decision_id,
                "applicant_id": self.applicant_id,
                "rule_version": self.rule_version,
                "rule_set_hash": self.rule_set_hash,
                "evaluated_at": self.evaluated_at,
                "conflicted_fields": self.conflicted_fields,
                "review_reasons": self.review_reasons,
                "completeness": self.completeness,
                "rule_trace": self.rule_trace,
                "evidence": self.evidence,
            })
        return d

    def to_full_dict(self) -> Dict[str, Any]:
        """Returns complete serialized decision object including execution metadata and trace."""
        return self.to_dict(include_metadata=True)

