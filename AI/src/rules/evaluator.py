"""
PolicySetu Rule Evaluator.
Executes deterministic AST condition trees against citizen profiles.
"""

from typing import Dict, Any, List, Tuple, Union, Optional
import sys
from pathlib import Path

_CUR = Path(__file__).resolve()
while _CUR.name != "AI" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_AI_DIR = _CUR
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

try:
    from .models import (
        Rule,
        LogicGroup,
        SchemeRuleSet,
        RuleStatus,
        RuleEvaluationResult,
        ApplicantProfile,
        RuleType
    )
    from .operators import evaluate_operator
    from .logic import evaluate_and, evaluate_or, evaluate_not, evaluate_group_operator
    from .exceptions import RuleEngineError
except (ImportError, ValueError):
    from src.rules.models import (
        Rule,
        LogicGroup,
        SchemeRuleSet,
        RuleStatus,
        RuleEvaluationResult,
        ApplicantProfile,
        RuleType,
    )
    from src.rules.operators import evaluate_operator
    from src.rules.logic import (
        evaluate_and,
        evaluate_or,
        evaluate_not,
        evaluate_group_operator,
    )
    from src.rules.exceptions import RuleEngineError

class RuleEvaluator:
    """Evaluates rules and rule sets deterministically with zero hallucinations."""

    @staticmethod
    def _coerce_profile(profile: Union[ApplicantProfile, Dict[str, Any]]) -> ApplicantProfile:
        if isinstance(profile, ApplicantProfile):
            return profile
        if isinstance(profile, dict):
            return ApplicantProfile(profile)
        raise RuleEngineError(f"Invalid profile type: {type(profile)}. Expected dict or ApplicantProfile.")

    def evaluate_rule(
        self,
        rule: Rule,
        profile: Union[ApplicantProfile, Dict[str, Any]]
    ) -> RuleEvaluationResult:
        """Evaluates an atomic rule against an applicant profile."""
        prof = self._coerce_profile(profile)
        
        applicant_val = prof.get_value(rule.field)
        has_conflict = prof.has_conflict(rule.field)

        status, reason = evaluate_operator(
            operator=rule.operator,
            applicant_val=applicant_val,
            expected_val=rule.expected_value,
            field_name=rule.field,
            has_conflict=has_conflict
        )

        return RuleEvaluationResult(
            rule_id=rule.rule_id,
            rule_type=rule.rule_type,
            field=rule.field,
            operator=rule.operator,
            status=status,
            applicant_value=applicant_val,
            expected_value=rule.expected_value,
            hard_constraint=rule.hard_constraint,
            reason=reason,
            raw_text=rule.raw_text,
            rule=rule
        )

    def evaluate_ruleset(
        self,
        ruleset: SchemeRuleSet,
        profile: Union[ApplicantProfile, Dict[str, Any]]
    ) -> Tuple[RuleStatus, List[RuleEvaluationResult]]:
        """
        Evaluates a complete scheme rule set against an applicant profile.
        
        Evaluation Protocol:
        1. Evaluate all atomic rules.
        2. Evaluate composite logic groups if defined.
        3. Combine logic group statuses and top-level rules using ruleset.root_logic (AND/OR).
        4. Invariant: Any hard constraint failure produces overall FAIL (immediate disqualification).
        """
        prof = self._coerce_profile(profile)
        rule_results: List[RuleEvaluationResult] = []
        rule_map: Dict[str, RuleEvaluationResult] = {}

        for rule in ruleset.rules:
            res = self.evaluate_rule(rule, prof)
            rule_results.append(res)
            rule_map[rule.rule_id] = res

        # 1. Critical Invariant: Hard constraint check
        # If any hard constraint fails, the overall outcome must be FAIL
        hard_failures = [
            r for r in rule_results
            if r.hard_constraint and r.status == RuleStatus.FAIL
        ]
        if hard_failures:
            return (RuleStatus.FAIL, rule_results)

        # 2. If composite logic groups are explicitly defined:
        if ruleset.logic_groups:
            group_statuses: List[RuleStatus] = []
            grouped_rule_ids = set()

            for lg in ruleset.logic_groups:
                member_statuses = [
                    rule_map[rid].status for rid in lg.rule_ids if rid in rule_map
                ]
                grouped_rule_ids.update(lg.rule_ids)
                grp_status = evaluate_group_operator(lg.operator, member_statuses)
                group_statuses.append(grp_status)

            # Collect ungrouped rules
            ungrouped_statuses = [
                r.status for r in rule_results if r.rule_id not in grouped_rule_ids
            ]
            all_top_level = group_statuses + ungrouped_statuses
            overall_status = evaluate_group_operator(ruleset.root_logic, all_top_level)
            return (overall_status, rule_results)

        # 3. If logic_groups attribute on rules is used (e.g. DEFAULT, EXCLUSIONS_GROUP, etc.):
        logic_groups_dict: Dict[str, List[RuleEvaluationResult]] = {}
        for res in rule_results:
            grp = getattr(res.rule, "logic_group", "DEFAULT") if res.rule else "DEFAULT"
            logic_groups_dict.setdefault(grp, []).append(res)

        # Evaluate each named group
        group_verdicts: List[RuleStatus] = []
        for grp_name, group_res in logic_groups_dict.items():
            grp_statuses = [r.status for r in group_res]
            # If group name contains OR, evaluate as OR; if NOT, evaluate as NOT; else AND
            if "OR" in grp_name.upper():
                group_verdicts.append(evaluate_or(grp_statuses))
            elif "NOT" in grp_name.upper():
                group_verdicts.append(evaluate_not(evaluate_and(grp_statuses)))
            else:
                group_verdicts.append(evaluate_and(grp_statuses))

        overall_status = evaluate_group_operator(ruleset.root_logic, group_verdicts)
        return (overall_status, rule_results)