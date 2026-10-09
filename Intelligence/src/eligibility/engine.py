"""
FIN Deterministic Eligibility Engine.
Evaluates citizen profiles against statutory government policy rules with zero hallucinations.
Enforces multi-version registration, activation gates, deterministic rollback, and audit traces.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Union

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.rules.evaluator import RuleEvaluator
from src.rules.exceptions import RuleEngineError
from src.rules.models import ApplicantProfile, RuleStatus, SchemeRuleSet
from src.rules.operators import SUPPORTED_OPERATORS
from src.rules.validator import RuleValidator
from src.rules.versioning import SchemeRuleRegistry

try:
    from .decision import EligibilityDecision
except (ImportError, ValueError):
    from src.eligibility.decision import EligibilityDecision

logger = logging.getLogger("fin.eligibility.engine")


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
    - Historical decisions remain pinned to the exact rule version evaluated
    """

    def __init__(self, rules_dir: Optional[Union[str, Path]] = None):
        self._validator = RuleValidator()
        self._registry = SchemeRuleRegistry(self._validator)
        self._evaluator = RuleEvaluator()
        if rules_dir:
            self.load_rules_from_directory(rules_dir)

    @property
    def _rulesets(self) -> Dict[str, SchemeRuleSet]:
        """Backward-compatibility property returning active rulesets keyed by slug and scheme_id."""
        mapping: Dict[str, SchemeRuleSet] = {}
        for rset in self._registry.get_all_active_rulesets():
            mapping[rset.scheme_slug] = rset
            if rset.scheme_id:
                mapping[rset.scheme_id] = rset
        return mapping

    @property
    def supported_operators(self) -> List[str]:
        """Returns list of supported comparison and logical operators."""
        return sorted(list(SUPPORTED_OPERATORS))

    @property
    def supported_decision_states(self) -> List[str]:
        """Returns list of supported four-state decision statuses."""
        return [s.value for s in RuleStatus]

    def load_rules_from_file(self, file_path: Union[str, Path]) -> SchemeRuleSet:
        """Loads and registers a SchemeRuleSet from a JSON file into the registry."""
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"Rule file not found: {file_path}")
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        ruleset = SchemeRuleSet.from_dict(data)
        # Register and activate with validation
        self._registry.register_ruleset(ruleset, activate=True, validate=True)
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
                logger.debug("Skipping file %s: %s", f.name, e)
                continue
        return count

    def register_ruleset(self, ruleset: SchemeRuleSet, activate: bool = True) -> None:
        """Registers a scheme rule set under its slug and ID."""
        self._registry.register_ruleset(ruleset, activate=activate, validate=True)

    def activate_version(self, identifier: str, version: str) -> None:
        """Activates a specific version of a scheme rule set."""
        self._registry.activate_version(identifier, version)

    def rollback_version(self, identifier: str, target_version: str) -> None:
        """Rolls back the active version to a specified prior version."""
        self._registry.rollback_version(identifier, target_version)

    def get_ruleset(self, identifier: str, version: Optional[str] = None) -> SchemeRuleSet:
        """Retrieves a registered scheme rule set by slug or ID, optionally pinned to version."""
        if version:
            return self._registry.get_ruleset_version(identifier, version)
        return self._registry.get_active_ruleset(identifier)

    def evaluate(
        self,
        identifier: str,
        profile: Union[ApplicantProfile, Dict[str, Any]],
        version: Optional[str] = None,
        applicant_id: Optional[str] = None,
    ) -> EligibilityDecision:
        """
        Evaluates an applicant profile against a registered scheme rule set.
        Guaranteed to be deterministic, idempotent, and version-pinned.
        If scheme is not registered, returns UNKNOWN (never passes, never fails).
        """
        # Scenario 17: Unregistered scheme handling
        try:
            ruleset = self.get_ruleset(identifier, version=version)
        except KeyError:
            return EligibilityDecision(
                scheme_id=identifier,
                scheme_slug=identifier,
                scheme_name=identifier,
                status=RuleStatus.UNKNOWN,
                eligible=None,
                missing_fields=[f"scheme_{identifier}_not_registered"],
                disqualification_reasons=[],
                review_reasons=[f"Scheme '{identifier}' is not registered in the statutory rule engine."],
                applicant_id=applicant_id,
                rule_version="UNREGISTERED",
                completeness="UNSTRUCTURED",
            )

        overall_status, rule_results = self._evaluator.evaluate_ruleset(ruleset, profile)
        ruleset_hash = self._registry.get_hash(identifier, version=ruleset.version)

        return EligibilityDecision.from_evaluation(
            scheme_id=ruleset.scheme_id,
            scheme_slug=ruleset.scheme_slug,
            scheme_name=ruleset.scheme_name,
            overall_status=overall_status,
            rule_results=rule_results,
            rule_version=ruleset.version,
            rule_set_hash=ruleset_hash,
            applicant_id=applicant_id,
        )

    def evaluate_applicant_context(
        self,
        identifier: str,
        context: Any,
        version: Optional[str] = None,
    ) -> EligibilityDecision:
        """
        Binds directly to ApplicantContext, converting canonical facts to ApplicantProfile
        while preserving applicant ID and conflict annotations.
        """
        applicant_id = getattr(context, "applicant_id", None)
        if hasattr(context, "to_applicant_profile"):
            profile = context.to_applicant_profile()
        elif isinstance(context, dict):
            profile = ApplicantProfile(context)
            applicant_id = applicant_id or context.get("applicant_id")
        else:
            profile = ApplicantProfile(context)

        return self.evaluate(
            identifier=identifier,
            profile=profile,
            version=version,
            applicant_id=applicant_id,
        )

    def evaluate_all(
        self,
        profile: Union[ApplicantProfile, Dict[str, Any]],
        version: Optional[str] = None,
    ) -> List[EligibilityDecision]:
        """Evaluates an applicant profile against all unique registered schemes."""
        active_rulesets = self._registry.get_all_active_rulesets()
        decisions: List[EligibilityDecision] = []
        for rset in active_rulesets:
            dec = self.evaluate(rset.scheme_slug, profile, version=version)
            decisions.append(dec)
        return decisions

    def get_eligible_schemes(
        self,
        profile: Union[ApplicantProfile, Dict[str, Any]],
    ) -> List[EligibilityDecision]:
        """Returns all schemes where applicant satisfies 100% of criteria (PASS)."""
        return [d for d in self.evaluate_all(profile) if d.status == RuleStatus.PASS]

    def get_potential_schemes(
        self,
        profile: Union[ApplicantProfile, Dict[str, Any]],
    ) -> List[EligibilityDecision]:
        """
        Returns all schemes where applicant is not disqualified, but missing
        information requires follow-up user input (UNKNOWN).
        """
        return [d for d in self.evaluate_all(profile) if d.status == RuleStatus.UNKNOWN]

    def get_disqualified_schemes(
        self,
        profile: Union[ApplicantProfile, Dict[str, Any]],
    ) -> List[EligibilityDecision]:
        """Returns all schemes where applicant fails one or more hard statutory criteria (FAIL)."""
        return [d for d in self.evaluate_all(profile) if d.status == RuleStatus.FAIL]

    def get_review_schemes(
        self,
        profile: Union[ApplicantProfile, Dict[str, Any]],
    ) -> List[EligibilityDecision]:
        """Returns all schemes requiring manual administrative review (REVIEW)."""
        return [d for d in self.evaluate_all(profile) if d.status == RuleStatus.REVIEW]
