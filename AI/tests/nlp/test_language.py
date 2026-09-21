"""
Unit tests for multi-lingual language detection.
Tests English, Hindi Devanagari, Hinglish Romanized Hindi, and edge cases.
"""

import unittest
import sys
from pathlib import Path

_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from src.nlp.language import LanguageDetector


class TestLanguageDetector(unittest.TestCase):

    def setUp(self):
        self.detector = LanguageDetector()

    def test_english_detection(self):
        queries = [
            "Show me scholarship schemes for SC students in Gujarat",
            "How to apply for PM Kisan scheme online?",
            "What documents are required for passport application?",
            "Income limit for economically weaker section",
        ]
        for q in queries:
            res = self.detector.detect(q)
            self.assertEqual(res.language, "en", f"Failed for query: {q}")
            self.assertEqual(res.script, "Latin")
            self.assertGreater(res.confidence, 0.7)

    def test_hindi_devanagari_detection(self):
        queries = [
            "गुजरात में एससी छात्रों के लिए कौन सी छात्रवृत्ति है?",
            "मुझे किसान सम्मान निधि योजना के बारे में जानकारी चाहिए",
            "मेरी उम्र 23 साल है और मेरी पारिवारिक आय 4 लाख रुपये है",
            "आवेदन प्रक्रिया क्या है?",
        ]
        for q in queries:
            res = self.detector.detect(q)
            self.assertEqual(res.language, "hi", f"Failed for query: {q}")
            self.assertIn(res.script, ("Devanagari", "Mixed"))
            self.assertGreater(res.confidence, 0.7)

    def test_hinglish_detection(self):
        queries = [
            "mujhe Gujarat me SC students ke liye scholarship chahiye",
            "mere family ki income 4 lakh hai, kaunsi yojana milegi?",
            "meri age 23 hai aur main kisan hoon",
            "form kaise bhare online batao",
        ]
        for q in queries:
            res = self.detector.detect(q)
            self.assertEqual(res.language, "hinglish", f"Failed for query: {q}")
            self.assertEqual(res.script, "Latin")
            self.assertGreater(res.confidence, 0.6)

    def test_empty_and_whitespace(self):
        res_empty = self.detector.detect("")
        self.assertEqual(res_empty.language, "unknown")
        self.assertEqual(res_empty.confidence, 0.0)

        res_spaces = self.detector.detect("   \n\t  ")
        self.assertEqual(res_spaces.language, "unknown")


if __name__ == "__main__":
    unittest.main()
