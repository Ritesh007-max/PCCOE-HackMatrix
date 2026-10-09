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
    get_applicant_context_service,
)
from ..schemas import DocumentProcessResponse, ProcessedDocumentItem
from ..errors import APIError, PayloadTooLargeError, UnsupportedMediaTypeError
from src.documents.pipeline import DocumentPipeline
from src.documents.models import DocumentProcessingStatus
from src.documents.field_extractor import extract_document_fields
from src.context.service import ApplicantContextService

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
    context_service: ApplicantContextService = Depends(get_applicant_context_service),
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

        full_text = doc_content.get_full_text()
        extracted_fields = extract_document_fields(
            full_text=full_text,
            doc_type=doc_content.document_type.value if hasattr(doc_content.document_type, "value") else str(doc_content.document_type),
            filename=filename
        )

        # 3. Canonical fact extraction, OCR provenance mapping, and structured persistence
        applicant_id = (
            request.headers.get("X-Applicant-ID")
            or request.query_params.get("applicant_id")
            or "default_applicant"
        )
        try:
            doc_ctx, canonical_facts, evidence_list = context_service.process_and_store_document(
                doc_content, applicant_id=applicant_id
            )
        except Exception as exc:
            import logging
            logging.getLogger("fin.api.routes.documents").warning(
                "Local persistence skipped for '%s': %s", filename, exc
            )

        conf_val = float(doc_content.metadata.get("detected_type_confidence") or 0.0)
        final_conf = conf_val if conf_val > 0 else (0.95 if extracted_fields else 0.85)

        processed_items.append(
            ProcessedDocumentItem(
                document_id=doc_content.document_id,
                file_name=doc_content.file_name,
                document_type=doc_content.document_type.value if hasattr(doc_content.document_type, "value") else str(doc_content.document_type),
                status=doc_content.status.value if hasattr(doc_content.status, "value") else str(doc_content.status),
                page_count=doc_content.page_count,
                extraction_method=doc_content.extraction_method.value if hasattr(doc_content.extraction_method, "value") else str(doc_content.extraction_method),
                sha256=doc_content.sha256,
                error_message=doc_content.error_message,
                extracted_text=full_text if full_text else None,
                extracted_fields=extracted_fields,
                confidence_score=round(final_conf, 3),
            )
        )

    return DocumentProcessResponse(
        request_id=req_id,
        document_count=len(processed_items),
        documents=processed_items,
    )


@router.delete(
    "/{document_id}",
    summary="Delete Ingested Document",
    description="Removes an ingested document, its facts, and evidence from the applicant context.",
)
async def delete_document(
    document_id: str,
    request: Request,
    _: str = Depends(verify_service_api_key),
    context_service: ApplicantContextService = Depends(get_applicant_context_service),
):
    applicant_id = (
        request.headers.get("X-Applicant-ID")
        or request.query_params.get("applicant_id")
        or "default_applicant"
    )
    context_service.delete_document(applicant_id, document_id)
    return {"success": True, "message": f"Document {document_id} deleted for applicant {applicant_id}"}
