# FIN — Existing Security Baseline & Gap Analysis

## 1. Existing Protections (Phases 1–13)

Prior phases implemented foundational defense mechanisms:

1. **Source Ingestion & URL Validation:**
   - Strict allowlisting of `.gov.in` and `.nic.in` domains (`AcquisitionSecurityValidator`).
   - Rejection of deceptive domain patterns (e.g., `*.gov.in.attacker.com`).
   - Explicit Hugging Face repository allowlist (`Intelligence/src/data_pipeline/sources/registry.py`).
   - Supplementary tier isolation: Hugging Face datasets cannot override official statutory criteria.

2. **File Processing Defense:**
   - Pre-ingestion validation (`DocumentValidator` in `Intelligence/src/documents/validator.py`).
   - Basic magic byte detection for PDF, ZIP/DOCX, PNG, JPEG, WEBP.
   - Decompression bomb check via `MAX_IMAGE_PIXELS` (100 MP limit).
   - Filename sanitization against path traversal (`../`) and null bytes (`\x00`).

3. **API & Endpoint Security:**
   - Basic `X-AI-Service-Key` header authentication (`Intelligence/src/api/auth.py`) using `hmac.compare_digest`.
   - Correlation tracking with `X-Request-ID` middleware.
   - Basic in-memory sliding-window rate limiter (`InMemoryRateLimiter`).
   - Standardized error handlers masking uncaught exceptions into `500 INTERNAL_SERVER_ERROR`.

4. **LLM Safety & Prompt Injection:**
   - Non-destructive injection regex detection (`PromptInjectionDetector` in `Intelligence/src/llm/safety.py`).
   - XML wrapping (`<UNTRUSTED_USER_INPUT>`).
   - Deterministic eligibility guard (`DecisionImmutabilityGuard`): LLM cannot overturn Phase 3 rule evaluation outcomes.

---

## 2. Identified Security Gaps & Hardening Mandates

Despite robust foundations, several production-critical hardening gaps must be resolved:

| Domain | Baseline Limitation | Phase 14 Hardening Mandate |
|---|---|---|
| **Configuration** | Settings spread across `api/config.py` and `llm/config.py`; no strict environment enforcement. | Create centralized `Intelligence/src/config/security.py` with explicit `DEV`, `TEST`, `PROD` modes. Fail closed on missing production credentials. |
| **Secrets Management** | Inadvertent logging of API keys or Bearer tokens in tracebacks or error messages possible. | Implement automated secret and PII redactor filter across all logging handlers, exception formatters, and API responses. |
| **Authentication** | Default dev key accepted in all modes; no key length or entropy checks. Public routes not cleanly isolated from protected routes. | Restrict public access to `/health/live`. Require $\ge 16$ char high-entropy keys in production. Constant-time validation with zero secret reflection. |
| **Authorization** | Flat service key; no role distinction between citizens, internal service calls, administrators, and reviewers. | Implement lightweight role-based access control (`CITIZEN`, `SERVICE`, `ADMIN`, `REVIEWER`). Restrict policy mutations (`/v1/policy/*`) to `ADMIN`. |
| **Input Validation** | Individual routes parse raw Pydantic bodies without global payload size or string length caps. | Enforce global request body limit (30MB), string length caps, query sanitization, and traversal rejection across all endpoints. |
| **File Security** | Temporary files stored in standard `/tmp` or local directory without strict UUID isolation. No DOCX zip bomb ratio check. | Isolate temporary uploads in dedicated UUID subdirectories; enforce 50:1 compression ratio limit and reject macro-enabled DOCX (`vbaProject.bin`). |
| **SSRF & HTTP** | Outbound HTTP clients do not strictly validate destination IPs upon following redirects. | Implement strict redirect tracking (max 3) with re-validation after every hop. Reject all private RFC 1918, link-local, loopback, and cloud metadata IPs. |
| **Rate Limiting** | Single global rate limit bucket; expensive operations (OCR, RAG, LLM chat, policy sync) share limit with lightweight reads. | Introduce multi-tiered rate limiting: `PUBLIC` (60/min), `PROTECTED` (120/min), `EXPENSIVE` (20/min). |
| **CORS & Headers** | `allow_origins=["*"]` used with `allow_credentials=True` in development. Missing standard security headers. | Enforce explicit origin allowlists; add `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, and restrictive `Content-Security-Policy`. |
| **Storage Safety** | File writes in data pipeline and snapshot manager use direct `open(..., "w")`. | Implement atomic writes (`tempfile` + `os.replace`) to prevent partial file corruption during concurrent operations or power failures. |
| **Logging & Privacy** | Log entries may contain user query text with un-redacted Aadhaar/PAN or phone numbers. | Enforce automatic PII redaction (Aadhaar, PAN, phone, email, tokens) in structured logging middleware. |

---

## 3. Threat Model & Boundaries

```
[Untrusted Client / Citizen Browser]
           │
           │  (HTTPS, X-Request-ID, CORS, Rate Limiting)
           ▼
┌────────────────────────────────────────────────────────┐
│  FastAPI Security Edge                                │
│  - Security Headers & Request Body Size Check (30MB)   │
│  - Authentication: X-AI-Service-Key (Constant Time)    │
│  - Authorization: Role Enforcement (CITIZEN/ADMIN/etc) │
│  - Input Validation: Regex & Traversal Sanitization   │
└────────────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────┐
│  Core Processing Layers                                │
│  - Document Ingestion: Magic Byte & Zip Bomb Defense   │
│  - Deterministic Rules: Phase 3 Invariant Enforcer     │
│  - Outbound HTTP: SSRF & Cloud Metadata Blocking      │
│  - LLM Orchestration: XML Trust Boundaries & Redact   │
│  - Storage Engine: Atomic Replaces & Snapshot Hashes   │
└────────────────────────────────────────────────────────┘
```
