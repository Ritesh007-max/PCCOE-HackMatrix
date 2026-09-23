# PolicySetu OpenRouter Fallback Specification

## 1. Role & Operational Scope

OpenRouter serves strictly as a **secondary fallback provider** when Google Gemini suffers transient operational failure.
All interactions with OpenRouter use OpenAI-compatible HTTP REST endpoints (`https://openrouter.ai/api/v1/chat/completions`).

### Mandatory Headers
```http
POST /api/v1/chat/completions HTTP/1.1
Host: openrouter.ai
Authorization: Bearer <OPENROUTER_API_KEY>
Content-Type: application/json
HTTP-Referer: https://policysetu.gov.in
X-Title: PolicySetu AI Subsystem
```

## 2. Text-Based Normalized Ingestion

To circumvent OpenRouter's native file upload limitations, OpenRouter is never fed raw binary PDFs or images.
Instead, PolicySetu passes the clean, normalized, and pre-extracted `DocumentContent` text and structured tables generated during the ingestion phase.

## 3. Strict Fallback Eligibility Rules

Fallback to OpenRouter is permitted **ONLY** on the following explicit operational failure categories:
1. `ProviderTimeoutError`: Gemini request exceeded timeout threshold (30 seconds).
2. `ProviderRateLimitError`: Gemini API returned HTTP 429 or quota exceeded.
3. `ProviderUnavailableError`: Gemini API returned HTTP 500, 502, 503, or 504.
4. `ProviderNetworkError`: Socket connection drop, DNS failure, or transport error.
5. `ProviderInvalidResponseError` / `ProviderStructuredOutputError`: Gemini returned empty response or unparseable payload.

### Strict Prohibition
- **Authentication & Configuration Errors**: HTTP 401, 403, or invalid/missing API keys MUST immediately raise `ProviderAuthenticationError` or `ProviderConfigurationError`. **Fallback is strictly prohibited on authentication errors.**
- **Decision Outcomes**: Deterministic rule failures (FAIL / UNKNOWN / REVIEW) MUST NEVER trigger fallback.

## 4. Operational Telemetry

When fallback occurs, `LLMRouter` records complete operational metrics in `ProviderExecutionResult`:
```python
{
    "provider": "openrouter",
    "model": "google/gemini-2.5-flash",
    "status": "success",
    "attempt": 2,
    "latency_ms": 1420.5,
    "fallback_used": True,
    "fallback_reason": "gemini_providertimeouterror"
}
```
