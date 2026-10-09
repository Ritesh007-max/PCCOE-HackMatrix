"""
FIN Rule Engine Exceptions.
"""

class RuleEngineError(Exception):
    """Base exception for all rule engine errors."""
    pass

class InvalidOperatorError(RuleEngineError):
    """Raised when an unsupported or malformed operator is encountered."""
    pass

class InvalidRuleDefinitionError(RuleEngineError):
    """Raised when a rule definition does not adhere to schema or contains invalid values."""
    pass

class ProfileEvaluationError(RuleEngineError):
    """Raised when an applicant profile cannot be evaluated."""
    pass

class ContradictoryEvidenceError(RuleEngineError):
    """Raised when an applicant profile contains conflicting/contradictory evidence."""
    pass

class ActivationGateError(RuleEngineError):
    """Raised when a candidate rule set fails validation gates required for activation."""
    pass

class RuleVersionNotFoundError(RuleEngineError):
    """Raised when a requested rule set version does not exist in the registry."""
    pass

class ContradictoryRuleError(RuleEngineError):
    """Raised when a rule set contains mutually contradictory logic conditions."""
    pass
