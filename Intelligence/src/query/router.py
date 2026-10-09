"""
FIN Query Routing Abstraction.
Directs structured queries to appropriate downstream processing pipelines.
"""

from typing import Tuple

from src.query.models import CanonicalIntent, DownstreamRoute


ROUTE_MAP = {
    CanonicalIntent.PERSONAL_FACT_LOOKUP: (
        DownstreamRoute.PERSONAL_FACT_SERVICE,
        "Route to PersonalFactService to retrieve applicant facts and supporting evidence"
    ),
    CanonicalIntent.DOCUMENT_QUERY: (
        DownstreamRoute.DOCUMENT_CONTEXT_SERVICE,
        "Route to DocumentContextService to inspect ingested documents and provenance"
    ),
    CanonicalIntent.SCHEME_RECOMMENDATION: (
        DownstreamRoute.SCHEME_RECOMMENDATION_PIPELINE,
        "Route to Phase 19 Scheme Recommendation pipeline for discovery and matching"
    ),
    CanonicalIntent.SCHEME_DISCOVERY: (
        DownstreamRoute.SCHEME_RECOMMENDATION_PIPELINE,
        "Route to Phase 19 Scheme Recommendation pipeline for discovery and matching"
    ),
    CanonicalIntent.ELIGIBILITY_QUERY: (
        DownstreamRoute.ELIGIBILITY_PIPELINE,
        "Route to deterministic RuleEvaluator eligibility pipeline"
    ),
    CanonicalIntent.ELIGIBILITY_QUESTION: (
        DownstreamRoute.ELIGIBILITY_PIPELINE,
        "Route to deterministic RuleEvaluator eligibility pipeline"
    ),
    CanonicalIntent.BENEFIT_QUERY: (
        DownstreamRoute.BENEFIT_PIPELINE,
        "Route to BenefitCalculator for statutory assistance quantification"
    ),
    CanonicalIntent.BENEFIT_QUESTION: (
        DownstreamRoute.BENEFIT_PIPELINE,
        "Route to BenefitCalculator for statutory assistance quantification"
    ),
    CanonicalIntent.POLICY_INFORMATION: (
        DownstreamRoute.POLICY_RAG,
        "Route to grounded Policy RAG for statutory guidance and scheme overview"
    ),
    CanonicalIntent.GENERAL_INFORMATION: (
        DownstreamRoute.POLICY_RAG,
        "Route to grounded Policy RAG for statutory guidance and scheme overview"
    ),
    CanonicalIntent.DOCUMENT_REQUIREMENTS: (
        DownstreamRoute.DOCUMENT_GUIDANCE,
        "Route to Document Guidance layer for mandatory upload requirements"
    ),
    CanonicalIntent.MISSING_INFORMATION: (
        DownstreamRoute.COMPLETENESS_SERVICE,
        "Route to Context Completeness Service to explain missing applicant facts"
    ),
    CanonicalIntent.DECISION_EXPLANATION: (
        DownstreamRoute.EXPLANATION_SERVICE,
        "Route to Grounded Explanation Service for AST rule evaluation audit"
    ),
    CanonicalIntent.CLARIFICATION_REQUIRED: (
        DownstreamRoute.CLARIFICATION_HANDLER,
        "Route to Clarification Handler due to ambiguity or neutralized adversarial input"
    ),
    CanonicalIntent.UNKNOWN: (
        DownstreamRoute.UNKNOWN_HANDLER,
        "Route to fallback assistant dialogue"
    ),
}


class QueryRouter:
    """Computes routing target for canonical intent."""

    @staticmethod
    def route(intent: CanonicalIntent) -> Tuple[DownstreamRoute, str]:
        """Returns (downstream_route, reason)."""
        return ROUTE_MAP.get(
            intent,
            (DownstreamRoute.UNKNOWN_HANDLER, "Default fallback route for unclassified intent")
        )
