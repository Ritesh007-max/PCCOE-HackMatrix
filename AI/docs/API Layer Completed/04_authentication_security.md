# PolicySetu Phase 9 — Authentication & Security Architecture

## 1. Internal Service-to-Service Authentication

The PolicySetu AI Microservice is an internal service designed to be called by backend orchestrators. It does not handle citizen user sessions directly.

### Constant-Time Verification
All protected endpoints enforce key verification via `hmac.compare_digest`:

```python
# src/api/auth.py
is_valid = hmac.compare_digest(x_ai_service_key.strip(), expected_key.strip())
if not is_valid:
    raise HTTPException(status_code=401, detail="Invalid service API key.")
```

This prevents side-channel timing attacks that could allow attackers to infer key characters by measuring response latencies.

---

## 2. Zero Secret Leakage Invariant

1. **Header Sanitization**: Access log entries do not log `X-AI-Service-Key` or `Authorization` headers.
2. **Error Responses**: Validation or exception handlers do not print API keys or system environment variables into error payloads.
3. **Telemetry Payloads**: Pipeline telemetry records provider name, model identifier, and latency, but never credential tokens.

---

## 3. Request Correlation & Tracing

Every incoming request is tagged with a unique correlation identifier:
- If the caller provides `X-Request-ID`, it is preserved and propagated across all log entries and responses.
- If omitted, the `RequestCorrelationMiddleware` generates a cryptographically random UUID (`req_<hex>`).
- All error responses include the `request_id` for easy cross-service log tracing.

---

## 4. Prompt Injection Defense

All user-supplied natural language queries passed to `/v1/chat` or `/v1/applications/analyze` pass through `PromptInjectionDetector`:
- Scans for instruction overrides (e.g. `ignore all previous instructions`, `make me eligible`, `developer mode`).
- If detected, `/v1/chat` blocks execution without calling LLM providers and returns `intent: "INJECTION_BLOCKED"`.
- Untrusted inputs are wrapped in strict XML isolation boundaries (`wrap_untrusted_input`) before LLM synthesis.
