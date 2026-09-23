"""
PolicySetu Deterministic Eligibility Engine.
Evaluates citizen profiles against statutory government policy rules with zero hallucinations.
"""

import json
from pathlib import Path
import sys
from typing import Dict, Any, List, Optional, Union

_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from src.rules.models import SchemeRuleSet, RuleStatus, ApplicantProfile
from src.rules.evaluator import RuleEvaluator
from src.rules.operators import SUPPORTED_OPERATORS
from src.rules.exceptions import RuleEngineError
try:
    from .decision import EligibilityDecision
except (ImportError, ValueError):
    from src.eligibility.decision import EligibilityDecision

class EligibilityEngine:
    """
    Deterministic rule engine that evaluates citizen profiles against policy rule sets.
    Enforces critical invariants:
    - UNKNOWN != PASS
    - UNKNOWN != FAIL
    - Hard constraint FAIL causes immediate disqualification
    - Contradictory evidence causes REVIEW
    - Same input always produces identical results (idempotent & pure)
    - LLMs are never permitted to decide eligibility
    """

    def __init__(self, rules_dir: Optional[Union[str, Path]] = None):
        self._evaluator = RuleEvaluator()
        self._rulesets: Dict[str, SchemeRuleSet] = {}
        if rules_dir:
            self.load_rules_from_directory(rules_dir)

    @property
    def supported_operators(self) -> List[str]:
        """Returns list of supported comparison and logical operators."""
        return sorted(list(SUPPORTED_OPERATORS))

    @property
    def supported_decision_states(self) -> List[str]:
        """Returns list of supported four-state decision statuses."""
        return [s.value for s in RuleStatus]

    def load_rules_from_file(self, file_path: Union[str, Path]) -> SchemeRuleSet:
        """Loads and registers a SchemeRuleSet from a JSON file."""
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"Rule file not found: {file_path}")
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        ruleset = SchemeRuleSet.from_dict(data)
        self.register_ruleset(ruleset)
        return ruleset

    def load_rules_from_directory(self, dir_path: Union[str, Path]) -> int:
        """Loads all *.json rule files from a directory into the engine registry."""
        p = Path(dir_path)
        if not p.exists() or not p.is_dir():
            raise NotADirectoryError(f"Directory not found: {dir_path}")
        count = 0
        for f in p.glob("*.json"):
            try:
                self.load_rules_from_file(f)
                count += 1
            except Exception as e:
                # Skip files that are not valid scheme rule sets (e.g. schemas)
                continue
        return count

    def register_ruleset(self, ruleset: SchemeRuleSet) -> None:
        """Registers a scheme rule set under its slug and ID."""
        self._rulesets[ruleset.scheme_slug] = ruleset
        if ruleset.scheme_id:
            self._rulesets[ruleset.scheme_id] = ruleset

    def get_ruleset(self, identifier: str) -> SchemeRuleSet:
        """Retrieves a registered scheme rule set by slug or ID."""
        if identifier not in self._rulesets:
            raise KeyError(f"Scheme rule set '{identifier}' is not registered in the engine.")
        return self._rulesets[identifier]

    def evaluate(
        self,
        identifier: str,
        profile: Union[ApplicantProfile, Dict[str, Any]]
    ) -> EligibilityDecision:
        """
        Evaluates an applicant profile against a registered scheme rule set.
        Guaranteed to be deterministic and idempotent.
        """
        ruleset = self.get_ruleset(identifier)
        overall_status, rule_results = self._evaluator.evaluate_ruleset(ruleset, profile)

        return EligibilityDecision.from_evaluation(
            scheme_id=ruleset.scheme_id,
            scheme_slug=ruleset.scheme_slug,
            scheme_name=ruleset.scheme_name,
            overall_status=overall_status,
            rule_results=rule_results
        )

    def evaluate_all(
        self,
        profile: Union[ApplicantProfile, Dict[str, Any]]
    ) -> List[EligibilityDecision]:
        """Evaluates an applicant profile against all unique registered schemes."""
        seen_slugs = set()
        decisions: List[EligibilityDecision] = []
        for slug, rset in self._rulesets.items():
            if rset.scheme_slug in seen_slugs:
                continue
            seen_slugs.add(rset.scheme_slug)
            dec = self.evaluate(rset.scheme_slug, profile)
            decisions.append(dec)
        return decisions

    def get_eligible_schemes(
        self,
        profile: Union[ApplicantProfile, Dict[str, Any]]
    ) -> List[EligibilityDecision]:
        """Returns all schemes where applicant satisfies 100% of criteria (PASS)."""
        return [d for d in self.evaluate_all(profile) if d.status == RuleStatus.PASS]

    def get_potential_schemes(
        self,
        profile: Union[ApplicantProfile, Dict[str, Any]]
    ) -> List[EligibilityDecision]:
        """
        Returns all schemes where applicant is not disqualified, but missing
        information requires follow-up user input (UNKNOWN).
        """
        return [d for d in self.evaluate_all(profile) if d.status == RuleStatus.UNKNOWN]

    def get_disqualified_schemes(
        self,
        profile: Union[ApplicantProfile, Dict[str, Any]]
    ) -> List[EligibilityDecision]:
        """Returns all schemes where applicant fails one or more hard statutory criteria (FAIL)."""
        return [d for d in self.evaluate_all(profile) if d.status == RuleStatus.FAIL]

    def get_review_schemes(
        self,
        profile: Union[ApplicantProfile, Dict[str, Any]]
    ) -> List[EligibilityDecision]:
        """Returns all schemes requiring manual administrative review (REVIEW)."""
        return [d for d in self.evaluate_all(profile) if d.status == RuleStatus.REVIEW]
