"""
Unit tests for FIN Ingestion Pipeline.
Verifies multi-source data loading, tier preservation, deduplication, and schema validation.
"""

import sys
from pathlib import Path

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

import unittest
from src.rag.ingestion import RAGIngestionPipeline
from src.rag.models import SourceTier, RAGDocument
from src.rag.config import RAGConfig


class TestIngestion(unittest.TestCase):
    """Tests RAG ingestion pipeline across source tiers."""

    def setUp(self):
        self.config = RAGConfig()
        self.pipeline = RAGIngestionPipeline(self.config)

    def test_load_primary_schemes(self):
        """Tests that primary schemes are loaded with PRIMARY_SCHEME tier."""
        docs = self.pipeline.load_primary_schemes(limit=5)
        self.assertGreater(len(docs), 0)
        for d in docs:
            self.assertEqual(d.source_tier, SourceTier.PRIMARY_SCHEME.value)
            self.assertIsNotNone(d.scheme_slug)
            self.assertTrue(len(d.content) > 0)
            self.assertTrue(len(d.text_hash) > 0)

    def test_load_primary_faqs(self):
        """Tests that FAQs are loaded with PRIMARY_FAQ tier."""
        docs = self.pipeline.load_primary_faqs(limit=10)
        self.assertGreater(len(docs), 0)
        for d in docs:
            self.assertEqual(d.source_tier, SourceTier.PRIMARY_FAQ.value)
            self.assertEqual(d.content_type, "faq")
            self.assertIn("Question:", d.content)
            self.assertIn("Answer:", d.content)

    def test_deduplication_in_pipeline(self):
        """Tests that identical duplicate text chunks are safely deduplicated."""
        docs = self.pipeline.run_ingestion(
            scheme_limit=3,
            faq_limit=5,
            include_supplementary=False,
            save_to_disk=False
        )
        hashes = [d.text_hash for d in docs]
        self.assertEqual(len(hashes), len(set(hashes)), "Text hashes must be unique in ingested collection.")


if __name__ == "__main__":
    unittest.main()
