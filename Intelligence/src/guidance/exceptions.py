"""
Domain Exceptions for Application Guidance & Preparation Layer.
Phase 11: FIN Guidance Layer.
"""

class GuidanceError(Exception):
    """Base exception for all guidance and preparation errors."""
    pass


class GuidanceValidationError(GuidanceError):
    """Raised when an application guidance package fails consistency validation."""
    def __init__(self, message: str, rule_name: str = "", details: str = ""):
        self.rule_name = rule_name
        self.details = details
        msg = f"Guidance validation failed ({rule_name}): {message}" if rule_name else f"Guidance validation failed: {message}"
        if details:
            msg += f" Details: {details}"
        super().__init__(msg)


class ContradictoryGuidanceError(GuidanceValidationError):
    """Raised when generated guidance text contradicts deterministic statutory truth."""
    def __init__(self, statutory_truth: str, generated_claim: str):
        self.statutory_truth = statutory_truth
        self.generated_claim = generated_claim
        super().__init__(
            message=f"Generated claim '{generated_claim}' contradicts deterministic truth '{statutory_truth}'",
            rule_name="NO_CONTRADICTORY_GENERATION",
        )


class InvalidSourceURLError(GuidanceError):
    """Raised when an untrusted or non-authoritative URL is supplied as an official link."""
    def __init__(self, url: str, reason: str = ""):
        self.url = url
        self.reason = reason
        msg = f"Untrusted or invalid official portal URL: '{url}'"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg)


class MissingSourceMetadataError(GuidanceError):
    """Raised when required scheme source metadata cannot be found in the active snapshot."""
    def __init__(self, scheme_id: str):
        self.scheme_id = scheme_id
        super().__init__(f"Authoritative source metadata for scheme '{scheme_id}' not found in active snapshot")
