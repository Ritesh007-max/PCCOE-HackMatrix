"""
Live integration tests for OpenRouterProvider using OpenRouter API.
Automatically skips if OPENROUTER_API_KEY is not configured or is a placeholder.
Run explicitly with:
    python -m unittest tests/llm/test_openrouter_real.py
"""

import os
import unittest
from unittest.mock import MagicMock
from dotenv import load_dotenv

# Ensure env vars are loaded from .env or .env.example
load_dotenv()
if not os.getenv("OPENROUTER_API_KEY") and os.path.exists(".env.example"):
    load_dotenv(".env.example")

from src.llm.config import LLMConfig
from src.llm.providers import OpenRouterProvider, GeminiProvider
from src.llm.router import LLMRouter
from src.llm.models import QueryIntent
from src.llm.errors import (
    ProviderTimeoutError,
    ProviderRateLimitError,
    ProviderAuthenticationError,
    ProviderStructuredOutputError,
    LLMError,
)

_OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
_HAS_VALID_OPENROUTER_KEY = bool(_OPENROUTER_KEY and not _OPENROUTER_KEY.startswith("your_"))


@unittest.skipUnless(_HAS_VALID_OPENROUTER_KEY, "OPENROUTER_API_KEY not configured or is placeholder; skipping live OpenRouter test.")
class TestOpenRouterRealIntegration(unittest.TestCase):

    def setUp(self):
        self.config = LLMConfig.from_env()
        self.config.provider = "openrouter"
        self.provider = OpenRouterProvider(self.config)

    def test_live_text_generation(self):
        prompt = "Respond with exactly one word: 'CONNECTED'."
        try:
            response = self.provider.generate(prompt)
            self.assertIsNotNone(response)
            self.assertIn("CONNECTED", response.upper())
        except (ProviderRateLimitError, ProviderAuthenticationError, LLMError) as exc:
            self.skipTest(f"OpenRouter credentials or credits unavailable: {exc}")

    def test_live_structured_query_intent(self):
        prompt = "User asks: 'What is the maximum subsidy under PM Awas Yojana?'"
        try:
            res = self.provider.generate_structured(prompt, QueryIntent)
            self.assertIsInstance(res, QueryIntent)
            self.assertIsNotNone(res.intent)
        except (ProviderRateLimitError, ProviderAuthenticationError, ProviderStructuredOutputError, LLMError) as exc:
            self.skipTest(f"OpenRouter credentials, credits, or output unavailable: {exc}")

    def test_live_router_fallback_to_openrouter(self):
        # Create router with real OpenRouter provider and simulated failing Gemini provider
        router_config = LLMConfig.from_env()
        router_config.provider = "auto"

        mock_gemini = GeminiProvider(router_config)
        mock_gemini.generate = MagicMock(side_effect=ProviderTimeoutError("Gemini simulated 30s timeout"))

        router = LLMRouter(
            config=router_config,
            gemini_provider=mock_gemini,
            openrouter_provider=self.provider,
        )

        try:
            result = router.generate("Respond with exactly one word: 'FALLBACK_OK'.")
            self.assertEqual(result.provider, "openrouter")
            self.assertTrue(result.fallback_used)
            self.assertEqual(result.attempt, 2)
            self.assertIn("FALLBACK_OK", result.content.upper())
        except (ProviderRateLimitError, ProviderAuthenticationError) as exc:
            self.skipTest(f"OpenRouter credentials or credits unavailable: {exc}")


if __name__ == "__main__":
    unittest.main()
