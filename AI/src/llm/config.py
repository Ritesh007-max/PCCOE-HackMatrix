"""
PolicySetu LLM Configuration.
Centralizes provider settings, inference parameters, safety thresholds, and timeouts.
Never hardcodes secrets. Default configuration operates in 'auto' (Gemini -> OpenRouter).
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from dotenv import load_dotenv

# Auto-load .env or .env.example if present
load_dotenv()
if not os.getenv("GEMINI_API_KEY") and os.path.exists(".env.example"):
    load_dotenv(".env.example")


@dataclass
class LLMConfig:
    """Configuration settings for LLM and NLP operations."""
    provider: str = "auto"  # "auto", "gemini", "openrouter", "mock"
    model: str = "gemini-2.5-flash"
    temperature: float = 0.0  # 0.0 for deterministic fact extraction
    max_tokens: int = 2048
    timeout_seconds: float = 30.0
    retry_count: int = 1
    allow_mock_fallback: bool = False
    max_input_chars: int = 15000
    confidence_threshold: float = 0.6
    grounding_required: bool = True

    # Gemini settings
    gemini_api_key: Optional[str] = field(default=None, repr=False)
    gemini_model: str = "gemini-2.5-flash"

    # OpenRouter settings
    openrouter_api_key: Optional[str] = field(default=None, repr=False)
    openrouter_model: str = "google/gemini-2.5-flash"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Backward compatibility
    api_key: Optional[str] = field(default=None, repr=False)
    api_base: Optional[str] = None

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Builds configuration from environment variables with safe defaults."""
        provider = os.getenv("LLM_PROVIDER", "auto").strip().lower()

        gemini_key = os.getenv("GEMINI_API_KEY")
        gemini_model = os.getenv("GEMINI_MODEL") or os.getenv("DEFAULT_LLM_MODEL") or "gemini-2.5-flash"

        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        openrouter_model = os.getenv("OPENROUTER_MODEL") or "google/gemini-2.5-flash"
        openrouter_base = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")

        # Legacy OpenAI compat
        legacy_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
        legacy_base = os.getenv("OPENAI_API_BASE") or os.getenv("LLM_API_BASE")

        model = gemini_model if provider in ("gemini", "auto") else openrouter_model

        return cls(
            provider=provider,
            model=model,
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2048")),
            timeout_seconds=float(os.getenv("LLM_TIMEOUT", "30.0")),
            retry_count=int(os.getenv("LLM_RETRIES", "1")),
            allow_mock_fallback=os.getenv("LLM_ALLOW_MOCK_FALLBACK", "false").strip().lower() == "true",
            max_input_chars=int(os.getenv("LLM_MAX_INPUT_CHARS", "15000")),
            confidence_threshold=float(os.getenv("LLM_CONFIDENCE_THRESHOLD", "0.6")),
            grounding_required=os.getenv("LLM_GROUNDING_REQUIRED", "true").strip().lower() == "true",
            gemini_api_key=gemini_key,
            gemini_model=gemini_model,
            openrouter_api_key=openrouter_key,
            openrouter_model=openrouter_model,
            openrouter_base_url=openrouter_base,
            api_key=legacy_key or gemini_key,
            api_base=legacy_base,
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
            "gemini_model": self.gemini_model,
            "has_gemini_key": bool(self.gemini_api_key),
            "openrouter_model": self.openrouter_model,
            "openrouter_base_url": self.openrouter_base_url,
            "has_openrouter_key": bool(self.openrouter_api_key),
        }


DEFAULT_LLM_CONFIG = LLMConfig.from_env()
