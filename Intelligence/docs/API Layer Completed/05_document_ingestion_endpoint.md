# FIN Phase 9 — Document Ingestion Endpoint

## 1. Endpoint Overview

`POST /v1/documents/process` ingests raw citizen documents, parses their layout and text, and returns structured extraction metadata.

- **URL**: `/v1/documents/process`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Authentication**: Required (`X-AI-Service-Key`)

---

## 2. Request Parameters

| Parameter | Type | In | Description |
| :--- | :--- | :--- | :--- |
| `files` | `List[UploadFile]` | `form-data` | One or more citizen documents (PDF, JPG, PNG, WEBP, DOCX, TXT) |

---

## 3. Supported Document Formats & Limits

- **Formats**: PDF (native & scanned), Images (JPEG, PNG, WEBP), Word (.docx), Plain Text (.txt)
- **Max File Size**: 25 MB per document (configurable via `AI_MAX_UPLOAD_SIZE_MB`)
- **Max Files Per Batch**: 10 files (configurable via `AI_MAX_FILES_PER_REQUEST`)
- **Decompression Bomb Guard**: Max image limit 100 Megapixels.
- **Unfamiliar Documents**: Classified safely as `UNKNOWN_DOCUMENT` without aborting.

---

## 4. Response Payload Schema

```json
{
  "request_id": "req_8f1b2c3d4e5f",
  "document_count": 1,
  "documents": [
    {
      "document_id": "doc_e3b0c44298fc",
      "file_name": "income_certificate.pdf",
      "document_type": "INCOME_CERTIFICATE",
      "status": "VALID",
      "page_count": 1,
      "extraction_method": "NATIVE_PDF",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "error_message": null
    }
  ]
}
```

---

## 5. Error Scenarios

- **400 Bad Request**: Empty (0-byte) file uploaded (`EMPTY_FILE`).
- **413 Payload Too Large**: Upload exceeds configured size ceiling (`PAYLOAD_TOO_LARGE`).
- **415 Unsupported Media Type**: Corrupted or unrecognized file magic bytes (`UNSUPPORTED_MEDIA_TYPE`).
