"""
PolicySetu Scheme Search Route.
Provides POST /v1/schemes/search via HybridRetriever (dense semantic search + sparse BM25).
CRITICAL INVARIANT: Retrieval never decides statutory eligibility.
"""

import logging
from typing import List
from fastapi import APIRouter, Body, Depends, Request
from fastapi.concurrency import run_in_threadpool

from src.rag.retriever import HybridRetriever
from src.rag.models import RetrievalQuery

from ..auth import verify_api_key
from ..config import ServiceConfig
from ..dependencies import get_hybrid_retriever, get_rate_limiter, get_service_config
from ..errors import RateLimitExceededError
from ..middleware import InMemoryRateLimiter
from ..schemas import SchemeSearchRequest, SchemeSearchResponse, SchemeSearchResultItem

logger = logging.getLogger("policysetu.api.routes.schemes")

router = APIRouter(prefix="/v1/schemes", tags=["Schemes"])


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
        items.append(
            SchemeSearchResultItem(
                scheme_id=res.scheme_slug,
                scheme_name=res.scheme_name,
                relevance_score=res.aggregate_score,
                source_authority=res.source_metadata.get("ministry"),
                source_url=res.source_metadata.get("source_url"),
                evidence_snippets=snippets,
                state=res.source_metadata.get("state"),
                details=res.source_metadata,
            )
        )

    return SchemeSearchResponse(
        request_id=request_id,
        query=body.query,
        total_results=len(items),
        results=items,
    )
