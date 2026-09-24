"""
FIN Document Ingestion Endpoint.
Processes and validates uploaded citizen documents (PDF, DOCX, Images, Scans)
using Phase 8 multi-format parsers, magic byte inspection, and SHA-256 deduplication.
"""

from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from ..auth import verify_service_api_key
from ..dependencies import (
    get_document_pipeline,
    get_rate_limiter,
    get_service_config,
)
from ..schemas import DocumentProcessResponse, ProcessedDocumentItem
from ..errors import APIError, PayloadTooLargeError, UnsupportedMediaTypeError
from src.documents.pipeline import DocumentPipeline
from src.documents.models import DocumentProcessingStatus

router = APIRouter(prefix="/v1/documents", tags=["Documents"])


@router.post(
    "/process",
    response_model=DocumentProcessResponse,
    summary="Process and Validate Documents",
    description="Accepts one or more multipart document files, validates security, detects format, and extracts content. Protected.",
)
async def process_documents(
    request: Request,
    files: List[UploadFile] = File(..., description="Uploaded document files (PDF, DOCX, PNG, JPG, TIFF)"),
    _: str = Depends(verify_service_api_key),
    doc_pipeline: DocumentPipeline = Depends(get_document_pipeline),
    rate_limiter = Depends(get_rate_limiter),
    config = Depends(get_service_config),
) -> DocumentProcessResponse:
    """Ingests multi-format uploaded documents using the Phase 8 parsing and security pipeline."""
    # 1. Rate limiting check
    client_id = request.headers.get("X-AI-Service-Key", request.client.host if request.client else "default")
    rate_limiter.check(client_id)

    req_id = getattr(request.state, "request_id", "req_unknown")

    # 2. File count check
    if len(files) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one document file must be uploaded."
        )

    if len(files) > config.max_files_per_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exceeded maximum allowed files per request ({config.max_files_per_request})."
        )

    processed_items: List[ProcessedDocumentItem] = []
    max_bytes = config.max_upload_size_mb * 1024 * 1024

    for file_obj in files:
        filename = file_obj.filename or "uploaded_document"
        raw_bytes = await file_obj.read()

        # Check payload size limit
        if len(raw_bytes) > max_bytes:
            raise PayloadTooLargeError(
                f"File '{filename}' exceeds maximum allowed size of {config.max_upload_size_mb} MB."
            )

        # Execute DocumentPipeline
        doc_content = doc_pipeline.process_bytes(raw_bytes, filename=filename)

        if doc_content.status != DocumentProcessingStatus.VALID:
            msg = doc_content.error_message or f"Document rejected with status {doc_content.status.value}"
            if doc_content.status == DocumentProcessingStatus.UNSUPPORTED or "mime" in msg.lower():
                raise UnsupportedMediaTypeError(f"Rejected '{filename}': {msg}")
            raise APIError(
                status_code=400,
                error_code=f"DOCUMENT_{doc_content.status.value}",
                message=f"Rejected '{filename}': {msg}",
            )

        processed_items.append(
            ProcessedDocumentItem(
                document_id=doc_content.document_id,
                file_name=doc_content.file_name,
                document_type=doc_content.document_type.value,
                status=doc_content.status.value,
                page_count=doc_content.page_count,
                extraction_method=doc_content.extraction_method.value,
                sha256=doc_content.sha256,
                error_message=doc_content.error_message,
            )
        )

    return DocumentProcessResponse(
        request_id=req_id,
        document_count=len(processed_items),
        documents=processed_items,
    )
