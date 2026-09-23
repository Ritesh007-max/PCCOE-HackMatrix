"""
Live integration tests for API endpoints using live OpenRouter Provider.
Separated from the standard regression suite.
Automatically skips if OPENROUTER_API_KEY is not configured or is a placeholder.

Run explicitly with:
    python -m unittest tests/api/test_api_real_openrouter.py
"""

import os
import unittest
from unittest.mock import MagicMock
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()
if not os.getenv("OPENROUTER_API_KEY") and os.path.exists(".env.example"):
    load_dotenv(".env.example")

from src.api.app import app
from src.api.config import DEFAULT_SERVICE_CONFIG
from src.api.dependencies import get_hybrid_retriever
from src.rag.models import RetrievedChunk, SchemeRetrievalResult, SourceTier
from src.llm.errors import LLMError, ProviderRateLimitError, ProviderUnavailableError

_OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
_HAS_VALID_OPENROUTER_KEY = bool(_OPENROUTER_KEY and not _OPENROUTER_KEY.startswith("your_"))


@unittest.skipUnless(_HAS_VALID_OPENROUTER_KEY, "OPENROUTER_API_KEY not configured or is placeholder; skipping live API OpenRouter tests.")
class TestApiRealOpenRouter(unittest.TestCase):
    def setUp(self):
        # Mock retriever to isolate live test strictly to live LLM generation
        mock_retriever = MagicMock()
        mock_chunk = RetrievedChunk(
            chunk_id="chunk_real_01",
            content="PM Kisan Samman Nidhi provides Rs 6,000 per year to small and marginal farmers.",
            scheme_slug="pm-kisan",
            scheme_name="PM Kisan Samman Nidhi",
            source_tier=SourceTier.PRIMARY_SCHEME.value,
            dense_score=0.95,
            rerank_score=0.98,
            metadata={"source_url": "https://pmkisan.gov.in", "ministry": "Ministry of Agriculture", "state": "All-India"},
        )
        mock_scheme = SchemeRetrievalResult(
            scheme_slug="pm-kisan",
            scheme_name="PM Kisan Samman Nidhi",
            aggregate_score=0.98,
            best_matching_chunks=[mock_chunk],
            source_metadata={"source_url": "https://pmkisan.gov.in", "ministry": "Ministry of Agriculture", "state": "All-India"},
        )
        mock_retriever.retrieve.return_value = [mock_chunk]
        mock_retriever.retrieve_schemes.return_value = [mock_scheme]
        app.dependency_overrides[get_hybrid_retriever] = lambda: mock_retriever

        self.client = TestClient(app)
        self.headers = {"X-AI-Service-Key": DEFAULT_SERVICE_CONFIG.service_api_key}

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_live_chat_endpoint_openrouter(self):
        """Live /v1/chat grounded query execution against OpenRouter."""
        try:
            resp = self.client.post(
                "/v1/chat",
                headers=self.headers,
                json={"query": "Explain what benefits are offered under PM Kisan Samman Nidhi."}
            )
            if resp.status_code == 200:
                data = resp.json()
                self.assertIn("answer", data)
                self.assertTrue(len(data["answer"]) > 0)
                if data.get("provider_telemetry"):
                    self.assertIn(data["provider_telemetry"].get("provider"), ("openrouter", "gemini", "local_fallback"))
            elif resp.status_code == 429:
                self.skipTest("Live OpenRouter rate limit 429 received.")
            else:
                self.assertEqual(resp.status_code, 200)
        except (ProviderRateLimitError, ProviderUnavailableError, LLMError) as exc:
            self.skipTest(f"OpenRouter live network/quota exception: {exc}")


if __name__ == "__main__":
    unittest.main()
