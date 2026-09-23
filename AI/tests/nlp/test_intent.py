"""
Unit tests for multi-lingual intent classification.
Tests scheme discovery, application process, document requirements,
eligibility questions, benefit questions, and ambiguous text.
"""

import unittest
import sys
from pathlib import Path

_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from src.nlp.intent import IntentClassifier
from src.llm.models import UserIntent


class TestIntentClassifier(unittest.TestCase):

    def setUp(self):
        self.classifier = IntentClassifier()

    def test_document_requirements_intents(self):
        queries = [
            "documents required for OBC scholarship",
            "kya documents lagenge is yojana ke liye?",
            "छात्रवृत्ति के लिए कौन से दस्तावेज़ चाहिए?",
            "certificates needed for domicile verification",
        ]
        for q in queries:
            primary, _, conf = self.classifier.classify_intent(q)
            self.assertEqual(primary, UserIntent.DOCUMENT_REQUIREMENTS, f"Failed for: {q}")
            self.assertGreater(conf, 0.8)

    def test_application_process_intents(self):
        queries = [
            "how to apply for PM Kisan scheme online",
            "form kaise bhare online portal par",
            "आवेदन कैसे करें इस योजना में?",
            "registration steps for scholarship",
        ]
        for q in queries:
            primary, _, conf = self.classifier.classify_intent(q)
            self.assertEqual(primary, UserIntent.APPLICATION_PROCESS, f"Failed for: {q}")
            self.assertGreater(conf, 0.8)

    def test_benefit_question_intents(self):
        queries = [
            "how much benefit amount will I get?",
            "kitna paisa milega is scheme me?",
            "आवास योजना में कितना पैसा मिलेगा?",
            "financial assistance details and subsidy percentage",
        ]
        for q in queries:
            primary, _, conf = self.classifier.classify_intent(q)
            self.assertEqual(primary, UserIntent.BENEFIT_QUESTION, f"Failed for: {q}")
            self.assertGreater(conf, 0.8)

    def test_eligibility_question_intents(self):
        queries = [
            "am I eligible for this scholarship?",
            "kya main eligible hoon is yojana ke liye?",
            "क्या मैं इस योजना के लिए पात्र हूँ?",
            "eligibility criteria for minority students",
        ]
        for q in queries:
            primary, _, conf = self.classifier.classify_intent(q)
            self.assertEqual(primary, UserIntent.ELIGIBILITY_QUESTION, f"Failed for: {q}")
            self.assertGreater(conf, 0.8)

    def test_scheme_discovery_intents(self):
        queries = [
            "show me scholarship schemes for SC students in Gujarat",
            "mujhe Gujarat me SC students ke liye scholarship chahiye",
            "गुजरात में एससी छात्रों के लिए कौन सी छात्रवृत्ति है?",
            "mere family ki income 4 lakh hai, kaunsi yojana milegi?",
        ]
        for q in queries:
            primary, _, conf = self.classifier.classify_intent(q)
            self.assertEqual(primary, UserIntent.SCHEME_DISCOVERY, f"Failed for: {q}")
            self.assertGreater(conf, 0.8)

    def test_unknown_and_empty(self):
        primary, _, conf = self.classifier.classify_intent("")
        self.assertEqual(primary, UserIntent.UNKNOWN)
        self.assertEqual(conf, 0.0)

        primary, _, conf = self.classifier.classify_intent("hello there")
        self.assertEqual(primary, UserIntent.UNKNOWN)


if __name__ == "__main__":
    unittest.main()
