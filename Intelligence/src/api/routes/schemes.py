"""
FIN Scheme Search Route.
Provides POST /v1/schemes/search via HybridRetriever (dense semantic search + sparse BM25).
CRITICAL INVARIANT: Retrieval never decides statutory eligibility.
"""

import logging
import math
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Depends, Request
from fastapi.concurrency import run_in_threadpool

from src.rag.retriever import HybridRetriever
from src.rag.models import RetrievalQuery

from ..auth import verify_api_key
from ..config import ServiceConfig
from ..dependencies import (
    get_hybrid_retriever,
    get_rate_limiter,
    get_service_config,
    get_scheme_recommendation_service,
)
from ..errors import RateLimitExceededError
from ..middleware import InMemoryRateLimiter
from ..schemas import (
    SchemeSearchRequest,
    SchemeSearchResponse,
    SchemeSearchResultItem,
    SchemeRecommendationRequest,
    SchemeRecommendationResponse,
    SchemeRecommendationItemSchema,
)

logger = logging.getLogger("fin.api.routes.schemes")

router = APIRouter(prefix="/v1/schemes", tags=["Schemes"])


def _normalize_optional_str(val: Any) -> Optional[str]:
    """
    Normalizes optional metadata strings.
    Preserves valid non-empty strings.
    Converts None, NaN (float), and empty/whitespace strings to None.
    Never produces literal 'nan' string or fabricates metadata.
    """
    if val is None:
        return None
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    if isinstance(val, str):
        cleaned = val.strip()
        if not cleaned or cleaned.lower() == "nan":
            return None
        return cleaned
    return None


def _clean_dict(d: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Recursively replaces float NaN/inf values with None for JSON compliance."""
    if not d or not isinstance(d, dict):
        return {}
    clean: Dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            clean[k] = None
        elif isinstance(v, dict):
            clean[k] = _clean_dict(v)
        else:
            clean[k] = v
    return clean


@router.post(
    "/search",
    response_model=SchemeSearchResponse,
    summary="Search policy corpus using hybrid dense-sparse retrieval",
    description=(
        "Executes hybrid semantic search (dense vector embeddings + sparse BM25 keyword matching) "
        "with metadata filtering. Aggregates chunks into deduplicated scheme-level rankings."
    ),
)
async def search_schemes(
    request: Request,
    body: SchemeSearchRequest = Body(...),
    api_key: str = Depends(verify_api_key),
    service_config: ServiceConfig = Depends(get_service_config),
    rate_limiter: InMemoryRateLimiter = Depends(get_rate_limiter),
    retriever: HybridRetriever = Depends(get_hybrid_retriever),
) -> SchemeSearchResponse:
    """Performs hybrid retrieval across statutory policy documents."""
    request_id = getattr(request.state, "request_id", "req_unknown")

    # Rate limiting
    allowed, retry_after = rate_limiter.check_rate_limit(api_key, service_config)
    if not allowed:
        raise RateLimitExceededError(retry_after=retry_after)

    retrieval_query = RetrievalQuery(
        query_text=body.query,
        language=body.language,
        top_k=body.top_k,
        state_filter=body.state,
        category_filter=body.social_category,
        beneficiary_filter=body.beneficiary_type,
    )

    scheme_results = await run_in_threadpool(retriever.retrieve_schemes, retrieval_query)

    items: List[SchemeSearchResultItem] = []
    for res in scheme_results:
        snippets = [c.content for c in res.best_matching_chunks[:3]]
        meta = res.source_metadata or {}
        items.append(
            SchemeSearchResultItem(
                scheme_id=res.scheme_slug,
                scheme_name=res.scheme_name,
                relevance_score=res.aggregate_score,
                source_authority=_normalize_optional_str(meta.get("ministry")),
                source_url=_normalize_optional_str(meta.get("source_url")),
                evidence_snippets=snippets,
                state=_normalize_optional_str(meta.get("state")),
                details=_clean_dict(meta),
            )
        )

    return SchemeSearchResponse(
        request_id=request_id,
        query=body.query,
        total_results=len(items),
        results=items,
    )


@router.post(
    "/recommend",
    response_model=SchemeRecommendationResponse,
    summary="Personalized scheme recommendation based on canonical applicant context",
    description=(
        "Personalized scheme discovery orchestrator: bridges canonical ApplicantContext facts "
        "and QueryUnderstanding signals to HybridRetriever, computes deterministic compatibility scores, "
        "identifies missing statutory fields, and optionally evaluates deterministic eligibility."
    ),
)
async def recommend_schemes(
    request: Request,
    body: SchemeRecommendationRequest = Body(...),
    api_key: str = Depends(verify_api_key),
    service_config: ServiceConfig = Depends(get_service_config),
    rate_limiter: InMemoryRateLimiter = Depends(get_rate_limiter),
    recommendation_service = Depends(get_scheme_recommendation_service),
) -> SchemeRecommendationResponse:
    """Produces personalized, evidence-grounded scheme recommendations."""
    request_id = getattr(request.state, "request_id", "req_unknown")

    # Rate limiting
    allowed, retry_after = rate_limiter.check_rate_limit(api_key, service_config)
    if not allowed:
        raise RateLimitExceededError(retry_after=retry_after)

    rec_result = await run_in_threadpool(
        recommendation_service.recommend_schemes,
        applicant_id=body.applicant_id,
        query=body.query,
        top_k=body.top_k,
        language=body.language,
        include_eligibility=body.include_eligibility,
        include_missing_fields=body.include_missing_fields,
        state_override=body.state_override,
        category_override=body.category_override,
        applicant_facts=body.applicant_facts,
        document_facts=body.document_facts,
    )

    items: List[SchemeRecommendationItemSchema] = []
    for r in rec_result.recommendations:
        ev_dict = _clean_dict(r.evidence.to_dict()) if r.evidence else None
        items.append(
            SchemeRecommendationItemSchema(
                scheme_id=r.scheme_id,
                scheme_slug=r.scheme_slug,
                scheme_name=r.scheme_name,
                relevance_score=r.relevance_score,
                compatibility_score=r.compatibility_score,
                overall_match_score=r.overall_match_score,
                matched_facts=r.matched_facts,
                unmatched_facts=r.unmatched_facts,
                missing_fields=r.missing_fields,
                missing_fields_status=r.missing_fields_status,
                conflict_fields=r.conflict_fields,
                eligibility_status=r.eligibility_status,
                is_eligible=r.is_eligible,
                evidence=ev_dict,
                source_metadata=_clean_dict(r.source_metadata),
                recommendation_reasons=r.recommendation_reasons,
            )
        )

    return SchemeRecommendationResponse(
        request_id=request_id,
        applicant_id=rec_result.applicant_id,
        query=rec_result.query,
        total_candidates_retrieved=rec_result.total_candidates_retrieved,
        recommendations=items,
        applied_filters=_clean_dict(rec_result.applied_filters),
        active_facts_summary=_clean_dict(rec_result.active_facts_summary),
        conflicts_detected=rec_result.conflicts_detected,
        metadata=_clean_dict(rec_result.metadata),
        created_at=rec_result.created_at or "",
    )
