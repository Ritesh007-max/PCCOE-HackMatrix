"""
PolicySetu Rule Engine Operators.
Evaluates atomic conditions against applicant attributes.
"""

from typing import Any, Tuple, List, Dict, Set
from .models import RuleStatus
from .exceptions import InvalidOperatorError

SUPPORTED_OPERATORS: Set[str] = {
    ">=", ">", "<=", "<", "=", "!=",
    "between", "in", "not_in", "contains",
    "contains_any", "contains_all",
    "is_true", "is_false",
    "manual_review", "unstructured_nlp"
}

def _to_numeric(val: Any) -> float:
    """Helper to convert value to float, handling string numeric inputs."""
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        cleaned = val.replace(',', '').replace('₹', '').replace('Rs.', '').replace('Rs', '').strip()
        return float(cleaned)
    raise ValueError(f"Cannot convert {type(val)} to numeric: {val}")

def _to_bool(val: Any) -> bool:
    """Helper to convert value to boolean."""
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        lower = val.strip().lower()
        if lower in {"true", "yes", "1", "y"}:
            return True
        if lower in {"false", "no", "0", "n"}:
            return False
    raise ValueError(f"Cannot convert {type(val)} to boolean: {val}")

def evaluate_operator(
    operator: str,
    applicant_val: Any,
    expected_val: Any,
    field_name: str = "",
    has_conflict: bool = False
) -> Tuple[RuleStatus, str]:
    """
    Evaluates an operator given applicant value and expected statutory value.
    
    Returns:
        Tuple[RuleStatus, str]: (Verdict Status, Explanatory Reason)
    """
    # Invariant: Contradictory evidence must produce REVIEW
    if has_conflict:
        return (
            RuleStatus.REVIEW,
            f"Contradictory evidence detected for '{field_name}'. Manual review required."
        )

    # Invariant: Missing value must produce UNKNOWN (never PASS, never FAIL)
    if applicant_val is None or (isinstance(applicant_val, str) and applicant_val.strip() == ""):
        return (
            RuleStatus.UNKNOWN,
            f"Applicant information for '{field_name}' is missing or unverified."
        )

    op = operator.strip().lower()
    if op not in SUPPORTED_OPERATORS and operator not in SUPPORTED_OPERATORS:
        raise InvalidOperatorError(f"Unsupported operator: {operator}")

    # Special Non-Deterministic / Casework Operators
    if op in {"manual_review", "unstructured_nlp"}:
        return (
            RuleStatus.REVIEW,
            f"Clause requires official manual review or validated NLP verification: {expected_val}"
        )

    # 1. Numeric Comparisons: >=, >, <=, <
    if op in {">=", ">", "<=", "<"}:
        try:
            a_num = _to_numeric(applicant_val)
            e_num = _to_numeric(expected_val)
        except (ValueError, TypeError) as e:
            return (
                RuleStatus.REVIEW,
                f"Numeric conversion error for field '{field_name}': {e}"
            )

        if op == ">=":
            passed = a_num >= e_num
        elif op == ">":
            passed = a_num > e_num
        elif op == "<=":
            passed = a_num <= e_num
        elif op == "<":
            passed = a_num < e_num
        else:
            passed = False

        if passed:
            return (RuleStatus.PASS, f"{field_name} ({a_num}) satisfies condition ({op} {e_num}).")
        else:
            return (RuleStatus.FAIL, f"{field_name} ({a_num}) violates condition ({op} {e_num}).")

    # 2. Equality (=) and Inequality (!=)
    if op in {"=", "=="}:
        # Check boolean equality
        if isinstance(expected_val, bool):
            try:
                a_bool = _to_bool(applicant_val)
                passed = a_bool == expected_val
                if passed:
                    return (RuleStatus.PASS, f"{field_name} matches expected boolean ({expected_val}).")
                else:
                    return (RuleStatus.FAIL, f"{field_name} ({a_bool}) does not match expected boolean ({expected_val}).")
            except (ValueError, TypeError):
                return (RuleStatus.REVIEW, f"Boolean conversion failed for {field_name}.")

        # Check numeric equality if both can be numeric
        try:
            a_num = _to_numeric(applicant_val)
            e_num = _to_numeric(expected_val)
            if a_num == e_num:
                return (RuleStatus.PASS, f"{field_name} ({a_num}) equals expected value ({e_num}).")
            else:
                return (RuleStatus.FAIL, f"{field_name} ({a_num}) does not equal expected value ({e_num}).")
        except (ValueError, TypeError):
            pass

        # String equality (case-insensitive, whitespace normalized)
        a_str = str(applicant_val).strip().lower()
        e_str = str(expected_val).strip().lower()
        if a_str == e_str:
            return (RuleStatus.PASS, f"{field_name} ('{applicant_val}') matches expected ('{expected_val}').")
        else:
            return (RuleStatus.FAIL, f"{field_name} ('{applicant_val}') does not match expected ('{expected_val}').")

    if op in {"!=", "<>"}:
        eq_status, _ = evaluate_operator("=", applicant_val, expected_val, field_name, has_conflict=False)
        if eq_status == RuleStatus.PASS:
            return (RuleStatus.FAIL, f"{field_name} ({applicant_val}) equals excluded value ({expected_val}).")
        elif eq_status == RuleStatus.FAIL:
            return (RuleStatus.PASS, f"{field_name} ({applicant_val}) differs from excluded value ({expected_val}).")
        return (eq_status, f"Evaluation inconclusive for {field_name}.")

    # 3. Range Operator: between
    if op == "between":
        try:
            a_num = _to_numeric(applicant_val)
            if isinstance(expected_val, dict):
                min_v = _to_numeric(expected_val["min"])
                max_v = _to_numeric(expected_val["max"])
            elif isinstance(expected_val, (list, tuple)) and len(expected_val) == 2:
                min_v = _to_numeric(expected_val[0])
                max_v = _to_numeric(expected_val[1])
            else:
                return (RuleStatus.REVIEW, f"Malformed range object for between: {expected_val}")
        except (ValueError, TypeError, KeyError) as e:
            return (RuleStatus.REVIEW, f"Range conversion error for {field_name}: {e}")

        if min_v <= a_num <= max_v:
            return (RuleStatus.PASS, f"{field_name} ({a_num}) is within statutory range [{min_v}, {max_v}].")
        else:
            return (RuleStatus.FAIL, f"{field_name} ({a_num}) is outside statutory range [{min_v}, {max_v}].")

    # 4. Membership Operators: in, not_in
    if op == "in":
        if not isinstance(expected_val, (list, tuple, set)):
            expected_list = [expected_val]
        else:
            expected_list = list(expected_val)

        a_clean = str(applicant_val).strip().lower()
        e_clean_list = [str(x).strip().lower() for x in expected_list]

        if a_clean in e_clean_list:
            return (RuleStatus.PASS, f"{field_name} ('{applicant_val}') is in accepted list.")
        else:
            return (RuleStatus.FAIL, f"{field_name} ('{applicant_val}') is not in accepted list {expected_list}.")

    if op == "not_in":
        in_status, _ = evaluate_operator("in", applicant_val, expected_val, field_name, has_conflict=False)
        if in_status == RuleStatus.PASS:
            return (RuleStatus.FAIL, f"{field_name} ('{applicant_val}') is in excluded list.")
        elif in_status == RuleStatus.FAIL:
            return (RuleStatus.PASS, f"{field_name} ('{applicant_val}') is not in excluded list.")
        return (in_status, f"Evaluation inconclusive for {field_name}.")

    # 5. Collection Containment: contains, contains_any, contains_all
    if op == "contains":
        if isinstance(applicant_val, (list, tuple, set)):
            a_set = {str(x).strip().lower() for x in applicant_val}
            e_str = str(expected_val).strip().lower()
            if e_str in a_set:
                return (RuleStatus.PASS, f"{field_name} contains required item '{expected_val}'.")
            return (RuleStatus.FAIL, f"{field_name} does not contain required item '{expected_val}'.")
        else:
            # String substring check
            if str(expected_val).strip().lower() in str(applicant_val).strip().lower():
                return (RuleStatus.PASS, f"{field_name} contains '{expected_val}'.")
            return (RuleStatus.FAIL, f"{field_name} does not contain '{expected_val}'.")

    if op == "contains_any":
        if not isinstance(applicant_val, (list, tuple, set)):
            a_set = {str(applicant_val).strip().lower()}
        else:
            a_set = {str(x).strip().lower() for x in applicant_val}

        if not isinstance(expected_val, (list, tuple, set)):
            e_set = {str(expected_val).strip().lower()}
        else:
            e_set = {str(x).strip().lower() for x in expected_val}

        if bool(a_set & e_set):
            return (RuleStatus.PASS, f"{field_name} satisfies at least one target in {expected_val}.")
        return (RuleStatus.FAIL, f"{field_name} does not contain any item from {expected_val}.")

    if op == "contains_all":
        if not isinstance(applicant_val, (list, tuple, set)):
            a_set = {str(applicant_val).strip().lower()}
        else:
            a_set = {str(x).strip().lower() for x in applicant_val}

        if not isinstance(expected_val, (list, tuple, set)):
            e_set = {str(expected_val).strip().lower()}
        else:
            e_set = {str(x).strip().lower() for x in expected_val}

        if e_set.issubset(a_set):
            return (RuleStatus.PASS, f"{field_name} contains all required items from {expected_val}.")
        return (RuleStatus.FAIL, f"{field_name} is missing some required items from {expected_val}.")

    # 6. Boolean State: is_true, is_false
    if op == "is_true":
        try:
            a_bool = _to_bool(applicant_val)
            if a_bool is True:
                return (RuleStatus.PASS, f"{field_name} is verified True.")
            return (RuleStatus.FAIL, f"{field_name} is False (expected True).")
        except (ValueError, TypeError):
            return (RuleStatus.REVIEW, f"Boolean conversion failed for {field_name}: {applicant_val}")

    if op == "is_false":
        try:
            a_bool = _to_bool(applicant_val)
            if a_bool is False:
                return (RuleStatus.PASS, f"{field_name} is verified False.")
            return (RuleStatus.FAIL, f"{field_name} is True (expected False).")
        except (ValueError, TypeError):
            return (RuleStatus.REVIEW, f"Boolean conversion failed for {field_name}: {applicant_val}")

    raise InvalidOperatorError(f"Unhandled operator: {operator}")
