"""
Unit tests for LLMRouter.
Verifies Gemini primary execution, operational fallback to OpenRouter,
strict prohibition of fallback on authentication/configuration errors,
and provider telemetry metadata recording.
"""

import unittest
from unittest.mock import MagicMock

from src.llm.config import LLMConfig
from src.llm.errors import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from src.llm.models import QueryIntent
from src.llm.providers import LLMProvider, MockLLMProvider
from src.llm.router import LLMRouter, ProviderExecutionResult


class DummyProvider(LLMProvider):
    def __init__(self, name: str, model: str):
        super().__init__(LLMConfig(provider=name, model=model))
        self._name = name
        self._model = model

    @property
    def provider_name(self) -> str:
        return self._name

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str, system_prompt=None, **kwargs) -> str:
        return f"Output from {self._name}"

    def generate_structured(self, prompt: str, schema_cls, system_prompt=None, **kwargs):
        mock = MockLLMProvider()
        return mock.generate_structured(prompt, schema_cls)


class TestLLMRouter(unittest.TestCase):

    def test_gemini_success_no_fallback(self):
        gemini = DummyProvider("gemini", "gemini-2.5-flash")
        openrouter = DummyProvider("openrouter", "google/gemini-2.5-flash")

        router = LLMRouter(
            config=LLMConfig(provider="auto"),
            gemini_provider=gemini,
            openrouter_provider=openrouter,
        )

        res = router.generate("Hello world")
        self.assertEqual(res.content, "Output from gemini")
        self.assertEqual(res.provider, "gemini")
        self.assertEqual(res.attempt, 1)
        self.assertFalse(res.fallback_used)
        self.assertIsNone(res.fallback_reason)

    def test_gemini_operational_failure_triggers_openrouter_fallback(self):
        gemini = DummyProvider("gemini", "gemini-2.5-flash")
        openrouter = DummyProvider("openrouter", "google/gemini-2.5-flash")

        # Mock Gemini to raise a transient timeout error
        gemini.generate = MagicMock(side_effect=ProviderTimeoutError("Gemini timed out after 30s"))

        router = LLMRouter(
            config=LLMConfig(provider="auto"),
            gemini_provider=gemini,
            openrouter_provider=openrouter,
        )

        res = router.generate("Hello world")
        self.assertEqual(res.content, "Output from openrouter")
        self.assertEqual(res.provider, "openrouter")
        self.assertEqual(res.attempt, 2)
        self.assertTrue(res.fallback_used)
        self.assertEqual(res.fallback_reason, "gemini_providertimeouterror")

    def test_gemini_rate_limit_triggers_openrouter_fallback(self):
        gemini = DummyProvider("gemini", "gemini-2.5-flash")
        openrouter = DummyProvider("openrouter", "google/gemini-2.5-flash")

        gemini.generate = MagicMock(side_effect=ProviderRateLimitError("Gemini 429 quota exceeded"))

        router = LLMRouter(
            config=LLMConfig(provider="auto"),
            gemini_provider=gemini,
            openrouter_provider=openrouter,
        )

        res = router.generate("Hello world")
        self.assertEqual(res.content, "Output from openrouter")
        self.assertTrue(res.fallback_used)
        self.assertEqual(res.fallback_reason, "gemini_providerratelimiterror")

    def test_gemini_auth_error_strictly_forbids_fallback(self):
        gemini = DummyProvider("gemini", "gemini-2.5-flash")
        openrouter = DummyProvider("openrouter", "google/gemini-2.5-flash")

        # Mock Gemini to raise an authentication error (HTTP 401/403)
        gemini.generate = MagicMock(side_effect=ProviderAuthenticationError("Invalid API key"))

        router = LLMRouter(
            config=LLMConfig(provider="auto"),
            gemini_provider=gemini,
            openrouter_provider=openrouter,
        )

        # MUST NOT fallback to OpenRouter! Must raise ProviderAuthenticationError immediately.
        with self.assertRaises(ProviderAuthenticationError):
            router.generate("Hello world")

    def test_gemini_config_error_strictly_forbids_fallback(self):
        gemini = DummyProvider("gemini", "gemini-2.5-flash")
        openrouter = DummyProvider("openrouter", "google/gemini-2.5-flash")

        # Mock Gemini to raise a configuration error (missing key)
        gemini.generate = MagicMock(side_effect=ProviderConfigurationError("GEMINI_API_KEY is not configured"))

        router = LLMRouter(
            config=LLMConfig(provider="auto"),
            gemini_provider=gemini,
            openrouter_provider=openrouter,
        )

        with self.assertRaises(ProviderConfigurationError):
            router.generate("Hello world")

    def test_raw_gemini_exception_with_auth_keyword_strictly_forbids_fallback(self):
        gemini = DummyProvider("gemini", "gemini-2.5-flash")
        openrouter = DummyProvider("openrouter", "google/gemini-2.5-flash")

        # Mock Gemini to raise an unclassified Exception with 401 Unauthorized
        gemini.generate = MagicMock(side_effect=Exception("API call failed: 401 UNAUTHENTICATED: Invalid API key provided"))

        router = LLMRouter(
            config=LLMConfig(provider="auto"),
            gemini_provider=gemini,
            openrouter_provider=openrouter,
        )

        with self.assertRaises(ProviderAuthenticationError):
            router.generate("Hello world")

    def test_structured_generation_with_fallback(self):
        gemini = DummyProvider("gemini", "gemini-2.5-flash")
        openrouter = DummyProvider("openrouter", "google/gemini-2.5-flash")

        gemini.generate_structured = MagicMock(side_effect=ProviderUnavailableError("Gemini 503 unavailable"))

        router = LLMRouter(
            config=LLMConfig(provider="auto"),
            gemini_provider=gemini,
            openrouter_provider=openrouter,
        )

        query = "Show me scholarship schemes for SC students in Gujarat"
        res = router.generate_structured(query, QueryIntent)
        self.assertIsInstance(res.content, QueryIntent)
        self.assertEqual(res.provider, "openrouter")
        self.assertTrue(res.fallback_used)
        self.assertEqual(res.fallback_reason, "gemini_providerunavailableerror")


if __name__ == "__main__":
    unittest.main()
