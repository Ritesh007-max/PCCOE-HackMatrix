"""
Application Guidance Package Generator.
Phase 11: Coordinates deterministic builders, metadata resolution, multilingual localization,
and validation into an auditable citizen guidance package.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from src.application.case import ApplicationCase, SchemeEvaluation
from src.application.decision import DecisionSnapshot
from src.application.status import StatutoryDecision, ReadinessStatus

from .models import (
    ApplicationGuidancePackage,
    ApplicationMode,
    BenefitGuidance,
    DeadlineGuidance,
    DocumentGuidanceItem,
    EligibilitySummary,
    GuidanceWarning,
    SourceCitation,
)
from .sources import SourceMetadataResolver
from .eligibility_summary import EligibilitySummaryBuilder
from .benefit_summary import BenefitSummaryBuilder
from .documents import DocumentGuidanceBuilder
from .steps import ApplicationStepBuilder
from .warnings import WarningGenerator
from .checklist import GuidanceChecklistAdapter
from .localization import GuidanceLocalizer
from .validator import GuidanceValidator
from .exceptions import GuidanceValidationError, ContradictoryGuidanceError

logger = logging.getLogger("fin.guidance.generator")


class ApplicationGuidanceGenerator:
    """
    Constructs an authoritative ApplicationGuidancePackage directly from Phase 10 case state
    and verified policy metadata.
    """

    def __init__(
        self,
        source_resolver: Optional[SourceMetadataResolver] = None,
        localizer: Optional[GuidanceLocalizer] = None,
    ):
        self.source_resolver = source_resolver or SourceMetadataResolver()
        self.localizer = localizer or GuidanceLocalizer()

    def generate(
        self,
        case: ApplicationCase,
        target_scheme_id: Optional[str] = None,
        snapshot: Optional[DecisionSnapshot] = None,
        language: str = "en",
        query_text: Optional[str] = None,
    ) -> ApplicationGuidancePackage:
        """
        Generates, localizes, and validates the complete citizen guidance package.
        """
        # 1. Determine target scheme and evaluation
        scheme_id = target_scheme_id or case.selected_scheme_id
        if not scheme_id and case.candidate_schemes:
            scheme_id = next(iter(case.candidate_schemes.keys()))
        scheme_id = scheme_id or "unknown_scheme"

        evaluation = case.candidate_schemes.get(scheme_id) if case.candidate_schemes else None
        scheme_name = evaluation.scheme_name if evaluation else scheme_id

        # 2. Resolve authoritative metadata from active Phase 7 snapshot
        meta = self.source_resolver.get_scheme_metadata(scheme_id) or {}
        scheme_name = meta.get("scheme_name") or scheme_name
        app_mode = self.source_resolver.resolve_application_mode(scheme_id)
        portal_url = self.source_resolver.resolve_official_portal_url(scheme_id)
        source_url = self.source_resolver.validate_official_url(meta.get("source_url"))
        policy_version = (snapshot.policy_snapshot_version if snapshot else (evaluation.policy_snapshot_version if evaluation else "snapshot_20260921_193823"))
        rule_version = (snapshot.rule_version if snapshot else (evaluation.rule_version if evaluation else "1.0.0"))

        deadlines = self.source_resolver.resolve_deadlines(scheme_id, policy_version=policy_version)

        # 3. Determine Language
        lang = language
        if lang == "en" and query_text:
            lang = self.localizer.detect_language(query_text)

        # 4. Build Eligibility Summary
        elig_summary = EligibilitySummaryBuilder.build_summary(
            evaluation=evaluation,
            snapshot=snapshot,
            scheme_name=scheme_name,
        )

        # 5. Build Benefit Guidance
        benefit_data = evaluation.benefit_summary if evaluation else (snapshot.benefit_result if snapshot else None)
        ben_guidance = BenefitSummaryBuilder.build_guidance(
            benefit_data=benefit_data,
            scheme_name=scheme_name,
        )

        # 6. Build Document Guidance
        req_docs_raw = meta.get("documents_required")
        required_doc_types: List[str] = []
        if isinstance(req_docs_raw, list):
            required_doc_types = [str(d) for d in req_docs_raw if d is not None]
        elif isinstance(req_docs_raw, str) and req_docs_raw.strip():
            val = req_docs_raw.strip()
            if val.startswith("[") and val.endswith("]"):
                try:
                    import ast
                    parsed = ast.literal_eval(val)
                    if isinstance(parsed, list):
                        required_doc_types = [str(x) for x in parsed if x is not None]
                    else:
                        required_doc_types = [val]
                except Exception:
                    required_doc_types = [val]
            else:
                required_doc_types = [val]

        if not required_doc_types and case.next_actions:
            for act in case.next_actions:
                if act.get("action_type") == "UPLOAD_DOCUMENT":
                    doc_req = act.get("required_document_type") or act.get("required_document")
                    if doc_req and doc_req not in required_doc_types:
                        required_doc_types.append(doc_req)

        doc_guidance = DocumentGuidanceBuilder.build_guidance(
            case=case,
            required_doc_types=required_doc_types,
        )
        missing_docs = doc_guidance.get("missing", [])

        # 7. Build Application Steps
        app_process_text = meta.get("application_process")
        steps = ApplicationStepBuilder.build_steps(
            scheme_id=scheme_id,
            scheme_name=scheme_name,
            application_process_text=app_process_text,
            application_mode=app_mode,
            official_portal_url=portal_url,
            source_url=source_url,
            missing_documents=missing_docs,
        )

        # 8. Build Warnings
        warnings = WarningGenerator.generate_warnings(
            case=case,
            evaluation=evaluation,
            snapshot=snapshot,
            official_portal_url=portal_url,
            missing_documents=missing_docs,
            benefit_status=ben_guidance.status,
            scheme_id=scheme_id,
        )

        # 9. Source Provenance Citations
        sources: List[SourceCitation] = []
        sources.append(
            SourceCitation(
                scheme_id=scheme_id,
                scheme_name=scheme_name,
                source_authority=meta.get("ministry") or meta.get("department") or "Government Portal",
                official_url=portal_url or source_url,
                section="application_process",
                policy_snapshot_version=policy_version,
            )
        )

        # 10. Adapt Checklist
        checklist_data = GuidanceChecklistAdapter.adapt_checklist(
            case=case,
            evaluation=evaluation,
            required_documents=required_doc_types,
        )

        # 11. Format Information & Actions
        merged_missing = list(case.facts.missing_fields)
        if evaluation and evaluation.missing_fields:
            for mf in evaluation.missing_fields:
                if mf not in merged_missing:
                    merged_missing.append(mf)

        information_data = {
            "known": [f"{k}: {v}" for k, v in case.facts.facts.items() if k not in case.facts.conflicted_fields],
            "missing": merged_missing,
            "conflicted": list(case.facts.conflicted_fields),
        }

        # Localize Action Titles if language != "en"
        localized_actions: List[Dict[str, Any]] = []
        for act in case.next_actions:
            act_copy = dict(act)
            if lang != "en":
                act_copy["title"] = self.localizer.localize_action_title(
                    action_type=act.get("action_type", ""),
                    fallback_title=act.get("title", ""),
                    language=lang,
                )
            localized_actions.append(act_copy)

        # Localize Eligibility Summary & Readiness Reason
        if lang != "en":
            elig_summary.summary = self.localizer.localize_eligibility_summary(
                summary=elig_summary.summary,
                decision=elig_summary.status,
                language=lang,
            )

        readiness_reason = self.localizer.localize_readiness_reason(case.readiness.value, lang)

        # 12. Assemble Package
        stat_decision = snapshot.decision_status.value if snapshot else (evaluation.decision_status.value if evaluation else StatutoryDecision.UNKNOWN.value)

        package = ApplicationGuidancePackage(
            application_id=case.application_id,
            scheme_id=scheme_id,
            scheme_name=scheme_name,
            statutory_decision=stat_decision,
            readiness_status=case.readiness.value,
            readiness={
                "status": case.readiness.value,
                "reason": readiness_reason,
            },
            eligibility=elig_summary,
            documents=doc_guidance,
            information=information_data,
            benefit=ben_guidance,
            application={
                "mode": app_mode.value,
                "official_portal_url": portal_url,
                "steps": [s.to_dict() for s in steps],
                "deadlines": deadlines.to_dict(),
                "checklist": checklist_data,
            },
            actions=localized_actions,
            warnings=warnings,
            sources=sources,
            policy_snapshot_version=policy_version,
            rule_version=rule_version,
            language=lang,
            generated_at=datetime.now(timezone.utc).isoformat(),
            is_deterministic_fallback=False,
        )

        # 13. Validate package
        try:
            GuidanceValidator.validate_package(package)
        except ContradictoryGuidanceError as c_err:
            logger.warning("Contradictory guidance detected (%s). Applying deterministic template fallback.", c_err)
            # Revert summary to deterministic template
            package.eligibility.summary = EligibilitySummaryBuilder.build_summary(
                evaluation=evaluation, snapshot=snapshot, scheme_name=scheme_name
            ).summary
            package.is_deterministic_fallback = True
            GuidanceValidator.validate_package(package)

        return package
