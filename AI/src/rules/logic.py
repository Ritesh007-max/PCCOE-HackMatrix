"""
PolicySetu Multi-Valued Ternary Logic Evaluator (Kleene Extended Algebra).
Handles AND, OR, NOT operations and nested logic groups.
"""

from typing import List, Dict, Any, Optional
from .models import RuleStatus
from .exceptions import RuleEngineError

def evaluate_and(statuses: List[RuleStatus]) -> RuleStatus:
    """
    Evaluates an AND conjunction across multiple rule statuses.
    
    Truth Table Semantics:
    - Any FAIL -> FAIL (short-circuit / overriding)
    - If no FAIL and any UNKNOWN -> UNKNOWN (missing information prevents decision)
    - If no FAIL and no UNKNOWN and any REVIEW -> REVIEW
    - All PASS -> PASS
    """
    if not statuses:
        return RuleStatus.PASS

    # 1. Any FAIL fails the entire AND chain
    if any(s == RuleStatus.FAIL for s in statuses):
        return RuleStatus.FAIL

    # 2. If no failure, any UNKNOWN means outcome is UNKNOWN
    if any(s == RuleStatus.UNKNOWN for s in statuses):
        return RuleStatus.UNKNOWN

    # 3. If no failure and no unknown, any REVIEW requires REVIEW
    if any(s == RuleStatus.REVIEW for s in statuses):
        return RuleStatus.REVIEW

    # 4. If all PASS, conjunction passes
    return RuleStatus.PASS

def evaluate_or(statuses: List[RuleStatus]) -> RuleStatus:
    """
    Evaluates an OR disjunction across multiple rule statuses.
    
    Truth Table Semantics:
    - Any PASS -> PASS (short-circuit / overriding)
    - If no PASS and any UNKNOWN -> UNKNOWN
    - If no PASS and no UNKNOWN and any REVIEW -> REVIEW
    - All FAIL -> FAIL
    """
    if not statuses:
        return RuleStatus.FAIL

    # 1. Any PASS satisfies the entire OR chain
    if any(s == RuleStatus.PASS for s in statuses):
        return RuleStatus.PASS

    # 2. If no PASS, any UNKNOWN means outcome is UNKNOWN
    if any(s == RuleStatus.UNKNOWN for s in statuses):
        return RuleStatus.UNKNOWN

    # 3. If no PASS and no unknown, any REVIEW requires REVIEW
    if any(s == RuleStatus.REVIEW for s in statuses):
        return RuleStatus.REVIEW

    # 4. If all FAIL, disjunction fails
    return RuleStatus.FAIL

def evaluate_not(status: RuleStatus) -> RuleStatus:
    """
    Evaluates a NOT inversion for negative/exclusion criteria.
    
    Truth Table Semantics:
    - PASS -> FAIL (matching an exclusion disqualifies)
    - FAIL -> PASS (violating an exclusion clears the applicant)
    - UNKNOWN -> UNKNOWN
    - REVIEW -> REVIEW
    """
    if status == RuleStatus.PASS:
        return RuleStatus.FAIL
    if status == RuleStatus.FAIL:
        return RuleStatus.PASS
    if status == RuleStatus.UNKNOWN:
        return RuleStatus.UNKNOWN
    if status == RuleStatus.REVIEW:
        return RuleStatus.REVIEW
    raise RuleEngineError(f"Unexpected status in NOT operation: {status}")

def evaluate_group_operator(operator: str, statuses: List[RuleStatus]) -> RuleStatus:
    """Combines a list of statuses using the specified boolean operator."""
    op = operator.strip().upper()
    if op == "AND":
        return evaluate_and(statuses)
    elif op == "OR":
        return evaluate_or(statuses)
    elif op == "NOT":
        if len(statuses) == 1:
            return evaluate_not(statuses[0])
        # If multiple conditions under NOT, evaluate as NOT(AND(conditions)) or NOT(OR(conditions))
        # Standard de Morgan / exclusion semantics: NOT of conjunction
        return evaluate_not(evaluate_and(statuses))
    else:
        raise RuleEngineError(f"Unsupported group operator: {operator}")
