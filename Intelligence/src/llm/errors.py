"""
FIN LLM & NLP Exception Hierarchy.
Clear, typed exceptions for provider issues, authentication failures, parsing errors, and safety violations.
"""

class LLMError(Exception):
    """Base exception for all LLM/NLP intelligence layer errors."""
    pass


class ProviderUnavailableError(LLMError):
    """Raised when an LLM provider is unreachable due to outage or 5xx error."""
    pass


class ProviderTimeoutError(LLMError):
    """Raised when an LLM provider call exceeds the configured timeout."""
    pass


class ProviderRateLimitError(LLMError):
    """Raised when an LLM provider returns HTTP 429 / quota exceeded."""
    pass


class ProviderNetworkError(LLMError):
    """Raised when network transport fails (DNS, socket timeout, connection reset)."""
    pass


class ProviderAuthenticationError(LLMError):
    """
    Raised on HTTP 401/403 or invalid API credentials.
    CRITICAL INVARIANT: Authentication errors MUST NOT trigger silent fallback.
    """
    pass


class ProviderConfigurationError(LLMError):
    """
    Raised when required configuration or API keys are missing.
    CRITICAL INVARIANT: Configuration errors MUST NOT trigger silent fallback.
    """
    pass


class ProviderInvalidResponseError(LLMError):
    """Raised when provider returns an empty, corrupted, or unexpected response format."""
    pass


class ProviderStructuredOutputError(LLMError):
    """Raised when structured JSON parsing or validation fails after reasonable retry."""
    pass


class MalformedOutputError(LLMError):
    """Raised when the LLM produces invalid JSON or malformed content."""
    pass


class SchemaValidationError(LLMError):
    """Raised when LLM structured output fails schema constraints."""
    pass


class PromptInjectionDetectedError(LLMError):
    """Raised or flagged when adversarial instruction override patterns are detected."""
    pass


class DecisionContradictionError(LLMError):
    """Raised when generated explanation text contradicts the authoritative Phase 3 decision."""
    pass


class UngroundedClaimError(LLMError):
    """Raised or flagged when a factual claim lacks provenance or evidence support."""
    pass


__all__ = [
    "LLMError",
    "ProviderUnavailableError",
    "ProviderTimeoutError",
    "ProviderRateLimitError",
    "ProviderNetworkError",
    "ProviderAuthenticationError",
    "ProviderConfigurationError",
    "ProviderInvalidResponseError",
    "ProviderStructuredOutputError",
    "MalformedOutputError",
    "SchemaValidationError",
    "PromptInjectionDetectedError",
    "DecisionContradictionError",
    "UngroundedClaimError",
]
