"""
FIN Application Analysis Route.
Provides POST /v1/applications/analyze, calling the authoritative Phase 8 ApplicationPipeline directly.
The API layer only validates/transforms the request and serializes the result.
"""

import logging
from pathlib import Path
from typing import List, Optional, Union
from fastapi import APIRouter, Depends, File, Form, Header, Request, UploadFile
from fastapi.concurrency import run_in_threadpool

from src.pipelines.application_pipeline import ApplicationPipeline
from src.documents.pipeline import DocumentPipeline
from src.documents.models import DocumentContent

from ..auth import verify_api_key
from ..config import ServiceConfig
from ..dependencies import (
    get_application_pipeline,
    get_document_pipeline,
    get_rate_limiter,
    get_service_config,
)
from ..errors import APIError, PayloadTooLargeError, RateLimitExceededError
from ..middleware import InMemoryRateLimiter
from ..schemas import ApplicationAnalyzeResponse

logger = logging.getLogger("fin.api.routes.applications")

router = APIRouter(prefix="/v1/applications", tags=["Applications"])


@router.post(
    "/analyze",
    response_model=ApplicationAnalyzeResponse,
    summary="Analyze citizen documents and query through 21-step pipeline",
    description=(
        "Accepts multi-document uploads and user query, directly invoking the Phase 8 "
        "ApplicationPipeline. Executes 21-step extraction, AST validation, deterministic "
        "eligibility, benefit calculation, and grounded explanation."
    ),
)
async def analyze_application(
    request: Request,
    files: List[UploadFile] = File(..., description="Uploaded citizen documents (PDF, images, docx)"),
    query: Optional[str] = Form(None, description="Optional citizen search query or intent"),
    target_scheme: Optional[str] = Form(None, description="Optional target scheme slug or ID"),
    session_id: Optional[str] = Form(None, description="Optional caller session or application tracking ID"),
    api_key: str = Depends(verify_api_key),
    service_config: ServiceConfig = Depends(get_service_config),
    rate_limiter: InMemoryRateLimiter = Depends(get_rate_limiter),
    doc_pipeline: DocumentPipeline = Depends(get_document_pipeline),
    app_pipeline: ApplicationPipeline = Depends(get_application_pipeline),
) -> ApplicationAnalyzeResponse:
    """Coordinates document ingestion and delegates directly to ApplicationPipeline."""
    request_id = getattr(request.state, "request_id", "req_unknown")

    # Rate limiting check (disabled in development by default)
    allowed, retry_after = rate_limiter.check_rate_limit(api_key, service_config)
    if not allowed:
        raise RateLimitExceededError(retry_after=retry_after)

    # Validate file presence
    if not files:
        raise APIError(
            status_code=400,
            error_code="NO_FILES_PROVIDED",
            message="At least one document must be uploaded for application analysis.",
        )

    # Validate file count limit
    if len(files) > service_config.max_files_per_request:
        raise APIError(
            status_code=400,
            error_code="TOO_MANY_FILES",
            message=f"Maximum {service_config.max_files_per_request} files allowed per request (received {len(files)}).",
        )

    # Read and validate each file
    max_bytes = service_config.max_upload_size_mb * 1024 * 1024
    parsed_docs: List[DocumentContent] = []

    for upload_file in files:
        raw_bytes = await upload_file.read()
        if len(raw_bytes) > max_bytes:
            raise PayloadTooLargeError(
                f"File '{upload_file.filename}' exceeds maximum allowed size of {service_config.max_upload_size_mb} MB."
            )
        if len(raw_bytes) == 0:
            raise APIError(
                status_code=400,
                error_code="EMPTY_FILE",
                message=f"File '{upload_file.filename}' is empty (0 bytes).",
            )

        # Parse in threadpool to keep event loop responsive
        doc_content = await run_in_threadpool(
            doc_pipeline.process_bytes,
            raw_bytes,
            upload_file.filename or "uploaded_document.bin",
        )
        parsed_docs.append(doc_content)

    doc_inputs: List[Union[str, Path, bytes, DocumentContent]] = [d for d in parsed_docs]
    # Directly execute Phase 8 ApplicationPipeline in worker threadpool
    result = await run_in_threadpool(
        app_pipeline.process_application,
        documents=doc_inputs,
        user_query=query,
        target_scheme=target_scheme,
        session_id=session_id,
    )

    result_dict = result.to_dict()
    result_dict["request_id"] = request_id

    return ApplicationAnalyzeResponse(**result_dict)
