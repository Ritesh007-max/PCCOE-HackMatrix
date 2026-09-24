"""
FIN Grounded Chat Route.
Provides POST /v1/chat.
CRITICAL INVARIANT: Chat must remain grounded strictly in the verified RAG policy corpus.
Never acts as a generic hallucinating chatbot.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Body, Depends, Request
from fastapi.concurrency import run_in_threadpool

from src.rag.retriever import HybridRetriever
from src.rag.models import RetrievalQuery
from src.llm.client import LLMClient
from src.llm.safety import PromptInjectionDetector

from ..auth import verify_api_key
from ..config import ServiceConfig
from ..dependencies import (
    get_hybrid_retriever,
    get_llm_client,
    get_rate_limiter,
    get_service_config,
)
from ..errors import RateLimitExceededError
from ..middleware import InMemoryRateLimiter
from ..schemas import ChatCitationItem, ChatRequest, ChatResponse

logger = logging.getLogger("fin.api.routes.chat")

router = APIRouter(prefix="/v1/chat", tags=["Chat"])

_safety_detector = PromptInjectionDetector()

SYSTEM_PROMPT_GROUNDED_CHAT = """You are FIN's authoritative government welfare assistant.
You assist Indian citizens in discovering statutory schemes, understanding eligibility criteria, and identifying application steps.

CRITICAL INVARIANTS:
1. Ground every claim strictly and exclusively in the provided <POLICY_EVIDENCE> chunks.
2. If the statutory records do not contain the answer, explicitly state: "This information is not available in the verified government scheme repository."
3. NEVER hallucinate eligibility rules, deadlines, or monetary benefits.
4. Reference the supporting evidence chunk IDs where appropriate.
5. Maintain a professional, empathetic, and clear public-service tone."""


@router.post(
    "",
    response_model=ChatResponse,
    summary="Grounded conversational assistance backed by verified policy evidence",
    description=(
        "Answers citizen queries grounded strictly in verified policy evidence chunks. "
        "Employs safety guardrails, hybrid RAG retrieval, and citation tracking. "
        "Zero generic or ungrounded LLM responses."
    ),
)
async def chat(
    request: Request,
    body: ChatRequest = Body(...),
    api_key: str = Depends(verify_api_key),
    service_config: ServiceConfig = Depends(get_service_config),
    rate_limiter: InMemoryRateLimiter = Depends(get_rate_limiter),
    retriever: HybridRetriever = Depends(get_hybrid_retriever),
    llm_client: LLMClient = Depends(get_llm_client),
) -> ChatResponse:
    """Answers citizen inquiries with strict statutory RAG grounding."""
    request_id = getattr(request.state, "request_id", "req_unknown")

    # Rate limiting
    allowed, retry_after = rate_limiter.check_rate_limit(api_key, service_config)
    if not allowed:
        raise RateLimitExceededError(retry_after=retry_after)

    # 1. Safety & prompt injection check
    safety_scan = _safety_detector.scan(body.query)
    if safety_scan.is_injection_risk:
        logger.warning(
            "Blocked prompt injection attempt in /v1/chat (request %s): %s",
            request_id,
            safety_scan.detected_threats,
        )
        return ChatResponse(
            request_id=request_id,
            conversation_id=body.conversation_id,
            answer=(
                "Your request contains disallowed instruction override patterns. "
                "FIN is strictly restricted to providing information from verified government scheme records."
            ),
            intent="INJECTION_BLOCKED",
            citations=[],
            suggested_schemes=[],
        )

    # 2. Hybrid RAG retrieval
    retrieval_query = RetrievalQuery(
        query_text=body.query,
        language=body.language,
        top_k=5,
    )

    chunks = await run_in_threadpool(retriever.retrieve, retrieval_query)
    schemes = await run_in_threadpool(retriever.retrieve_schemes, retrieval_query)

    # If no relevant chunks exist in the repository
    if not chunks:
        return ChatResponse(
            request_id=request_id,
            conversation_id=body.conversation_id,
            answer=(
                "No verified government schemes or policy documents were found matching your query "
                "in the statutory repository. Please try searching with specific keywords "
                "(e.g., 'farmer subsidy', 'scholarship', 'pension', or state name)."
            ),
            intent="SCHEME_DISCOVERY",
            citations=[],
            suggested_schemes=[],
        )

    # 3. Format citations and suggested schemes
    citations: List[ChatCitationItem] = []
    for c in chunks[:5]:
        citations.append(
            ChatCitationItem(
                chunk_id=c.chunk_id,
                scheme_id=c.scheme_slug or "unknown_scheme",
                url=c.metadata.get("source_url") or "",
                excerpt=c.content[:250].strip() + ("..." if len(c.content) > 250 else ""),
            )
        )

    suggested_schemes = [
        {
            "scheme_id": s.scheme_slug,
            "scheme_name": s.scheme_name,
            "relevance_score": s.aggregate_score,
            "ministry": s.source_metadata.get("ministry"),
            "state": s.source_metadata.get("state"),
        }
        for s in schemes[:3]
    ]

    # 4. Construct grounded LLM prompt
    evidence_blocks = []
    for idx, c in enumerate(chunks[:5], start=1):
        evidence_blocks.append(
            f"--- EVIDENCE CHUNK {idx} (ID: {c.chunk_id}, Scheme: {c.scheme_name}) ---\n"
            f"{c.content}\n"
        )
    evidence_text = "\n".join(evidence_blocks)

    wrapped_query = _safety_detector.wrap_untrusted_input(body.query)

    llm_prompt = (
        f"<POLICY_EVIDENCE>\n{evidence_text}\n</POLICY_EVIDENCE>\n\n"
        f"Citizen Query:\n{wrapped_query}\n\n"
        "Provide a grounded, transparent explanation based strictly on the above statutory evidence."
    )

    # 5. Call LLM with graceful fallback
    telemetry = None
    try:
        exec_res = await run_in_threadpool(
            llm_client.generate_with_metadata,
            llm_prompt,
            system_prompt=SYSTEM_PROMPT_GROUNDED_CHAT,
            operation="grounded_chat",
            request_id=request_id,
        )
        answer = exec_res.content
        telemetry = {
            "provider": exec_res.provider,
            "model": exec_res.model,
            "latency_ms": round(exec_res.latency_ms, 2),
            "fallback_used": exec_res.fallback_used,
        }
    except Exception as e:
        logger.warning(
            "LLM generation failed for grounded chat (request %s): %s; generating evidence-derived fallback.",
            request_id,
            e,
        )
        # Grounded deterministic fallback directly synthesizing top evidence chunks
        top_scheme_names = ", ".join(s["scheme_name"] for s in suggested_schemes)
        answer = (
            f"Based on verified statutory scheme records, the most relevant schemes matching your query are: {top_scheme_names}.\n\n"
            f"Key statutory details:\n- {citations[0].excerpt}\n\n"
            "Please review the attached source citations for full eligibility and application guidelines."
        )
        telemetry = {"provider": "local_fallback", "model": "evidence_synthesizer", "latency_ms": 0.0}

    return ChatResponse(
        request_id=request_id,
        conversation_id=body.conversation_id,
        answer=answer,
        intent="SCHEME_DISCOVERY",
        citations=citations,
        suggested_schemes=suggested_schemes,
        provider_telemetry=telemetry,
    )
