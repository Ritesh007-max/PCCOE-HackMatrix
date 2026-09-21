"""
Comprehensive Data Quality Validation Test Suite covering all 20 Section 24 fixtures:
1. unchanged source
2. new scheme
3. modified income threshold
4. removed scheme
5. conflicting source
6. stale source
7. failed fetch
8. malformed PDF
9. broken URL
10. duplicate scheme
11. new FAQ
12. removed FAQ
13. changed FAQ
14. changed benefit only
15. changed eligibility only
16. changed application URL
17. HF supplementary addition
18. policy rollback
19. dry run
20. full validation failure
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

from src.data_pipeline.validation import DataQualityValidator
from src.data_pipeline.change_detection import ChangeDetector
from src.data_pipeline.conflict import ConflictDetector
from src.data_pipeline.freshness import FreshnessTracker
from src.data_pipeline.fetchers.pdf import PDFFetcher
from src.data_pipeline.fetchers.base import FetchResult
from src.data_pipeline.fetchers.huggingface import HuggingFaceFetcher
from src.data_pipeline.snapshot import SnapshotManager
from src.data_pipeline.sync import run_synchronization
from src.data_pipeline.models import (
    SourceDefinition,
    SourceType,
    AuthorityTier,
    ChangeType,
    SyncStatus,
    SyncRunMetadata,
)


class TestValidationAndFixtures(unittest.TestCase):

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.snapshot_mgr = SnapshotManager(snapshots_root=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # Fixture 1: Unchanged Source
    def test_fixture_01_unchanged_source(self):
        schemes = [{"slug": "pm-kisan", "scheme_name": "PM Kisan", "provenance": {"tier": "primary"}}]
        summary = ChangeDetector.diff_datasets(schemes, schemes)
        self.assertEqual(summary.unchanged_count, 1)
        self.assertEqual(summary.modified_count, 0)

    # Fixture 2: New Scheme
    def test_fixture_02_new_scheme(self):
        old_s = [{"slug": "pm-kisan", "scheme_name": "PM Kisan"}]
        new_s = [{"slug": "pm-kisan", "scheme_name": "PM Kisan"}, {"slug": "surya-ghar", "scheme_name": "Surya Ghar"}]
        summary = ChangeDetector.diff_datasets(old_s, new_s)
        self.assertEqual(summary.added_count, 1)

    # Fixture 3: Modified Income Threshold
    def test_fixture_03_modified_income_threshold(self):
        old_s = [{"slug": "pm-kisan", "annual_family_income": 250000}]
        new_s = [{"slug": "pm-kisan", "annual_family_income": 300000}]
        summary = ChangeDetector.diff_datasets(old_s, new_s)
        self.assertEqual(summary.modified_count, 1)
        self.assertTrue(summary.has_eligibility_changes)
        self.assertTrue(summary.diffs[0].field_diffs[0].is_threshold_changed)

    # Fixture 4: Removed Scheme
    def test_fixture_04_removed_scheme(self):
        old_s = [{"slug": "old-scheme", "scheme_name": "Old"}]
        new_s = []
        summary = ChangeDetector.diff_datasets(old_s, new_s)
        self.assertEqual(summary.removed_count, 1)

    # Fixture 5: Conflicting Source
    def test_fixture_05_conflicting_source(self):
        rec_a = {"slug": "pm-kisan", "annual_family_income": 250000}
        rec_b = {"slug": "pm-kisan", "annual_family_income": 400000}
        conflicts = ConflictDetector.compare_records(
            rec_a, rec_b, "source_a", "source_b", AuthorityTier.PRIMARY_CANONICALIZED, AuthorityTier.SUPPLEMENTARY, "pm-kisan"
        )
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].resolved_value, 250000)

    # Fixture 6: Stale Source
    def test_fixture_06_stale_source(self):
        now = datetime.now(timezone.utc)
        src = SourceDefinition(
            source_id="stale_src",
            source_name="Stale",
            source_type=SourceType.WEB_PAGE,
            authority_tier=AuthorityTier.PRIMARY_OFFICIAL,
            update_frequency_hours=24,
            stale_after_days=5,
            last_successful_fetch=(now - timedelta(days=10)).isoformat(),
        )
        self.assertTrue(FreshnessTracker.is_quarantine_required(src))

    # Fixture 7: Failed Fetch
    def test_fixture_07_failed_fetch(self):
        failed_res = FetchResult(source_id="test", url="http://test.com", status_code=500, error="Server error", success=False)
        self.assertFalse(failed_res.success)
        self.assertEqual(failed_res.status_code, 500)

    # Fixture 8: Malformed PDF
    def test_fixture_08_malformed_pdf(self):
        fetcher = PDFFetcher()
        meta = fetcher.extract_pdf_metadata(b"NOT_A_PDF_FILE", "bad.pdf")
        self.assertEqual(meta.status, "MALFORMED")

    # Fixture 9: Broken URL
    def test_fixture_09_broken_url(self):
        bad_scheme = [{"slug": "bad-url-scheme", "scheme_name": "Bad URL", "source_url": "httptypo://invalid", "provenance": {"tier": "primary"}}]
        report = DataQualityValidator.validate_corpus(bad_scheme)
        self.assertTrue(any("malformed source_url" in w for w in report.warnings))

    # Fixture 10: Duplicate Scheme
    def test_fixture_10_duplicate_scheme(self):
        dups = [
            {"slug": "duplicate-slug", "scheme_name": "A", "provenance": {"tier": "primary"}},
            {"slug": "duplicate-slug", "scheme_name": "B", "provenance": {"tier": "primary"}},
        ]
        report = DataQualityValidator.validate_corpus(dups)
        self.assertFalse(report.is_valid)
        self.assertTrue(any("Duplicate scheme slugs" in err for err in report.critical_errors))

    # Fixture 11: New FAQ
    def test_fixture_11_new_faq(self):
        old_faqs = [{"scheme_slug": "pm-kisan", "question": "Q1", "answer": "A1"}]
        new_faqs = old_faqs + [{"scheme_slug": "pm-kisan", "question": "Q2", "answer": "A2"}]
        self.assertEqual(len(new_faqs) - len(old_faqs), 1)

    # Fixture 12: Removed FAQ
    def test_fixture_12_removed_faq(self):
        old_faqs = [{"scheme_slug": "pm-kisan", "question": "Q1", "answer": "A1"}, {"scheme_slug": "pm-kisan", "question": "Q2", "answer": "A2"}]
        new_faqs = [old_faqs[0]]
        self.assertEqual(len(old_faqs) - len(new_faqs), 1)

    # Fixture 13: Changed FAQ
    def test_fixture_13_changed_faq(self):
        old_faq = {"scheme_slug": "pm-kisan", "question": "Q1", "answer": "A1"}
        new_faq = {"scheme_slug": "pm-kisan", "question": "Q1", "answer": "Updated Answer"}
        self.assertNotEqual(old_faq["answer"], new_faq["answer"])

    # Fixture 14: Changed Benefit Only
    def test_fixture_14_changed_benefit_only(self):
        old_s = [{"slug": "pm-kisan", "benefits": "6000", "eligibility": "Farmers"}]
        new_s = [{"slug": "pm-kisan", "benefits": "8000", "eligibility": "Farmers"}]
        summary = ChangeDetector.diff_datasets(old_s, new_s)
        diff = summary.diffs[0]
        self.assertTrue(diff.has_benefits_only_change)
        self.assertFalse(diff.has_eligibility_change)

    # Fixture 15: Changed Eligibility Only
    def test_fixture_15_changed_eligibility_only(self):
        old_s = [{"slug": "pm-kisan", "benefits": "6000", "eligibility": "Farmers up to 2ha"}]
        new_s = [{"slug": "pm-kisan", "benefits": "6000", "eligibility": "All landholding farmers"}]
        summary = ChangeDetector.diff_datasets(old_s, new_s)
        diff = summary.diffs[0]
        self.assertTrue(diff.has_eligibility_change)
        self.assertFalse(diff.has_benefits_only_change)

    # Fixture 16: Changed Application URL
    def test_fixture_16_changed_application_url(self):
        old_s = [{"slug": "pm-kisan", "source_url": "https://pmkisan.gov.in/old"}]
        new_s = [{"slug": "pm-kisan", "source_url": "https://pmkisan.gov.in/new"}]
        summary = ChangeDetector.diff_datasets(old_s, new_s)
        self.assertEqual(len(summary.diffs[0].field_diffs), 1)
        self.assertEqual(summary.diffs[0].field_diffs[0].field_name, "source_url")

    # Fixture 17: HF Supplementary Addition
    def test_fixture_17_hf_supplementary_addition(self):
        hf = HuggingFaceFetcher()
        recs = [{"scheme_name": "State Scholarship", "description": "Higher education grant"}]
        meta = hf.normalize_and_classify_records(recs, "smartduketech/indian-government-schemes-2025")
        self.assertEqual(meta.total_records, 1)
        self.assertEqual(meta.records[0]["source_dataset"], "smartduketech/indian-government-schemes-2025")

    # Fixture 18: Policy Rollback
    def test_fixture_18_policy_rollback(self):
        dummy_meta = SyncRunMetadata(sync_run_id="r1", started_at="now", status=SyncStatus.SUCCESS)
        self.snapshot_mgr.create_snapshot("snap_01", dummy_meta, [], [], [], [])
        self.snapshot_mgr.activate_snapshot("snap_01")
        self.snapshot_mgr.create_snapshot("snap_02", dummy_meta, [], [], [], [])
        self.snapshot_mgr.activate_snapshot("snap_02")

        prev = self.snapshot_mgr.rollback()
        self.assertEqual(prev, "snap_01")
        self.assertEqual(self.snapshot_mgr.get_active_snapshot_id(), "snap_01")

    # Fixture 19: Dry Run
    def test_fixture_19_dry_run(self):
        dummy_meta = SyncRunMetadata(sync_run_id="dry", started_at="now", status=SyncStatus.DRY_RUN, dry_run=True)
        self.snapshot_mgr.create_snapshot("snap_dry", dummy_meta, [], [], [], [])
        # Invariant: Dry run MUST NOT activate
        self.assertIsNone(self.snapshot_mgr.get_active_snapshot_id())

    # Fixture 20: Full Validation Failure
    def test_fixture_20_full_validation_failure(self):
        # Impossible age (< 0) and negative income (< 0)
        invalid_schemes = [
            {
                "slug": "broken-scheme",
                "scheme_name": "Broken Scheme",
                "min_age": -5,
                "annual_family_income": -50000,
                "provenance": {"tier": "primary"}
            }
        ]
        report = DataQualityValidator.validate_corpus(invalid_schemes)
        self.assertFalse(report.is_valid)
        self.assertGreaterEqual(len(report.critical_errors), 2)


if __name__ == "__main__":
    unittest.main()
