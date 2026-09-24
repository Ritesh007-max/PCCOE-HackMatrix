"""
Checklist Adapter for Citizen Guidance.
Phase 11: Guidance-friendly representation of Phase 10 checklist without duplicating business logic.
"""

from typing import Any, Dict, List, Optional
from src.application.case import ApplicationCase, SchemeEvaluation
from src.application.readiness import ApplicationReadinessEvaluator, ApplicationChecklist


class GuidanceChecklistAdapter:
    """
    Transforms Phase 10 ApplicationChecklist into a guidance-friendly format
    suitable for immediate frontend rendering.
    """

    @classmethod
    def adapt_checklist(
        cls,
        case: ApplicationCase,
        evaluation: Optional[SchemeEvaluation] = None,
        required_documents: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Extracts checklist ready/missing/review items.
        """
        raw_checklist: ApplicationChecklist = ApplicationReadinessEvaluator.generate_checklist(
            case=case,
            target_evaluation=evaluation,
            required_documents=required_documents,
        )

        docs_ready: List[str] = []
        docs_missing: List[str] = []
        docs_clarification: List[str] = []

        for doc in raw_checklist.documents:
            name = doc.get("item", "")
            st = doc.get("status", "")
            if st == "COMPLETE":
                docs_ready.append(name)
            elif st == "CONFLICTED":
                docs_clarification.append(name)
            else:
                docs_missing.append(name)

        return {
            "documents_ready": docs_ready,
            "documents_missing": docs_missing,
            "documents_needing_clarification": docs_clarification,
            "all_document_items": raw_checklist.documents,
            "information_items": raw_checklist.information,
            "review_items": raw_checklist.review,
            "application_steps": raw_checklist.application_steps,
        }
