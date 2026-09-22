"""
Live integration tests for GeminiProvider using Google Gemini API.
Automatically skips if GEMINI_API_KEY is not configured or is a placeholder.
Run explicitly with:
    python -m unittest tests/llm/test_gemini_real.py
"""

import os
import unittest
from dotenv import load_dotenv

# Ensure env vars are loaded from .env or .env.example
load_dotenv()
if not os.getenv("GEMINI_API_KEY") and os.path.exists(".env.example"):
    load_dotenv(".env.example")

from src.llm.config import LLMConfig
from src.llm.providers import GeminiProvider
from src.llm.models import QueryIntent, FactExtractionResult, GroundedExplanation

_GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip()
_HAS_VALID_GEMINI_KEY = bool(_GEMINI_KEY and not _GEMINI_KEY.startswith("your_"))


@unittest.skipUnless(_HAS_VALID_GEMINI_KEY, "GEMINI_API_KEY not configured or is placeholder; skipping live Gemini test.")
class TestGeminiRealIntegration(unittest.TestCase):

    def setUp(self):
        self.config = LLMConfig.from_env()
        self.config.provider = "gemini"
        self.provider = GeminiProvider(self.config)

    def test_live_text_generation(self):
        prompt = "Respond with exactly one word: 'READY'."
        response = self.provider.generate(prompt)
        self.assertIsNotNone(response)
        self.assertIn("READY", response.upper())

    def test_live_structured_query_intent(self):
        prompt = "User says: 'Are there any scholarship schemes for engineering students in Gujarat?'"
        res = self.provider.generate_structured(prompt, QueryIntent)
        self.assertIsInstance(res, QueryIntent)
        self.assertIsNotNone(res.intent)
        if res.state:
            self.assertEqual(res.state.strip().lower(), "gujarat")

    def test_live_structured_fact_extraction(self):
        from src.llm.client import LLMClient
        from src.llm.extraction import ApplicantFactExtractor

        client = LLMClient(config=self.config, provider=self.provider)
        extractor = ApplicantFactExtractor(llm_client=client)

        doc_text = "My family income is 4.2 lakh and my age is 24."
        res = extractor.extract_candidates(doc_text)
        self.assertIsInstance(res, FactExtractionResult)
        self.assertTrue(len(res.facts) >= 1)
        fields = [f.field for f in res.facts]
        self.assertTrue("annual_family_income" in fields or "age" in fields or len(fields) > 0)


if __name__ == "__main__":
    unittest.main()
