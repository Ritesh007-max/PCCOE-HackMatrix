"""
Unit tests for query parser and entity extraction.
Enforces the critical invariant: Query entities are retrieval hints ONLY,
not automatically applicant facts.
"""

import unittest
import sys
from pathlib import Path

_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from src.nlp.query_parser import QueryParser


class TestQueryParser(unittest.TestCase):

    def test_search_hints_extraction_english(self):
        query = "show me scholarship schemes for SC students in Gujarat"
        hints = QueryParser.extract_search_hints(query)
        self.assertEqual(hints["state"], "Gujarat")
        self.assertEqual(hints["social_category"], "SC")
        self.assertEqual(hints["beneficiary_type"], "student")
        self.assertEqual(hints["policy_domain"], "Education & Learning")
        self.assertIn("scholarship", hints["keywords"])

    def test_search_hints_extraction_hindi(self):
        query = "गुजरात में एससी छात्रों के लिए कौन सी छात्रवृत्ति है?"
        hints = QueryParser.extract_search_hints(query)
        self.assertEqual(hints["state"], "Gujarat")
        self.assertEqual(hints["social_category"], "SC")
        self.assertEqual(hints["beneficiary_type"], "student")

    def test_self_declaration_vs_search_query(self):
        # Third-person search queries: MUST NOT be self declarations
        search_queries = [
            "show me scholarship schemes for SC students in Gujarat",
            "what schemes are available for farmers in Maharashtra?",
            "schemes for disabled women in Uttar Pradesh",
        ]
        for q in search_queries:
            self.assertFalse(
                QueryParser.is_self_declaration(q),
                f"Query wrongly identified as self-declaration: {q}"
            )

        # First-person citizen statements: MUST be self declarations
        self_declarations = [
            "I am a farmer from Gujarat and my income is 3 lakh",
            "meri age 23 hai aur main student hoon",
            "मेरी उम्र 24 साल है और मैं महाराष्ट्र में रहता हूँ",
            "My family income is 4 lakh",
        ]
        for q in self_declarations:
            self.assertTrue(
                QueryParser.is_self_declaration(q),
                f"Self-declaration failed to be identified: {q}"
            )


if __name__ == "__main__":
    unittest.main()
