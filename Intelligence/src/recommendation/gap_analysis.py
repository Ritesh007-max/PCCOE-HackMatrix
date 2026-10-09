"""
FIN Scheme Missing-Field Gap Analysis Engine.
Identifies applicant facts that are missing or conflicted which are genuinely
required to evaluate statutory scheme eligibility.

CRITICAL INVARIANTS:
1. Legal requirements are reported ONLY when backed by structured statutory rules.
2. For schemes lacking structured rule sets, missing_fields_status is set to UNKNOWN.
3. Missing fields are NEVER fabricated from freeform text or unverified datasets.
"""

import logging
from typing import Dict, List, Optional, Tuple

from src.context.models import ApplicantContext
from src.recommendation.models import MissingField, MissingFieldCriticality
from src.rag.models import SchemeRetrievalResult
from src.eligibility.engine import EligibilityEngine

logger = logging.getLogger("fin.recommendation.gap_analysis")


class MissingFieldGapAnalyzer:
    """
    Deterministic gap analyzer identifying missing statutory fields per scheme candidate.
    """

    def __init__(self, eligibility_engine: Optional[EligibilityEngine] = None):
        self.eligibility_engine = eligibility_engine

    def analyze(
        self,
        scheme: SchemeRetrievalResult,
        applicant_context: Optional[ApplicantContext],
    ) -> Tuple[List[MissingField], str]:
        """
        Analyzes missing fields for a scheme candidate.
        Returns:
            Tuple of (List[MissingField], missing_fields_status)
        """
        if not self.eligibility_engine:
            return [], "UNKNOWN"

        slug = scheme.scheme_slug
        # Check if the scheme has a registered SchemeRuleSet
        if slug not in self.eligibility_engine._rulesets:
            # Check by scheme_id if available
            scheme_id = scheme.best_matching_chunks[0].scheme_id if scheme.best_matching_chunks else None
            if not scheme_id or scheme_id not in self.eligibility_engine._rulesets:
                # No structured rules exist for this scheme -> report UNKNOWN, do NOT invent fields!
                return [], "UNKNOWN"
            ruleset = self.eligibility_engine.get_ruleset(scheme_id)
        else:
            ruleset = self.eligibility_engine.get_ruleset(slug)

        missing_fields: List[MissingField] = []
        seen_fields = set()

        conflicts = set(applicant_context.conflicts) if applicant_context else set()

        for rule in ruleset.rules:
            field_name = rule.field
            if field_name in seen_fields:
                continue

            # Check if applicant context has this fact and it is not in conflict
            has_fact = False
            is_conflicted = field_name in conflicts

            if applicant_context and not is_conflicted:
                val = applicant_context.get_value(field_name)
                if val is not None:
                    has_fact = True

            if not has_fact:
                seen_fields.add(field_name)
                crit = (
                    MissingFieldCriticality.MANDATORY
                    if rule.hard_constraint
                    else MissingFieldCriticality.OPTIONAL
                )
                reason_text = (
                    f"Required by statutory rule '{rule.rule_id}': {rule.raw_text}"
                    if rule.raw_text
                    else f"Mandatory eligibility parameter '{field_name}' required for {ruleset.scheme_name}."
                )
                if is_conflicted:
                    reason_text += " (Currently in conflict across applicant documents)."

                missing_fields.append(MissingField(
                    field=field_name,
                    reason=reason_text,
                    required_for="eligibility",
                    rule_id=rule.rule_id,
                    criticality=crit,
                ))

        return missing_fields, "DETERMINISTIC_RULES"
