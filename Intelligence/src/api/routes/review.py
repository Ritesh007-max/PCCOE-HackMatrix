"""
FIN Human Review & Conflict Resolution API Endpoints.
Provides caseworker endpoints:
  GET  /v1/review/conflicts
  GET  /v1/review/conflicts/{conflict_id}
  POST /v1/review/conflicts/{conflict_id}/resolve
  POST /v1/review/conflicts/{conflict_id}/reject
  POST /v1/review/conflicts/{conflict_id}/escalate
Protected by X-AI-Service-Key with full immutable provenance and audit trails.
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Request, status
from pydantic import BaseModel, Field

from src.review.models import ConflictRecord, ConflictStatus
from src.review.service import ConflictResolutionService

from ..auth import verify_api_key
from ..config import ServiceConfig
from ..dependencies import (
    get_conflict_resolution_service,
    get_rate_limiter,
    get_service_config,
)
from ..middleware import InMemoryRateLimiter

logger = logging.getLogger("fin.api.routes.review")

router = APIRouter(prefix="/v1/review", tags=["Human Review & Conflicts"])


class ResolveConflictRequest(BaseModel):
    resolver_id: str = Field(..., description="Authenticated caseworker/officer identifier")
    selected_source: str = Field(..., description="Selected authoritative source (e.g. DOCUMENT or USER_INPUT)")
    reason: str = Field(..., description="Mandatory justification for resolving the conflict")
    authoritative_value: Optional[Any] = Field(None, description="Optional explicit override value verified by caseworker")


class RejectConflictRequest(BaseModel):
    resolver_id: str = Field(..., description="Authenticated caseworker/officer identifier")
    reason: str = Field(..., description="Mandatory justification for rejecting conflict")


class EscalateConflictRequest(BaseModel):
    resolver_id: str = Field(..., description="Authenticated caseworker/officer identifier")
    reason: str = Field(..., description="Mandatory justification for escalating conflict to supervisor")


@router.get(
    "/conflicts",
    summary="List factual conflicts requiring human review",
    description="Lists all recorded factual conflicts across documents, self-declarations, and profile fields.",
)
async def list_conflicts(
    applicant_id: Optional[str] = Query(None, description="Filter by applicant ID"),
    conflict_status: Optional[str] = Query(None, alias="status", description="Filter by status (OPEN, RESOLVED, etc.)"),
    api_key: str = Depends(verify_api_key),
    service_config: ServiceConfig = Depends(get_service_config),
    conflict_service: ConflictResolutionService = Depends(get_conflict_resolution_service),
) -> List[Dict[str, Any]]:
    c_status = None
    if conflict_status:
        try:
            c_status = ConflictStatus(conflict_status.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status '{conflict_status}'. Allowed: OPEN, UNDER_REVIEW, RESOLVED, REJECTED, ESCALATED.",
            )
    records = conflict_service.list_conflicts(applicant_id=applicant_id, status=c_status)
    return [r.to_dict() for r in records]


@router.get(
    "/conflicts/{conflict_id}",
    summary="Get single conflict detail by ID",
    description="Retrieves full evidence records, discordant values, and resolution metadata for a conflict.",
)
async def get_conflict(
    conflict_id: str = Path(..., description="Unique conflict record identifier"),
    api_key: str = Depends(verify_api_key),
    service_config: ServiceConfig = Depends(get_service_config),
    conflict_service: ConflictResolutionService = Depends(get_conflict_resolution_service),
) -> Dict[str, Any]:
    record = conflict_service.get_conflict(conflict_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conflict record '{conflict_id}' was not found.",
        )
    return record.to_dict()


@router.post(
    "/conflicts/{conflict_id}/resolve",
    summary="Authorize caseworker resolution of a factual conflict",
    description=(
        "Caseworker resolution selects the authoritative evidence source or provides a verified override value. "
        "Enforces immutability: historical decisions remain untouched; canonical ApplicantContext is updated for future evaluations."
    ),
)
async def resolve_conflict(
    conflict_id: str = Path(..., description="Unique conflict record identifier"),
    body: ResolveConflictRequest = Body(...),
    api_key: str = Depends(verify_api_key),
    service_config: ServiceConfig = Depends(get_service_config),
    conflict_service: ConflictResolutionService = Depends(get_conflict_resolution_service),
) -> Dict[str, Any]:
    try:
        updated = conflict_service.resolve_conflict(
            conflict_id=conflict_id,
            resolver_id=body.resolver_id,
            selected_source=body.selected_source,
            reason=body.reason,
            authoritative_value=body.authoritative_value,
        )
        return {
            "message": "Conflict resolved successfully.",
            "conflict": updated.to_dict(),
        }
    except KeyError as ke:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ke))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.post(
    "/conflicts/{conflict_id}/reject",
    summary="Reject an invalid conflict report",
    description="Marks a reported conflict as REJECTED with mandatory justification.",
)
async def reject_conflict(
    conflict_id: str = Path(..., description="Unique conflict record identifier"),
    body: RejectConflictRequest = Body(...),
    api_key: str = Depends(verify_api_key),
    service_config: ServiceConfig = Depends(get_service_config),
    conflict_service: ConflictResolutionService = Depends(get_conflict_resolution_service),
) -> Dict[str, Any]:
    try:
        updated = conflict_service.reject_conflict(
            conflict_id=conflict_id,
            resolver_id=body.resolver_id,
            reason=body.reason,
        )
        return {
            "message": "Conflict rejected successfully.",
            "conflict": updated.to_dict(),
        }
    except KeyError as ke:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ke))


@router.post(
    "/conflicts/{conflict_id}/escalate",
    summary="Escalate conflict to supervisory review",
    description="Marks conflict as ESCALATED for supervisory adjudication.",
)
async def escalate_conflict(
    conflict_id: str = Path(..., description="Unique conflict record identifier"),
    body: EscalateConflictRequest = Body(...),
    api_key: str = Depends(verify_api_key),
    service_config: ServiceConfig = Depends(get_service_config),
    conflict_service: ConflictResolutionService = Depends(get_conflict_resolution_service),
) -> Dict[str, Any]:
    try:
        updated = conflict_service.escalate_conflict(
            conflict_id=conflict_id,
            resolver_id=body.resolver_id,
            reason=body.reason,
        )
        return {
            "message": "Conflict escalated successfully.",
            "conflict": updated.to_dict(),
        }
    except KeyError as ke:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ke))
