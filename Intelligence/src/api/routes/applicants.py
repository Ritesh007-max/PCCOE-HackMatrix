"""
FIN Canonical Applicant Context & Facts API Routes.
Exposes canonical fact queries, multi-document evidence provenance,
conflict states, and unified ApplicantContext to downstream services and clients.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Request, status

from ..auth import verify_api_key
from ..dependencies import get_applicant_context_service, get_rate_limiter
from ..errors import APIError
from src.context.service import ApplicantContextService
from src.extraction.models import ApplicantFact, Evidence

router = APIRouter(prefix="/v1/applicants", tags=["Applicants"])


@router.get(
    "/{applicant_id}/context",
    summary="Get Canonical Applicant Context",
    description="Returns the aggregated canonical applicant context across profile, documents, and user inputs with conflict states.",
)
async def get_applicant_context(
    request: Request,
    applicant_id: str = Path(..., description="Unique applicant or citizen identifier"),
    _: str = Depends(verify_api_key),
    context_service: ApplicantContextService = Depends(get_applicant_context_service),
) -> Dict[str, Any]:
    """Returns canonical context with reconciled facts and multi-document provenance."""
    ctx = context_service.get_applicant_context(applicant_id)
    return {
        "status": "success",
        "applicant_id": applicant_id,
        "context": ctx.to_dict(),
        "canonical_facts": {k: f.to_dict() for k, f in ctx.canonical_facts.items()},
        "conflicts": ctx.conflicts,
        "has_conflicts": len(ctx.conflicts) > 0,
        "document_count": len(ctx.documents),
        "evidence_count": len(ctx.evidence),
    }


@router.get(
    "/{applicant_id}/facts",
    summary="Get All Applicant Facts",
    description="Returns all atomic facts recorded for the applicant across documents and declarations.",
)
async def get_applicant_facts(
    request: Request,
    applicant_id: str = Path(..., description="Unique applicant or citizen identifier"),
    _: str = Depends(verify_api_key),
    context_service: ApplicantContextService = Depends(get_applicant_context_service),
) -> Dict[str, Any]:
    """Returns list of all atomic facts with full provenance."""
    facts = context_service.get_all_facts(applicant_id)
    return {
        "status": "success",
        "applicant_id": applicant_id,
        "count": len(facts),
        "facts": [f.to_dict() for f in facts],
    }


@router.get(
    "/{applicant_id}/facts/{fact_key}",
    summary="Get Specific Canonical Fact with Provenance",
    description="Returns the consolidated canonical fact, raw verbatim value, normalized value, and supporting evidence.",
)
async def get_applicant_fact(
    request: Request,
    applicant_id: str = Path(..., description="Unique applicant identifier"),
    fact_key: str = Path(..., description="Canonical fact key (e.g. annual_family_income, age, state)"),
    _: str = Depends(verify_api_key),
    context_service: ApplicantContextService = Depends(get_applicant_context_service),
) -> Dict[str, Any]:
    """Returns a specific fact with supporting evidence and history."""
    ctx = context_service.get_applicant_context(applicant_id)
    fact = ctx.get_raw_fact(fact_key)
    evidence_records = ctx.get_evidence(fact_key)
    history = context_service.get_fact_history(applicant_id, fact_key)

    if not fact and not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fact '{fact_key}' not found for applicant '{applicant_id}'.",
        )

    is_conflict = ctx.has_conflict(fact_key)

    return {
        "status": "success",
        "applicant_id": applicant_id,
        "fact_key": fact_key,
        "is_conflicted": is_conflict,
        "canonical_fact": fact.to_dict() if fact else None,
        "normalized_value": fact.normalized_value if fact and not is_conflict else None,
        "raw_value": fact.value if fact else None,
        "evidence": [e.to_dict() for e in evidence_records],
        "candidates": [h.to_dict() for h in history],
    }


@router.get(
    "/{applicant_id}/evidence",
    summary="Get All Evidence Records",
    description="Returns all evidence records and citations for the applicant.",
)
async def get_applicant_evidence(
    request: Request,
    applicant_id: str = Path(..., description="Unique applicant identifier"),
    _: str = Depends(verify_api_key),
    context_service: ApplicantContextService = Depends(get_applicant_context_service),
) -> Dict[str, Any]:
    """Returns all evidence records with OCR coordinates, document hashes, and source URIs."""
    evidence_list = context_service.get_evidence_for_applicant(applicant_id)
    return {
        "status": "success",
        "applicant_id": applicant_id,
        "count": len(evidence_list),
        "evidence": [e.to_dict() for e in evidence_list],
    }
