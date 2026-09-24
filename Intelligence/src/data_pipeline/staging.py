"""
FIN Candidate Snapshot Staging and Atomic Promotion Engine.
Phase 12: Manages candidate snapshots, pre-activation staging, atomic active version switching,
and automatic post-activation verification rollback.
"""

from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional, Set, Tuple

import sys
_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.data_pipeline.models import (
    ConflictRecord,
    RecordDiff,
    SourceDefinition,
    SyncRunMetadata,
    SyncStatus,
)
from src.data_pipeline.gates import GateEvaluationReport
from src.data_pipeline.snapshot import SnapshotManager

logger = logging.getLogger("fin.data_pipeline.staging")


class CandidateSnapshotStager:
    """
    Coordinates safe pre-activation staging of candidate policy datasets.
    Guarantees that active policy state is never modified until all activation gates pass.
    """

    def __init__(
        self,
        snapshots_root: Optional[Path] = None,
        snapshot_manager: Optional[SnapshotManager] = None,
    ):
        self.snapshots_root = snapshots_root or _INTELLIGENCE_DIR / "data" / "snapshots"
        self.snapshots_root.mkdir(parents=True, exist_ok=True)
        self.snapshot_manager = snapshot_manager or SnapshotManager(snapshots_root=self.snapshots_root)

    def stage_candidate(
        self,
        candidate_id: str,
        sources: List[SourceDefinition],
        canonical_records: List[Dict[str, Any]],
        diffs: List[RecordDiff],
        conflicts: List[ConflictRecord],
        gate_report: GateEvaluationReport,
        rule_files: Optional[Dict[str, Dict[str, Any]]] = None,
        rag_chunks_meta: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Stages candidate files into a dedicated staging directory.
        active_version.json is NOT modified during staging.
        """
        cand_dir = self.snapshots_root / f"candidate_{candidate_id}"
        cand_dir.mkdir(parents=True, exist_ok=True)

        canonical_dir = cand_dir / "canonical"
        rules_dir = cand_dir / "rules"
        rag_dir = cand_dir / "rag"

        canonical_dir.mkdir(exist_ok=True)
        rules_dir.mkdir(exist_ok=True)
        rag_dir.mkdir(exist_ok=True)

        # 1. candidate_meta.json
        meta = {
            "candidate_id": candidate_id,
            "staged_at": datetime.now(timezone.utc).isoformat(),
            "status": "STAGED",
            "total_records": len(canonical_records),
            "diffs_count": len(diffs),
            "conflicts_count": len(conflicts),
            "can_activate": gate_report.can_activate,
            "gates_passed": gate_report.gates_passed,
            "gates_failed": gate_report.gates_failed,
        }
        with open(cand_dir / "candidate_meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        # 2. gate_report.json
        with open(cand_dir / "gate_report.json", "w", encoding="utf-8") as f:
            json.dump(gate_report.to_dict(), f, indent=2, ensure_ascii=False)

        # 3. changes.json
        with open(cand_dir / "changes.json", "w", encoding="utf-8") as f:
            changes_data = [
                {
                    "scheme_slug": d.scheme_slug,
                    "change_type": d.change_type.value,
                    "impact_flags": [flg.value for flg in d.impact_flags],
                    "rule_recompile_required": d.rule_recompile_required,
                    "field_diffs": [
                        {
                            "field": fd.field_name,
                            "old": fd.old_value,
                            "new": fd.new_value,
                            "is_threshold": fd.is_threshold_changed,
                        }
                        for fd in d.field_diffs
                    ],
                }
                for d in diffs
            ]
            json.dump(changes_data, f, indent=2, ensure_ascii=False)

        # 4. conflicts.json
        with open(cand_dir / "conflicts.json", "w", encoding="utf-8") as f:
            json.dump([c.to_dict() for c in conflicts], f, indent=2, ensure_ascii=False)

        # 5. canonical/schemes.jsonl
        schemes_jsonl = canonical_dir / "schemes.jsonl"
        with open(schemes_jsonl, "w", encoding="utf-8") as f:
            for rec in canonical_records:
                f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")

        # 6. rules/
        if rule_files:
            for rname, rcontent in rule_files.items():
                with open(rules_dir / f"{rname}.json", "w", encoding="utf-8") as f:
                    json.dump(rcontent, f, indent=2, ensure_ascii=False)

        # 7. rag/
        if rag_chunks_meta:
            with open(rag_dir / "rag_meta.json", "w", encoding="utf-8") as f:
                json.dump(rag_chunks_meta, f, indent=2, ensure_ascii=False)

        return cand_dir

    def promote_candidate(
        self,
        candidate_id: str,
        target_snapshot_id: str,
        metadata: SyncRunMetadata,
        sources: List[SourceDefinition],
    ) -> Tuple[bool, Optional[str]]:
        """
        Atomically promotes a verified candidate into an active snapshot.
        Enforces post-activation verification and immediate rollback on failure.
        """
        cand_dir = self.snapshots_root / f"candidate_{candidate_id}"
        if not cand_dir.exists():
            return False, f"Candidate directory '{cand_dir}' does not exist."

        target_snap_dir = self.snapshots_root / target_snapshot_id
        target_snap_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Copy all staged artifacts to final snapshot folder
            for item in cand_dir.iterdir():
                dest = target_snap_dir / item.name
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

            # Write standard metadata and source manifest
            with open(target_snap_dir / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)

            with open(target_snap_dir / "source_manifest.json", "w", encoding="utf-8") as f:
                json.dump([s.to_dict() for s in sources], f, indent=2, ensure_ascii=False)

            # Atomic activation pointer switch
            self.snapshot_manager.activate_snapshot(target_snapshot_id)

            # Post-Activation Verification Gate
            post_active_id = self.snapshot_manager.get_active_snapshot_id()
            if post_active_id != target_snapshot_id:
                logger.critical("Post-activation verification failed! Active ID '%s' != target '%s'. Rolling back.", post_active_id, target_snapshot_id)
                self.snapshot_manager.rollback()
                return False, "Post-activation pointer verification mismatch; rolled back immediately."

            # Verify presence of canonical dataset
            active_jsonl = target_snap_dir / "canonical" / "schemes.jsonl"
            if not active_jsonl.exists() or active_jsonl.stat().st_size == 0:
                logger.critical("Post-activation canonical dataset check failed! Rolling back.")
                self.snapshot_manager.rollback()
                return False, "Post-activation schemes.jsonl missing or empty; rolled back immediately."

            return True, None

        except Exception as e:
            logger.error("Error during candidate promotion: %s. Initiating recovery rollback.", e)
            try:
                self.snapshot_manager.rollback()
            except Exception:
                pass
            return False, str(e)
