"""
PolicySetu LLM & NLP Exception Hierarchy.
Clear, typed exceptions for provider issues, parsing failures, and safety violations.
"""

class LLMError(Exception):
    """Base exception for all LLM/NLP intelligence layer errors."""
    pass


class ProviderUnavailableError(LLMError):
    """Raised when an LLM provider is unreachable or missing credentials."""
    pass


class ProviderTimeoutError(LLMError):
    """Raised when an LLM provider call exceeds the configured timeout."""
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
