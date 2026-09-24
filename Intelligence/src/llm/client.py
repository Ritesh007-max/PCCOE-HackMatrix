"""
FIN LLM Client Coordinator.
Provides unified facade for LLM calls with safe auditing, latency telemetry,
input truncation checks, provider routing, and fallback tracking.
"""

import time
import uuid
from typing import Any, Dict, Optional, Tuple, Type, TypeVar
import sys
from pathlib import Path

_CUR = Path(__file__).resolve()
while _CUR.name != "Intelligence" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_INTELLIGENCE_DIR = _CUR
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

try:
    from .config import LLMConfig, DEFAULT_LLM_CONFIG
    from .models import LLMMetadata
    from .providers import LLMProvider, get_llm_provider
    from .router import LLMRouter, ProviderExecutionResult
    from .errors import LLMError, ProviderUnavailableError
except (ImportError, ValueError):
    from src.llm.config import LLMConfig, DEFAULT_LLM_CONFIG
    from src.llm.models import LLMMetadata
    from src.llm.providers import LLMProvider, get_llm_provider
    from src.llm.router import LLMRouter, ProviderExecutionResult
    from src.llm.errors import LLMError, ProviderUnavailableError

T = TypeVar("T")


class LLMClient:
    """Production coordinator for LLM operations."""

    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        provider: Optional[LLMProvider] = None,
        router: Optional[LLMRouter] = None,
    ):
        self.config = config or LLMConfig.from_env()
        self.router = router or LLMRouter(self.config)
        self.provider = provider  # Optional override
        self.last_telemetry: Optional[Dict[str, Any]] = None

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        operation: str = "text_generation",
        request_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """Executes raw generation and returns text string."""
        exec_res = self.generate_with_metadata(
            prompt, system_prompt=system_prompt, operation=operation, request_id=request_id, **kwargs
        )
        return exec_res.content

    def generate_with_metadata(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        operation: str = "text_generation",
        request_id: Optional[str] = None,
        **kwargs
    ) -> ProviderExecutionResult[str]:
        """Executes raw generation and returns content + provider telemetry."""
        self._validate_input_length(prompt)

        if self.provider is not None:
            # Direct provider bypass (e.g. testing specific mock)
            start = time.perf_counter()
            res = self.provider.generate(prompt, system_prompt=system_prompt, **kwargs)
            lat = (time.perf_counter() - start) * 1000.0
            exec_res = ProviderExecutionResult(
                content=res,
                provider=self.provider.provider_name,
                model=self.provider.model_name,
                status="success",
                attempt=1,
                latency_ms=lat,
                fallback_used=False,
            )
        else:
            exec_res = self.router.generate(prompt, system_prompt=system_prompt, **kwargs)

        self.last_telemetry = exec_res.to_metadata_dict()
        return exec_res

    def generate_structured(
        self,
        prompt: str,
        schema_cls: Type[T],
        system_prompt: Optional[str] = None,
        operation: str = "structured_generation",
        request_id: Optional[str] = None,
        **kwargs
    ) -> T:
        """Executes structured generation and schema validation, returning instantiated schema."""
        exec_res = self.generate_structured_with_metadata(
            prompt, schema_cls=schema_cls, system_prompt=system_prompt, operation=operation, request_id=request_id, **kwargs
        )
        return exec_res.content

    def generate_structured_with_metadata(
        self,
        prompt: str,
        schema_cls: Type[T],
        system_prompt: Optional[str] = None,
        operation: str = "structured_generation",
        request_id: Optional[str] = None,
        **kwargs
    ) -> ProviderExecutionResult[T]:
        """Executes structured generation and returns instantiated schema + provider telemetry."""
        self._validate_input_length(prompt)

        if self.provider is not None:
            start = time.perf_counter()
            res = self.provider.generate_structured(prompt, schema_cls=schema_cls, system_prompt=system_prompt, **kwargs)
            lat = (time.perf_counter() - start) * 1000.0
            exec_res = ProviderExecutionResult(
                content=res,
                provider=self.provider.provider_name,
                model=self.provider.model_name,
                status="success",
                attempt=1,
                latency_ms=lat,
                fallback_used=False,
            )
        else:
            exec_res = self.router.generate_structured(prompt, schema_cls=schema_cls, system_prompt=system_prompt, **kwargs)

        self.last_telemetry = exec_res.to_metadata_dict()
        return exec_res

    def _validate_input_length(self, text: str) -> None:
        if len(text) > self.config.max_input_chars:
            raise LLMError(
                f"Input text exceeds safety length threshold: {len(text)} > {self.config.max_input_chars}"
            )