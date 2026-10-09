"""
FIN Unified Intelligence Query API Endpoint.
Exposes POST /v1/intelligence/query protected by X-AI-Service-Key.
Integrates all Phases 17-24 into a single, cohesive Intelligence Brain.
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from src.orchestration.models import UnifiedIntelligenceRequest, UnifiedIntelligenceResponse
from src.orchestration.orchestrator import UnifiedIntelligenceOrchestrator

from ..auth import verify_api_key
from ..config import ServiceConfig
from ..dependencies import (
    get_service_config,
    get_rate_limiter,
    get_unified_orchestrator,
)
from ..middleware import InMemoryRateLimiter

logger = logging.getLogger("fin.api.routes.intelligence")

router = APIRouter(prefix="/v1/intelligence", tags=["Unified Intelligence"])


class IntelligenceQueryRequest(BaseModel):
    applicant_id: str = Field(..., description="Unique persistent applicant/citizen identifier")
    message: str = Field(..., description="Citizen natural language message or query")
    conversation_id: Optional[str] = Field(None, description="Optional multi-turn conversation session ID")
    language: str = Field("en", description="Target language ('en', 'hi', 'gu')")
    scheme_id: Optional[str] = Field(None, description="Optional explicit scheme identifier")
    document_id: Optional[str] = Field(None, description="Optional explicit document reference")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary client metadata")


@router.post(
    "/query",
    summary="Process natural-language query through Unified Intelligence Brain",
    description=(
        "Executes the full interconnected FIN pipeline: Query Understanding -> Conversation Memory -> "
        "Applicant Context -> Scheme Retrieval -> Recommendation -> Deterministic Rules -> Evidence -> "
        "Grounding -> Final Response."
    ),
)
async def query_intelligence(
    request: Request,
    body: IntelligenceQueryRequest = Body(...),
    api_key: str = Depends(verify_api_key),
    service_config: ServiceConfig = Depends(get_service_config),
    rate_limiter: InMemoryRateLimiter = Depends(get_rate_limiter),
    orchestrator: UnifiedIntelligenceOrchestrator = Depends(get_unified_orchestrator),
) -> Dict[str, Any]:
    # Rate limiting
    client_ip = request.client.host if request.client else "unknown"
    rate_limiter.check(client_ip)

    try:
        orch_req = UnifiedIntelligenceRequest(
            applicant_id=body.applicant_id,
            message=body.message,
            conversation_id=body.conversation_id,
            language=body.language,
            scheme_id=body.scheme_id,
            document_id=body.document_id,
            metadata=body.metadata,
        )
        response = orchestrator.process_query(orch_req)
        return response.to_dict()
    except ValueError as ve:
        logger.warning("Validation error in intelligence query: %s", ve)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        logger.error("Unexpected error processing intelligence query: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while evaluating your request. Please try again later.",
        )
