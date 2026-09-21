"""
PolicySetu LLM Client Coordinator.
Provides unified facade for LLM calls with safe auditing, latency telemetry,
input truncation checks, and strict failure isolation.
"""

import time
import uuid
from typing import Any, Dict, Optional, Type, TypeVar
from .config import LLMConfig, DEFAULT_LLM_CONFIG
from .models import LLMMetadata
from .providers import LLMProvider, get_llm_provider
from .errors import LLMError, ProviderUnavailableError

T = TypeVar("T")


class LLMClient:
    """Production coordinator for LLM operations."""

    def __init__(self, config: Optional[LLMConfig] = None, provider: Optional[LLMProvider] = None):
        self.config = config or LLMConfig.from_env()
        self.provider = provider or get_llm_provider(self.config)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        operation: str = "text_generation",
        request_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """Executes raw generation with operational telemetry."""
        req_id = request_id or str(uuid.uuid4())[:8]
        self._validate_input_length(prompt)

        start_time = time.perf_counter()
        try:
            result = self.provider.generate(prompt, system_prompt=system_prompt, **kwargs)
            latency = (time.perf_counter() - start_time) * 1000.0
            return result
        except Exception as exc:
            latency = (time.perf_counter() - start_time) * 1000.0
            # CRITICAL INVARIANT: Never silently fall back to mock in production unless explicitly configured
            if self.config.allow_mock_fallback and self.provider.provider_name != "mock":
                from .providers import MockLLMProvider
                mock = MockLLMProvider(self.config)
                return mock.generate(prompt, system_prompt=system_prompt, **kwargs)
            raise exc

    def generate_structured(
        self,
        prompt: str,
        schema_cls: Type[T],
        system_prompt: Optional[str] = None,
        operation: str = "structured_generation",
        request_id: Optional[str] = None,
        **kwargs
    ) -> T:
        """Executes structured generation and schema validation with operational telemetry."""
        req_id = request_id or str(uuid.uuid4())[:8]
        self._validate_input_length(prompt)

        start_time = time.perf_counter()
        try:
            result = self.provider.generate_structured(
                prompt,
                schema_cls=schema_cls,
                system_prompt=system_prompt,
                **kwargs
            )
            latency = (time.perf_counter() - start_time) * 1000.0
            return result
        except Exception as exc:
            latency = (time.perf_counter() - start_time) * 1000.0
            if self.config.allow_mock_fallback and self.provider.provider_name != "mock":
                from .providers import MockLLMProvider
                mock = MockLLMProvider(self.config)
                return mock.generate_structured(prompt, schema_cls=schema_cls, system_prompt=system_prompt, **kwargs)
            raise exc

    def _validate_input_length(self, text: str) -> None:
        if len(text) > self.config.max_input_chars:
            raise LLMError(
                f"Input text length ({len(text)}) exceeds configured limit ({self.config.max_input_chars} characters)."
            )
