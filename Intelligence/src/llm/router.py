"""
FIN LLM Provider Router.
Orchestrates Gemini (Primary) -> OpenRouter (Fallback) provider execution.
Enforces strict fallback rules:
  1. Fallback ONLY for transient operational errors (network, timeout, 429, 5xx, outage, unparseable output).
  2. Authentication & configuration errors (HTTP 401, 403, missing credentials) MUST NOT trigger fallback.
  3. Deterministic decision outcomes (PASS/FAIL/UNKNOWN/REVIEW) MUST NEVER trigger fallback.
  4. Telemetry records provider, model, attempt, latency, fallback_used, and fallback_reason.
"""

from dataclasses import dataclass
import logging
import os
import time
from typing import Any, Dict, Generic, Optional, Tuple, Type, TypeVar
import sys
from pathlib import Path

_CUR = Path(__file__).resolve()
while _CUR.name != "Intelligence" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_INTELLIGENCE_DIR = _CUR
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

try:
    from .config import LLMConfig
    from .errors import (
        LLMError,
        ProviderAuthenticationError,
        ProviderConfigurationError,
        ProviderInvalidResponseError,
        ProviderNetworkError,
        ProviderRateLimitError,
        ProviderStructuredOutputError,
        ProviderTimeoutError,
        ProviderUnavailableError,
    )
    from .providers import (
        GeminiProvider,
        LLMProvider,
        MockLLMProvider,
        OpenRouterProvider,
    )
except (ImportError, ValueError):
    from src.llm.config import LLMConfig
    from src.llm.errors import (
        LLMError,
        ProviderAuthenticationError,
        ProviderConfigurationError,
        ProviderInvalidResponseError,
        ProviderNetworkError,
        ProviderRateLimitError,
        ProviderStructuredOutputError,
        ProviderTimeoutError,
        ProviderUnavailableError,
    )
    from src.llm.providers import (
        GeminiProvider,
        LLMProvider,
        MockLLMProvider,
        OpenRouterProvider,
    )

logger = logging.getLogger("fin.llm.router")
T = TypeVar("T")


# The explicit operational error categories that permit fallback
OPERATIONAL_FALLBACK_ERRORS = (
    ProviderTimeoutError,
    ProviderRateLimitError,
    ProviderUnavailableError,
    ProviderNetworkError,
    ProviderInvalidResponseError,
    ProviderStructuredOutputError,
)


@dataclass
class ProviderExecutionResult(Generic[T]):
    """Encapsulates execution result with operational telemetry."""
    content: T
    provider: str
    model: str
    status: str
    attempt: int
    latency_ms: float
    fallback_used: bool
    fallback_reason: Optional[str] = None

    def to_metadata_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "status": self.status,
            "attempt": self.attempt,
            "latency_ms": round(self.latency_ms, 2),
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
        }


class LLMRouter:
    """
    Central provider router.
    Attempts Gemini PRIMARY first; falls back to OpenRouter only on eligible operational errors.
    """

    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        gemini_provider: Optional[LLMProvider] = None,
        openrouter_provider: Optional[LLMProvider] = None,
        mock_provider: Optional[LLMProvider] = None,
    ):
        self.config = config or LLMConfig.from_env()
        self.gemini_provider = gemini_provider or GeminiProvider(self.config)
        self.openrouter_provider = openrouter_provider or OpenRouterProvider(self.config)
        self.mock_provider = mock_provider or MockLLMProvider(self.config)

    @property
    def active_mode(self) -> str:
        return self.config.provider.strip().lower()

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> ProviderExecutionResult[str]:
        """Executes text generation through the configured provider routing topology."""
        return self._execute_routed(
            call_fn=lambda prov: prov.generate(prompt, system_prompt=system_prompt, **kwargs)
        )

    def generate_structured(
        self,
        prompt: str,
        schema_cls: Type[T],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> ProviderExecutionResult[T]:
        """Executes structured JSON generation through the configured provider routing topology."""
        return self._execute_routed(
            call_fn=lambda prov: prov.generate_structured(
                prompt, schema_cls=schema_cls, system_prompt=system_prompt, **kwargs
            )
        )

    def _execute_routed(self, call_fn) -> ProviderExecutionResult[Any]:
        mode = self.active_mode

        # 1. Mock Mode (100% offline deterministic testing)
        if mode == "mock":
            if os.getenv("AI_ENV", "").strip().lower() == "production":
                raise ProviderConfigurationError("Mock LLM provider is strictly prohibited in production.")
            start = time.perf_counter()
            res = call_fn(self.mock_provider)
            lat = (time.perf_counter() - start) * 1000.0
            return ProviderExecutionResult(
                content=res,
                provider="mock",
                model=self.mock_provider.model_name,
                status="success",
                attempt=1,
                latency_ms=lat,
                fallback_used=False,
            )

        # 2. Explicit Gemini-Only Mode (no fallback)
        if mode in ("gemini_only", "gemini-only"):
            start = time.perf_counter()
            res = call_fn(self.gemini_provider)
            lat = (time.perf_counter() - start) * 1000.0
            return ProviderExecutionResult(
                content=res,
                provider="gemini",
                model=self.gemini_provider.model_name,
                status="success",
                attempt=1,
                latency_ms=lat,
                fallback_used=False,
            )

        # 3. Explicit OpenRouter-Only Mode (no fallback)
        if mode == "openrouter":
            start = time.perf_counter()
            res = call_fn(self.openrouter_provider)
            lat = (time.perf_counter() - start) * 1000.0
            return ProviderExecutionResult(
                content=res,
                provider="openrouter",
                model=self.openrouter_provider.model_name,
                status="success",
                attempt=1,
                latency_ms=lat,
                fallback_used=False,
            )

        # 4. Default 'auto' Mode: Gemini PRIMARY -> OpenRouter FALLBACK
        start_gemini = time.perf_counter()
        try:
            res = call_fn(self.gemini_provider)
            lat = (time.perf_counter() - start_gemini) * 1000.0
            return ProviderExecutionResult(
                content=res,
                provider="gemini",
                model=self.gemini_provider.model_name,
                status="success",
                attempt=1,
                latency_ms=lat,
                fallback_used=False,
            )
        except (ProviderAuthenticationError, ProviderConfigurationError) as auth_err:
            # CRITICAL INVARIANT: Authentication/config errors MUST NOT trigger fallback
            logger.error("Gemini authentication/configuration failure; fallback strictly prohibited: %s", auth_err)
            raise auth_err
        except Exception as gemini_err:
            lat_gemini = (time.perf_counter() - start_gemini) * 1000.0
            err_str = str(gemini_err).lower()

            # Defense-in-depth: Check for authentication / configuration failures
            if any(w in err_str for w in ("api_key", "api key", "unauthenticated", "401", "403", "forbidden", "unauthorized", "permission_denied")):
                logger.error("Gemini authentication/configuration failure detected in router; fallback strictly prohibited: %s", gemini_err)
                raise ProviderAuthenticationError(f"Gemini authentication failure: {gemini_err}") from gemini_err

            # Check if this error qualifies as an operational failure
            is_operational = isinstance(gemini_err, OPERATIONAL_FALLBACK_ERRORS)
            if not is_operational:
                if any(w in err_str for w in ("timeout", "rate limit", "429", "500", "502", "503", "504", "network", "unavailable")):
                    is_operational = True

            if not is_operational:
                # Programming bug or application logic error: DO NOT fallback
                logger.error("Non-operational Gemini failure; re-raising without fallback: %s", gemini_err)
                raise gemini_err

            # Operational failure qualified: Execute OpenRouter FALLBACK once
            fallback_reason = f"gemini_{type(gemini_err).__name__.lower()}"
            logger.warning(
                "Gemini operational failure (%s after %.1fms). Initiating OpenRouter fallback...",
                type(gemini_err).__name__,
                lat_gemini,
            )

            start_fallback = time.perf_counter()
            try:
                fallback_res = call_fn(self.openrouter_provider)
                lat_fb = (time.perf_counter() - start_fallback) * 1000.0
                return ProviderExecutionResult(
                    content=fallback_res,
                    provider="openrouter",
                    model=self.openrouter_provider.model_name,
                    status="success",
                    attempt=2,
                    latency_ms=lat_fb,
                    fallback_used=True,
                    fallback_reason=fallback_reason,
                )
            except Exception as fb_err:
                logger.error("OpenRouter fallback also failed: %s", fb_err)
                # If mock fallback explicitly enabled (e.g. testing)
                is_prod = os.getenv("AI_ENV", "").strip().lower() == "production"
                if self.config.allow_mock_fallback and not is_prod:
                    mock_res = call_fn(self.mock_provider)
                    return ProviderExecutionResult(
                        content=mock_res,
                        provider="mock",
                        model=self.mock_provider.model_name,
                        status="success",
                        attempt=3,
                        latency_ms=0.0,
                        fallback_used=True,
                        fallback_reason=f"{fallback_reason}_openrouter_failed",
                    )
                raise fb_err
