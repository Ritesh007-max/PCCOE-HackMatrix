"""
FIN Query Understanding Module (Phase 18).
Provides canonical intent classification, conversational fact extraction,
entity/reference resolution, and structured query routing.
"""

from src.query.models import (
    CanonicalIntent,
    DownstreamRoute,
    QueryUnderstandingResult,
    QueryContext,
)
from src.query.intent_classifier import IntentClassifier
from src.query.fact_extractor import UserFactExtractor
from src.query.reference_resolver import ReferenceResolver
from src.query.router import QueryRouter
from src.query.service import QueryUnderstandingService

__all__ = [
    "CanonicalIntent",
    "DownstreamRoute",
    "QueryUnderstandingResult",
    "QueryContext",
    "IntentClassifier",
    "UserFactExtractor",
    "ReferenceResolver",
    "QueryRouter",
    "QueryUnderstandingService",
]
