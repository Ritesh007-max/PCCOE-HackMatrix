"""
Unit tests for Phase 12 Hugging Face Supplementary Data Ingestion.
Verifies supplementary authority, revision tracking, role routing, and schema drift handling.
"""

from pathlib import Path
import sys
import unittest

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.data_pipeline.models import AuthorityTier
from src.data_pipeline.sources.huggingface import (
    HFRole,
    HuggingFacePipeline,
    HFDatasetSpec,
)


class TestHFPipeline(unittest.TestCase):
    """Test suite for Hugging Face supplementary pipeline."""

    def setUp(self):
        self.pipeline = HuggingFacePipeline()

    def test_hf_authority_tier_remains_supplementary(self):
        """Hugging Face datasets are strictly classified as AuthorityTier.SUPPLEMENTARY."""
        sample_records = [
            {
                "scheme_name": "Kisan Credit Card Supplementary",
                "category": "Agriculture",
                "eligibility": "Farmers with valid land title",
            }
        ]
        report = self.pipeline.ingest_dataset(
            repo_id="smartduketech/indian-government-schemes-2025",
            raw_records_override=sample_records,
            commit_hash_override="a1b2c3d4e5f6",
        )
        self.assertTrue(report.success)
        self.assertEqual(report.authority_tier, AuthorityTier.SUPPLEMENTARY)
        self.assertEqual(report.commit_hash, "a1b2c3d4e5f6")
        self.assertEqual(len(report.normalized_records), 1)
        self.assertTrue(report.normalized_records[0]["is_supplementary"])

    def test_bharatschemes_qa_queries_routed_to_benchmarks(self):
        """BharatSchemes queries are routed to benchmark_queries; answers excluded from rules."""
        sample_qa = [
            {
                "question": "What is the income limit for Gujarat scholarship?",
                "question_english": "What is the income limit for Gujarat scholarship?",
                "scheme_name": "SC Post Matric Scholarship",
                "answer": "Rs 2,50,000 per annum according to guidelines.",
            }
        ]
        report = self.pipeline.ingest_dataset(
            repo_id="satyajitdas/bharatschemes-v1",
            raw_records_override=sample_qa,
        )
        self.assertTrue(report.success)
        self.assertEqual(report.role, HFRole.BENCHMARK_EVALUATION)
        self.assertEqual(len(report.benchmark_queries), 1)
        # Verify answer was NOT ingested into statutory rules
        self.assertNotIn("answer", report.benchmark_queries[0]["raw_metadata"])

    def test_schema_drift_warning_on_missing_required_keys(self):
        """Missing expected required keys triggers schema_drift_detected flag and warnings."""
        drifted_records = [
            {"unexpected_key": "some_value"}  # Missing scheme_name and category
        ]
        report = self.pipeline.ingest_dataset(
            repo_id="smartduketech/indian-government-schemes-2025",
            raw_records_override=drifted_records,
        )
        self.assertTrue(report.schema_drift_detected)
        self.assertGreater(len(report.drift_warnings), 0)

    def test_csr_ngo_classification_detection(self):
        """CSR and private foundation programs are classified as CSR_NGO."""
        csr_records = [
            {
                "scheme_name": "Tata Trust Higher Education Grant",
                "category": "Education",
                "description": "Corporate social responsibility initiative by Tata Foundation.",
            },
            {
                "scheme_name": "PM National Relief Fund",
                "category": "Social Welfare",
                "description": "Government statutory relief fund.",
            }
        ]
        report = self.pipeline.ingest_dataset(
            repo_id="smartduketech/indian-government-schemes-2025",
            raw_records_override=csr_records,
        )
        self.assertEqual(report.csr_ngo_count, 1)
        self.assertEqual(report.government_schemes_count, 1)


if __name__ == "__main__":
    unittest.main()
