"""
PolicySetu LLM Intelligence Layer.
Query understanding, candidate fact extraction, grounded semantic interpretation,
and decision explanation.
"""

from .models import (
    UserIntent,
    ExtractionConfidence,
    AmbiguityType,
    ClaimSupportStatus,
    AmbiguityRecord,
    QueryIntent,
    ApplicantFactCandidate,
    FactExtractionResult,
    FactualClaim,
    GroundedExplanation,
    LLMMetadata,
)
from .config import LLMConfig, DEFAULT_LLM_CONFIG
from .errors import (
    LLMError,
    ProviderUnavailableError,
    ProviderTimeoutError,
    MalformedOutputError,
    SchemaValidationError,
    PromptInjectionDetectedError,
    DecisionContradictionError,
    UngroundedClaimError,
)
from .providers import LLMProvider, MockLLMProvider, OpenAICompatibleProvider, get_llm_provider
from .client import LLMClient
from .safety import PromptInjectionDetector, DecisionImmutabilityGuard, SafetyScanResult
from .grounding import GroundingVerifier
from .extraction import ApplicantFactExtractor
from .explanation import GroundedExplanationGenerator
from .ast_analyzer import RuleASTMissingFieldAnalyzer

__all__ = [
    "UserIntent",
    "ExtractionConfidence",
    "AmbiguityType",
    "ClaimSupportStatus",
    "AmbiguityRecord",
    "QueryIntent",
    "ApplicantFactCandidate",
    "FactExtractionResult",
    "FactualClaim",
    "GroundedExplanation",
    "LLMMetadata",
    "LLMConfig",
    "DEFAULT_LLM_CONFIG",
    "LLMError",
    "ProviderUnavailableError",
    "ProviderTimeoutError",
    "MalformedOutputError",
    "SchemaValidationError",
    "PromptInjectionDetectedError",
    "DecisionContradictionError",
    "UngroundedClaimError",
    "LLMProvider",
    "MockLLMProvider",
    "OpenAICompatibleProvider",
    "get_llm_provider",
    "LLMClient",
    "PromptInjectionDetector",
    "DecisionImmutabilityGuard",
    "SafetyScanResult",
    "GroundingVerifier",
    "ApplicantFactExtractor",
    "GroundedExplanationGenerator",
    "RuleASTMissingFieldAnalyzer",
]
