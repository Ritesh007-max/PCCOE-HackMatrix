"""
Application Readiness and Document/Fact Completeness Evaluator.
Phase 10: Deterministic evaluation of application readiness and checklist generation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .status import (
    ReadinessStatus,
    StatutoryDecision,
    DocumentRequirementStatus,
    FactCompletenessStatus,
)
from .case import ApplicationCase, DocumentReference, SchemeEvaluation


@dataclass
class DocumentCompletenessReport:
    """Detailed audit of scheme document requirements vs attached documents."""
    required_documents: Dict[str, DocumentRequirementStatus] = field(default_factory=dict)
    missing_documents: List[str] = field(default_factory=list)
    available_documents: List[str] = field(default_factory=list)
    conflicted_documents: List[str] = field(default_factory=list)
    is_complete: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "required_documents": {k: v.value for k, v in self.required_documents.items()},
            "missing_documents": self.missing_documents,
            "available_documents": self.available_documents,
            "conflicted_documents": self.conflicted_documents,
            "is_complete": self.is_complete,
        }


@dataclass
class FactCompletenessReport:
    """Audit of required facts against applicant profile."""
    known_fields: List[str] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    conflicted_fields: List[str] = field(default_factory=list)
    is_complete: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "known_fields": self.known_fields,
            "missing_fields": self.missing_fields,
            "conflicted_fields": self.conflicted_fields,
            "is_complete": self.is_complete,
        }


@dataclass
class ApplicationChecklist:
    """Deterministic checklist representation for citizen or caseworker."""
    documents: List[Dict[str, str]] = field(default_factory=list)
    information: List[Dict[str, str]] = field(default_factory=list)
    review: List[Dict[str, str]] = field(default_factory=list)
    application_steps: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "documents": self.documents,
            "information": self.information,
            "review": self.review,
            "application_steps": self.application_steps,
        }


class ApplicationReadinessEvaluator:
    """
    Evaluates whether an application is ready to apply or requires actions.
    Enforces deterministic readiness matrix:
        PASS + complete documents + no conflicts -> READY_TO_APPLY
        PASS + missing documents                 -> ACTION_REQUIRED
        UNKNOWN + missing facts / docs           -> ACTION_REQUIRED
        REVIEW + conflict / unstructured rule    -> READY_FOR_REVIEW
        FAIL                                     -> NOT_READY
    """

    @staticmethod
    def _normalize_doc_name(name: str) -> str:
        """Normalize document names for matching (e.g. 'Income Certificate' -> 'income_certificate')."""
        return name.strip().lower().replace(" ", "_").replace("-", "_")

    @classmethod
    def evaluate_document_completeness(
        cls,
        required_document_types: List[str],
        attached_documents: List[DocumentReference],
    ) -> DocumentCompletenessReport:
        """
        Evaluate uploaded documents against scheme document requirements.
        """
        report = DocumentCompletenessReport()
        if not required_document_types:
            report.is_complete = True
            return report

        # Index available docs by normalized type
        available_types: Set[str] = set()
        for doc in attached_documents:
            norm_type = cls._normalize_doc_name(doc.document_type)
            norm_filename = cls._normalize_doc_name(doc.filename)
            available_types.add(norm_type)
            # Also check if filename hints at the doc type
            for req in required_document_types:
                if cls._normalize_doc_name(req) in norm_filename:
                    available_types.add(cls._normalize_doc_name(req))

        for req in required_document_types:
            norm_req = cls._normalize_doc_name(req)
            matched = False
            for avail in available_types:
                if norm_req in avail or avail in norm_req:
                    matched = True
                    break

            if matched:
                report.required_documents[req] = DocumentRequirementStatus.AVAILABLE
                report.available_documents.append(req)
            else:
                report.required_documents[req] = DocumentRequirementStatus.MISSING
                report.missing_documents.append(req)

        report.is_complete = (len(report.missing_documents) == 0 and len(report.conflicted_documents) == 0)
        return report

    @classmethod
    def evaluate_fact_completeness(
        cls,
        evaluation: SchemeEvaluation,
        profile_facts: Dict[str, Any],
        conflicted_fields: Optional[List[str]] = None,
    ) -> FactCompletenessReport:
        """
        Evaluate fact completeness from the evaluated rules and profile facts.
        """
        conflicts = set(conflicted_fields or [])
        conflicts.update(evaluation.conflicted_fields)

        missing = list(evaluation.missing_fields)
        known = [k for k in profile_facts.keys() if k not in conflicts and k not in missing]

        return FactCompletenessReport(
            known_fields=known,
            missing_fields=missing,
            conflicted_fields=list(conflicts),
            is_complete=(len(missing) == 0 and len(conflicts) == 0),
        )

    @classmethod
    def evaluate_readiness(
        cls,
        case: ApplicationCase,
        target_evaluation: Optional[SchemeEvaluation] = None,
        required_documents: Optional[List[str]] = None,
    ) -> ReadinessStatus:
        """
        Deterministic readiness evaluation.
        """
        eval_to_use = target_evaluation or case.get_selected_evaluation()
        if not eval_to_use:
            return ReadinessStatus.NOT_READY

        # Statutory decision
        decision = eval_to_use.decision_status
        if isinstance(decision, str):
            decision = StatutoryDecision(decision)

        # 1. Statutory FAIL -> NOT_READY
        if decision == StatutoryDecision.FAIL:
            return ReadinessStatus.NOT_READY

        # 2. Check for conflicts -> READY_FOR_REVIEW
        conflicts = set(case.facts.conflicted_fields) | set(eval_to_use.conflicted_fields)
        if conflicts or decision == StatutoryDecision.REVIEW:
            return ReadinessStatus.READY_FOR_REVIEW

        # 3. Check document completeness
        req_docs = required_documents or []
        doc_report = cls.evaluate_document_completeness(
            required_document_types=req_docs,
            attached_documents=list(case.documents.values()),
        )

        # 4. Check fact completeness
        has_missing_facts = len(eval_to_use.missing_fields) > 0 or decision == StatutoryDecision.UNKNOWN

        # Decision Matrix
        if decision == StatutoryDecision.PASS:
            if not doc_report.is_complete:
                return ReadinessStatus.ACTION_REQUIRED
            if has_missing_facts:
                return ReadinessStatus.ACTION_REQUIRED
            return ReadinessStatus.READY_TO_APPLY

        if decision == StatutoryDecision.UNKNOWN:
            return ReadinessStatus.ACTION_REQUIRED

        return ReadinessStatus.NOT_READY

    @classmethod
    def generate_checklist(
        cls,
        case: ApplicationCase,
        target_evaluation: Optional[SchemeEvaluation] = None,
        required_documents: Optional[List[str]] = None,
    ) -> ApplicationChecklist:
        """
        Generates a deterministic checklist of documents, facts, review, and application steps.
        """
        checklist = ApplicationChecklist()
        eval_to_use = target_evaluation or case.get_selected_evaluation()
        req_docs = required_documents or []

        # 1. Documents checklist
        doc_report = cls.evaluate_document_completeness(req_docs, list(case.documents.values()))
        for doc in req_docs:
            st = doc_report.required_documents.get(doc, DocumentRequirementStatus.MISSING)
            checklist.documents.append({
                "item": doc,
                "status": "COMPLETE" if st == DocumentRequirementStatus.AVAILABLE else "PENDING",
            })

        # 2. Information checklist
        if eval_to_use:
            for f in eval_to_use.missing_fields:
                checklist.information.append({
                    "item": f,
                    "status": "MISSING",
                })
            for k in case.facts.facts.keys():
                checklist.information.append({
                    "item": k,
                    "status": "COMPLETE",
                })

        # 3. Review checklist
        conflicts = set(case.facts.conflicted_fields)
        if eval_to_use:
            conflicts.update(eval_to_use.conflicted_fields)
        for c in conflicts:
            checklist.review.append({
                "item": f"Resolve conflict in '{c}'",
                "status": "REQUIRED",
            })

        # 4. Application steps
        readiness = cls.evaluate_readiness(case, eval_to_use, req_docs)
        if readiness == ReadinessStatus.READY_TO_APPLY:
            checklist.application_steps.append({
                "item": "Visit official portal to submit application",
                "status": "READY",
            })
            checklist.application_steps.append({
                "item": "Download pre-filled verification summary",
                "status": "READY",
            })
        else:
            checklist.application_steps.append({
                "item": "Complete outstanding checklist items before application submission",
                "status": "BLOCKED",
            })

        return checklist
