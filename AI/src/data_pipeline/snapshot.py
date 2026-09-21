"""
PolicySetu Snapshot and Rollback Management System.
Creates immutable synchronization snapshots under AI/data/snapshots/snapshot_YYYYMMDD_HHMMSS/.
Enforces conservative activation: failed validations never replace the active version.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
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
    from .models import SyncRunMetadata, RecordDiff, ConflictRecord, SourceDefinition
except (ImportError, ValueError):
    from src.data_pipeline.models import (
        SyncRunMetadata,
        RecordDiff,
        ConflictRecord,
        SourceDefinition,
    )


class SnapshotManager:
    """
    Manages immutable synchronization snapshots and atomic active version switching.
    """

    def __init__(self, snapshots_root: Optional[Path] = None):
        self.snapshots_root = snapshots_root or Path(__file__).resolve().parents[2] / "data" / "snapshots"
        self.snapshots_root.mkdir(parents=True, exist_ok=True)
        self.active_pointer_file = self.snapshots_root / "active_version.json"

    def create_snapshot(
        self,
        snapshot_id: str,
        metadata: SyncRunMetadata,
        sources: List[SourceDefinition],
        canonical_records: List[Dict[str, Any]],
        diffs: List[RecordDiff],
        conflicts: List[ConflictRecord],
        rule_files: Optional[Dict[str, Dict[str, Any]]] = None,
        rag_chunks_meta: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Persists an immutable snapshot directory with all audited artifacts.
        """
        snap_dir = self.snapshots_root / snapshot_id
        snap_dir.mkdir(parents=True, exist_ok=True)

        # Subdirectories
        canonical_dir = snap_dir / "canonical"
        rules_dir = snap_dir / "rules"
        rag_dir = snap_dir / "rag"

        canonical_dir.mkdir(exist_ok=True)
        rules_dir.mkdir(exist_ok=True)
        rag_dir.mkdir(exist_ok=True)

        # 1. metadata.json
        meta_path = snap_dir / "metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)

        # 2. source_manifest.json
        manifest_path = snap_dir / "source_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump([s.to_dict() for s in sources], f, indent=2, ensure_ascii=False)

        # 3. changes.json
        changes_path = snap_dir / "changes.json"
        with open(changes_path, "w", encoding="utf-8") as f:
            diff_dicts = [
                {
                    "scheme_slug": d.scheme_slug,
                    "change_type": d.change_type.value,
                    "field_diffs": [
                        {
                            "field": fd.field_name,
                            "old": fd.old_value,
                            "new": fd.new_value,
                            "is_threshold": fd.is_threshold_changed,
                            "desc": fd.description,
                        }
                        for fd in d.field_diffs
                    ],
                }
                for d in diffs
            ]
            json.dump(diff_dicts, f, indent=2, ensure_ascii=False)

        # 4. conflicts.json
        conflicts_path = snap_dir / "conflicts.json"
        with open(conflicts_path, "w", encoding="utf-8") as f:
            json.dump([c.to_dict() for c in conflicts], f, indent=2, ensure_ascii=False)

        # 5. canonical/schemes.jsonl
        schemes_jsonl = canonical_dir / "schemes.jsonl"
        with open(schemes_jsonl, "w", encoding="utf-8") as f:
            for rec in canonical_records:
                f.write(
                    json.dumps(
                        rec,
                        ensure_ascii=False,
                        default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o),
                    )
                    + "\n"
                )

        # 6. rules/
        if rule_files:
            for rname, rcontent in rule_files.items():
                rpath = rules_dir / f"{rname}.json"
                with open(rpath, "w", encoding="utf-8") as f:
                    json.dump(rcontent, f, indent=2, ensure_ascii=False)

        # 7. rag/
        if rag_chunks_meta:
            with open(rag_dir / "rag_meta.json", "w", encoding="utf-8") as f:
                json.dump(rag_chunks_meta, f, indent=2, ensure_ascii=False)

        return snap_dir

    def activate_snapshot(self, snapshot_id: str) -> None:
        """
        Atomically switches active version pointer to the newly validated snapshot.
        """
        snap_dir = self.snapshots_root / snapshot_id
        if not snap_dir.exists():
            raise FileNotFoundError(f"Snapshot directory does not exist: {snap_dir}")

        current_active = self.get_active_snapshot_id()

        pointer_data = {
            "active_snapshot": snapshot_id,
            "previous_snapshot": current_active,
            "activated_at": datetime.now(timezone.utc).isoformat(),
            "status": "ACTIVE",
        }

        temp_pointer = self.snapshots_root / "active_version.json.tmp"
        with open(temp_pointer, "w", encoding="utf-8") as f:
            json.dump(pointer_data, f, indent=2)

        # Atomic replacement
        shutil.move(str(temp_pointer), str(self.active_pointer_file))

    def mark_snapshot_failed(self, snapshot_id: str, reason: str) -> None:
        """
        Quarantines a snapshot without deleting it, preserving it for post-mortem debugging.
        """
        snap_dir = self.snapshots_root / snapshot_id
        if not snap_dir.exists():
            return

        meta_path = snap_dir / "metadata.json"
        meta_dict = {}
        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta_dict = json.load(f)
            except Exception:
                pass

        meta_dict["status"] = "FAILED_VALIDATION"
        meta_dict["failure_reason"] = reason
        meta_dict["failed_at"] = datetime.now(timezone.utc).isoformat()

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_dict, f, indent=2, ensure_ascii=False)

    def get_active_snapshot_id(self) -> Optional[str]:
        """Returns the ID of the currently active snapshot."""
        if not self.active_pointer_file.exists():
            return None
        try:
            with open(self.active_pointer_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("active_snapshot")
        except Exception:
            return None

    def rollback(self) -> Optional[str]:
        """
        Rolls back the active version pointer to the previous known good snapshot.
        """
        if not self.active_pointer_file.exists():
            return None

        with open(self.active_pointer_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        prev_snap = data.get("previous_snapshot")
        if not prev_snap:
            return None

        prev_dir = self.snapshots_root / prev_snap
        if not prev_dir.exists():
            raise RuntimeError(f"Previous snapshot directory missing: {prev_dir}")

        current_active = data.get("active_snapshot")
        rollback_data = {
            "active_snapshot": prev_snap,
            "previous_snapshot": current_active,
            "rolled_back_at": datetime.now(timezone.utc).isoformat(),
            "status": "ROLLED_BACK",
            "rollback_from": current_active,
        }

        temp_pointer = self.snapshots_root / "active_version.json.tmp"
        with open(temp_pointer, "w", encoding="utf-8") as f:
            json.dump(rollback_data, f, indent=2)

        shutil.move(str(temp_pointer), str(self.active_pointer_file))
        return prev_snap