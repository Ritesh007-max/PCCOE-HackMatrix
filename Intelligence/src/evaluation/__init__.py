"""
FIN Phase 13 Evaluation & Red Team Module.
Comprehensive benchmarking harness measuring retrieval quality, eligibility determinism,
document fact extraction, evidence grounding, multilingual invariance, and security red teaming.
"""

from .models import (
    EvaluationCase,
    EvaluationResult,
    EvaluationRun,
    Severity,
    EvaluationCategory,
)
from .failures import FailureType, classify_failure
from .metrics import MetricAggregator
from .retrieval_eval import RetrievalEvaluator
from .eligibility_eval import EligibilityEvaluator
from .extraction_eval import DocumentExtractionEvaluator
from .grounding_eval import GroundingEvaluator
from .multilingual_eval import MultilingualEvaluator
from .red_team import RedTeamEvaluator
from .security_eval import APISecurityEvaluator
from .reports import ReportManager
from .runner import EvaluationSuiteRunner

__all__ = [
    "EvaluationCase",
    "EvaluationResult",
    "EvaluationRun",
    "Severity",
    "EvaluationCategory",
    "FailureType",
    "classify_failure",
    "MetricAggregator",
    "RetrievalEvaluator",
    "EligibilityEvaluator",
    "DocumentExtractionEvaluator",
    "GroundingEvaluator",
    "MultilingualEvaluator",
    "RedTeamEvaluator",
    "APISecurityEvaluator",
    "ReportManager",
    "EvaluationSuiteRunner",
]
