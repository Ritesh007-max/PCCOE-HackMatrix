"""
Tests for FIN Devanagari & Cross-Lingual Retrieval Normalization (Intelligence/src/rag/query_normalization.py).
Validates pure Devanagari queries, nukta variations, Hinglish queries,
and cross-lingual concept expansion.
"""

import sys
from pathlib import Path
import unittest

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.rag.query_normalization import QueryNormalizer


class TestDevanagariRetrievalNormalization(unittest.TestCase):
    """Test suite for Devanagari and cross-lingual retrieval pipeline."""

    def setUp(self):
        self.normalizer = QueryNormalizer()

    def test_devanagari_apy_retrieval_expansion(self):
        """Devanagari APY query produces English concept expansion for hybrid RAG."""
        hi_q = "अटल पेंशन योजना में न्यूनतम कितनी पेंशन मिलती है"
        rec = self.normalizer.normalize(hi_q)
        self.assertEqual(rec.detected_language, "hi")
        self.assertIn("Atal Pension Yojana", rec.search_query)
        self.assertIn("pension", rec.search_query)
        self.assertEqual(rec.original_query, hi_q)

    def test_devanagari_pm_kisan_query(self):
        """Devanagari PM-KISAN query expands to canonical PM-KISAN title."""
        hi_q = "प्रधानमंत्री किसान सम्मान निधि योजना के तहत 6000 रुपये"
        rec = self.normalizer.normalize(hi_q)
        self.assertIn("PM-KISAN", rec.search_query)
        self.assertIn("farmer", rec.search_query)

    def test_devanagari_document_requirement_query(self):
        """Document requirement keywords expand to English keywords."""
        hi_q = "योजना के लिए आवश्यक दस्तावेज और कागजात"
        rec = self.normalizer.normalize(hi_q)
        self.assertIn("documents", rec.search_query)

    def test_devanagari_benefit_query(self):
        """Benefit/financial assistance keywords expand to English equivalents."""
        hi_q = "सरकारी वित्तीय सहायता और लाभ राशि"
        rec = self.normalizer.normalize(hi_q)
        self.assertIn("financial assistance", rec.search_query)
        self.assertIn("benefit", rec.search_query)

    def test_nukta_and_orthographic_variations(self):
        """Standard and nukta variants normalize without semantic loss."""
        rec1 = self.normalizer.normalize("दस्तावेज")
        rec2 = self.normalizer.normalize("दस्तावेज़")
        self.assertIn("documents", rec1.search_query)
        self.assertIn("documents", rec2.search_query)

    def test_hinglish_queries(self):
        """Romanized Hindi queries expand with target scheme and intent."""
        h1 = "atal pension yojana ke liye documents"
        rec1 = self.normalizer.normalize(h1)
        self.assertIn("Atal Pension Yojana", rec1.search_query)

        h2 = "kisan samman nidhi ka benefit kya hai"
        rec2 = self.normalizer.normalize(h2)
        self.assertIn("PM-KISAN", rec2.search_query)

    def test_mixed_language_query(self):
        """Mixed English + Hindi query preserves both components."""
        mixed = "PM SVANidhi योजना में working capital loan कैसे मिलेगा"
        rec = self.normalizer.normalize(mixed)
        self.assertIn("SVANidhi", rec.search_query)
        self.assertIn("working capital", rec.search_query)


if __name__ == "__main__":
    unittest.main()
