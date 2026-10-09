"""
FIN Rule AST Validator and Verification Gates.
Enforces static schema validation, operator verification, range consistency,
policy ambiguity detection, and deterministic contradiction detection.
"""

from enum import Enum
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from .exceptions import InvalidOperatorError, InvalidRuleDefinitionError
from .models import LogicGroup, Rule, RuleType, SchemeRuleSet
from .operators import SUPPORTED_OPERATORS


class RuleSetCompleteness(str, Enum):
    """Completeness rating of a statutory scheme rule set."""
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNSTRUCTURED = "UNSTRUCTURED"
    FAILED = "FAILED"


# Known ambiguous terms in policy texts that cannot be deterministically evaluated
# without an explicit statutory threshold provided by authoritative sources.
AMBIGUOUS_POLICY_PATTERNS = [
    re.compile(r"\b(young\s+applicants?|youth)\b", re.IGNORECASE),
    re.compile(r"\b(low\s+income|poor\s+families|economically\s+weaker)\b", re.IGNORECASE),
    re.compile(r"\b(priority\s+will\s+be\s+given)\b", re.IGNORECASE),
    re.compile(r"\b(eligible\s+families|eligible\s+beneficiar(y|ies))\b", re.IGNORECASE),
    re.compile(r"\b(marginal\s+farmers?)\b", re.IGNORECASE),
    re.compile(r"\b(suitable\s+candidates?)\b", re.IGNORECASE),
    re.compile(r"\b(as\s+prescribed|as\s+decided\s+by\s+government)\b", re.IGNORECASE),
]

# Prompt injection patterns in policy texts attempting to subvert rule evaluation
POLICY_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous\s+)?instructions?", re.IGNORECASE),
    re.compile(r"always\s+return\s+pass", re.IGNORECASE),
    re.compile(r"mark\s+(every|all)\s+applicant(s)?\s+eligible", re.IGNORECASE),
    re.compile(r"disregard\s+(the\s+)?system", re.IGNORECASE),
    re.compile(r"system\s*:\s*override", re.IGNORECASE),
]

ALLOWED_VALUE_TYPES: Set[str] = {
    "numeric", "string", "boolean", "list_string", "range", "unstructured"
}


class RuleSetValidationResult:
    """Encapsulates the outcome of validating a rule set against activation gates."""

    def __init__(
        self,
        is_valid: bool,
        can_activate: bool,
        completeness: RuleSetCompleteness,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        ambiguities: Optional[List[str]] = None,
        contradictions: Optional[List[str]] = None,
    ):
        self.is_valid = is_valid
        self.can_activate = can_activate
        self.completeness = completeness
        self.errors = errors or []
        self.warnings = warnings or []
        self.ambiguities = ambiguities or []
        self.contradictions = contradictions or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "can_activate": self.can_activate,
            "completeness": self.completeness.value,
            "errors": self.errors,
            "warnings": self.warnings,
            "ambiguities": self.ambiguities,
            "contradictions": self.contradictions,
        }


def _to_float_safe(val: Any) -> Optional[float]:
    """Helper to parse a numeric value or return None."""
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        cleaned = val.replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def validate_rule(rule: Rule) -> List[str]:
    """
    Validates a single atomic Rule AST node.
    Returns a list of error strings (empty if valid).
    """
    errors: List[str] = []

    if not rule.rule_id or not rule.rule_id.strip():
        errors.append("Missing required 'rule_id'.")

    if not rule.field or not rule.field.strip():
        errors.append(f"Rule '{rule.rule_id}': Missing target 'field'.")

    op = (rule.operator or "").strip().lower()
    if op not in SUPPORTED_OPERATORS and rule.operator not in SUPPORTED_OPERATORS:
        errors.append(f"Rule '{rule.rule_id}': Unsupported operator '{rule.operator}'.")

    if rule.value_type not in ALLOWED_VALUE_TYPES:
        errors.append(
            f"Rule '{rule.rule_id}': Invalid value_type '{rule.value_type}'. Allowed: {sorted(list(ALLOWED_VALUE_TYPES))}."
        )

    # Operator-specific checks
    if op in {">=", ">", "<=", "<"}:
        num = _to_float_safe(rule.expected_value)
        if num is None:
            errors.append(
                f"Rule '{rule.rule_id}': Comparison operator '{rule.operator}' requires numeric expected_value, got '{rule.expected_value}'."
            )

    elif op == "between":
        if isinstance(rule.expected_value, dict):
            min_v = _to_float_safe(rule.expected_value.get("min"))
            max_v = _to_float_safe(rule.expected_value.get("max"))
            if min_v is None or max_v is None:
                errors.append(f"Rule '{rule.rule_id}': 'between' dict must contain numeric 'min' and 'max'.")
            elif min_v > max_v:
                errors.append(
                    f"Rule '{rule.rule_id}': 'between' range is impossible: min ({min_v}) > max ({max_v})."
                )
        elif isinstance(rule.expected_value, (list, tuple)) and len(rule.expected_value) == 2:
            min_v = _to_float_safe(rule.expected_value[0])
            max_v = _to_float_safe(rule.expected_value[1])
            if min_v is None or max_v is None:
                errors.append(f"Rule '{rule.rule_id}': 'between' pair must contain 2 numeric values.")
            elif min_v > max_v:
                errors.append(
                    f"Rule '{rule.rule_id}': 'between' range is impossible: min ({min_v}) > max ({max_v})."
                )
        else:
            errors.append(
                f"Rule '{rule.rule_id}': 'between' operator requires dict with min/max or 2-element list."
            )

    elif op in {"in", "not_in"}:
        if not isinstance(rule.expected_value, (list, tuple, set)) and rule.expected_value is None:
            errors.append(f"Rule '{rule.rule_id}': '{op}' operator requires non-empty collection.")

    return errors


def detect_contradictions(rules: List[Rule]) -> List[str]:
    """
    Detects deterministic contradictions across rules intended to be satisfied together.
    Examples:
    - age >= 18 AND age < 18
    - income <= 100000 AND income >= 500000
    - is_taxpayer == True AND is_taxpayer == False
    """
    contradictions: List[str] = []

    # Group rules by (field, logic_group)
    field_groups: Dict[Tuple[str, str], List[Rule]] = {}
    for r in rules:
        key = (r.field, r.logic_group or "DEFAULT")
        field_groups.setdefault(key, []).append(r)

    for (field, grp), r_list in field_groups.items():
        if len(r_list) < 2:
            continue

        # Check numeric intervals for contradictions
        min_allowed: float = -math.inf
        max_allowed: float = math.inf
        strict_min: bool = False
        strict_max: bool = False

        bool_targets: Set[bool] = set()

        for r in r_list:
            op = r.operator.strip().lower()

            if op == ">=":
                val = _to_float_safe(r.expected_value)
                if val is not None and val > min_allowed:
                    min_allowed = val
                    strict_min = False
            elif op == ">":
                val = _to_float_safe(r.expected_value)
                if val is not None and val >= min_allowed:
                    min_allowed = val
                    strict_min = True
            elif op == "<=":
                val = _to_float_safe(r.expected_value)
                if val is not None and val < max_allowed:
                    max_allowed = val
                    strict_max = False
            elif op == "<":
                val = _to_float_safe(r.expected_value)
                if val is not None and val <= max_allowed:
                    max_allowed = val
                    strict_max = True
            elif op in {"is_true"}:
                bool_targets.add(True)
            elif op in {"is_false"}:
                bool_targets.add(False)
            elif op in {"=", "=="} and isinstance(r.expected_value, bool):
                bool_targets.add(r.expected_value)

        # Check if min_allowed and max_allowed form an empty interval
        if min_allowed > max_allowed:
            contradictions.append(
                f"Contradictory numeric bounds on '{field}' in group '{grp}': lower bound ({min_allowed}) exceeds upper bound ({max_allowed})."
            )
        elif min_allowed == max_allowed and (strict_min or strict_max):
            contradictions.append(
                f"Strict contradiction on '{field}' in group '{grp}': no value satisfies boundary ({min_allowed})."
            )

        # Check boolean contradiction
        if True in bool_targets and False in bool_targets:
            contradictions.append(
                f"Direct boolean contradiction on '{field}' in group '{grp}': requires both True and False."
            )

    return contradictions


def detect_ambiguities(rules: List[Rule]) -> List[str]:
    """
    Scans raw text of rules for ungrounded statutory ambiguity where
    an authoritative numeric or categorical threshold is missing.
    """
    ambiguities: List[str] = []
    for r in rules:
        text = r.raw_text or ""
        for pattern in AMBIGUOUS_POLICY_PATTERNS:
            match = pattern.search(text)
            if match:
                # If the rule has an operator like manual_review or unstructured_nlp, it's flagged as needing review
                # If it's a numeric rule with a guessed threshold from an ambiguous text, flag it
                term = match.group(0)
                if r.operator in {"manual_review", "unstructured_nlp"} or r.confidence < 0.8:
                    ambiguities.append(
                        f"Rule '{r.rule_id}' on field '{r.field}' contains ambiguous statutory phrasing '{term}' in clause: \"{text}\""
                    )
                elif not r.condition or r.condition.get("val") is None:
                    ambiguities.append(
                        f"Rule '{r.rule_id}' has ambiguous clause '{term}' without deterministic threshold."
                    )
    return ambiguities


def detect_prompt_injections(rules: List[Rule]) -> List[str]:
    """
    Detects prompt injection attempts embedded in policy raw text.
    """
    injections: List[str] = []
    for r in rules:
        text = r.raw_text or ""
        for p in POLICY_INJECTION_PATTERNS:
            if p.search(text):
                injections.append(
                    f"Rule '{r.rule_id}' contains adversarial injection phrase matching '{p.pattern}' in text: \"{text}\""
                )
    return injections


class RuleValidator:
    """Comprehensive validator enforcing Phase 20 activation gates on SchemeRuleSets."""

    def validate_ruleset(self, ruleset: SchemeRuleSet) -> RuleSetValidationResult:
        errors: List[str] = []
        warnings: List[str] = []
        ambiguities: List[str] = []
        contradictions: List[str] = []

        # 1. Identity & Metadata Checks
        if not ruleset.scheme_id or not ruleset.scheme_id.strip():
            errors.append("SchemeRuleSet missing required 'scheme_id'.")
        if not ruleset.scheme_slug or not ruleset.scheme_slug.strip():
            errors.append("SchemeRuleSet missing required 'scheme_slug'.")
        if not ruleset.version or not ruleset.version.strip():
            errors.append("SchemeRuleSet missing required 'version'.")

        root_op = (ruleset.root_logic or "AND").upper()
        if root_op not in {"AND", "OR"}:
            errors.append(f"Invalid root_logic '{ruleset.root_logic}'. Expected 'AND' or 'OR'.")

        if not ruleset.rules:
            errors.append("SchemeRuleSet has no rules defined.")
            return RuleSetValidationResult(
                is_valid=False,
                can_activate=False,
                completeness=RuleSetCompleteness.FAILED,
                errors=errors,
            )

        # 2. Rule ID uniqueness & atomic node validation
        rule_ids_seen: Set[str] = set()
        unstructured_count = 0

        for r in ruleset.rules:
            if r.rule_id in rule_ids_seen:
                errors.append(f"Duplicate rule_id detected: '{r.rule_id}'.")
            rule_ids_seen.add(r.rule_id)

            # Node validation
            r_errs = validate_rule(r)
            errors.extend(r_errs)

            if r.operator in {"manual_review", "unstructured_nlp"} or r.rule_type == RuleType.CONDITIONAL.value:
                unstructured_count += 1

            # Provenance checks
            if not r.source_document and not r.source_url:
                warnings.append(f"Rule '{r.rule_id}' lacks source document and URL provenance.")

        # 3. Logic Groups validation
        if ruleset.logic_groups:
            for lg in ruleset.logic_groups:
                if not lg.group_id:
                    errors.append("LogicGroup missing required 'group_id'.")
                if lg.operator not in {"AND", "OR", "NOT"}:
                    errors.append(f"LogicGroup '{lg.group_id}' has invalid operator '{lg.operator}'.")
                if not lg.rule_ids:
                    errors.append(f"LogicGroup '{lg.group_id}' has no referenced rule_ids (empty node).")
                for rid in lg.rule_ids:
                    if rid not in rule_ids_seen:
                        errors.append(
                            f"LogicGroup '{lg.group_id}' references unknown rule_id '{rid}'."
                        )

        # 4. Contradiction Detection
        contradictions = detect_contradictions(ruleset.rules)
        if contradictions:
            errors.extend(contradictions)

        # 5. Ambiguity Detection
        ambiguities = detect_ambiguities(ruleset.rules)
        if ambiguities:
            warnings.extend(ambiguities)

        # 6. Policy Text Prompt Injection Detection
        injections = detect_prompt_injections(ruleset.rules)
        if injections:
            errors.extend(injections)

        # 7. Determine Completeness
        if errors:
            completeness = RuleSetCompleteness.FAILED
        elif unstructured_count > 0:
            completeness = RuleSetCompleteness.PARTIAL
        elif len(ruleset.rules) < 2:
            completeness = RuleSetCompleteness.PARTIAL
        else:
            completeness = RuleSetCompleteness.COMPLETE

        is_valid = len(errors) == 0
        # Can only activate if valid and zero contradictions and zero injections
        can_activate = is_valid and (len(contradictions) == 0) and (len(injections) == 0)

        return RuleSetValidationResult(
            is_valid=is_valid,
            can_activate=can_activate,
            completeness=completeness,
            errors=errors,
            warnings=warnings,
            ambiguities=ambiguities,
            contradictions=contradictions,
        )
