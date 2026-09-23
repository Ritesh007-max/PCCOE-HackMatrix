"""
Deterministic Next Action Engine.
Phase 10: Rule-based, policy-grounded next action generation.
LLMs must NOT invent actions; all actions are derived from workflow state and evidence.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional

from .status import ActionType, ActionPriority, ReadinessStatus, StatutoryDecision
from .case import ApplicationCase, SchemeEvaluation
from .readiness import DocumentCompletenessReport


def generate_action_id() -> str:
    """Generate unique action identifier."""
    return f"act_{uuid.uuid4().hex[:12]}"


@dataclass
class NextAction:
    """
    Deterministic next action item for applicant or caseworker.
    """
    action_id: str
    action_type: ActionType
    priority: ActionPriority
    title: str
    reason: str
    related_scheme_id: Optional[str] = None
    required_document_type: Optional[str] = None
    required_field: Optional[str] = None
    evidence_reference: Optional[str] = None
    action_metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "priority": self.priority.value,
            "title": self.title,
            "reason": self.reason,
            "related_scheme_id": self.related_scheme_id,
            "required_document_type": self.required_document_type,
            "required_field": self.required_field,
            "evidence_reference": self.evidence_reference,
            "action_metadata": self.action_metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NextAction":
        atype_raw = data["action_type"]
        atype = ActionType(atype_raw) if atype_raw in ActionType.__members__ else ActionType.PROVIDE_INFORMATION
        prio_raw = data.get("priority", ActionPriority.MEDIUM.value)
        prio = ActionPriority(prio_raw) if prio_raw in ActionPriority.__members__ else ActionPriority.MEDIUM

        return cls(
            action_id=data["action_id"],
            action_type=atype,
            priority=prio,
            title=data.get("title", ""),
            reason=data.get("reason", ""),
            related_scheme_id=data.get("related_scheme_id"),
            required_document_type=data.get("required_document_type"),
            required_field=data.get("required_field"),
            evidence_reference=data.get("evidence_reference"),
            action_metadata=data.get("action_metadata", {}),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
        )


class NextActionEngine:
    """
    Produces deterministic, grounded actions directly from workflow state,
    rule evaluations, and document completeness reports.
    """

    @classmethod
    def generate_actions(
        cls,
        case: ApplicationCase,
        target_evaluation: Optional[SchemeEvaluation] = None,
        doc_report: Optional[DocumentCompletenessReport] = None,
        official_portal_url: Optional[str] = None,
    ) -> List[NextAction]:
        """
        Generate prioritized actions for the application case.
        """
        actions: List[NextAction] = []
        eval_to_use = target_evaluation or case.get_selected_evaluation()
        scheme_id = eval_to_use.scheme_id if eval_to_use else case.selected_scheme_id

        # 1. High Priority: Resolve Conflicts
        conflicts = set(case.facts.conflicted_fields)
        if eval_to_use:
            conflicts.update(eval_to_use.conflicted_fields)
        for conflict_field in sorted(conflicts):
            actions.append(
                NextAction(
                    action_id=generate_action_id(),
                    action_type=ActionType.RESOLVE_CONFLICT,
                    priority=ActionPriority.HIGH,
                    title=f"Resolve Conflicting Data: {conflict_field}",
                    reason=f"Multiple documents or sources provide contradictory values for '{conflict_field}'.",
                    related_scheme_id=scheme_id,
                    required_field=conflict_field,
                )
            )

        # 2. High Priority: Upload Missing Required Documents
        if doc_report and doc_report.missing_documents:
            for missing_doc in doc_report.missing_documents:
                actions.append(
                    NextAction(
                        action_id=generate_action_id(),
                        action_type=ActionType.UPLOAD_DOCUMENT,
                        priority=ActionPriority.HIGH,
                        title=f"Upload Required Document: {missing_doc}",
                        reason=f"This scheme requires '{missing_doc}' to verify eligibility.",
                        related_scheme_id=scheme_id,
                        required_document_type=missing_doc,
                    )
                )

        # 3. Medium Priority: Provide Missing Information / Profile Facts
        if eval_to_use and eval_to_use.missing_fields:
            for missing_field in eval_to_use.missing_fields:
                actions.append(
                    NextAction(
                        action_id=generate_action_id(),
                        action_type=ActionType.PROVIDE_INFORMATION,
                        priority=ActionPriority.MEDIUM,
                        title=f"Provide Profile Information: {missing_field}",
                        reason=f"Field '{missing_field}' is required to evaluate eligibility for scheme '{eval_to_use.scheme_name or scheme_id}'.",
                        related_scheme_id=scheme_id,
                        required_field=missing_field,
                    )
                )

        # 4. Medium Priority: Manual Caseworker Review
        if eval_to_use and eval_to_use.decision_status == StatutoryDecision.REVIEW:
            actions.append(
                NextAction(
                    action_id=generate_action_id(),
                    action_type=ActionType.REVIEW_ELIGIBILITY,
                    priority=ActionPriority.MEDIUM,
                    title="Manual Caseworker Review Required",
                    reason="Policy contains subjective conditions, ambiguous wording, or requires departmental verification.",
                    related_scheme_id=scheme_id,
                )
            )

        # 5. Low Priority: View Computed Benefit
        if eval_to_use and eval_to_use.benefit_summary:
            benefit_val = eval_to_use.benefit_summary.get("amount") or eval_to_use.benefit_summary.get("description", "Benefit")
            actions.append(
                NextAction(
                    action_id=generate_action_id(),
                    action_type=ActionType.VIEW_BENEFIT,
                    priority=ActionPriority.LOW,
                    title="Review Estimated Benefit Entitlement",
                    reason=f"Estimated entitlement calculated: {benefit_val}.",
                    related_scheme_id=scheme_id,
                    action_metadata=eval_to_use.benefit_summary,
                )
            )

        # 6. High/Medium Priority: Ready to Apply
        if case.readiness == ReadinessStatus.READY_TO_APPLY:
            actions.append(
                NextAction(
                    action_id=generate_action_id(),
                    action_type=ActionType.READY_TO_APPLY,
                    priority=ActionPriority.HIGH,
                    title="Proceed to Application Submission",
                    reason="All statutory conditions satisfied and all required documentation verified.",
                    related_scheme_id=scheme_id,
                )
            )
            portal = official_portal_url or "https://myscheme.gov.in"
            actions.append(
                NextAction(
                    action_id=generate_action_id(),
                    action_type=ActionType.VISIT_OFFICIAL_PORTAL,
                    priority=ActionPriority.HIGH,
                    title="Visit Official Government Scheme Portal",
                    reason=f"Apply online at the official state/central portal: {portal}",
                    related_scheme_id=scheme_id,
                    action_metadata={"portal_url": portal},
                )
            )
            actions.append(
                NextAction(
                    action_id=generate_action_id(),
                    action_type=ActionType.CHECK_APPLICATION_STEPS,
                    priority=ActionPriority.MEDIUM,
                    title="Review Formal Application Submission Steps",
                    reason="Verify submission deadlines, fee exemptions, and department verification procedures.",
                    related_scheme_id=scheme_id,
                )
            )

        return actions
