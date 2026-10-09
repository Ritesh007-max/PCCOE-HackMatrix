"""
FIN Phase 21 Policy Explanation and Guidance API Route.
Provides:
  POST /v1/explanation/generate
  POST /v1/explanation/compare
Enforces deterministic decision immutability, zero secret leakage, and PII-safe logging.
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Depends, Request
from fastapi.concurrency import run_in_threadpool

from src.context.service import ApplicantContextService
from src.eligibility.engine import EligibilityEngine
from src.explanation.service import PolicyExplanationService
from src.explanation.models import ExplanationBundle, SchemeComparisonResult
from src.rules.models import ApplicantProfile

from ..auth import verify_api_key
from ..config import ServiceConfig
from ..dependencies import (
    get_applicant_context_service,
    get_eligibility_engine,
    get_explanation_service,
    get_rate_limiter,
    get_service_config,
)
from ..errors import APIError
from ..middleware import InMemoryRateLimiter
from ..schemas import (
    ExplanationRequest,
    ExplanationResponse,
    SchemeComparisonRequest,
    SchemeComparisonResponse,
)

logger = logging.getLogger("fin.api.routes.explanation")

router = APIRouter(prefix="/v1/explanation", tags=["Explanation & Guidance"])


@router.post(
    "/generate",
    response_model=ExplanationResponse,
    summary="Generate evidence-grounded policy explanation and actionable guidance",
    description=(
        "Converts deterministic eligibility decisions and recommendation context into "
        "evidence-backed, citation-grounded explanations. Guarantees 100% decision immutability."
    ),
)
async def generate_explanation(
    request: Request,
    body: ExplanationRequest = Body(...),
    api_key: str = Depends(verify_api_key),
    service_config: ServiceConfig = Depends(get_service_config),
    rate_limiter: InMemoryRateLimiter = Depends(get_rate_limiter),
    explanation_service: PolicyExplanationService = Depends(get_explanation_service),
    engine: EligibilityEngine = Depends(get_eligibility_engine),
    context_service: ApplicantContextService = Depends(get_applicant_context_service),
) -> ExplanationResponse:
    request_id = getattr(request.state, "request_id", "req_unknown")

    # 1. Resolve Applicant Context
    context = None
    if body.applicant_id:
        try:
            context = await run_in_threadpool(
                context_service.get_applicant_context, body.applicant_id
            )
        except Exception as e:
            logger.warning("Could not load ApplicantContext for %s: %s", body.applicant_id, e)

    # 2. Build Profile
    if context and hasattr(context, "to_applicant_profile"):
        profile = context.to_applicant_profile()
        if body.applicant_facts:
            profile._data.update(body.applicant_facts)
    elif body.applicant_facts:
        profile = ApplicantProfile(body.applicant_facts)
    else:
        profile = ApplicantProfile({})

    # 3. Evaluate Deterministic Eligibility (sole statutory authority)
    decision = await run_in_threadpool(
        engine.evaluate,
        body.scheme_id,
        profile,
        body.rule_version,
        body.applicant_id,
    )

    # 4. Generate Grounded Explanation Bundle
    bundle = await run_in_threadpool(
        explanation_service.explain_decision,
        decision=decision,
        recommendation=None,
        context=context,
        query=body.query,
        language=body.language,
        use_llm_enhancement=body.use_llm,
    )

    # PII-Safe logging
    logger.info(
        "Generated explanation req_id=%s scheme=%s status=%s grounding=%s",
        request_id,
        decision.scheme_id,
        decision.status.value,
        bundle.grounding_status.value,
    )

    return ExplanationResponse(
        request_id=request_id,
        explanation=bundle.to_dict(),
    )


@router.post(
    "/compare",
    response_model=SchemeComparisonResponse,
    summary="Compare multiple candidate schemes side-by-side objectively",
    description=(
        "Generates an objective comparative analysis across multiple government schemes, "
        "highlighting differences in eligibility, benefits, and required documents without bias."
    ),
)
async def compare_schemes(
    request: Request,
    body: SchemeComparisonRequest = Body(...),
    api_key: str = Depends(verify_api_key),
    service_config: ServiceConfig = Depends(get_service_config),
    rate_limiter: InMemoryRateLimiter = Depends(get_rate_limiter),
    explanation_service: PolicyExplanationService = Depends(get_explanation_service),
    engine: EligibilityEngine = Depends(get_eligibility_engine),
    context_service: ApplicantContextService = Depends(get_applicant_context_service),
) -> SchemeComparisonResponse:
    request_id = getattr(request.state, "request_id", "req_unknown")

    context = None
    if body.applicant_id:
        try:
            context = await run_in_threadpool(
                context_service.get_applicant_context, body.applicant_id
            )
        except Exception as e:
            logger.warning("Could not load context for comparison: %s", e)

    profile = context.to_applicant_profile() if context else ApplicantProfile(body.applicant_facts or {})

    # Evaluate all schemes in comparison list
    decisions_map = {}
    recommendations_list = []

    for sid in body.scheme_ids:
        dec = await run_in_threadpool(engine.evaluate, sid, profile, None, body.applicant_id)
        decisions_map[sid] = dec
        decisions_map[dec.scheme_slug] = dec

        # Create lightweight recommendation container for comparison
        from src.recommendation.models import SchemeRecommendationItem
        rec_item = SchemeRecommendationItem(
            scheme_id=dec.scheme_id,
            scheme_slug=dec.scheme_slug,
            scheme_name=dec.scheme_name,
            relevance_score=1.0,
            compatibility_score=1.0 if dec.status.value == "PASS" else 0.5,
            overall_match_score=1.0,
            eligibility_status=dec.status.value,
            is_eligible=dec.eligible,
        )
        recommendations_list.append(rec_item)

    comparison_res = await run_in_threadpool(
        explanation_service.compare_schemes,
        recommendations=recommendations_list,
        decisions=decisions_map,
    )

    logger.info(
        "Compared %d schemes req_id=%s schemes=%s",
        len(body.scheme_ids),
        request_id,
        body.scheme_ids,
    )

    return SchemeComparisonResponse(
        request_id=request_id,
        comparison=comparison_res.to_dict(),
    )
