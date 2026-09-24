"""
Unit tests for FIN Section-Aware Chunking.
Verifies section preservation, atomic FAQs, chunk overlap, and stable deterministic IDs.
"""

import sys
from pathlib import Path

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

import unittest
from src.rag.chunking import (
    chunk_scheme_record,
    chunk_faq_record,
    split_text_with_overlap,
)
from src.rag.models import ContentType, SourceTier
from src.rag.config import RAGConfig


class TestChunking(unittest.TestCase):
    """Tests chunking strategies for schemes and FAQs."""

    def setUp(self):
        self.config = RAGConfig(chunk_size=100, chunk_overlap=20, min_chunk_length=10)

    def test_split_text_with_overlap(self):
        """Tests that long text splits cleanly with specified overlap."""
        text = "First paragraph here.\n\nSecond paragraph here with more words.\n\nThird paragraph follows."
        chunks = split_text_with_overlap(text, chunk_size=40, chunk_overlap=10)
        self.assertGreater(len(chunks), 1)
        # All text content should be represented
        combined = " ".join(chunks)
        self.assertIn("First", combined)
        self.assertIn("Third", combined)

    def test_empty_text_chunking(self):
        """Tests that empty or whitespace text returns empty chunk list."""
        self.assertEqual(split_text_with_overlap("", chunk_size=100, chunk_overlap=20), [])
        self.assertEqual(split_text_with_overlap("   ", chunk_size=100, chunk_overlap=20), [])

    def test_chunk_scheme_sections_preserved(self):
        """Tests that scheme records produce section-typed chunks."""
        record = {
            "id": "sch_test_01",
            "slug": "test-yojana",
            "scheme_name": "Test Welfare Yojana",
            "brief_description": "A welfare scheme providing agricultural assistance.",
            "detailed_description": "Detailed guidelines on implementation across districts.",
            "eligibility": "Farmers owning between 1 and 2 hectares of cultivable land.",
            "exclusions": "Institutional landholders and income tax payees.",
            "benefits": "Financial subsidy of 6000 INR per annum.",
            "application_process": "Apply online through the citizen portal with Aadhaar.",
            "documents_required": "Aadhaar Card, Land Title Deed (ROR), Bank Passbook.",
            "state": "Assam",
            "ministry": "Ministry of Agriculture",
        }

        chunks = chunk_scheme_record(
            record,
            source_tier=SourceTier.PRIMARY_SCHEME.value,
            source_dataset="schemes.csv",
            config=self.config
        )

        self.assertGreater(len(chunks), 0)
        content_types = {c.content_type for c in chunks}
        self.assertIn(ContentType.SCHEME_OVERVIEW.value, content_types)
        self.assertIn(ContentType.ELIGIBILITY.value, content_types)
        self.assertIn(ContentType.EXCLUSIONS.value, content_types)
        self.assertIn(ContentType.BENEFITS.value, content_types)
        self.assertIn(ContentType.APPLICATION_PROCESS.value, content_types)
        self.assertIn(ContentType.DOCUMENTS_REQUIRED.value, content_types)

        # Verify scheme identity is embedded in content header
        for c in chunks:
            self.assertIn("Test Welfare Yojana", c.content)
            self.assertEqual(c.scheme_slug, "test-yojana")
            self.assertEqual(c.source_tier, SourceTier.PRIMARY_SCHEME.value)

    def test_faq_remains_atomic(self):
        """Tests that an FAQ question and answer remain unified in a single chunk."""
        faq_record = {
            "scheme_slug": "apy",
            "scheme_name": "Atal Pension Yojana",
            "faq_number": 3,
            "question": "What is the minimum pension provided?",
            "answer": "The minimum guaranteed pension is 1,000 INR per month up to 5,000 INR per month.",
        }

        chunks = chunk_faq_record(faq_record, config=self.config)
        self.assertEqual(len(chunks), 1)
        c = chunks[0]
        self.assertEqual(c.content_type, ContentType.FAQ.value)
        self.assertIn("Question: What is the minimum pension provided?", c.content)
        self.assertIn("Answer: The minimum guaranteed pension", c.content)
        self.assertEqual(c.faq_id, "faq_3")
        self.assertEqual(c.source_tier, SourceTier.PRIMARY_FAQ.value)

    def test_deterministic_chunk_ids(self):
        """Tests that chunk IDs are 100% deterministic on identical data."""
        record = {
            "id": "sch_test_02",
            "slug": "stable-slug",
            "scheme_name": "Stable Scheme",
            "eligibility": "Age must be between 18 and 60 years.",
        }

        chunks1 = chunk_scheme_record(record, config=self.config)
        chunks2 = chunk_scheme_record(record, config=self.config)

        self.assertEqual(len(chunks1), len(chunks2))
        for c1, c2 in zip(chunks1, chunks2):
            self.assertEqual(c1.id, c2.id)
            self.assertEqual(c1.text_hash, c2.text_hash)


if __name__ == "__main__":
    unittest.main()
