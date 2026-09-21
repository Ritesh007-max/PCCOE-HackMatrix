"""
Unit tests for Freshness Tracking, Conservative Activation, and Rollback Engine.
Verifies immutable snapshot structure, quarantine of stale/failed sources, and atomic rollback.
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from src.data_pipeline.freshness import FreshnessTracker
from src.data_pipeline.snapshot import SnapshotManager
from src.data_pipeline.models import (
    SourceDefinition,
    SourceType,
    AuthorityTier,
    FreshnessStatus,
    SyncRunMetadata,
    SyncStatus,
)


class TestFreshnessAndRollback(unittest.TestCase):

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.snapshot_mgr = SnapshotManager(snapshots_root=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_freshness_evaluation_states(self):
        now = datetime.now(timezone.utc)

        # 1. Fresh source (fetched 2 hours ago, refresh interval 24h)
        fresh_src = SourceDefinition(
            source_id="fresh_source",
            source_name="Fresh",
            source_type=SourceType.WEB_PAGE,
            authority_tier=AuthorityTier.PRIMARY_OFFICIAL,
            update_frequency_hours=24,
            stale_after_days=7,
            last_successful_fetch=(now - timedelta(hours=2)).isoformat(),
        )
        self.assertEqual(FreshnessTracker.evaluate_freshness(fresh_src, now=now), FreshnessStatus.FRESH)
        self.assertFalse(FreshnessTracker.is_quarantine_required(fresh_src))

        # 2. Aging source (fetched 30 hours ago, refresh interval 24h, but < 7 days)
        aging_src = SourceDefinition(
            source_id="aging_source",
            source_name="Aging",
            source_type=SourceType.WEB_PAGE,
            authority_tier=AuthorityTier.PRIMARY_OFFICIAL,
            update_frequency_hours=24,
            stale_after_days=7,
            last_successful_fetch=(now - timedelta(hours=30)).isoformat(),
        )
        self.assertEqual(FreshnessTracker.evaluate_freshness(aging_src, now=now), FreshnessStatus.AGING)
        self.assertFalse(FreshnessTracker.is_quarantine_required(aging_src))

        # 3. Stale source (fetched 10 days ago, stale after 7 days)
        stale_src = SourceDefinition(
            source_id="stale_source",
            source_name="Stale",
            source_type=SourceType.WEB_PAGE,
            authority_tier=AuthorityTier.PRIMARY_OFFICIAL,
            update_frequency_hours=24,
            stale_after_days=7,
            last_successful_fetch=(now - timedelta(days=10)).isoformat(),
        )
        self.assertEqual(FreshnessTracker.evaluate_freshness(stale_src, now=now), FreshnessStatus.STALE)
        self.assertTrue(FreshnessTracker.is_quarantine_required(stale_src))

    def test_conservative_activation_and_rollback(self):
        """
        Tests:
        1. Snapshot 1 created and activated (known good).
        2. Snapshot 2 created and activated.
        3. Snapshot 3 fails validation -> quarantined, NOT activated.
        4. Rollback from Snapshot 2 -> Snapshot 1.
        """
        dummy_meta = SyncRunMetadata(
            sync_run_id="run_01",
            started_at=datetime.now(timezone.utc).isoformat(),
            status=SyncStatus.SUCCESS,
        )

        # 1. Snapshot 1
        self.snapshot_mgr.create_snapshot(
            snapshot_id="snapshot_01",
            metadata=dummy_meta,
            sources=[],
            canonical_records=[{"slug": "pm-kisan", "name": "PM Kisan v1"}],
            diffs=[],
            conflicts=[],
        )
        self.snapshot_mgr.activate_snapshot("snapshot_01")
        self.assertEqual(self.snapshot_mgr.get_active_snapshot_id(), "snapshot_01")

        # 2. Snapshot 2
        self.snapshot_mgr.create_snapshot(
            snapshot_id="snapshot_02",
            metadata=dummy_meta,
            sources=[],
            canonical_records=[{"slug": "pm-kisan", "name": "PM Kisan v2"}],
            diffs=[],
            conflicts=[],
        )
        self.snapshot_mgr.activate_snapshot("snapshot_02")
        self.assertEqual(self.snapshot_mgr.get_active_snapshot_id(), "snapshot_02")

        # 3. Snapshot 3 fails validation
        self.snapshot_mgr.create_snapshot(
            snapshot_id="snapshot_03",
            metadata=dummy_meta,
            sources=[],
            canonical_records=[{"slug": "broken-scheme"}],
            diffs=[],
            conflicts=[],
        )
        self.snapshot_mgr.mark_snapshot_failed("snapshot_03", reason="Invalid criteria")
        # Invariant: Snapshot 2 MUST REMAIN active!
        self.assertEqual(self.snapshot_mgr.get_active_snapshot_id(), "snapshot_02")
        # Snapshot 3 is preserved on disk
        self.assertTrue((self.temp_dir / "snapshot_03" / "metadata.json").exists())

        # 4. Rollback from Snapshot 2 back to Snapshot 1
        prev = self.snapshot_mgr.rollback()
        self.assertEqual(prev, "snapshot_01")
        self.assertEqual(self.snapshot_mgr.get_active_snapshot_id(), "snapshot_01")


if __name__ == "__main__":
    unittest.main()
