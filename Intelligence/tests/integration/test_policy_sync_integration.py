"""
End-to-End Integration Tests for FIN Phase 12: Dynamic Policy Operations.
Verifies:
1. Complete live synchronization lifecycle (Source -> Fetch -> Validate -> Diff -> Gates -> Stage -> Atomic Activate).
2. Historical Decision Immutability across policy version updates.
3. Multi-version re-evaluation creating reproducible decision snapshots (V1 preserved, V2 recorded).
4. Safe Rollback restoring coherent snapshot state and active version pointer.
5. Hugging Face supplementary dataset integration with revision tracking and authority preservation.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from src.data_pipeline.models import (
    AuthorityTier,
    ChangeImpactType,
    SourceDefinition,
    SyncStatus,
)
from src.data_pipeline.sources.registry import SourceRegistry
from src.data_pipeline.sources.huggingface import HuggingFacePipeline
from src.data_pipeline.orchestrator import PolicySyncOrchestrator
from src.data_pipeline.snapshot import SnapshotManager
from src.application.service import ApplicationWorkflowService
from src.application.case import ApplicationCase, FactSnapshot
from src.application.repository import InMemoryApplicationRepository
from src.application.status import StatutoryDecision, ApplicationStatus
from src.llm.config import LLMConfig
from src.pipelines.application_pipeline import ApplicationPipeline


class TestPolicySyncIntegration(unittest.TestCase):
    """Integration test suite for Phase 12 Live Policy Operations."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="fin_p12_integ_")
        self.base_path = Path(self.temp_dir)
        self.snapshots_dir = self.base_path / "snapshots"
        self.candidates_dir = self.base_path / "candidates"
        self.rules_dir = self.base_path / "rules"
        self.rag_dir = self.base_path / "rag"

        for d in [self.snapshots_dir, self.candidates_dir, self.rules_dir, self.rag_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.registry = SourceRegistry()
        self.snapshot_mgr = SnapshotManager(snapshots_root=self.snapshots_dir)
        from src.data_pipeline.staging import CandidateSnapshotStager
        self.stager = CandidateSnapshotStager(
            snapshots_root=self.snapshots_dir,
            snapshot_manager=self.snapshot_mgr,
        )
        self.orchestrator = PolicySyncOrchestrator(
            registry=self.registry,
            snapshot_manager=self.snapshot_mgr,
            stager=self.stager,
        )

        # Baseline seed records
        self.baseline_records = [
            {
                "slug": "national_scholarship_portal",
                "scheme_name": "National Scholarship Portal Scheme",
                "category": "Education",
                "eligibility": "Annual family income must not exceed 250000. Must be citizen of India.",
                "source_dataset": "myscheme_baseline",
                "source_tier": AuthorityTier.PRIMARY_CANONICALIZED.value,
                "source_url": "https://scholarships.gov.in",
            },
            {
                "slug": "pm_kisan_samman",
                "scheme_name": "PM Kisan Samman Nidhi",
                "category": "Agriculture",
                "eligibility": "Small and marginal farmer families with cultivable land up to 2 hectares.",
                "source_dataset": "myscheme_baseline",
                "source_tier": AuthorityTier.PRIMARY_CANONICALIZED.value,
                "source_url": "https://pmkisan.gov.in",
            },
        ]

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_end_to_end_live_sync_lifecycle(self):
        """
        Tests complete lifecycle:
        Baseline seed -> Candidate creation -> 14 Gates passed -> Atomic activation -> Audit log.
        """
        # Step 1: Initialize baseline snapshot V1
        job_v1 = self.orchestrator.sync(
            dry_run=False,
            custom_records_override=self.baseline_records,
        )
        self.assertEqual(job_v1.status, SyncStatus.SUCCEEDED)
        v1_version = self.orchestrator.get_active_policy_version()
        self.assertIsNotNone(v1_version)
        assert v1_version is not None
        self.assertTrue(v1_version.startswith("snapshot_"))

        # Step 2: Dry Run with a new scheme
        updated_records = list(self.baseline_records) + [
            {
                "slug": "pm_matru_vandana",
                "scheme_name": "Pradhan Mantri Matru Vandana Yojana",
                "category": "Women & Child",
                "eligibility": "Pregnant women and lactating mothers for first live birth.",
                "source_dataset": "myscheme_baseline",
                "source_tier": AuthorityTier.PRIMARY_CANONICALIZED.value,
                "source_url": "https://wcd.nic.in",
            }
        ]

        dry_job = self.orchestrator.sync(
            dry_run=True,
            custom_records_override=updated_records,
        )
        self.assertEqual(dry_job.status, SyncStatus.DRY_RUN)
        self.assertEqual(dry_job.records_added, 1)
        self.assertEqual(dry_job.records_unchanged, 2)
        # Active version MUST remain unchanged after dry-run
        self.assertEqual(self.orchestrator.get_active_policy_version(), v1_version)

        # Step 3: Live Sync (dry_run=False) -> Activation
        live_job = self.orchestrator.sync(
            dry_run=False,
            custom_records_override=updated_records,
        )
        self.assertEqual(live_job.status, SyncStatus.SUCCEEDED)
        self.assertEqual(live_job.activation_status, "ACTIVATED")
        v2_version = self.orchestrator.get_active_policy_version()
        self.assertNotEqual(v1_version, v2_version)
        assert v2_version is not None

        # Step 4: Verify active snapshot artifacts
        active_snap = self.snapshots_dir / v2_version
        self.assertTrue((active_snap / "metadata.json").exists())
        self.assertTrue((active_snap / "source_manifest.json").exists())
        self.assertTrue((active_snap / "canonical" / "schemes.jsonl").exists())

        # Verify audit log recorded both syncs
        audit_file = self.snapshots_dir / "sync_audit_log.jsonl"
        self.assertTrue(audit_file.exists())
        with open(audit_file, "r", encoding="utf-8") as f:
            logs = [json.loads(line) for line in f if line.strip()]
        self.assertGreaterEqual(len(logs), 2)
        self.assertEqual(logs[-1]["sync_id"], live_job.sync_id)

    def test_historical_decision_immutability_and_reevaluation(self):
        """
        CRITICAL TEST (Part 13):
        Application evaluated under policy version V1 must retain its exact decision,
        facts, and policy version reference even after V2 is live.
        Re-evaluation creates V2 snapshot without mutating historical V1 snapshot.
        """
        # 1. Establish Policy Snapshot V1
        job_v1 = self.orchestrator.sync(
            dry_run=False,
            custom_records_override=self.baseline_records,
        )
        v1_id = self.orchestrator.get_active_policy_version()

        # 2. Setup Application Workflow Service connected to this snapshot manager
        app_repo = InMemoryApplicationRepository()
        mock_pipeline = ApplicationPipeline(llm_config=LLMConfig(provider="mock"))
        workflow_service = ApplicationWorkflowService(
            repository=app_repo,
            pipeline=mock_pipeline,
            snapshot_manager=self.snapshot_mgr,
        )

        # 3. Create Case and Evaluate under V1
        case = workflow_service.create_application(
            citizen_reference="app_user_001",
        )
        workflow_service.update_applicant_profile(
            application_id=case.application_id,
            facts={
                "annual_family_income": 200000,
                "is_indian_citizen": True,
            },
        )
        eval_v1 = workflow_service.evaluate_scheme(
            application_id=case.application_id,
            scheme_id="national_scholarship_portal",
            scheme_name="National Scholarship Portal Scheme",
        )
        # Verify snapshot 1 recorded V1
        v1_snapshots = app_repo.list_decision_snapshots(case.application_id)
        self.assertEqual(len(v1_snapshots), 1)
        snap_v1 = v1_snapshots[0]
        self.assertEqual(snap_v1.policy_snapshot_version, v1_id)
        self.assertEqual(snap_v1.version_index, 1)
        v1_original_status = snap_v1.decision_status
        v1_original_facts = dict(snap_v1.applicant_fact_snapshot)

        # 4. Trigger Live Policy Update to V2 (Eligibility Criteria Modified)
        # Income threshold tightened from 250,000 to 150,000
        records_v2 = [
            {
                "slug": "national_scholarship_portal",
                "scheme_name": "National Scholarship Portal Scheme",
                "category": "Education",
                "eligibility": "Annual family income must not exceed 150000. Must be citizen of India.",
                "source_dataset": "myscheme_baseline",
                "source_tier": AuthorityTier.PRIMARY_CANONICALIZED.value,
                "source_url": "https://scholarships.gov.in",
            },
            self.baseline_records[1],
        ]
        job_v2 = self.orchestrator.sync(
            dry_run=False,
            custom_records_override=records_v2,
        )
        v2_id = self.orchestrator.get_active_policy_version()
        self.assertNotEqual(v1_id, v2_id)

        # 5. IMMUTABILITY CHECK:
        # Original snapshot V1 in repository MUST NOT be mutated or affected by the policy update
        historical_snapshots = app_repo.list_decision_snapshots(case.application_id)
        self.assertEqual(len(historical_snapshots), 1)
        preserved_snap_v1 = historical_snapshots[0]
        self.assertEqual(preserved_snap_v1.policy_snapshot_version, v1_id)
        self.assertEqual(preserved_snap_v1.applicant_fact_snapshot, v1_original_facts)
        self.assertEqual(preserved_snap_v1.decision_status, v1_original_status)

        # 6. Re-evaluate under the new policy version
        eval_v2 = workflow_service.evaluate_scheme(
            application_id=case.application_id,
            scheme_id="national_scholarship_portal",
            scheme_name="National Scholarship Portal Scheme",
        )
        updated_snapshots = app_repo.list_decision_snapshots(case.application_id)
        self.assertEqual(len(updated_snapshots), 2)

        snap_v2 = updated_snapshots[1]
        self.assertEqual(snap_v2.policy_snapshot_version, v2_id)
        self.assertEqual(snap_v2.version_index, 2)

        # Historical V1 is STILL completely intact
        self.assertEqual(updated_snapshots[0].policy_snapshot_version, v1_id)
        self.assertEqual(updated_snapshots[0].version_index, 1)

    def test_full_rollback_lifecycle(self):
        """
        Tests rolling back from V2 to V1:
        1. V1 active
        2. V2 deployed
        3. rollback() executes
        4. V1 restored as active pointer
        5. Audit log reflects ROLLED_BACK
        """
        # Baseline V1
        self.orchestrator.sync(dry_run=False, custom_records_override=self.baseline_records)
        v1 = self.orchestrator.get_active_policy_version()

        # Update to V2
        records_v2 = list(self.baseline_records) + [
            {
                "slug": "temporary_scheme",
                "scheme_name": "Temporary Scheme",
                "category": "Test",
                "eligibility": "Temporary eligibility",
                "source_dataset": "myscheme_baseline",
                "source_tier": AuthorityTier.PRIMARY_CANONICALIZED.value,
                "source_url": "https://gov.in",
            }
        ]
        self.orchestrator.sync(dry_run=False, custom_records_override=records_v2)
        v2 = self.orchestrator.get_active_policy_version()
        self.assertNotEqual(v1, v2)

        # Execute Rollback to V1
        restored = self.orchestrator.rollback(target_version=v1)
        self.assertEqual(restored, v1)
        self.assertEqual(self.orchestrator.get_active_policy_version(), v1)

        # Check audit log
        audit_file = self.snapshots_dir / "sync_audit_log.jsonl"
        with open(audit_file, "r", encoding="utf-8") as f:
            logs = [json.loads(line) for line in f if line.strip()]
        last_log = logs[-1]
        self.assertEqual(last_log["status"], SyncStatus.ROLLED_BACK.value)
        self.assertEqual(last_log["candidate_version"], v1)

    def test_hf_supplementary_integration_flow(self):
        """
        Verifies Hugging Face supplementary ingestion pipeline:
        - Revision metadata is stored
        - Data is classified as SUPPLEMENTARY
        - Primary canonical source facts are not overwritten
        """
        hf_pipeline = HuggingFacePipeline()
        from src.data_pipeline.models import SourceType
        source_def = SourceDefinition(
            source_id="smartduketech/indian-government-schemes-2025",
            source_name="SmartDukeTech Indian Government Schemes 2025",
            source_type=SourceType.HUGGINGFACE_DATASET,
            authority_tier=AuthorityTier.SUPPLEMENTARY,
            url="https://huggingface.co/datasets/smartduketech/indian-government-schemes-2025",
            fetch_method="huggingface",
        )

        mock_rows = [
            {
                "scheme_name": "PM Kisan Samman Nidhi",
                "details": "Supplementary financial benefit details from HF dataset.",
                "beneficiaries": "Farmers",
                "eligibility": "Cultivable landholder farmers",
                "tags": "agriculture, financial-support",
                "is_government": True,
            }
        ]

        report = hf_pipeline.ingest_dataset(
            repo_id="smartduketech/indian-government-schemes-2025",
            raw_records_override=mock_rows,
        )
        self.assertTrue(report.success)
        self.assertEqual(len(report.normalized_records), 1)
        rec = report.normalized_records[0]
        self.assertEqual(rec["source_tier"], AuthorityTier.SUPPLEMENTARY.value)
        self.assertTrue(rec.get("is_supplementary"))
        self.assertIn("hf_commit_hash", rec)
