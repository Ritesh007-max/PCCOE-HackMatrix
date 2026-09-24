"""
FIN Policy Synchronization Orchestrator and Live Update Engine.
Phase 12: Central controller coordinating source fetching, validation, diff classification,
rule impact analysis, candidate staging, 14 activation gates, atomic promotion, and rollback.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import sys
_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.data_pipeline.models import (
    AuthorityTier,
    ChangeImpactType,
    ConflictRecord,
    FreshnessStatus,
    RecordDiff,
    SourceDefinition,
    SourceType,
    SyncJob,
    SyncRunMetadata,
    SyncStatus,
)
from src.data_pipeline.sources.registry import SourceRegistry, DEFAULT_SOURCE_REGISTRY
from src.data_pipeline.fetchers.local import BaselineSourceAdapter
from src.data_pipeline.sources.huggingface import HuggingFacePipeline, APPROVED_HF_DATASETS
from src.data_pipeline.change_detection import ChangeDetector
from src.data_pipeline.conflict import ConflictDetector
from src.data_pipeline.impact import PolicyChangeClassifier, RuleImpactAnalyzer
from src.data_pipeline.gates import ActivationGateEvaluator, GateEvaluationReport
from src.data_pipeline.snapshot import SnapshotManager
from src.data_pipeline.staging import CandidateSnapshotStager
from src.data_pipeline.incremental_rag import IncrementalRAGUpdater
from src.data_pipeline.lineage.tracker import LineageTracker

logger = logging.getLogger("fin.data_pipeline.orchestrator")


class PolicySyncOrchestrator:
    """
    Production-oriented policy update orchestrator with fail-closed semantics,
    dry-run execution, bounded retries, source failure isolation, and atomic rollback.
    """

    def __init__(
        self,
        registry: Optional[SourceRegistry] = None,
        snapshot_manager: Optional[SnapshotManager] = None,
        stager: Optional[CandidateSnapshotStager] = None,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ):
        self.registry = registry or DEFAULT_SOURCE_REGISTRY
        self.snapshot_manager = snapshot_manager or SnapshotManager()
        self.stager = stager or CandidateSnapshotStager(snapshot_manager=self.snapshot_manager)
        self.baseline_adapter = BaselineSourceAdapter()
        self.hf_pipeline = HuggingFacePipeline()
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        self.audit_log_path = self.snapshot_manager.snapshots_root / "sync_audit_log.jsonl"
        self._sync_jobs: Dict[str, SyncJob] = {}

    def get_active_policy_version(self) -> Optional[str]:
        """Returns the identifier of the currently active policy snapshot."""
        return self.snapshot_manager.get_active_snapshot_id()

    def get_sync_status(self, sync_id: str) -> Optional[SyncJob]:
        """Retrieves in-memory or persisted sync job status."""
        return self._sync_jobs.get(sync_id)

    def get_last_sync(self) -> Optional[SyncJob]:
        """Returns the most recent synchronization job metadata."""
        if self._sync_jobs:
            return list(self._sync_jobs.values())[-1]
        # Check audit log if available
        if self.audit_log_path.exists():
            try:
                lines = self.audit_log_path.read_text(encoding="utf-8").strip().splitlines()
                if lines:
                    last_dict = json.loads(lines[-1])
                    return SyncJob(
                        sync_id=last_dict["sync_id"],
                        source_id=last_dict.get("source_id"),
                        started_at=last_dict["started_at"],
                        completed_at=last_dict.get("completed_at"),
                        status=SyncStatus(last_dict["status"]),
                        previous_version=last_dict.get("previous_version"),
                        candidate_version=last_dict.get("candidate_version"),
                        records_seen=last_dict.get("records_seen", 0),
                        records_added=last_dict.get("records_added", 0),
                        records_updated=last_dict.get("records_updated", 0),
                        records_removed=last_dict.get("records_removed", 0),
                        records_unchanged=last_dict.get("records_unchanged", 0),
                        activation_status=last_dict.get("activation_status", "UNKNOWN"),
                        error_summary=last_dict.get("error_summary"),
                    )
            except Exception as e:
                logger.warning("Could not read audit log: %s", e)
        return None

    def list_sources(self) -> List[SourceDefinition]:
        """Lists registered data sources sorted by authority tier."""
        return self.registry.sorted_by_precedence(enabled_only=False)

    def get_source_health(self) -> Dict[str, Any]:
        """Exposes operational health and freshness of all registered sources."""
        sources = self.registry.list_sources(enabled_only=False)
        health_map: Dict[str, Any] = {}
        for s in sources:
            health_map[s.source_id] = {
                "source_name": s.source_name,
                "tier": s.authority_tier.value,
                "enabled": s.enabled,
                "fetch_method": s.fetch_method,
                "last_successful_fetch": s.last_successful_fetch,
                "freshness_status": FreshnessStatus.FRESH.value if s.last_successful_fetch else FreshnessStatus.UNKNOWN.value,
            }
        return health_map

    def get_rollback_versions(self) -> List[str]:
        """Lists all historically available immutable snapshots eligible for rollback."""
        snapshots = []
        if self.snapshot_manager.snapshots_root.exists():
            for p in sorted(self.snapshot_manager.snapshots_root.iterdir()):
                if p.is_dir() and p.name.startswith("snapshot_") and (p / "metadata.json").exists():
                    snapshots.append(p.name)
        return snapshots

    def sync(
        self,
        dry_run: bool = False,
        source_id: Optional[str] = None,
        force_rebuild: bool = False,
        custom_records_override: Optional[List[Dict[str, Any]]] = None,
    ) -> SyncJob:
        """
        Executes policy synchronization workflow with bounded retry and source failure isolation.
        """
        start_time = datetime.now(timezone.utc)
        sync_id = f"sync_{start_time.strftime('%Y%m%d_%H%M%S')}"

        previous_version = self.get_active_policy_version()
        job = SyncJob(
            sync_id=sync_id,
            source_id=source_id,
            started_at=start_time.isoformat(),
            status=SyncStatus.DRY_RUN if dry_run else SyncStatus.RUNNING,
            previous_version=previous_version,
        )
        self._sync_jobs[sync_id] = job

        # 1. Load Baseline / Active Corpus
        old_records: List[Dict[str, Any]] = []
        if previous_version and not force_rebuild:
            active_jsonl = self.snapshot_manager.snapshots_root / previous_version / "canonical" / "schemes.jsonl"
            if active_jsonl.exists():
                try:
                    with open(active_jsonl, "r", encoding="utf-8") as f:
                        old_records = [json.loads(line) for line in f if line.strip()]
                except Exception as e:
                    logger.warning("Could not read active snapshot schemes: %s", e)

        if not old_records:
            if custom_records_override is not None:
                old_records = []
            else:
                old_records = self.baseline_adapter.load_baseline_schemes()

        # 2. Ingest Sources with Failure Isolation & Retry
        candidate_records: List[Dict[str, Any]] = []
        sources_to_sync = (
            [self.registry.get(source_id)] if source_id and self.registry.get(source_id)
            else self.registry.list_sources(enabled_only=True)
        )
        sources_to_sync = [s for s in sources_to_sync if s is not None]

        supplementary_records: List[Dict[str, Any]] = []

        if custom_records_override is not None:
            candidate_records = list(custom_records_override)
        else:
            # Baseline Primary
            candidate_records = self.baseline_adapter.load_baseline_schemes()

            # Attempt Supplementary Ingestions with Source Isolation
            for src in sources_to_sync:
                if src.source_id == "myscheme_csv_baseline":
                    continue

                success = False
                attempts = 0
                while attempts < self.max_retries and not success:
                    attempts += 1
                    try:
                        if src.source_type == SourceType.LOCAL_BASELINE or src.fetch_method == "local":
                            supp = self.baseline_adapter.load_supplementary_schemes()
                            supplementary_records.extend(supp)
                            success = True
                        elif src.source_type == SourceType.HUGGINGFACE_DATASET:
                            hf_report = self.hf_pipeline.ingest_dataset(repo_id=src.url or src.source_id)
                            if hf_report.success:
                                supplementary_records.extend(hf_report.normalized_records)
                                success = True
                            else:
                                job.warnings.append(f"HF source '{src.source_id}' warning: {hf_report.error}")
                        else:
                            success = True
                    except Exception as err:
                        logger.warning("Attempt %d failed for source '%s': %s", attempts, src.source_id, err)
                        if attempts < self.max_retries:
                            time.sleep(self.backoff_factor * (2 ** (attempts - 1)))
                        else:
                            job.warnings.append(f"Source '{src.source_id}' failed after {self.max_retries} attempts: {err}")

        # 3. Change Detection & Classification
        change_summary = ChangeDetector.diff_datasets(
            old_records=old_records,
            new_records=candidate_records,
            key_field="slug",
        )

        # Enhance diffs with multi-label semantic impact and rule impact
        for diff in change_summary.diffs:
            impacts = PolicyChangeClassifier.classify_diff(diff)
            diff.impact_flags = impacts
            diff.rule_recompile_required = RuleImpactAnalyzer.requires_rule_recompile(diff)

        # 4. Conflict Detection
        conflicts = ConflictDetector.batch_detect_conflicts(
            primary_records=candidate_records,
            supplementary_records=supplementary_records,
            primary_source_id="myscheme_csv_baseline",
            supplementary_source_id="supplementary_feed",
        )
        job.conflicts = [c.to_dict() for c in conflicts]

        # 5. Evaluate 14 Activation Gates
        gate_report = ActivationGateEvaluator.evaluate_gates(
            candidate_records=candidate_records,
            diffs=change_summary.diffs,
            conflicts=conflicts,
            sources=sources_to_sync,
            registry=self.registry,
            baseline_record_count=len(old_records),
        )
        job.validation_errors = gate_report.rejection_reasons
        job.warnings.extend(gate_report.warnings)

        job.records_seen = len(candidate_records)
        job.records_added = change_summary.added_count
        job.records_updated = change_summary.modified_count
        job.records_removed = change_summary.removed_count
        job.records_unchanged = change_summary.unchanged_count

        # 6. Candidate Staging
        candidate_version = f"snapshot_{start_time.strftime('%Y%m%d_%H%M%S_%f')}"
        job.candidate_version = candidate_version

        self.stager.stage_candidate(
            candidate_id=sync_id,
            sources=sources_to_sync,
            canonical_records=candidate_records,
            diffs=change_summary.diffs,
            conflicts=conflicts,
            gate_report=gate_report,
        )

        # 7. Promotion / Activation Handling
        if dry_run:
            job.status = SyncStatus.DRY_RUN
            job.activation_status = "BYPASSED_DRY_RUN"
            job.completed_at = datetime.now(timezone.utc).isoformat()
            self._persist_audit_log(job)
            return job

        if not gate_report.can_activate:
            job.status = SyncStatus.REJECTED
            job.activation_status = "REJECTED_BY_GATES"
            job.error_summary = f"Rejected: {gate_report.rejection_reasons[:3]}"
            job.completed_at = datetime.now(timezone.utc).isoformat()
            self._persist_audit_log(job)
            return job

        # Execute Atomic Promotion
        sync_run_meta = SyncRunMetadata(
            sync_run_id=sync_id,
            started_at=start_time.isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            status=SyncStatus.SUCCEEDED,
            sources_attempted=[s.source_id for s in sources_to_sync],
            sources_succeeded=[s.source_id for s in sources_to_sync],
            records_added=job.records_added,
            records_modified=job.records_updated,
            records_removed=job.records_removed,
            records_unchanged=job.records_unchanged,
            conflicts_detected=len(conflicts),
            validation_failures=len(gate_report.rejection_reasons),
            activated_version=candidate_version,
            dry_run=False,
            notes="Phase 12 live policy synchronization.",
        )

        promoted, error_msg = self.stager.promote_candidate(
            candidate_id=sync_id,
            target_snapshot_id=candidate_version,
            metadata=sync_run_meta,
            sources=sources_to_sync,
        )

        if promoted:
            job.status = SyncStatus.SUCCEEDED
            job.activation_status = "ACTIVATED"
        else:
            job.status = SyncStatus.FAILED
            job.activation_status = "PROMOTION_FAILED"
            job.error_summary = error_msg or "Atomic promotion failed; active version preserved."

        job.completed_at = datetime.now(timezone.utc).isoformat()
        self._persist_audit_log(job)
        return job

    def rollback(self, target_version: Optional[str] = None) -> Optional[str]:
        """
        Executes atomic rollback to the previous known good policy snapshot.
        Restores canonical schemes, rules, RAG state, and lineage.
        """
        rolled_back_id = self.snapshot_manager.rollback()
        if rolled_back_id:
            # Audit rollback
            audit_job = SyncJob(
                sync_id=f"rollback_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                started_at=datetime.now(timezone.utc).isoformat(),
                completed_at=datetime.now(timezone.utc).isoformat(),
                status=SyncStatus.ROLLED_BACK,
                candidate_version=rolled_back_id,
                activation_status=f"ROLLED_BACK_TO_{rolled_back_id}",
            )
            self._persist_audit_log(audit_job)
        return rolled_back_id

    def _persist_audit_log(self, job: SyncJob) -> None:
        """Appends sync execution entry to persistent audit log without logging PII or secrets."""
        try:
            self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(job.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error("Could not write to sync audit log: %s", e)
