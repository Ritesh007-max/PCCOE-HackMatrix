"""
FIN Query Understanding Route.
Provides POST /v1/query/understand for testing and downstream integration.
Translates citizen messages into canonical QueryUnderstandingResult models.
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from src.query.service import QueryUnderstandingService
from src.api.dependencies import get_query_understanding_service

logger = logging.getLogger("fin.api.routes.query")

router = APIRouter(prefix="/v1/query", tags=["Query Understanding"])


class QueryUnderstandRequest(BaseModel):
    """Payload for POST /v1/query/understand."""
    applicant_id: str = Field(..., min_length=1, description="Citizen identifier")
    message: str = Field(..., min_length=1, max_length=4000, description="Natural language citizen utterance")
    conversation_history: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Prior conversation turns")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Client session metadata")


class QueryUnderstandResponse(BaseModel):
    """Canonical structured response for POST /v1/query/understand."""
    status: str = "success"
    applicant_id: str
    understanding: Dict[str, Any]


@router.post(
    "/understand",
    response_model=QueryUnderstandResponse,
    summary="Understand citizen query intent, facts, and references",
    description=(
        "Processes citizen utterance against canonical ApplicantContext. "
        "Extracts candidate facts, classifies intent, detects conflicts, resolves references, "
        "and produces structured query routing contract ready for Phase 19."
    ),
)
async def understand_query(
    body: QueryUnderstandRequest = Body(...),
    query_service: QueryUnderstandingService = Depends(get_query_understanding_service),
) -> QueryUnderstandResponse:
    """Produces structured QueryUnderstandingResult for an applicant message."""
    try:
        result = query_service.understand_query(
            applicant_id=body.applicant_id,
            message=body.message,
            conversation_history=body.conversation_history,
        )
        return QueryUnderstandResponse(
            status="success",
            applicant_id=body.applicant_id,
            understanding=result.to_dict(),
        )
    except Exception as e:
        logger.exception("Failed to understand query for applicant %s: %s", body.applicant_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query understanding failed: {str(e)}",
        )
