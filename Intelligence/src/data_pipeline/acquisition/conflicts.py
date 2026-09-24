"""
FIN Multi-Tier Conflict Detection & Resolution Engine.
Identifies discrepancies across official portals, statutory instruments, and myScheme.
Enforces deterministic resolution using authority tiers and effective-date logic.
Forbids silent overrides and flags ambiguous contradictions for administrative REVIEW.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from .models import Conflict, ConflictResolutionStatus, AuthorityTierName
from .authority import AuthorityHierarchy


class AcquisitionConflictResolver:
    """
    Deterministic conflict arbiter adhering strictly to statutory hierarchy:
    Tier 0 (Statutory) > Tier 1 (Ministry Portals) > Tier 2 (myScheme) > Tier 3 > Tier 4 > Tier 5.
    """

    COMPARISON_FIELDS = [
        "annual_family_income",
        "min_age",
        "max_age",
        "gender",
        "caste_category",
        "monetary_benefit",
        "application_mode",
        "central_or_state",
        "state_or_ut",
        "is_student",
        "is_bpl",
    ]

    @classmethod
    def detect_and_resolve_conflicts(
        cls,
        scheme_slug: str,
        record_a: Dict[str, Any],
        record_b: Dict[str, Any],
        source_a: str,
        source_b: str,
        authority_a: AuthorityTierName,
        authority_b: AuthorityTierName,
        effective_date_a: Optional[str] = None,
        effective_date_b: Optional[str] = None,
    ) -> List[Conflict]:
        """
        Compares two representations of a scheme and resolves or flags discrepancies.
        """
        conflicts: List[Conflict] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for field_name in cls.COMPARISON_FIELDS:
            val_a = record_a.get(field_name)
            val_b = record_b.get(field_name)

            if val_a is not None and val_b is not None and val_a != val_b:
                cid = f"conf_{scheme_slug}_{field_name}_{uuid.uuid4().hex[:6]}"
                conflicting_text = f"Source A ({source_a}): {val_a} vs Source B ({source_b}): {val_b}"

                # 1. Authority Precedence Check
                rank_diff = AuthorityHierarchy.compare_precedence(authority_a, authority_b)

                if rank_diff > 0:
                    # Source A strictly outranks Source B
                    status = ConflictResolutionStatus.RESOLVED
                    resolved_val = val_a
                    note = f"Deterministically resolved to {authority_a.value} ({source_a}) over lower tier {authority_b.value} ({source_b})"
                elif rank_diff < 0:
                    # Source B strictly outranks Source A
                    status = ConflictResolutionStatus.RESOLVED
                    resolved_val = val_b
                    note = f"Deterministically resolved to {authority_b.value} ({source_b}) over lower tier {authority_a.value} ({source_a})"
                else:
                    # Equal authority tier: check effective date / supersession
                    if effective_date_a and effective_date_b:
                        try:
                            dt_a = datetime.fromisoformat(effective_date_a.replace("Z", "+00:00"))
                            dt_b = datetime.fromisoformat(effective_date_b.replace("Z", "+00:00"))
                            if dt_a > dt_b:
                                status = ConflictResolutionStatus.RESOLVED
                                resolved_val = val_a
                                note = f"Resolved via newer effective date ({effective_date_a} > {effective_date_b}) within same tier"
                            elif dt_b > dt_a:
                                status = ConflictResolutionStatus.RESOLVED
                                resolved_val = val_b
                                note = f"Resolved via newer effective date ({effective_date_b} > {effective_date_a}) within same tier"
                            else:
                                status = ConflictResolutionStatus.REVIEW
                                resolved_val = None
                                note = "Identical authority tier and identical effective dates; flagged for administrative REVIEW"
                        except Exception:
                            status = ConflictResolutionStatus.REVIEW
                            resolved_val = None
                            note = "Unparseable effective dates within equal authority tier; flagged for administrative REVIEW"
                    else:
                        status = ConflictResolutionStatus.REVIEW
                        resolved_val = None
                        note = "Equal authority tier without verified chronological supersession; flagged for administrative REVIEW"

                conflicts.append(
                    Conflict(
                        conflict_id=cid,
                        scheme_slug=scheme_slug,
                        field_name=field_name,
                        source_a=source_a,
                        value_a=val_a,
                        authority_a=authority_a.value,
                        date_a=effective_date_a,
                        source_b=source_b,
                        value_b=val_b,
                        authority_b=authority_b.value,
                        date_b=effective_date_b,
                        conflicting_text=conflicting_text,
                        resolution_status=status,
                        resolved_value=resolved_val,
                        notes=note,
                        detected_at=now_iso,
                    )
                )

        return conflicts
