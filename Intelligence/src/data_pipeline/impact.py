"""
FIN Deterministic Change Impact and Rule Impact Detection Engine.
Phase 12: Classifies detected differences across 15 semantic categories and
determines whether statutory rule recompilation is required.
"""

from typing import Any, Dict, List, Optional, Set
import sys
from pathlib import Path

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.data_pipeline.models import (
    ChangeImpactType,
    ChangeType,
    FieldDiff,
    RecordDiff,
)


class RuleImpactAnalyzer:
    """
    Analyzes whether changed scheme attributes affect deterministic statutory rules.
    Statutory constraints: age, income, state/domicile, category, disability, land, etc.
    """

    STATUTORY_RULE_FIELDS: Set[str] = {
        "eligibility",
        "eligibility_criteria",
        "annual_family_income",
        "income_limit",
        "age",
        "min_age",
        "max_age",
        "state",
        "level",
        "social_category",
        "caste",
        "gender",
        "disability_percentage",
        "is_disabled",
        "landholding_hectares",
        "land_size",
        "is_student",
        "is_bpl",
        "is_taxpayer",
        "occupation",
        "residency_duration_years",
        "exclusions",
    }

    @classmethod
    def is_rule_affecting_field(cls, field_name: str) -> bool:
        """Determines if a specific field touches deterministic applicant facts or rule constraints."""
        clean = field_name.strip().lower()
        if clean in cls.STATUTORY_RULE_FIELDS:
            return True
        # Check subfield patterns
        statutory_tokens = {"income", "age", "caste", "category", "disab", "land", "student", "bpl", "tax"}
        return any(tok in clean for tok in statutory_tokens)

    @classmethod
    def requires_rule_recompile(cls, diff: RecordDiff) -> bool:
        """
        Determines if a changed record requires rule recompilation.
        Added, removed, or modified statutory criteria trigger recompilation.
        """
        if diff.change_type in (ChangeType.ADDED, ChangeType.REMOVED):
            return True

        if diff.change_type == ChangeType.MODIFIED:
            for fd in diff.field_diffs:
                if cls.is_rule_affecting_field(fd.field_name):
                    return True
        return False


class PolicyChangeClassifier:
    """
    Classifies atomic and record-level changes into 15 distinct semantic ChangeImpactTypes.
    """

    @classmethod
    def classify_diff(cls, diff: RecordDiff, is_supplementary_source: bool = False) -> List[ChangeImpactType]:
        """
        Emits all applicable ChangeImpactTypes for a scheme difference.
        """
        impacts: List[ChangeImpactType] = []

        if diff.change_type == ChangeType.UNCHANGED:
            impacts.append(ChangeImpactType.NO_CHANGE)
            return impacts

        if diff.change_type == ChangeType.ADDED:
            impacts.append(ChangeImpactType.SCHEME_ADDED)
            if RuleImpactAnalyzer.requires_rule_recompile(diff):
                impacts.append(ChangeImpactType.RULE_AFFECTING_CHANGE)
            if is_supplementary_source:
                impacts.append(ChangeImpactType.SUPPLEMENTARY_ONLY_CHANGE)
            return impacts

        if diff.change_type == ChangeType.REMOVED:
            impacts.append(ChangeImpactType.SCHEME_REMOVED)
            impacts.append(ChangeImpactType.RULE_AFFECTING_CHANGE)
            return impacts

        # ChangeType.MODIFIED
        impacts.append(ChangeImpactType.SCHEME_UPDATED)

        for fd in diff.field_diffs:
            fname = fd.field_name.strip().lower()

            if RuleImpactAnalyzer.is_rule_affecting_field(fname):
                if ChangeImpactType.ELIGIBILITY_CHANGED not in impacts:
                    impacts.append(ChangeImpactType.ELIGIBILITY_CHANGED)
                if ChangeImpactType.RULE_AFFECTING_CHANGE not in impacts:
                    impacts.append(ChangeImpactType.RULE_AFFECTING_CHANGE)

            if any(b in fname for b in ("benefit", "amount", "financial", "subsidy", "allowance")):
                if ChangeImpactType.BENEFIT_CHANGED not in impacts:
                    impacts.append(ChangeImpactType.BENEFIT_CHANGED)

            if any(d in fname for d in ("document", "certificate", "proof", "enclosure")):
                if ChangeImpactType.DOCUMENT_REQUIREMENT_CHANGED not in impacts:
                    impacts.append(ChangeImpactType.DOCUMENT_REQUIREMENT_CHANGED)

            if any(s in fname for s in ("process", "step", "how_to_apply", "procedure")):
                if ChangeImpactType.APPLICATION_STEP_CHANGED not in impacts:
                    impacts.append(ChangeImpactType.APPLICATION_STEP_CHANGED)

            if any(dl in fname for dl in ("deadline", "open_date", "close_date", "last_date")):
                if ChangeImpactType.DEADLINE_CHANGED not in impacts:
                    impacts.append(ChangeImpactType.DEADLINE_CHANGED)

            if any(u in fname for u in ("source_url", "official_website", "portal", "link")):
                if ChangeImpactType.SOURCE_URL_CHANGED not in impacts:
                    impacts.append(ChangeImpactType.SOURCE_URL_CHANGED)

            if fname in ("faq", "faqs", "question", "answer"):
                if ChangeImpactType.FAQ_CHANGED not in impacts:
                    impacts.append(ChangeImpactType.FAQ_CHANGED)

        if is_supplementary_source:
            impacts.append(ChangeImpactType.SUPPLEMENTARY_ONLY_CHANGE)

        # If no specific semantic impact was matched beyond SCHEME_UPDATED, classify as METADATA_CHANGED
        if len(impacts) == 1 and impacts[0] == ChangeImpactType.SCHEME_UPDATED:
            impacts.append(ChangeImpactType.METADATA_CHANGED)

        return impacts
