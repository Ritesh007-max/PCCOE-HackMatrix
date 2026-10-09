"""
FIN Rules Subsystem.
Implements the AST rule schema, deterministic operators, Kleene multi-valued logic,
candidate rule extraction, validation gates, and immutable versioning.
"""

from .candidate import (
    CandidateRule,
    CandidateRuleExtractor,
    RuleLifecycleStatus,
    SourceTier,
)
from .evaluator import RuleEvaluator
from .exceptions import (
    ActivationGateError,
    ContradictoryEvidenceError,
    ContradictoryRuleError,
    InvalidOperatorError,
    InvalidRuleDefinitionError,
    ProfileEvaluationError,
    RuleEngineError,
    RuleVersionNotFoundError,
)
from .logic import (
    evaluate_and,
    evaluate_group_operator,
    evaluate_not,
    evaluate_or,
)
from .models import (
    ApplicantProfile,
    LogicGroup,
    Rule,
    RuleEvaluationResult,
    RuleStatus,
    RuleType,
    SchemeRuleSet,
)
from .operators import (
    SUPPORTED_OPERATORS,
    evaluate_operator,
)
from .validator import (
    RuleSetCompleteness,
    RuleSetValidationResult,
    RuleValidator,
    detect_ambiguities,
    detect_contradictions,
    detect_prompt_injections,
    validate_rule,
)
from .versioning import (
    SchemeRuleRegistry,
    compute_ruleset_hash,
)

__all__ = [
    "Rule",
    "LogicGroup",
    "SchemeRuleSet",
    "RuleStatus",
    "RuleType",
    "RuleEvaluationResult",
    "ApplicantProfile",
    "evaluate_operator",
    "SUPPORTED_OPERATORS",
    "evaluate_and",
    "evaluate_or",
    "evaluate_not",
    "evaluate_group_operator",
    "RuleEvaluator",
    "RuleValidator",
    "RuleSetCompleteness",
    "RuleSetValidationResult",
    "validate_rule",
    "detect_contradictions",
    "detect_ambiguities",
    "detect_prompt_injections",
    "CandidateRule",
    "CandidateRuleExtractor",
    "SourceTier",
    "RuleLifecycleStatus",
    "SchemeRuleRegistry",
    "compute_ruleset_hash",
    "RuleEngineError",
    "InvalidOperatorError",
    "InvalidRuleDefinitionError",
    "ProfileEvaluationError",
    "ContradictoryEvidenceError",
    "ActivationGateError",
    "RuleVersionNotFoundError",
    "ContradictoryRuleError",
]
