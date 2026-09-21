"""
PolicySetu Conflict Detection and Resolution Engine.
Compares overlapping scheme records across disparate sources.
Generates explicit ConflictRecords and forbids silent merging of contradictions.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import sys
from pathlib import Path

_CUR = Path(__file__).resolve()
while _CUR.name != "AI" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_AI_DIR = _CUR
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

try:
    from .models import ConflictRecord, ConflictResolution, AuthorityTier
except (ImportError, ValueError):
    from src.data_pipeline.models import ConflictRecord, ConflictResolution, AuthorityTier


class ConflictDetector:
    """
    Detects and audits contradictions between primary and supplementary sources.
    Enforces authority hierarchy without silent value overrides.
    """

    COMPARISON_FIELDS = [
        "annual_family_income",
        "income_limit",
        "min_age",
        "max_age",
        "age",
        "level",
        "state",
        "beneficiary_type",
        "benefit_type",
        "dbt_scheme",
    ]

    @classmethod
    def compare_records(
        cls,
        record_a: Dict[str, Any],
        record_b: Dict[str, Any],
        source_a: str,
        source_b: str,
        tier_a: AuthorityTier,
        tier_b: AuthorityTier,
        scheme_slug: str
    ) -> List[ConflictRecord]:
        """
        Compares two records for the same scheme slug and emits ConflictRecords for discrepancies.
        """
        conflicts: List[ConflictRecord] = []
        now = datetime.now(timezone.utc).isoformat()

        for field in cls.COMPARISON_FIELDS:
            val_a = record_a.get(field)
            val_b = record_b.get(field)

            # Both sources must provide a non-null value to constitute an explicit contradiction
            if val_a is not None and val_b is not None and val_a != val_b:
                # Determine resolution based on explicit authority precedence
                if tier_a.priority > tier_b.priority:
                    status = ConflictResolution.PRIMARY_CONFIRMED
                    resolved = val_a
                    note = f"Resolved to {source_a} ({tier_a.value}) over {source_b} ({tier_b.value})"
                elif tier_b.priority > tier_a.priority:
                    status = ConflictResolution.PRIMARY_CONFIRMED
                    resolved = val_b
                    note = f"Resolved to {source_b} ({tier_b.value}) over {source_a} ({tier_a.value})"
                else:
                    status = ConflictResolution.MANUAL_REVIEW
                    resolved = None
                    note = f"Equal authority tier ({tier_a.value}); requires administrative review"

                conflicts.append(
                    ConflictRecord(
                        scheme_slug=scheme_slug,
                        field_name=field,
                        source_a=source_a,
                        value_a=val_a,
                        tier_a=tier_a,
                        source_b=source_b,
                        value_b=val_b,
                        tier_b=tier_b,
                        detected_at=now,
                        resolution_status=status,
                        resolved_value=resolved,
                        notes=note,
                    )
                )

        return conflicts

    @classmethod
    def batch_detect_conflicts(
        cls,
        primary_records: List[Dict[str, Any]],
        supplementary_records: List[Dict[str, Any]],
        primary_source_id: str,
        supplementary_source_id: str,
        primary_tier: AuthorityTier = AuthorityTier.PRIMARY_CANONICALIZED,
        supplementary_tier: AuthorityTier = AuthorityTier.SUPPLEMENTARY,
    ) -> List[ConflictRecord]:
        """
        Scans entire datasets for overlapping slug contradictions.
        """
        primary_map = {
            str(r.get("slug", "")).strip().lower(): r
            for r in primary_records if r.get("slug")
        }
        all_conflicts: List[ConflictRecord] = []

        for supp_rec in supplementary_records:
            slug = str(supp_rec.get("slug", "")).strip().lower()
            if slug and slug in primary_map:
                pri_rec = primary_map[slug]
                conflicts = cls.compare_records(
                    record_a=pri_rec,
                    record_b=supp_rec,
                    source_a=primary_source_id,
                    source_b=supplementary_source_id,
                    tier_a=primary_tier,
                    tier_b=supplementary_tier,
                    scheme_slug=slug,
                )
                all_conflicts.extend(conflicts)

        return all_conflicts