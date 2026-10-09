"""
FIN Orchestration Error Hierarchy.
Defines explicit domain exceptions that fail gracefully and do not leak internals to clients.
"""


class OrchestrationError(Exception):
    """Base class for all orchestration errors."""
    def __init__(self, message: str, code: str = "ORCHESTRATION_ERROR", details: dict = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class QueryUnderstandingError(OrchestrationError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="QUERY_UNDERSTANDING_ERROR", details=details)


class ApplicantContextError(OrchestrationError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="APPLICANT_CONTEXT_ERROR", details=details)


class SchemeRetrievalError(OrchestrationError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="SCHEME_RETRIEVAL_ERROR", details=details)


class EligibilityEvaluationError(OrchestrationError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="ELIGIBILITY_EVALUATION_ERROR", details=details)


class ExplanationGroundingError(OrchestrationError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="EXPLANATION_GROUNDING_ERROR", details=details)


class ConflictResolutionError(OrchestrationError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="CONFLICT_RESOLUTION_ERROR", details=details)


class ConversationContextError(OrchestrationError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="CONVERSATION_CONTEXT_ERROR", details=details)


class LLMProviderError(OrchestrationError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="LLM_PROVIDER_ERROR", details=details)


class PolicySourceError(OrchestrationError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="POLICY_SOURCE_ERROR", details=details)


class AuthorizationError(OrchestrationError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="AUTHORIZATION_ERROR", details=details)


class ValidationError(OrchestrationError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="VALIDATION_ERROR", details=details)
