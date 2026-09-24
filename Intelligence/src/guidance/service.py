"""
Application Guidance Service.
Phase 11: Orchestrates guidance generation, multi-dimensional caching,
and structured package export.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from src.application.service import ApplicationWorkflowService
from src.application.repository import ApplicationRepository, InMemoryApplicationRepository
from src.application.exceptions import ApplicationNotFoundError
from src.application.case import ApplicationCase
from src.application.decision import DecisionSnapshot

from .models import ApplicationGuidancePackage
from .generator import ApplicationGuidanceGenerator
from .sources import SourceMetadataResolver
from .localization import GuidanceLocalizer
from .validator import GuidanceValidator
from .exceptions import GuidanceError

logger = logging.getLogger("fin.guidance.service")


class ApplicationGuidanceService:
    """
    High-level service interface for generating, caching, and exporting
    citizen application guidance packages.
    """

    def __init__(
        self,
        workflow_service: Optional[ApplicationWorkflowService] = None,
        repository: Optional[ApplicationRepository] = None,
        generator: Optional[ApplicationGuidanceGenerator] = None,
    ):
        self.workflow_service = workflow_service or ApplicationWorkflowService(repository=repository)
        self.repository = self.workflow_service.repository
        self.generator = generator or ApplicationGuidanceGenerator()
        # Multi-dimensional cache: (app_id, scheme_id, policy_version, rule_version, language, facts_repr, case_timestamp) -> Package
        self._cache: Dict[Tuple[str, str, str, str, str, str, str], ApplicationGuidancePackage] = {}

    def _compute_cache_key(
        self,
        case: ApplicationCase,
        scheme_id: str,
        policy_version: str,
        rule_version: str,
        language: str,
    ) -> Tuple[str, str, str, str, str, str, str]:
        facts_repr = str(sorted(case.facts.facts.items()))
        return (
            case.application_id,
            scheme_id,
            policy_version,
            rule_version,
            language,
            facts_repr,
            case.updated_at,
        )

    def generate_guidance(
        self,
        application_id: str,
        scheme_id: Optional[str] = None,
        language: str = "en",
        query_text: Optional[str] = None,
    ) -> ApplicationGuidancePackage:
        """
        Generates or retrieves cached guidance for an application.
        Invalidates automatically if application state, facts, or policy version change.
        """
        case = self.workflow_service.get_application_state(application_id)

        target_scheme = scheme_id or case.selected_scheme_id
        if not target_scheme and case.candidate_schemes:
            target_scheme = next(iter(case.candidate_schemes.keys()))
        target_scheme = target_scheme or "unknown_scheme"

        # Check for active DecisionSnapshot
        snapshot = None
        if case.active_decision_snapshot_id:
            snapshot = self.repository.get_decision_snapshot(case.active_decision_snapshot_id)

        policy_version = (snapshot.policy_snapshot_version if snapshot else self.workflow_service.get_active_policy_version())
        eval_obj = case.candidate_schemes.get(target_scheme)
        rule_version = (snapshot.rule_version if snapshot else (eval_obj.rule_version if eval_obj else "1.0.0"))

        cache_key = self._compute_cache_key(
            case=case,
            scheme_id=target_scheme,
            policy_version=policy_version,
            rule_version=rule_version,
            language=language,
        )

        if cache_key in self._cache:
            logger.info("Serving guidance package for application '%s' from cache", application_id)
            return self._cache[cache_key]

        package = self.generator.generate(
            case=case,
            target_scheme_id=target_scheme,
            snapshot=snapshot,
            language=language,
            query_text=query_text,
        )

        self._cache[cache_key] = package
        return package

    def get_guidance(
        self,
        application_id: str,
        scheme_id: Optional[str] = None,
        language: str = "en",
    ) -> ApplicationGuidancePackage:
        """Convenience method returning guidance for an application."""
        return self.generate_guidance(
            application_id=application_id,
            scheme_id=scheme_id,
            language=language,
        )

    def invalidate_cache(self, application_id: Optional[str] = None) -> None:
        """Invalidates cache entries for an application or completely."""
        if application_id:
            keys_to_del = [k for k in self._cache.keys() if k[0] == application_id]
            for k in keys_to_del:
                del self._cache[k]
        else:
            self._cache.clear()

    @staticmethod
    def export_guidance_markdown(package: ApplicationGuidancePackage) -> str:
        """
        Renders a clean, structured Markdown representation of the guidance package.
        """
        lines = [
            f"# Application Guidance: {package.scheme_name}",
            f"**Application ID:** `{package.application_id}`  ",
            f"**Statutory Decision:** `{package.statutory_decision}` | **Readiness:** `{package.readiness_status}`  ",
            f"**Policy Version:** `{package.policy_snapshot_version}` | **Language:** `{package.language}`\n",
            "---",
            "## 1. Eligibility Assessment",
            package.eligibility.summary,
            "",
        ]

        if package.eligibility.criteria:
            lines.append("### Evaluated Statutory Criteria")
            for c in package.eligibility.criteria:
                mark = "[x]" if c.get("satisfied") else "[ ]"
                crit = c.get("criterion", "")
                reason = c.get("reason", "")
                lines.append(f"- {mark} **{crit}**: {reason}")
            lines.append("")

        if package.benefit.amount is not None:
            lines.extend([
                "## 2. Estimated Statutory Benefit",
                f"- **Amount:** ₹{package.benefit.amount:,.0f}",
                f"- **Frequency:** {package.benefit.frequency or 'Standard'}",
                f"- **Disbursement:** {package.benefit.disbursement_structure}",
                f"- **Explanation:** {package.benefit.explanation}",
                "",
            ])

        lines.extend([
            "## 3. Required Documents & Preparation",
        ])
        doc_items = package.documents.get("items", [])
        if doc_items:
            for d in doc_items:
                st = d.get("status", "UNKNOWN")
                mark = "[x]" if st == "AVAILABLE" else "[ ]"
                d_name = d.get("display_name", d.get("document_type"))
                auth = d.get("issuing_authority", "Not specified")
                notes = d.get("preparation_notes", "")
                lines.append(f"- {mark} **{d_name}** ({st})")
                lines.append(f"  - *Issuing Authority:* {auth}")
                if notes:
                    lines.append(f"  - *Guidance:* {notes}")
        else:
            lines.append("- No mandatory document requirements recorded.")
        lines.append("")

        lines.extend([
            "## 4. Step-by-Step Application Procedure",
        ])
        steps = package.application.get("steps", [])
        for s in steps:
            s_num = s.get("step_number")
            instr = s.get("instruction")
            stype = s.get("source_type")
            notes = s.get("notes", "")
            lines.append(f"{s_num}. **{instr}** `[{stype}]`")
            if notes:
                lines.append(f"   - *Note:* {notes}")
        lines.append("")

        if package.application.get("official_portal_url"):
            lines.extend([
                "## 5. Verified Official Portal",
                f"Official Government Link: [{package.application.get('official_portal_url')}]({package.application.get('official_portal_url')})",
                "",
            ])

        if package.warnings:
            lines.append("## 6. Important Warnings & Notices")
            for w in package.warnings:
                lines.append(f"- **[{w.severity.value}] {w.code.value}:** {w.message}")
            lines.append("")

        return "\n".join(lines)
