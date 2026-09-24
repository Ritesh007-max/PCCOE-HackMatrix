# FIN Phase 9 — Rate Limiting & Resilience Architecture

## 1. Design Principles

Rate limiting protects high-compute AI operations (such as PDF OCR, dense vector embedding calculation, and LLM generative calls) from denial-of-service degradation.

> [!IMPORTANT]
> **Local Development Invariant**: Rate limiting is disabled by default in development mode (`AI_RATE_LIMIT_ENABLED=false`). It must never block local developer testing, regression runs, or onboarding workflows.

---

## 2. In-Memory Sliding-Window Implementation

The microservice includes `InMemoryRateLimiter`:
- Tracks request timestamps per client authentication key over a 60-second sliding window.
- Automatically evicts timestamps older than 60 seconds (`timestamps.popleft()`).
- Does not require external distributed memory caches (e.g. Redis) for single-instance or local setups.

### Configuration

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `AI_RATE_LIMIT_ENABLED` | `false` | Master toggle for rate limiting |
| `AI_RATE_LIMIT_PER_MINUTE` | `60` | Maximum requests permitted per 60-second window |

---

## 3. Rate Limit Rejection Handling

When a caller exceeds the configured threshold, the microservice immediately halts processing before expensive OCR or LLM tasks:

- **HTTP Status Code**: `429 Too Many Requests`
- **Header**: `Retry-After: <seconds_until_earliest_slot>`
- **Response Payload**:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded (60 req/min). Please try again shortly.",
    "request_id": "req_f8e7d6c5b4a3",
    "details": null
  }
}
```

---

## 4. Multi-Tier Provider Resilience

LLM invocations inside `/v1/chat` and `/v1/applications/analyze` benefit from the Phase 8 provider resilience framework:

1. **Primary Provider (Gemini)**: Executed by default.
2. **Transient Operational Failure**: If Gemini returns a timeout, network failure, or HTTP 429 rate limit, the router immediately initiates fallback to OpenRouter.
3. **Authentication Failure Protection**: If Gemini returns a 401 unauthenticated or invalid API key error, fallback is **strictly prohibited**. The service returns an explicit error to prevent silent credential drift.
4. **Offline RAG Fallback**: If all remote providers are unavailable, `/v1/chat` synthesizes a deterministic response directly from verified RAG chunk excerpts.
