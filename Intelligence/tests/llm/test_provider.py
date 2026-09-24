"""
Unit tests for LLM provider abstraction.
Enforces the critical invariant: Production provider failure MUST NOT silently fall back to Mock.
"""

import unittest
import sys
from pathlib import Path

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.llm.config import LLMConfig
from src.llm.providers import MockLLMProvider, OpenAICompatibleProvider, get_llm_provider
from src.llm.errors import ProviderUnavailableError
from src.llm.models import QueryIntent, FactExtractionResult, GroundedExplanation
from src.llm.client import LLMClient


class TestLLMProviders(unittest.TestCase):

    def test_mock_provider_offline_generation(self):
        config = LLMConfig(provider="mock")
        provider = MockLLMProvider(config)
        self.assertTrue(provider.is_available())
        self.assertEqual(provider.provider_name, "mock")

        # Structured query intent
        query = "Show me scholarship schemes for SC students in Gujarat"
        intent = provider.generate_structured(query, QueryIntent)
        self.assertEqual(intent.intent.value, "SCHEME_DISCOVERY")
        self.assertEqual(intent.state, "Gujarat")

        # Structured fact extraction
        text = "My family income is 4.2 lakh and age is 23"
        facts = provider.generate_structured(text, FactExtractionResult)
        self.assertGreaterEqual(len(facts.facts), 2)

    def test_production_provider_no_silent_fallback(self):
        # Configure OpenAI with missing credentials and allow_mock_fallback = False
        config = LLMConfig(
            provider="openai",
            api_key=None,
            api_base="https://invalid.openai.endpoint.local",
            allow_mock_fallback=False
        )
        provider = OpenAICompatibleProvider(config)
        self.assertFalse(provider.is_available())

        # Calling generate on unavailable provider must raise ProviderUnavailableError
        with self.assertRaises(ProviderUnavailableError):
            provider.generate("Hello world")

        # Coordinator client with allow_mock_fallback=False must also propagate error
        client = LLMClient(config=config, provider=provider)
        with self.assertRaises(ProviderUnavailableError):
            client.generate("Hello world")

    def test_provider_factory(self):
        mock_prov = get_llm_provider(LLMConfig(provider="mock"))
        self.assertIsInstance(mock_prov, MockLLMProvider)

        openai_prov = get_llm_provider(LLMConfig(provider="openai"))
        self.assertIsInstance(openai_prov, OpenAICompatibleProvider)

        with self.assertRaises(ValueError):
            get_llm_provider(LLMConfig(provider="unsupported_provider"))


if __name__ == "__main__":
    unittest.main()
