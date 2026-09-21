"""
Tests for PolicySetu Query Normalization & Metadata Filtering (AI/src/rag/filters.py).
Validates language detection, entity extraction, and metadata filter predicates.
"""

import sys
from pathlib import Path

_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

import unittest
from src.rag.filters import detect_language, normalize_query_intent, build_metadata_filter
from src.rag.models import RetrievalQuery


class TestRAGFilters(unittest.TestCase):
    """Test suite for query analysis and metadata filtering."""

    def test_detect_language_english(self):
        """Standard English query should detect 'en'."""
        self.assertEqual(detect_language("financial assistance for girl students"), "en")

    def test_detect_language_hindi(self):
        """Pure Devanagari query should detect 'hi'."""
        self.assertEqual(detect_language("अटल पेंशन योजना के तहत लाभ"), "hi")

    def test_detect_language_hinglish(self):
        """Code-mixed queries or queries with Hinglish markers should detect 'hi-en'."""
        self.assertEqual(detect_language("kisan yojana ke liye apply kaise karen"), "hi-en")
        self.assertEqual(detect_language("pension scheme chahiye mujhe"), "hi-en")

    def test_normalize_query_intent_state(self):
        """Detects state mentions and aliases."""
        intent = normalize_query_intent("housing subsidy scheme in UP")
        self.assertEqual(intent.detected_state, "Uttar Pradesh")

        intent2 = normalize_query_intent("scholarship in Gujarat for students")
        self.assertEqual(intent2.detected_state, "Gujarat")

    def test_normalize_query_intent_category(self):
        """Detects caste/social categories."""
        intent = normalize_query_intent("pre-matric scholarship for SC students")
        self.assertEqual(intent.detected_category, "SC")

        intent2 = normalize_query_intent("coaching scheme for OBC youth")
        self.assertEqual(intent2.detected_category, "OBC")

    def test_normalize_query_intent_beneficiary(self):
        """Detects beneficiary types."""
        intent = normalize_query_intent("credit card subsidy for kisan")
        self.assertEqual(intent.detected_beneficiary_type, "Farmer")

        intent2 = normalize_query_intent("micro loans for street vendors")
        self.assertEqual(intent2.detected_beneficiary_type, "Street Vendors")

    def test_normalize_query_intent_terms(self):
        """Extracts policy domain terms."""
        intent = normalize_query_intent("apply for education loan and monthly scholarship")
        self.assertIn("loan", intent.intent_terms)
        self.assertIn("scholarship", intent.intent_terms)

    def test_build_metadata_filter_none(self):
        """Returns None if query specifies no filters."""
        q = RetrievalQuery(query_text="general query")
        self.assertIsNone(build_metadata_filter(q))

    def test_build_metadata_filter_state(self):
        """Filter matches state-specific and central/all-india records."""
        q = RetrievalQuery(query_text="assam grant", state_filter="Assam")
        filt = build_metadata_filter(q)
        self.assertIsNotNone(filt)
        assert filt is not None

        # Matching state
        self.assertTrue(filt({"state": "Assam"}))
        # Case insensitive
        self.assertTrue(filt({"state": "assam"}))
        # Central schemes apply to all states
        self.assertTrue(filt({"state": "All India"}))
        self.assertTrue(filt({"state": "Central"}))
        self.assertTrue(filt({"state": None}))
        # Different state should fail
        self.assertFalse(filt({"state": "Bihar"}))

    def test_build_metadata_filter_content_type(self):
        """Filter matches exact content type."""
        q = RetrievalQuery(query_text="faq only", content_type_filter="faq")
        filt = build_metadata_filter(q)
        self.assertIsNotNone(filt)
        assert filt is not None
        self.assertTrue(filt({"content_type": "faq"}))
        self.assertFalse(filt({"content_type": "scheme_overview"}))


if __name__ == "__main__":
    unittest.main()
