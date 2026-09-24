"""
Unit tests for Phase 12 Activation Gates, Candidate Staging, and Promotion.
Verifies the 14 deterministic gates fail-closed behavior.
"""

from pathlib import Path
import shutil
import sys
import tempfile
import unittest

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.data_pipeline.models import (
    AuthorityTier,
    ChangeType,
    ConflictRecord,
    ConflictResolution,
    RecordDiff,
    SourceDefinition,
    SourceType,
    SyncRunMetadata,
    SyncStatus,
)
from src.data_pipeline.gates import ActivationGateEvaluator
from src.data_pipeline.snapshot import SnapshotManager
from src.data_pipeline.staging import CandidateSnapshotStager


class TestGatesAndStaging(unittest.TestCase):
    """Test suite for the 14 activation gates and candidate staging."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.snapshots_dir = self.temp_dir / "snapshots"
        self.snapshots_dir.mkdir()
        self.snapshot_mgr = SnapshotManager(snapshots_root=self.snapshots_dir)
        self.stager = CandidateSnapshotStager(snapshots_root=self.snapshots_dir, snapshot_manager=self.snapshot_mgr)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_gate_1_schema_validation_rejection(self):
        """Gate 1 rejects candidate records missing mandatory keys."""
        invalid_records = [
            {"slug": "valid_slug", "scheme_name": "", "category": "Health"},  # Empty scheme_name
        ]
        report = ActivationGateEvaluator.evaluate_gates(
            candidate_records=invalid_records,
            diffs=[],
            conflicts=[],
            sources=[],
        )
        self.assertFalse(report.can_activate)
        self.assertFalse(report.results[0].passed)
        self.assertEqual(report.results[0].gate_number, 1)

    def test_gate_2_source_authority_untrusted_rejection(self):
        """Gate 2 rejects schemes marked UNTRUSTED."""
        records = [
            {
                "slug": "scheme_untrusted",
                "scheme_name": "Untrusted Scheme",
                "category": "General",
                "source_tier": AuthorityTier.UNTRUSTED.value,
            }
        ]
        report = ActivationGateEvaluator.evaluate_gates(
            candidate_records=records,
            diffs=[],
            conflicts=[],
            sources=[],
        )
        self.assertFalse(report.can_activate)
        self.assertFalse(report.results[1].passed)
        self.assertEqual(report.results[1].gate_number, 2)

    def test_gate_3_url_allowlist_rejection(self):
        """Gate 3 rejects non-https URLs and unapproved domains."""
        records = [
            {
                "slug": "scheme_bad_url",
                "scheme_name": "Scheme Bad URL",
                "category": "General",
                "source_url": "http://unencrypted.com/scheme",  # Non-https
            }
        ]
        report = ActivationGateEvaluator.evaluate_gates(
            candidate_records=records,
            diffs=[],
            conflicts=[],
            sources=[],
        )
        self.assertFalse(report.can_activate)
        self.assertFalse(report.results[2].passed)
        self.assertEqual(report.results[2].gate_number, 3)

    def test_gate_5_duplicate_slug_rejection(self):
        """Gate 5 rejects duplicate scheme slugs."""
        records = [
            {"slug": "dup_slug", "scheme_name": "Scheme 1", "category": "General"},
            {"slug": "dup_slug", "scheme_name": "Scheme 2", "category": "General"},
        ]
        report = ActivationGateEvaluator.evaluate_gates(
            candidate_records=records,
            diffs=[],
            conflicts=[],
            sources=[],
        )
        self.assertFalse(report.can_activate)
        self.assertFalse(report.results[4].passed)
        self.assertEqual(report.results[4].gate_number, 5)

    def test_gate_12_catastrophic_deletion_rejection(self):
        """Gate 12 rejects candidate if record count drops precipitously (>15% drop)."""
        candidate = [
            {"slug": f"scheme_{i}", "scheme_name": f"Scheme {i}", "category": "General"}
            for i in range(50)
        ]
        # Baseline had 100 records
        report = ActivationGateEvaluator.evaluate_gates(
            candidate_records=candidate,
            diffs=[],
            conflicts=[],
            sources=[],
            baseline_record_count=100,
        )
        self.assertFalse(report.can_activate)
        self.assertFalse(report.results[11].passed)
        self.assertEqual(report.results[11].gate_number, 12)

    def test_candidate_staging_and_atomic_promotion(self):
        """Valid candidate is staged, passes gates, and atomically promoted to active."""
        valid_records = [
            {
                "slug": "post_matric_scholarship_sc",
                "scheme_name": "Post Matric Scholarship SC",
                "category": "Education & Learning",
                "eligibility": "SC category, income <= 250000",
                "source_dataset": "myscheme_baseline",
                "source_tier": AuthorityTier.PRIMARY_CANONICALIZED.value,
                "source_url": "https://scholarships.gov.in",
            }
        ]
        sources = [
            SourceDefinition(
                source_id="myscheme_baseline",
                source_name="MyScheme Baseline",
                source_type=SourceType.LOCAL_BASELINE,
                authority_tier=AuthorityTier.PRIMARY_CANONICALIZED,
            )
        ]
        diffs = [RecordDiff(scheme_slug="post_matric_scholarship_sc", change_type=ChangeType.ADDED)]
        conflicts: list[ConflictRecord] = []

        report = ActivationGateEvaluator.evaluate_gates(
            candidate_records=valid_records,
            diffs=diffs,
            conflicts=conflicts,
            sources=sources,
        )
        self.assertTrue(report.can_activate)

        # Stage
        cand_path = self.stager.stage_candidate(
            candidate_id="cand_test_01",
            sources=sources,
            canonical_records=valid_records,
            diffs=diffs,
            conflicts=conflicts,
            gate_report=report,
        )
        self.assertTrue(cand_path.exists())
        self.assertFalse(self.snapshot_mgr.active_pointer_file.exists())  # Staging does NOT modify active pointer

        # Promote
        sync_meta = SyncRunMetadata(
            sync_run_id="sync_test_01",
            started_at="2026-09-24T09:00:00Z",
            status=SyncStatus.SUCCEEDED,
        )
        promoted, err = self.stager.promote_candidate(
            candidate_id="cand_test_01",
            target_snapshot_id="snapshot_20260924_090000",
            metadata=sync_meta,
            sources=sources,
        )
        self.assertTrue(promoted)
        self.assertIsNone(err)

        # Verify active snapshot pointer
        active_id = self.snapshot_mgr.get_active_snapshot_id()
        self.assertEqual(active_id, "snapshot_20260924_090000")


if __name__ == "__main__":
    unittest.main()
