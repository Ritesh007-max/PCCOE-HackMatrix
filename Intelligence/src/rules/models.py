"""
FIN Rule Engine Data Models and State Enumerations.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
import dataclasses
from dataclasses import dataclass

class RuleStatus(str, Enum):
    """
    Four-state decision status for rule evaluation.
    Enforces the critical invariant: UNKNOWN != PASS and UNKNOWN != FAIL.
    """
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    REVIEW = "REVIEW"

class RuleType(str, Enum):
    """Functional role of the rule."""
    ELIGIBILITY = "eligibility"
    EXCLUSION = "exclusion"
    CONDITIONAL = "conditional"
    DOCUMENT_REQUIREMENT = "document_requirement"
    BENEFIT_CONDITION = "benefit_condition"

@dataclass
class Rule:
    """Represents a single atomic condition rule in the FIN schema."""
    rule_id: str
    scheme_id: str
    rule_type: str
    field: str
    operator: str
    expected_value: Any
    value_type: str
    logic_group: str = "DEFAULT"
    required: bool = True
    hard_constraint: bool = True
    condition: Dict[str, Any] = dataclasses.field(default_factory=dict)
    raw_text: str = ""
    source_url: str = ""
    source_document: str = "schemes_canonical.parquet"
    source_page: Optional[int] = None
    source_section: str = "eligibility"
    confidence: float = 1.0
    provenance: Dict[str, Any] = dataclasses.field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Rule":
        return cls(
            rule_id=data["rule_id"],
            scheme_id=data.get("scheme_id", ""),
            rule_type=data.get("rule_type", RuleType.ELIGIBILITY.value),
            field=data["field"],
            operator=data["operator"],
            expected_value=data.get("expected_value"),
            value_type=data.get("value_type", "string"),
            logic_group=data.get("logic_group", "DEFAULT"),
            required=data.get("required", True),
            hard_constraint=data.get("hard_constraint", True),
            condition=data.get("condition", {}),
            raw_text=data.get("raw_text", ""),
            source_url=data.get("source_url", ""),
            source_document=data.get("source_document", "schemes_canonical.parquet"),
            source_page=data.get("source_page"),
            source_section=data.get("source_section", "eligibility"),
            confidence=float(data.get("confidence", 1.0)),
            provenance=data.get("provenance", {})
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "scheme_id": self.scheme_id,
            "rule_type": self.rule_type,
            "field": self.field,
            "operator": self.operator,
            "expected_value": self.expected_value,
            "value_type": self.value_type,
            "logic_group": self.logic_group,
            "required": self.required,
            "hard_constraint": self.hard_constraint,
            "condition": self.condition,
            "raw_text": self.raw_text,
            "source_url": self.source_url,
            "source_document": self.source_document,
            "source_page": self.source_page,
            "source_section": self.source_section,
            "confidence": self.confidence,
            "provenance": self.provenance
        }

@dataclass
class LogicGroup:
    """Represents a composite grouping of rules (AND, OR, NOT)."""
    group_id: str
    operator: str
    rule_ids: List[str]
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogicGroup":
        return cls(
            group_id=data["group_id"],
            operator=data.get("operator", "AND").upper(),
            rule_ids=list(data.get("rule_ids", [])),
            description=data.get("description")
        )

@dataclass
class SchemeRuleSet:
    """Complete rule set for a government scheme."""
    scheme_id: str
    scheme_slug: str
    scheme_name: str
    version: str = "1.0.0"
    last_updated: Optional[str] = None
    root_logic: str = "AND"
    rules: List[Rule] = dataclasses.field(default_factory=list)
    logic_groups: List[LogicGroup] = dataclasses.field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SchemeRuleSet":
        rules = [Rule.from_dict(r) for r in data.get("rules", [])]
        groups = [LogicGroup.from_dict(g) for g in data.get("logic_groups", [])]
        return cls(
            scheme_id=data.get("scheme_id", ""),
            scheme_slug=data.get("scheme_slug", ""),
            scheme_name=data.get("scheme_name", ""),
            version=data.get("version", "1.0.0"),
            last_updated=data.get("last_updated"),
            root_logic=data.get("root_logic", "AND").upper(),
            rules=rules,
            logic_groups=groups
        )

@dataclass
class RuleEvaluationResult:
    """Result of evaluating a single rule against an applicant profile."""
    rule_id: str
    rule_type: str
    field: str
    operator: str
    status: RuleStatus
    applicant_value: Any
    expected_value: Any
    hard_constraint: bool
    reason: str
    raw_text: str
    rule: Optional[Rule] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_type": self.rule_type,
            "field": self.field,
            "operator": self.operator,
            "status": self.status.value,
            "applicant_value": self.applicant_value,
            "expected_value": self.expected_value,
            "hard_constraint": self.hard_constraint,
            "reason": self.reason,
            "raw_text": self.raw_text
        }

class ApplicantProfile:
    """
    Applicant profile wrapper supporting direct attributes, metadata,
    and explicit tracking of conflicting/contradictory evidence.
    """
    def __init__(self, data: Optional[Dict[str, Any]] = None, conflicts: Optional[List[str]] = None):
        self._data: Dict[str, Any] = data or {}
        # Track fields that have contradictory evidence (e.g. from discordant documents)
        self._conflicts: set = set(conflicts or [])
        if "_conflicts" in self._data and isinstance(self._data["_conflicts"], (list, set)):
            self._conflicts.update(self._data["_conflicts"])

    @property
    def conflicts(self) -> List[str]:
        """Returns list of all fields marked conflicted."""
        return sorted(list(self._conflicts))

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def has_field(self, key: str) -> bool:
        return key in self._data and self._data[key] is not None

    def has_conflict(self, key: str) -> bool:
        """Returns True if the attribute has conflicting/contradictory evidence."""
        if key in self._conflicts:
            return True
        val = self._data.get(key)
        if isinstance(val, dict) and (val.get("conflict") is True or val.get("conflicting_evidence") is True):
            return True
        return False

    def get_value(self, key: str) -> Any:
        """Returns the unwrapped value of a field, handling nested dict value wrappers."""
        val = self._data.get(key)
        if isinstance(val, dict) and "value" in val:
            return val["value"]
        return val

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)
