"""
Unit tests for Source Registry, Authority Tiers, Precedence, and URL Allowlists.
"""

from pathlib import Path
import sys
import unittest

_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from src.data_pipeline.models import SourceType, AuthorityTier, SourceDefinition
from src.data_pipeline.sources.registry import SourceRegistry
from src.data_pipeline.sources.sources import APPROVED_SOURCES


class TestSourceRegistry(unittest.TestCase):

    def setUp(self):
        self.registry = SourceRegistry()

    def test_approved_sources_registered(self):
        """Verify baseline and supplementary sources exist in default registry."""
        self.assertIsNotNone(self.registry.get("myscheme_csv_baseline"))
        self.assertIsNotNone(self.registry.get("myscheme_faqs_baseline"))
        self.assertIsNotNone(self.registry.get("updated_data_supplementary"))
        self.assertIsNotNone(self.registry.get("local_bilingual_dataset"))
        self.assertIsNotNone(self.registry.get("hf_bharatschemes"))
        self.assertIsNotNone(self.registry.get("official_portal_web"))

    def test_authority_precedence_ordering(self):
        """
        Verify strict precedence order:
        PRIMARY_OFFICIAL > PRIMARY_CANONICALIZED > SUPPLEMENTARY > ARCHIVE > EVALUATION_ONLY
        """
        sorted_sources = self.registry.sorted_by_precedence()
        tiers = [s.authority_tier for s in sorted_sources]

        # First tier must be PRIMARY_OFFICIAL
        self.assertEqual(tiers[0], AuthorityTier.PRIMARY_OFFICIAL)

        # Priority values must be monotonically non-increasing
        priorities = [t.priority for t in tiers]
        self.assertEqual(priorities, sorted(priorities, reverse=True))

    def test_url_allowlist_enforcement(self):
        """Disallow arbitrary external URLs; permit registered government portals and exact approved repos."""
        # Registered / allowed domains
        self.assertTrue(self.registry.is_url_allowed("https://www.myscheme.gov.in/schemes/pm-kisan"))
        self.assertTrue(self.registry.is_url_allowed("https://agricoop.nic.in/guidelines.pdf"))

        # Exact approved HuggingFace repository URLs
        self.assertTrue(self.registry.is_url_allowed("https://huggingface.co/datasets/satyajitdas/bharatschemes-v1"))
        self.assertTrue(self.registry.is_url_allowed("https://huggingface.co/datasets/smartduketech/indian-government-schemes-2025"))
        self.assertTrue(self.registry.is_url_allowed("https://huggingface.co/datasets/shrijayan/gov_myscheme"))
        self.assertTrue(self.registry.is_url_allowed("https://huggingface.co/datasets/satyajitdas/bharatschemes-v1/resolve/main/data.parquet"))

        # Disallow arbitrary or spoofed HuggingFace repositories
        self.assertFalse(self.registry.is_url_allowed("https://huggingface.co/datasets/attacker/fake-schemes"))
        self.assertFalse(self.registry.is_url_allowed("https://huggingface.co/random-user/random-repo"))
        self.assertFalse(self.registry.is_url_allowed("https://huggingface.co/datasets/satyajitdas/bharatschemes-v1-fake"))

        # Disallow broad arbitrary host platforms (e.g. raw.githubusercontent.com)
        self.assertFalse(self.registry.is_url_allowed("https://raw.githubusercontent.com/evil/data.csv"))
        self.assertFalse(self.registry.is_url_allowed("https://github.com/evil/repo"))

        # Arbitrary disallowed domains
        self.assertFalse(self.registry.is_url_allowed("https://random-commercial-site.com/scheme"))
        self.assertFalse(self.registry.is_url_allowed("https://unapproved-crawler-target.org/data"))
        self.assertFalse(self.registry.is_url_allowed(""))

    def test_distinct_hf_and_bilingual_datasets(self):
        """Verify local bilingual dataset is explicitly distinguished from HF bharatschemes."""
        local_bilingual = self.registry.get("local_bilingual_dataset")
        hf_bharat = self.registry.get("hf_bharatschemes")

        self.assertIsNotNone(local_bilingual)
        self.assertIsNotNone(hf_bharat)
        assert local_bilingual is not None and hf_bharat is not None
        self.assertNotEqual(local_bilingual.url, hf_bharat.url)
        self.assertEqual(local_bilingual.source_type, SourceType.LOCAL_BILINGUAL_DATASET)
        self.assertEqual(hf_bharat.source_type, SourceType.HUGGINGFACE_DATASET)


if __name__ == "__main__":
    unittest.main()
