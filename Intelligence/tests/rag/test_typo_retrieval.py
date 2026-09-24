"""
Tests for FIN Typo & Phonetic Retrieval Robustness (Intelligence/src/rag/scheme_name_index.py).
Validates severe phonetic typos, spelling variations, unseen scheme typos,
case insensitivity, and punctuation resilience.
"""

import sys
from pathlib import Path
import unittest

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.rag.scheme_name_index import SchemeNameIndex


class TestTypoRetrievalRobustness(unittest.TestCase):
    """Test suite for typo and phonetic robustness without overfitting."""

    def setUp(self):
        self.index = SchemeNameIndex()

    def test_severe_phonetic_typos_apy(self):
        """Regression tests for specific Atal Pension Yojana phonetic typos."""
        cases = [
            "Atle Penshan Yojna",
            "Atal Penson Yojna",
            "Atal Pension Yojna",
            "atal penshan",
            "Atall Penshion Yojna",
        ]
        for query in cases:
            res = self.index.match(query)
            self.assertIsNotNone(res, f"Failed to match typo query: '{query}'")
            self.assertEqual(res.scheme_slug, "apy", f"Expected 'apy' for '{query}', got '{res.scheme_slug}'")
            self.assertGreaterEqual(res.confidence, 0.70)

    def test_unseen_scheme_typo_generalization(self):
        """Unseen typo variants across other schemes must resolve correctly (Part 15)."""
        unseen_cases = [
            ("Pradan Mantri Kisaan Saman Nidi", "pm-kisan"),
            ("Aayushman Bharath PMJAI", "ab-pmjay"),
            ("Pradhan Mantri Mathru Vandhana", "pmmvy"),
            ("PM Savnidhi street vendor", "pm-svanidhi"),
        ]
        for query, expected_slug in unseen_cases:
            res = self.index.match(query)
            self.assertIsNotNone(res, f"Failed unseen generalization query: '{query}'")
            self.assertEqual(
                res.scheme_slug.replace("_", "-"),
                expected_slug.replace("_", "-"),
                f"Mismatch for '{query}': expected '{expected_slug}', got '{res.scheme_slug}'"
            )

    def test_punctuation_and_whitespace_invariance(self):
        """Extra whitespace, punctuation, and mixed casing must not alter matching."""
        variants = [
            "   ATAL   PENSION   YOJANA...  ",
            "atal-pension-yojana!!!",
            "AtAl   pEnShAn   YoJnA???",
        ]
        for q in variants:
            res = self.index.match(q)
            self.assertIsNotNone(res)
            self.assertEqual(res.scheme_slug, "apy")

    def test_low_confidence_ambiguity_preservation(self):
        """Ambiguous queries below threshold must return None or preserve candidate freedom."""
        res = self.index.match("some random unknown scheme name that doesn't exist")
        self.assertIsNone(res)


if __name__ == "__main__":
    unittest.main()
