# FIN Phase 9 — API Specification

## 1. Overview

The FIN AI Microservice exposes RESTful JSON and multipart endpoints under standard OpenAPI specifications. Interactive documentation is available at `/docs` (Swagger UI) and `/redoc` (ReDoc).

All endpoints require authentication via the `X-AI-Service-Key` header, except `/health/live`.

---

## 2. Endpoint Index

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/health/live` | Non-blocking liveness probe | No |
| `GET` | `/health/ready` | Component readiness audit | Yes |
| `GET` | `/version` | Build, pipeline, and snapshot metadata | Yes |
| `POST` | `/v1/documents/process` | Multi-format citizen document parsing | Yes |
| `POST` | `/v1/schemes/search` | Hybrid semantic & keyword policy search | Yes |
| `POST` | `/v1/eligibility/check` | 100% deterministic rule AST evaluation | Yes |
| `POST` | `/v1/chat` | Grounded conversational Q&A with citations | Yes |
| `POST` | `/v1/applications/analyze` | Complete 21-step document-to-decision pipeline | Yes |

---

## 3. Standard Request Headers

| Header | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `X-AI-Service-Key` | `string` | Yes | Pre-shared internal service authentication key |
| `X-Request-ID` | `string` | Optional | Client correlation ID (generated automatically if omitted) |
| `Content-Type` | `string` | Yes | `application/json` or `multipart/form-data` |

---

## 4. Standard Error Response Envelope

All error responses follow a uniform Pydantic model:

```json
{
  "error": {
    "code": "BAD_REQUEST",
    "message": "Human-readable explanation of error.",
    "request_id": "req_a1b2c3d4e5f6",
    "details": null
  }
}
```

### Standard Error Codes
- `UNAUTHORIZED` (401): Missing or invalid `X-AI-Service-Key`.
- `FORBIDDEN` (403): Request forbidden.
- `NOT_FOUND` (404): Resource or route not found.
- `VALIDATION_ERROR` (422): Malformed JSON or invalid schema field values.
- `RATE_LIMIT_EXCEEDED` (429): Client exceeded request quota.
- `PAYLOAD_TOO_LARGE` (413): Upload exceeded `AI_MAX_UPLOAD_SIZE_MB`.
- `UNSUPPORTED_MEDIA_TYPE` (415): File format rejected by validator.
- `INTERNAL_SERVER_ERROR` (500): Unhandled exception.
