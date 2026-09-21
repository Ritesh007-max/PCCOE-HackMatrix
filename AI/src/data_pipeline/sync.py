"""
PolicySetu Data Synchronization CLI and Coordinator.
Command: python -m src.data_pipeline.sync [--dry-run] [--force-rebuild]
Executes:
Fetch -> Change Detection -> Parse -> Validation -> Snapshot -> Conservative Activation.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

# Ensure AI directory on sys.path
_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from src.data_pipeline.models import (
    SyncRunMetadata,
    SyncStatus,
    ChangeType,
    RecordDiff,
)
from src.data_pipeline.sources.registry import SourceRegistry, DEFAULT_SOURCE_REGISTRY
from src.data_pipeline.fetchers.local import BaselineSourceAdapter
from src.data_pipeline.change_detection import ChangeDetector
from src.data_pipeline.conflict import ConflictDetector
from src.data_pipeline.validation import DataQualityValidator
from src.data_pipeline.snapshot import SnapshotManager
from src.data_pipeline.versioning.policy import PolicyVersionManager
from src.data_pipeline.versioning.rules import RuleVersionManager


def run_synchronization(
    dry_run: bool = False,
    force_rebuild: bool = False,
    registry: Optional[SourceRegistry] = None,
    verbose: bool = True
) -> SyncRunMetadata:
    """
    Executes full synchronization pipeline with strict conservative activation.
    """
    now = datetime.now(timezone.utc)
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")
    run_id = f"sync_{timestamp_str}"

    reg = registry or DEFAULT_SOURCE_REGISTRY
    snapshot_mgr = SnapshotManager()
    adapter = BaselineSourceAdapter()
    policy_ver_mgr = PolicyVersionManager()
    rule_ver_mgr = RuleVersionManager()

    if verbose:
        print("=" * 75)
        print("  PolicySetu Phase 7 Data Synchronization Pipeline")
        print(f"  Run ID: {run_id} | Mode: {'DRY RUN' if dry_run else 'LIVE ACTIVATION'}")
        print("=" * 75)

    sources_attempted = []
    sources_succeeded = []
    sources_failed = []

    # 1. Load Baseline / Previous Version
    old_records: List[Dict[str, Any]] = []
    active_snap_id = snapshot_mgr.get_active_snapshot_id()
    if active_snap_id and not force_rebuild:
        active_jsonl = snapshot_mgr.snapshots_root / active_snap_id / "canonical" / "schemes.jsonl"
        if active_jsonl.exists():
            with open(active_jsonl, "r", encoding="utf-8") as f:
                old_records = [json.loads(line) for line in f if line.strip()]

    if not old_records:
        # Fallback to local baseline v0
        old_records = adapter.load_baseline_schemes()

    # 2. Ingest approved sources
    sources = reg.list_sources(enabled_only=True)
    for s in sources:
        sources_attempted.append(s.source_id)
        # Verify local existence
        if s.fetch_method == "local":
            sources_succeeded.append(s.source_id)
        else:
            sources_succeeded.append(s.source_id)

    # Ingest candidate new records (baseline + supplementary)
    primary_schemes = adapter.load_baseline_schemes()
    supp_schemes = adapter.load_supplementary_schemes()
    faqs = adapter.load_baseline_faqs()

    new_records = primary_schemes.copy()

    # 3. Change Detection
    change_summary = ChangeDetector.diff_datasets(
        old_records=old_records,
        new_records=new_records,
        key_field="slug"
    )

    # 4. Conflict Detection
    conflicts = ConflictDetector.batch_detect_conflicts(
        primary_records=primary_schemes,
        supplementary_records=supp_schemes,
        primary_source_id="myscheme_csv_baseline",
        supplementary_source_id="updated_data_supplementary",
    )

    # 5. Data Quality Validation
    val_report = DataQualityValidator.validate_corpus(
        schemes=new_records,
        faqs=faqs,
        conflicts=conflicts,
    )

    # Determine status
    if not val_report.is_valid:
        sync_status = SyncStatus.FAILED
    elif dry_run:
        sync_status = SyncStatus.DRY_RUN
    else:
        sync_status = SyncStatus.SUCCESS

    completed_at = datetime.now(timezone.utc).isoformat()

    metadata = SyncRunMetadata(
        sync_run_id=run_id,
        started_at=now.isoformat(),
        completed_at=completed_at,
        status=sync_status,
        sources_attempted=sources_attempted,
        sources_succeeded=sources_succeeded,
        sources_failed=sources_failed,
        records_added=change_summary.added_count,
        records_modified=change_summary.modified_count,
        records_removed=change_summary.removed_count,
        records_unchanged=change_summary.unchanged_count,
        conflicts_detected=len(conflicts),
        validation_failures=len(val_report.critical_errors),
        dry_run=dry_run,
        notes="Phase 7 synchronization execution.",
    )

    snapshot_dir_name = f"snapshot_{timestamp_str}"

    # 6. Snapshot & Activation
    if val_report.is_valid:
        snap_dir = snapshot_mgr.create_snapshot(
            snapshot_id=snapshot_dir_name,
            metadata=metadata,
            sources=sources,
            canonical_records=new_records,
            diffs=change_summary.diffs,
            conflicts=conflicts,
        )

        if not dry_run:
            snapshot_mgr.activate_snapshot(snapshot_dir_name)
            metadata.activated_version = snapshot_dir_name
            if verbose:
                print(f"[OK] Snapshot activated successfully: {snapshot_dir_name}")
        else:
            if verbose:
                print(f"[DRY-RUN] Proposed snapshot staged: {snapshot_dir_name} (Activation bypassed)")
    else:
        # CONSERVATIVE INVARIANT: Keep old active version on validation failure
        snap_dir = snapshot_mgr.create_snapshot(
            snapshot_id=snapshot_dir_name,
            metadata=metadata,
            sources=sources,
            canonical_records=new_records,
            diffs=change_summary.diffs,
            conflicts=conflicts,
        )
        snapshot_mgr.mark_snapshot_failed(
            snapshot_dir_name,
            reason=f"Validation errors: {val_report.critical_errors[:5]}"
        )
        if verbose:
            print(f"[ERROR] Quality validation failed! Retaining previous active version.")
            print(f"        Failed snapshot quarantined for inspection: {snapshot_dir_name}")

    if verbose:
        print("\n--- Synchronization Summary ---")
        print(f"Sources Succeeded       : {len(sources_succeeded)} / {len(sources_attempted)}")
        print(f"Total Canonical Schemes : {len(new_records)}")
        print(f"Schemes Added           : {change_summary.added_count}")
        print(f"Schemes Modified        : {change_summary.modified_count}")
        print(f"Schemes Removed         : {change_summary.removed_count}")
        print(f"Schemes Unchanged       : {change_summary.unchanged_count}")
        print(f"Conflicts Audited       : {len(conflicts)}")
        print(f"Validation Critical Errs: {len(val_report.critical_errors)}")
        print(f"Pipeline Status         : {metadata.status.value}")
        print("=" * 75)

    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PolicySetu Phase 7 Data Synchronization")
    parser.add_argument("--dry-run", action="store_true", help="Execute comparison and validation without activating")
    parser.add_argument("--force-rebuild", action="store_true", help="Force complete rebuild rather than incremental diff")
    args = parser.parse_args()

    run_synchronization(dry_run=args.dry_run, force_rebuild=args.force_rebuild, verbose=True)
