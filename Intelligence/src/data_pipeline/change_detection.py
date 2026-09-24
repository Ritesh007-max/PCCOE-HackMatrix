"""
FIN Deterministic Change Detection and Diff Engine.
Detects UNCHANGED, ADDED, MODIFIED, and REMOVED schemes between synchronization snapshots.
Computes field-level threshold changes (e.g. income limit changes from 250000 to 300000)
and prevents silent replacement of statutory policy criteria.
"""

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Dict, List, Optional, Set, Tuple

import sys
from pathlib import Path

_CUR = Path(__file__).resolve()
while _CUR.name != "Intelligence" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_INTELLIGENCE_DIR = _CUR
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

try:
    from .models import ChangeType, FieldDiff, RecordDiff
except (ImportError, ValueError):
    from src.data_pipeline.models import ChangeType, FieldDiff, RecordDiff


@dataclass
class ChangeSummary:
    """Consolidated summary of changes across an entire dataset comparison."""
    total_old_records: int
    total_new_records: int
    added_count: int
    modified_count: int
    removed_count: int
    unchanged_count: int
    diffs: List[RecordDiff] = field(default_factory=list)
    has_eligibility_changes: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_old_records": self.total_old_records,
            "total_new_records": self.total_new_records,
            "added_count": self.added_count,
            "modified_count": self.modified_count,
            "removed_count": self.removed_count,
            "unchanged_count": self.unchanged_count,
            "has_eligibility_changes": self.has_eligibility_changes,
            "diffs_count": len(self.diffs),
        }


class ChangeDetector:
    """
    Compares two versions of a scheme dataset and produces field-level diffs.
    """

    STATUTORY_THRESHOLD_FIELDS = {
        "annual_family_income",
        "income_limit",
        "age",
        "min_age",
        "max_age",
        "landholding_hectares",
        "disability_percentage",
    }

    @classmethod
    def compute_record_hash(cls, record: Dict[str, Any]) -> str:
        """
        Computes deterministic SHA-256 hash over canonical fields,
        excluding volatile provenance timestamps.
        """
        # Copy and clean volatile keys, normalizing numpy arrays to lists
        stable_data = {
            k: (v.tolist() if hasattr(v, "tolist") else v)
            for k, v in record.items()
            if k not in ("retrieved_at", "created_at", "last_successful_fetch", "provenance")
        }
        raw_json = json.dumps(stable_data, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(raw_json.encode("utf-8")).hexdigest()

    @classmethod
    def diff_datasets(
        cls,
        old_records: List[Dict[str, Any]],
        new_records: List[Dict[str, Any]],
        key_field: str = "slug"
    ) -> ChangeSummary:
        """
        Performs full dataset diffing and returns structured ChangeSummary.
        """
        old_map: Dict[str, Dict[str, Any]] = {
            str(r.get(key_field, "")).strip().lower(): r for r in old_records if r.get(key_field)
        }
        new_map: Dict[str, Dict[str, Any]] = {
            str(r.get(key_field, "")).strip().lower(): r for r in new_records if r.get(key_field)
        }

        old_slugs: Set[str] = set(old_map.keys())
        new_slugs: Set[str] = set(new_map.keys())

        added_slugs = new_slugs - old_slugs
        removed_slugs = old_slugs - new_slugs
        common_slugs = old_slugs & new_slugs

        diffs: List[RecordDiff] = []
        unchanged_count = 0
        has_any_eligibility_change = False

        # 1. Added records
        for slug in sorted(added_slugs):
            new_rec = new_map[slug]
            rec_hash = cls.compute_record_hash(new_rec)
            diff = RecordDiff(
                scheme_slug=slug,
                change_type=ChangeType.ADDED,
                new_hash=rec_hash,
                source_id=new_rec.get("source_dataset", ""),
            )
            diffs.append(diff)

        # 2. Removed records
        for slug in sorted(removed_slugs):
            old_rec = old_map[slug]
            rec_hash = cls.compute_record_hash(old_rec)
            diff = RecordDiff(
                scheme_slug=slug,
                change_type=ChangeType.REMOVED,
                old_hash=rec_hash,
                source_id=old_rec.get("source_dataset", ""),
            )
            diffs.append(diff)

        # 3. Common records -> check hash and field diffs
        for slug in sorted(common_slugs):
            old_rec = old_map[slug]
            new_rec = new_map[slug]

            old_hash = cls.compute_record_hash(old_rec)
            new_hash = cls.compute_record_hash(new_rec)

            if old_hash == new_hash:
                unchanged_count += 1
                continue

            # Compute field-level differences
            field_diffs = cls.compute_field_diffs(old_rec, new_rec)
            diff = RecordDiff(
                scheme_slug=slug,
                change_type=ChangeType.MODIFIED,
                field_diffs=field_diffs,
                old_hash=old_hash,
                new_hash=new_hash,
                source_id=new_rec.get("source_dataset", ""),
            )
            if diff.has_eligibility_change:
                has_any_eligibility_change = True
            diffs.append(diff)

        return ChangeSummary(
            total_old_records=len(old_records),
            total_new_records=len(new_records),
            added_count=len(added_slugs),
            modified_count=len(diffs) - len(added_slugs) - len(removed_slugs),
            removed_count=len(removed_slugs),
            unchanged_count=unchanged_count,
            diffs=diffs,
            has_eligibility_changes=has_any_eligibility_change,
        )

    @classmethod
    def compute_field_diffs(
        cls,
        old_rec: Dict[str, Any],
        new_rec: Dict[str, Any]
    ) -> List[FieldDiff]:
        """
        Computes atomic differences between two scheme records.
        Highlights threshold modifications.
        """
        field_diffs: List[FieldDiff] = []
        all_keys = set(old_rec.keys()) | set(new_rec.keys())

        # Keys to ignore during field-level comparison
        ignore_keys = {"retrieved_at", "created_at", "last_successful_fetch", "provenance"}

        for k in sorted(all_keys):
            if k in ignore_keys:
                continue

            old_val = old_rec.get(k)
            new_val = new_rec.get(k)

            # Check if values differ safely across scalar and array types
            old_has_tolist = getattr(old_val, "tolist", None)
            new_has_tolist = getattr(new_val, "tolist", None)
            if callable(old_has_tolist) or callable(new_has_tolist):
                l_old = old_has_tolist() if callable(old_has_tolist) else old_val
                l_new = new_has_tolist() if callable(new_has_tolist) else new_val
                is_diff = l_old != l_new
            else:
                try:
                    # Handle pandas NaN vs None / NaN
                    if old_val is None and new_val is None:
                        is_diff = False
                    elif (isinstance(old_val, float) and str(old_val) == "nan") and (isinstance(new_val, float) and str(new_val) == "nan"):
                        is_diff = False
                    else:
                        is_diff = bool(old_val != new_val)
                except Exception:
                    is_diff = str(old_val) != str(new_val)

            if is_diff:
                is_threshold = k.lower() in cls.STATUTORY_THRESHOLD_FIELDS
                desc = f"POLICY_FIELD_CHANGED: field={k}, old={old_val}, new={new_val}"

                field_diffs.append(
                    FieldDiff(
                        field_name=k,
                        old_value=old_val,
                        new_value=new_val,
                        is_threshold_changed=is_threshold,
                        description=desc,
                    )
                )

        return field_diffs