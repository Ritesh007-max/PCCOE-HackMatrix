"""
FIN AST-Aware Missing Information Analyzer.
Traverses Phase 3 SchemeRuleSet AST condition trees (AND/OR/NOT logic groups)
to identify only the minimal set of unresolved applicant fields necessary to achieve PASS.
CRITICAL INVARIANT: Missing fields are NOT naive set subtraction (required - known).
They respect conditional branching, alternative OR pathways, and already-satisfied clauses.
"""

from typing import Any, Dict, List, Optional, Set
import sys
from pathlib import Path

# Ensure Intelligence directory is on sys.path
_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

try:
    from ..rules.models import (
        SchemeRuleSet,
        LogicGroup,
        Rule,
        RuleStatus,
        RuleEvaluationResult,
        ApplicantProfile,
    )
    from ..rules.evaluator import RuleEvaluator
except (ImportError, ValueError):
    from src.rules.models import (
        SchemeRuleSet,
        LogicGroup,
        Rule,
        RuleStatus,
        RuleEvaluationResult,
        ApplicantProfile,
    )
    from src.rules.evaluator import RuleEvaluator


class RuleASTMissingFieldAnalyzer:
    """
    Analyzes Phase 3 rule condition trees to find fields strictly necessary
    to turn an UNKNOWN decision into a PASS.
    """

    def __init__(self, evaluator: Optional[RuleEvaluator] = None):
        self.evaluator = evaluator or RuleEvaluator()

    def find_missing_fields_for_pass(
        self,
        ruleset: SchemeRuleSet,
        profile: ApplicantProfile
    ) -> List[str]:
        """
        Determines the unresolved fields that could resolve the ruleset to PASS.
        Returns empty list if already PASS or irreparably FAIL.
        """
        overall_status, rule_results = self.evaluator.evaluate_ruleset(ruleset, profile)

        # 1. If already PASS, no information is missing
        if overall_status == RuleStatus.PASS:
            return []

        # Map rule_id -> RuleEvaluationResult
        result_map: Dict[str, RuleEvaluationResult] = {r.rule_id: r for r in rule_results}
        rule_map: Dict[str, Rule] = {r.rule_id: r for r in ruleset.rules}

        # Case 1: Simple ruleset without logic groups
        if not ruleset.logic_groups:
            if ruleset.root_logic == "AND":
                # For AND, if any hard constraint already FAIL, no missing field can save it
                hard_fails = [
                    r for r in rule_results
                    if r.hard_constraint and r.status == RuleStatus.FAIL
                ]
                if hard_fails:
                    return []
                # All UNKNOWN fields are required
                missing = {
                    r.field for r in rule_results
                    if r.status == RuleStatus.UNKNOWN
                }
                return sorted(list(missing))
            else:
                # Root logic is OR:
                # If any rule is PASS, overall would be PASS (handled above)
                # Any rule that is UNKNOWN could potentially turn the OR into PASS
                unknown_fields = {
                    r.field for r in rule_results
                    if r.status == RuleStatus.UNKNOWN
                }
                return sorted(list(unknown_fields))

        # Case 2: Composite logic groups defined
        # Evaluate each group's viability and missing fields
        grouped_rule_ids: Set[str] = set()
        group_missing_map: Dict[str, Set[str]] = {}
        group_statuses: Dict[str, RuleStatus] = {}

        for group in ruleset.logic_groups:
            group_results = [result_map[rid] for rid in group.rule_ids if rid in result_map]
            for rid in group.rule_ids:
                grouped_rule_ids.add(rid)

            op = group.operator.upper()
            if op == "OR":
                # If any rule in OR group passed, the group passes -> 0 missing fields needed for this group
                if any(r.status == RuleStatus.PASS for r in group_results):
                    group_statuses[group.group_id] = RuleStatus.PASS
                    group_missing_map[group.group_id] = set()
                else:
                    # Collect unknown fields that could satisfy this OR group
                    unknown_in_group = {
                        r.field for r in group_results
                        if r.status == RuleStatus.UNKNOWN
                    }
                    group_missing_map[group.group_id] = unknown_in_group
                    group_statuses[group.group_id] = (
                        RuleStatus.UNKNOWN if unknown_in_group else RuleStatus.FAIL
                    )
            elif op == "AND":
                # If any hard constraint fails in AND group, group is FAIL
                if any(r.hard_constraint and r.status == RuleStatus.FAIL for r in group_results):
                    group_statuses[group.group_id] = RuleStatus.FAIL
                    group_missing_map[group.group_id] = set()
                elif all(r.status == RuleStatus.PASS for r in group_results):
                    group_statuses[group.group_id] = RuleStatus.PASS
                    group_missing_map[group.group_id] = set()
                else:
                    unknown_in_group = {
                        r.field for r in group_results
                        if r.status == RuleStatus.UNKNOWN
                    }
                    group_missing_map[group.group_id] = unknown_in_group
                    group_statuses[group.group_id] = RuleStatus.UNKNOWN
            else:
                # Default / other operator: collect UNKNOWN
                unknown_in_group = {
                    r.field for r in group_results
                    if r.status == RuleStatus.UNKNOWN
                }
                group_missing_map[group.group_id] = unknown_in_group
                group_statuses[group.group_id] = RuleStatus.UNKNOWN

        # Check top-level rules that are not part of any group
        ungrouped_results = [
            r for r in rule_results
            if r.rule_id not in grouped_rule_ids
        ]
        ungrouped_missing = {
            r.field for r in ungrouped_results
            if r.status == RuleStatus.UNKNOWN
        }

        # Combine logic according to root_logic
        root_op = ruleset.root_logic.upper()
        if root_op == "AND":
            # If any group is irrevocably FAIL, overall cannot pass
            if any(status == RuleStatus.FAIL for status in group_statuses.values()):
                return []
            if any(r.hard_constraint and r.status == RuleStatus.FAIL for r in ungrouped_results):
                return []

            # Needs all missing fields from all non-passing groups + ungrouped
            total_missing: Set[str] = set(ungrouped_missing)
            for fields in group_missing_map.values():
                total_missing.update(fields)
            return sorted(list(total_missing))
        else:
            # Root logic is OR:
            # Pick viable groups that require the minimal set of missing fields
            viable_sets = [
                fields for gid, fields in group_missing_map.items()
                if group_statuses.get(gid) != RuleStatus.FAIL and len(fields) > 0
            ]
            if ungrouped_missing:
                viable_sets.append(ungrouped_missing)

            if not viable_sets:
                return []

            # Return union of fields on viable paths, sorted
            all_viable_missing: Set[str] = set()
            for s in viable_sets:
                all_viable_missing.update(s)
            return sorted(list(all_viable_missing))
