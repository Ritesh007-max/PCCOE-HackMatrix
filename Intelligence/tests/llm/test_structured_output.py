"""
Unit tests for structured output parsing and schema validation.
"""

import unittest
import sys
from pathlib import Path

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.llm.structured_output import (
    clean_json_text,
    parse_structured_json,
    validate_and_instantiate,
)
from src.llm.models import QueryIntent, UserIntent
from src.llm.errors import MalformedOutputError, SchemaValidationError


class TestStructuredOutput(unittest.TestCase):

    def test_clean_json_markdown_blocks(self):
        text_with_fence = "```json\n{\"intent\": \"SCHEME_DISCOVERY\", \"state\": \"Gujarat\"}\n```"
        cleaned = clean_json_text(text_with_fence)
        self.assertEqual(cleaned, '{"intent": "SCHEME_DISCOVERY", "state": "Gujarat"}')

    def test_clean_json_conversational_prefix(self):
        text_with_prefix = "Sure! Here is the JSON you requested:\n{\"intent\": \"SCHEME_DISCOVERY\"}\nHope this helps!"
        cleaned = clean_json_text(text_with_prefix)
        self.assertEqual(cleaned, '{"intent": "SCHEME_DISCOVERY"}')

    def test_clean_trailing_comma(self):
        text_with_trailing = '{"intent": "SCHEME_DISCOVERY", "keywords": ["sc", "gujarat",],}'
        data = parse_structured_json(text_with_trailing)
        self.assertEqual(data["intent"], "SCHEME_DISCOVERY")
        self.assertEqual(len(data["keywords"]), 2)

    def test_malformed_json_raises_error(self):
        invalid_text = "This is definitely not JSON at all."
        with self.assertRaises(MalformedOutputError):
            parse_structured_json(invalid_text)

    def test_schema_validation_success(self):
        data = {
            "original_query": "schemes in Gujarat",
            "normalized_query": "schemes in gujarat",
            "language": "en",
            "intent": "SCHEME_DISCOVERY",
            "state": "Gujarat",
            "confidence": 0.95,
        }
        inst = validate_and_instantiate(data, QueryIntent)
        self.assertEqual(inst.intent, UserIntent.SCHEME_DISCOVERY)
        self.assertEqual(inst.state, "Gujarat")


if __name__ == "__main__":
    unittest.main()
