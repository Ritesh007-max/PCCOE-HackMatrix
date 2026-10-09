"""
FIN Recommendation Module.
Provides personalized scheme discovery, applicant-scheme compatibility scoring,
and statutory missing-field gap analysis.
"""

from .models import (
    CompatibilityResult,
    CompatibilityState,
    FactMatchDetail,
    MissingField,
    MissingFieldCriticality,
    RecommendationEvidence,
    SchemeRecommendationItem,
    SchemeRecommendationItemSchema,
    SchemeRecommendationRequest,
    SchemeRecommendationResponse,
    SchemeRecommendationResult,
)
from .bridge import ContextRetrievalBridge
from .compatibility import CompatibilityAnalyzer
from .gap_analysis import MissingFieldGapAnalyzer
from .service import SchemeRecommendationService

__all__ = [
    "CompatibilityResult",
    "CompatibilityState",
    "ContextRetrievalBridge",
    "CompatibilityAnalyzer",
    "FactMatchDetail",
    "MissingField",
    "MissingFieldCriticality",
    "MissingFieldGapAnalyzer",
    "RecommendationEvidence",
    "SchemeRecommendationItem",
    "SchemeRecommendationItemSchema",
    "SchemeRecommendationRequest",
    "SchemeRecommendationResponse",
    "SchemeRecommendationResult",
    "SchemeRecommendationService",
]
