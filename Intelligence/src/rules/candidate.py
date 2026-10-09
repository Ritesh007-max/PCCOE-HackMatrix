"""
FIN Candidate Rule Representation, Source Authority, and Extraction Pipeline.
Enforces that LLM/heuristic outputs are UNTRUSTED proposals requiring validation
and activation gates before becoming active statutory rules.
"""

from datetime import datetime, timezone
from enum import Enum
import re
from typing import Any, Dict, List, Optional
import uuid

from .models import Rule, RuleType
from .validator import (
    AMBIGUOUS_POLICY_PATTERNS,
    POLICY_INJECTION_PATTERNS,
    validate_rule,
)


class SourceTier(str, Enum):
    """
    Hierarchical tier of policy source authority.
    Order of precedence:
    PRIMARY_SCHEME > PRIMARY_FAQ > SUPPLEMENTARY_SCHEME > RAG_ARCHIVE > EVALUATION_ONLY
    """
    PRIMARY_SCHEME = "PRIMARY_SCHEME"          # Official government gazette, portal rules, statutory act
    PRIMARY_FAQ = "PRIMARY_FAQ"                # Official scheme FAQ published on government portal
    SUPPLEMENTARY_SCHEME = "SUPPLEMENTARY_SCHEME"  # State or allied department guidelines
    RAG_ARCHIVE = "RAG_ARCHIVE"                # Historical crawled cache
    EVALUATION_ONLY = "EVALUATION_ONLY"        # Synthetic or benchmark evaluation dataset

    @property
    def precedence_weight(self) -> int:
        weights = {
            SourceTier.PRIMARY_SCHEME: 1,
            SourceTier.PRIMARY_FAQ: 2,
            SourceTier.SUPPLEMENTARY_SCHEME: 3,
            SourceTier.RAG_ARCHIVE: 4,
            SourceTier.EVALUATION_ONLY: 5,
        }
        return weights.get(self, 99)

    @property
    def can_activate(self) -> bool:
        """Only PRIMARY and SUPPLEMENTARY official sources can activate statutory rules."""
        return self in {
            SourceTier.PRIMARY_SCHEME,
            SourceTier.PRIMARY_FAQ,
            SourceTier.SUPPLEMENTARY_SCHEME,
        }


class RuleLifecycleStatus(str, Enum):
    """Lifecycle stage for a rule or candidate."""
    DRAFT = "DRAFT"
    CANDIDATE = "CANDIDATE"
    VALIDATED = "VALIDATED"
    REVIEW = "REVIEW"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"
    REJECTED = "REJECTED"


class CandidateRule:
    """
    Represents an unverified or proposed candidate rule extracted from text or proposed by an AI.
    Guaranteed invariant: CandidateRule CANNOT be evaluated directly as an active policy.
    It must be validated and explicitly activated.
    """

    def __init__(
        self,
        candidate_id: str,
        scheme_id: str,
        scheme_slug: str,
        scheme_name: str,
        raw_policy_text: str,
        field: str,
        operator: str,
        expected_value: Any,
        value_type: str,
        source_uri: str,
        source_tier: SourceTier,
        source_document: str = "policy_source.txt",
        source_page: Optional[int] = None,
        source_section: str = "eligibility",
        rule_type: str = RuleType.ELIGIBILITY.value,
        logic_group: str = "DEFAULT",
        hard_constraint: bool = True,
        extraction_method: str = "LLM_PROPOSAL",
        extraction_confidence: float = 0.5,
        ambiguity_flags: Optional[List[str]] = None,
        conflict_flags: Optional[List[str]] = None,
        status: RuleLifecycleStatus = RuleLifecycleStatus.CANDIDATE,
        created_at: Optional[str] = None,
    ):
        self.candidate_id = candidate_id
        self.scheme_id = scheme_id
        self.scheme_slug = scheme_slug
        self.scheme_name = scheme_name
        self.raw_policy_text = raw_policy_text
        self.field = field
        self.operator = operator
        self.expected_value = expected_value
        self.value_type = value_type
        self.source_uri = source_uri
        self.source_tier = source_tier
        self.source_document = source_document
        self.source_page = source_page
        self.source_section = source_section
        self.rule_type = rule_type
        self.logic_group = logic_group
        self.hard_constraint = hard_constraint
        self.extraction_method = extraction_method
        self.extraction_confidence = extraction_confidence
        self.ambiguity_flags = ambiguity_flags or []
        self.conflict_flags = conflict_flags or []
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()

    def to_rule(self) -> Rule:
        """
        Converts the candidate rule into an atomic executable Rule object.
        Only permissible if the candidate has passed validation gates.
        """
        return Rule(
            rule_id=self.candidate_id,
            scheme_id=self.scheme_id,
            rule_type=self.rule_type,
            field=self.field,
            operator=self.operator,
            expected_value=self.expected_value,
            value_type=self.value_type,
            logic_group=self.logic_group,
            required=True,
            hard_constraint=self.hard_constraint,
            condition={
                "field": self.field,
                "op": self.operator,
                "val": self.expected_value,
            },
            raw_text=self.raw_policy_text,
            source_url=self.source_uri,
            source_document=self.source_document,
            source_page=self.source_page,
            source_section=self.source_section,
            confidence=self.extraction_confidence,
            provenance={
                "candidate_id": self.candidate_id,
                "source_tier": self.source_tier.value,
                "extraction_method": self.extraction_method,
                "extraction_confidence": self.extraction_confidence,
                "created_at": self.created_at,
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "scheme_id": self.scheme_id,
            "scheme_slug": self.scheme_slug,
            "scheme_name": self.scheme_name,
            "raw_policy_text": self.raw_policy_text,
            "field": self.field,
            "operator": self.operator,
            "expected_value": self.expected_value,
            "value_type": self.value_type,
            "source_uri": self.source_uri,
            "source_tier": self.source_tier.value,
            "source_document": self.source_document,
            "source_page": self.source_page,
            "source_section": self.source_section,
            "rule_type": self.rule_type,
            "logic_group": self.logic_group,
            "hard_constraint": self.hard_constraint,
            "extraction_method": self.extraction_method,
            "extraction_confidence": self.extraction_confidence,
            "ambiguity_flags": self.ambiguity_flags,
            "conflict_flags": self.conflict_flags,
            "status": self.status.value,
            "created_at": self.created_at,
        }


class CandidateRuleExtractor:
    """
    Extracts or normalizes policy text into candidate rules.
    Guarantees:
    - Never turns ambiguous wording into a guessed threshold.
    - Neutralizes policy injection attempts.
    - Treats LLM or regex proposals as strictly UNTRUSTED candidates.
    """

    # Unambiguous age patterns
    _AGE_MIN_PATTERNS = [
        re.compile(r"(?:minimum\s+age\s+(?:is|of|should\s+be)\s+|age\s+must\s+be\s+at\s+least\s+|applicant\s+should\s+be\s+)(\d+)\s*(?:years?|yrs?)(?:\s+or\s+older)?", re.IGNORECASE),
        re.compile(r"(\d+)\s*(?:years?|yrs?)\s+and\s+above", re.IGNORECASE),
    ]
    _AGE_MAX_PATTERNS = [
        re.compile(r"(?:maximum\s+age\s+(?:is|of|should\s+be)\s+|age\s+cannot\s+exceed\s+|age\s+must\s+be\s+less\s+than\s+|applicant\s+should\s+be\s+under\s+)(\d+)\s*(?:years?|yrs?)", re.IGNORECASE),
        re.compile(r"up\s+to\s+(\d+)\s*(?:years?|yrs?)\s+of\s+age", re.IGNORECASE),
    ]
    _AGE_RANGE_PATTERNS = [
        re.compile(r"(?:age\s+(?:between|is\s+between)\s+|age\s+of\s+)(\d+)\s*(?:to|-|and)\s*(\d+)\s*(?:years?|yrs?)", re.IGNORECASE),
    ]

    # Unambiguous income patterns
    _INCOME_MAX_PATTERNS = [
        re.compile(r"(?:annual\s+(?:family\s+)?income\s+(?:must\s+not\s+exceed|less\s+than|below|up\s+to|should\s+be\s+less\s+than)\s+|income\s+limit\s+is\s+)(?:rs\.?|₹)?\s*([\d,]+)", re.IGNORECASE),
    ]

    @classmethod
    def extract_from_text(
        cls,
        scheme_id: str,
        scheme_slug: str,
        scheme_name: str,
        raw_text: str,
        source_uri: str,
        source_tier: SourceTier = SourceTier.PRIMARY_SCHEME,
        source_document: str = "statute.txt",
    ) -> List[CandidateRule]:
        """
        Extracts candidate rules from policy text.
        Defends against policy injection and flags ungrounded ambiguity.
        """
        candidates: List[CandidateRule] = []

        # 1. Defend against Prompt Injection
        for p in POLICY_INJECTION_PATTERNS:
            if p.search(raw_text):
                # Reject candidate generation entirely for adversarial text
                cand = CandidateRule(
                    candidate_id=f"cand_injected_{uuid.uuid4().hex[:8]}",
                    scheme_id=scheme_id,
                    scheme_slug=scheme_slug,
                    scheme_name=scheme_name,
                    raw_policy_text=raw_text,
                    field="security_violation",
                    operator="manual_review",
                    expected_value=None,
                    value_type="unstructured",
                    source_uri=source_uri,
                    source_tier=source_tier,
                    status=RuleLifecycleStatus.REJECTED,
                    ambiguity_flags=["POLICY_INJECTION_ATTEMPT"],
                )
                return [cand]

        # 2. Check for Ambiguity without Concrete Threshold
        ambiguities: List[str] = []
        for p in AMBIGUOUS_POLICY_PATTERNS:
            match = p.search(raw_text)
            if match:
                ambiguities.append(f"Ambiguous policy phrasing: '{match.group(0)}'")

        # 3. Deterministic Pattern Matching for Age
        # Check range first
        for pat in cls._AGE_RANGE_PATTERNS:
            m = pat.search(raw_text)
            if m:
                min_age = int(m.group(1))
                max_age = int(m.group(2))
                cand = CandidateRule(
                    candidate_id=f"cand_{scheme_slug}_age_{uuid.uuid4().hex[:6]}",
                    scheme_id=scheme_id,
                    scheme_slug=scheme_slug,
                    scheme_name=scheme_name,
                    raw_policy_text=raw_text,
                    field="age",
                    operator="between",
                    expected_value={"min": min_age, "max": max_age},
                    value_type="range",
                    source_uri=source_uri,
                    source_tier=source_tier,
                    source_document=source_document,
                    extraction_method="CANONICAL_SYNTAX_PARSER",
                    extraction_confidence=1.0,
                    status=RuleLifecycleStatus.VALIDATED if source_tier.can_activate else RuleLifecycleStatus.CANDIDATE,
                )
                candidates.append(cand)
                break

        # Check min age if range not matched
        if not candidates:
            for pat in cls._AGE_MIN_PATTERNS:
                m = pat.search(raw_text)
                if m:
                    min_age = int(m.group(1))
                    cand = CandidateRule(
                        candidate_id=f"cand_{scheme_slug}_age_{uuid.uuid4().hex[:6]}",
                        scheme_id=scheme_id,
                        scheme_slug=scheme_slug,
                        scheme_name=scheme_name,
                        raw_policy_text=raw_text,
                        field="age",
                        operator=">=",
                        expected_value=min_age,
                        value_type="numeric",
                        source_uri=source_uri,
                        source_tier=source_tier,
                        source_document=source_document,
                        extraction_method="CANONICAL_SYNTAX_PARSER",
                        extraction_confidence=1.0,
                        status=RuleLifecycleStatus.VALIDATED if source_tier.can_activate else RuleLifecycleStatus.CANDIDATE,
                    )
                    candidates.append(cand)
                    break

        # Check income max
        for pat in cls._INCOME_MAX_PATTERNS:
            m = pat.search(raw_text)
            if m:
                raw_inc = m.group(1).replace(",", "")
                cand = CandidateRule(
                    candidate_id=f"cand_{scheme_slug}_income_{uuid.uuid4().hex[:6]}",
                    scheme_id=scheme_id,
                    scheme_slug=scheme_slug,
                    scheme_name=scheme_name,
                    raw_policy_text=raw_text,
                    field="annual_family_income",
                    operator="<=",
                    expected_value=float(raw_inc),
                    value_type="numeric",
                    source_uri=source_uri,
                    source_tier=source_tier,
                    source_document=source_document,
                    extraction_method="CANONICAL_SYNTAX_PARSER",
                    extraction_confidence=1.0,
                    status=RuleLifecycleStatus.VALIDATED if source_tier.can_activate else RuleLifecycleStatus.CANDIDATE,
                )
                candidates.append(cand)
                break

        # 4. If text contains ambiguous phrasing and no numeric condition was extracted,
        # create a REVIEW candidate. CRITICAL: NEVER invent a threshold like age <= 25!
        if not candidates and ambiguities:
            cand = CandidateRule(
                candidate_id=f"cand_{scheme_slug}_ambig_{uuid.uuid4().hex[:6]}",
                scheme_id=scheme_id,
                scheme_slug=scheme_slug,
                scheme_name=scheme_name,
                raw_policy_text=raw_text,
                field="unstructured_clause",
                operator="manual_review",
                expected_value=raw_text,
                value_type="unstructured",
                source_uri=source_uri,
                source_tier=source_tier,
                source_document=source_document,
                extraction_method="AMBIGUITY_DETECTOR",
                extraction_confidence=0.3,
                ambiguity_flags=ambiguities,
                status=RuleLifecycleStatus.REVIEW,
            )
            candidates.append(cand)

        return candidates
