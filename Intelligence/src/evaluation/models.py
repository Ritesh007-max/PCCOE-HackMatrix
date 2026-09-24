"""
FIN Phase 13 Evaluation Models.
Defines common data structures for test cases, results, and benchmark runs.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from typing import Any, Dict, List, Optional


class Severity(str, Enum):
    """Red team and evaluation defect severity levels."""
    CRITICAL = "CRITICAL"  # Unauthorized PASS/FAIL, policy override, historical mutation, secret leakage
    HIGH = "HIGH"          # Unsupported statutory claim, incorrect rule eval, authority confusion
    MEDIUM = "MEDIUM"      # Retrieval failure, language failure, citation mismatch
    LOW = "LOW"            # Formatting issue, non-critical metadata issue
    INFO = "INFO"          # Informational observation / baseline recording


class EvaluationCategory(str, Enum):
    """Categorization for evaluation suites and benchmarks."""
    DATA_QUALITY = "DATA_QUALITY"
    RETRIEVAL = "RETRIEVAL"
    EXTRACTION = "EXTRACTION"
    ELIGIBILITY = "ELIGIBILITY"
    GROUNDING = "GROUNDING"
    GUIDANCE = "GUIDANCE"
    API_BEHAVIOR = "API_BEHAVIOR"
    SECURITY_RED_TEAM = "SECURITY_RED_TEAM"
    POLICY_RESILIENCE = "POLICY_RESILIENCE"
    MULTILINGUAL = "MULTILINGUAL"
    END_TO_END = "END_TO_END"


@dataclass
class EvaluationCase:
    """A single evaluation or red-team test case."""
    case_id: str
    category: EvaluationCategory
    input_data: Any
    expected_output: Any = None
    expected_status: Optional[Any] = None
    expected_sources: List[str] = field(default_factory=list)
    expected_scheme_id: Optional[str] = None
    expected_language: str = "en"
    severity: Severity = Severity.MEDIUM
    tags: List[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "category": self.category.value,
            "input_data": self.input_data,
            "expected_output": self.expected_output,
            "expected_status": self.expected_status,
            "expected_sources": self.expected_sources,
            "expected_scheme_id": self.expected_scheme_id,
            "expected_language": self.expected_language,
            "severity": self.severity.value,
            "tags": self.tags,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvaluationCase":
        return cls(
            case_id=data["case_id"],
            category=EvaluationCategory(data["category"]),
            input_data=data.get("input_data") or data.get("input"),
            expected_output=data.get("expected_output"),
            expected_status=data.get("expected_status"),
            expected_sources=data.get("expected_sources", []),
            expected_scheme_id=data.get("expected_scheme_id"),
            expected_language=data.get("expected_language", "en"),
            severity=Severity(data.get("severity", "MEDIUM")),
            tags=data.get("tags", []),
            description=data.get("description", ""),
        )


@dataclass
class EvaluationResult:
    """Outcome of running an evaluation case."""
    case_id: str
    passed: bool
    actual_output: Any = None
    expected_output: Any = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    latency_ms: float = 0.0
    evidence_quality: Optional[float] = None
    grounding_quality: Optional[str] = None  # SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, CONTRADICTED
    failure_type: Optional[str] = None
    severity: Severity = Severity.MEDIUM

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "passed": self.passed,
            "actual_output": self.actual_output,
            "expected_output": self.expected_output,
            "errors": self.errors,
            "warnings": self.warnings,
            "latency_ms": self.latency_ms,
            "evidence_quality": self.evidence_quality,
            "grounding_quality": self.grounding_quality,
            "failure_type": self.failure_type,
            "severity": self.severity.value,
        }


@dataclass
class EvaluationRun:
    """Comprehensive benchmark execution record."""
    run_id: str
    started_at: str
    completed_at: str = ""
    suite_name: str = "full"
    total_cases: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    metrics: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    policy_snapshot_version: str = "snapshot_20260921_193823"
    rule_version: str = "1.0.0"
    rag_version: str = "1.0.0"
    model_provider_metadata: Dict[str, Any] = field(default_factory=dict)
    results: List[EvaluationResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "suite_name": self.suite_name,
            "total_cases": self.total_cases,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "metrics": self.metrics,
            "version": self.version,
            "policy_snapshot_version": self.policy_snapshot_version,
            "rule_version": self.rule_version,
            "rag_version": self.rag_version,
            "model_provider_metadata": self.model_provider_metadata,
            "results": [r.to_dict() for r in self.results],
        }
