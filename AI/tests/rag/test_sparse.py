"""
Unit tests for PolicySetu Sparse Retrieval (BM25Okapi).
Verifies exact term matching, multilingual Unicode tokenization, and index persistence.
"""

import unittest
import tempfile
from pathlib import Path
from src.rag.sparse import BM25Retriever, tokenize_text
from src.rag.models import RAGDocument, ContentType, SourceTier


class TestSparseRetrieval(unittest.TestCase):
    """Tests BM25 sparse keyword search."""

    def test_unicode_tokenization(self):
        """Tests that Latin and Devanagari words tokenize cleanly."""
        tokens_en = tokenize_text("Pradhan Mantri Awas Yojana 2024")
        self.assertIn("pradhan", tokens_en)
        self.assertIn("awas", tokens_en)

        tokens_hi = tokenize_text("अटल पेंशन योजना")
        self.assertIn("अटल", tokens_hi)
        self.assertIn("पेंशन", tokens_hi)
        self.assertIn("योजना", tokens_hi)

    def test_bm25_exact_term_search(self):
        """Tests that exact keyword queries rank matching documents highest."""
        doc1 = RAGDocument(
            id="doc_1",
            scheme_id="s1",
            scheme_slug="apy",
            scheme_name="Atal Pension Yojana",
            content="Atal Pension Yojana provides a guaranteed monthly pension to citizens between 18 and 40.",
            content_type=ContentType.ELIGIBILITY.value,
            source_dataset="test",
            source_tier=SourceTier.PRIMARY_SCHEME.value
        )
        doc2 = RAGDocument(
            id="doc_2",
            scheme_id="s2",
            scheme_slug="pmkisan",
            scheme_name="PM Kisan Samman Nidhi",
            content="PM Kisan provides 6000 rupees income support to landholding farmer families.",
            content_type=ContentType.BENEFITS.value,
            source_dataset="test",
            source_tier=SourceTier.PRIMARY_SCHEME.value
        )
        doc3 = RAGDocument(
            id="doc_3",
            scheme_id="s3",
            scheme_slug="pmmvy",
            scheme_name="Pradhan Mantri Matru Vandana Yojana",
            content="Maternity cash benefits of 5000 rupees for pregnant women and lactating mothers.",
            content_type=ContentType.BENEFITS.value,
            source_dataset="test",
            source_tier=SourceTier.PRIMARY_SCHEME.value
        )

        retriever = BM25Retriever()
        retriever.fit([doc1, doc2, doc3])

        # Query 1: "pension 18 to 40" -> doc1 must be top
        res1 = retriever.search("pension 18 to 40", top_k=2)
        self.assertGreater(len(res1), 0)
        self.assertEqual(res1[0][0], "doc_1")

        # Query 2: "farmer 6000 rupees" -> doc2 must be top
        res2 = retriever.search("farmer 6000 rupees", top_k=2)
        self.assertGreater(len(res2), 0)
        self.assertEqual(res2[0][0], "doc_2")

        # Query 3: "pregnant women maternity" -> doc3 must be top
        res3 = retriever.search("pregnant women maternity", top_k=2)
        self.assertGreater(len(res3), 0)
        self.assertEqual(res3[0][0], "doc_3")

    def test_bm25_empty_query(self):
        """Tests that empty query returns empty results without crashing."""
        retriever = BM25Retriever()
        self.assertEqual(retriever.search(""), [])
        self.assertEqual(retriever.search("   "), [])

    def test_save_and_load_bm25(self):
        """Tests serialization and deserialization of BM25 index."""
        doc = RAGDocument(
            id="doc_test",
            scheme_id="s1",
            scheme_slug="test-slug",
            scheme_name="Test Scheme",
            content="Unique test content for serialization testing.",
            content_type="overview",
            source_dataset="test",
            source_tier="PRIMARY_SCHEME"
        )
        retriever = BM25Retriever()
        retriever.fit([doc])

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_path = str(Path(tmp_dir) / "bm25.pkl")
            retriever.save(save_path)

            loaded = BM25Retriever.load(save_path)
            res = loaded.search("serialization", top_k=1)
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0][0], "doc_test")


if __name__ == "__main__":
    unittest.main()
