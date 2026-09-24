# FIN Rate Limiting & Resource Exhaustion Protection

## 1. Rate Limiting Architecture

FIN implements a multi-tier sliding-window rate limiter inside the AI microservice (`InMemoryRateLimiter`).

### 1.1 Operational Tiers

| Tier | Default Limit | Target Endpoints | Justification |
| :--- | :--- | :--- | :--- |
| **`PUBLIC`** | 60 req/min | `GET /health/live` | Lightweight liveness probe; defends against unauthenticated denial-of-service flooding. |
| **`PROTECTED`** | 120 req/min | `GET /health/ready`, `GET /version`, `POST /v1/schemes/search`, `GET /v1/policy/status` | Standard service-to-service operations; adequate bandwidth for BackEnd requests. |
| **`EXPENSIVE`** | 20 req/min | `POST /v1/documents/process`, `POST /v1/applications/analyze`, `POST /v1/chat/message`, `POST /v1/policy/sync`, `POST /v1/policy/rollback` | Heavy computational workflows (OCR rendering, model inference, embedding generation, live sync). |

### 1.2 Sliding Window Mechanics
- Window duration: 60.0 seconds rolling.
- Bucketing: Keys are isolated by `(client_ip, tier)`.
- Rejection: Bypassing the threshold raises `RateLimitExceededError` returning HTTP 429 Too Many Requests with `Retry-After` header.

---

## 2. Resource Exhaustion Protections

### 2.1 Request Payload Limits
- Content-Length inspected early via `RequestBodyLimitMiddleware`.
- Maximum request body size: 30 MB. Payloads exceeding this limit receive HTTP 413 Payload Too Large before body buffering.

### 2.2 Upload File Bounds
- Maximum single file size: 25 MB.
- Maximum files per batch: 10 files.
- PDF page limit: 100 pages maximum.
- Image pixel limit: 100 Megapixels maximum.
- DOCX decompression ratio: 50:1 ceiling (zip bomb defense).

### 2.3 Concurrency & Timeout Bounds
- Outbound crawler concurrency: Bounded to 20 threads.
- HTTP client request timeout: 30.0 seconds total ceiling.
- Policy sync mutex lock: Prevents concurrent live snapshot mutations or race conditions on the active policy pointer.
