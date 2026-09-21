"""
PolicySetu LLM Configuration.
Centralizes provider settings, inference parameters, safety thresholds, and timeouts.
Never hardcodes secrets. Default configuration operates offline with MockLLMProvider.
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class LLMConfig:
    """Configuration settings for LLM and NLP operations."""
    provider: str = "mock"  # "mock" or "openai"
    model: str = "mock-governance-v1"
    temperature: float = 0.0  # 0.0 for deterministic fact extraction
    max_tokens: int = 2048
    timeout_seconds: float = 30.0
    retry_count: int = 2
    # CRITICAL INVARIANT: Production provider failure MUST NOT silently fall back to mock
    allow_mock_fallback: bool = False
    max_input_chars: int = 10000
    confidence_threshold: float = 0.6
    grounding_required: bool = True
    api_key: Optional[str] = field(default=None, repr=False)
    api_base: Optional[str] = None

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Builds configuration from environment variables with safe offline defaults."""
        provider = os.getenv("LLM_PROVIDER", "mock").strip().lower()
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
        api_base = os.getenv("OPENAI_API_BASE") or os.getenv("LLM_API_BASE")
        model = os.getenv("LLM_MODEL", "gpt-4o-mini" if provider == "openai" else "mock-governance-v1")
        
        return cls(
            provider=provider,
            model=model,
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2048")),
            timeout_seconds=float(os.getenv("LLM_TIMEOUT", "30.0")),
            retry_count=int(os.getenv("LLM_RETRIES", "2")),
            allow_mock_fallback=os.getenv("LLM_ALLOW_MOCK_FALLBACK", "false").strip().lower() == "true",
            max_input_chars=int(os.getenv("LLM_MAX_INPUT_CHARS", "10000")),
            confidence_threshold=float(os.getenv("LLM_CONFIDENCE_THRESHOLD", "0.6")),
            grounding_required=os.getenv("LLM_GROUNDING_REQUIRED", "true").strip().lower() == "true",
            api_key=api_key,
            api_base=api_base,
        )

    def to_safe_dict(self) -> Dict[str, Any]:
        """Returns safe dictionary with API keys and secrets redacted."""
        return {
            "provider": self.provider,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "allow_mock_fallback": self.allow_mock_fallback,
            "max_input_chars": self.max_input_chars,
            "confidence_threshold": self.confidence_threshold,
            "grounding_required": self.grounding_required,
            "api_base": self.api_base,
            "has_api_key": bool(self.api_key),
        }


DEFAULT_LLM_CONFIG = LLMConfig()
