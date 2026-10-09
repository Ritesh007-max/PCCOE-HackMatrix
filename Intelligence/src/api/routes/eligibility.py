"""
FIN Deterministic Eligibility Check Route.
Provides POST /v1/eligibility/check.
CRITICAL INVARIANT: 100% deterministic rule engine evaluation.
Zero Gemini/OpenRouter calls are involved in deciding PASS/FAIL/UNKNOWN/REVIEW.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Body, Depends, Request
from fastapi.concurrency import run_in_threadpool

from src.context.service import ApplicantContextService
from src.eligibility.engine import EligibilityEngine
from src.rules.models import ApplicantProfile, RuleStatus

from ..auth import verify_api_key
from ..config import ServiceConfig
from ..dependencies import (
    get_applicant_context_service,
    get_eligibility_engine,
    get_rate_limiter,
    get_service_config,
)
from ..errors import APIError, RateLimitExceededError
from ..middleware import InMemoryRateLimiter
from ..schemas import (
    EligibilityCheckRequest,
    EligibilityCheckResponse,
    RuleEvaluationItem,
    SchemeEligibilityItem,
)

logger = logging.getLogger("fin.api.routes.eligibility")

router = APIRouter(prefix="/v1/eligibility", tags=["Eligibility"])


@router.post(
    "/check",
    response_model=EligibilityCheckResponse,
    summary="Deterministically evaluate applicant facts against statutory policy rules",
    description=(
        "Executes 100% deterministic AST rule evaluation against statutory government policies. "
        "Guaranteed zero hallucinations and zero LLM calls. Returns PASS, FAIL, UNKNOWN, or REVIEW "
        "with complete rule-level breakdown and missing field analysis."
    ),
)
async def check_eligibility(
    request: Request,
    body: EligibilityCheckRequest = Body(...),
    api_key: str = Depends(verify_api_key),
    service_config: ServiceConfig = Depends(get_service_config),
    rate_limiter: InMemoryRateLimiter = Depends(get_rate_limiter),
    engine: EligibilityEngine = Depends(get_eligibility_engine),
    context_service: ApplicantContextService = Depends(get_applicant_context_service),
) -> EligibilityCheckResponse:
    """Evaluates applicant profile deterministically without calling any LLM."""
    request_id = getattr(request.state, "request_id", "req_unknown")

    # Rate limiting
    allowed, retry_after = rate_limiter.check_rate_limit(api_key, service_config)
    if not allowed:
        raise RateLimitExceededError(retry_after=retry_after)

    if not body.scheme_ids:
        raise APIError(
            status_code=400,
            error_code="NO_SCHEMES_SPECIFIED",
            message="At least one scheme ID must be provided in 'scheme_ids'.",
        )

    # 1. Resolve applicant profile
    profile: Optional[ApplicantProfile] = None

    if body.applicant_id:
        try:
            ctx = await run_in_threadpool(context_service.get_context, body.applicant_id)
            if ctx:
                profile = ctx.to_applicant_profile()
                # If explicit applicant_facts were also passed, overlay them
                if body.applicant_facts:
                    profile._data.update(body.applicant_facts)
        except Exception as e:
            logger.warning("Could not fetch applicant context for %s: %s", body.applicant_id, e)

    if profile is None:
        profile = ApplicantProfile(data=body.applicant_facts or {})

    evaluations: List[SchemeEligibilityItem] = []

    for sid in body.scheme_ids:
        # Deterministic AST evaluation
        decision = await run_in_threadpool(
            engine.evaluate,
            sid,
            profile,
            body.rule_version,
            body.applicant_id,
        )

        rule_items = [
            RuleEvaluationItem(
                rule_id=r.rule_id,
                field=r.field,
                operator=r.operator,
                status=r.status.value,
                applicant_value=r.applicant_value,
                expected_value=r.expected_value,
                hard_constraint=r.hard_constraint,
                reason=r.reason,
            )
            for r in decision.rule_results
        ]

        evaluations.append(
            SchemeEligibilityItem(
                scheme_id=decision.scheme_id or sid,
                scheme_name=decision.scheme_name or sid,
                status=decision.status.value,
                is_eligible=decision.status == RuleStatus.PASS,
                rule_version=decision.rule_version,
                decision_id=decision.decision_id,
                rule_set_hash=decision.rule_set_hash,
                rules_evaluated=rule_items,
                matched_rules=decision.passed_rules,
                failed_rules=decision.failed_rules,
                missing_fields=decision.missing_fields,
                conflicted_fields=decision.conflicted_fields,
                disqualification_reasons=decision.disqualification_reasons,
                review_reasons=decision.review_reasons,
                evidence=decision.evidence,
            )
        )

        # PII-Safe logging: log only IDs and status, no raw personal facts
        logger.info(
            "Evaluated eligibility scheme=%s version=%s status=%s passed=%d failed=%d missing=%d",
            sid,
            decision.rule_version,
            decision.status.value,
            len(decision.passed_rules),
            len(decision.failed_rules),
            len(decision.missing_fields),
        )

    return EligibilityCheckResponse(
        request_id=request_id,
        evaluated_schemes_count=len(evaluations),
        evaluations=evaluations,
    )
