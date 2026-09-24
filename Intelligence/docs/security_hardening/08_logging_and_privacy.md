# FIN Structured Logging, Telemetry & Privacy Filtering

## 1. Zero-Trust Logging Principles
Operational telemetry must enable robust debugging, latency tracking, and security auditing without functioning as an unintended repository for secrets or citizen PII.

---

## 2. Telemetry Fields Recorded
Structured access logs record the following standard attributes:
- `timestamp`: ISO 8601 UTC timestamp.
- `level`: Log level (`INFO`, `WARNING`, `ERROR`, `CRITICAL`).
- `request_id`: Correlation tracing token (`req_<uuid>`).
- `method`: HTTP method (`GET`, `POST`, `OPTIONS`).
- `path`: API route path (e.g., `/v1/eligibility/check`).
- `status_code`: HTTP response status code.
- `latency_ms`: Elapsed execution latency in milliseconds.
- `source_id`: Policy source identifier where applicable.

---

## 3. Forbidden Log Fields (Strict Prohibitions)
The following fields are strictly prohibited from appearing in any log record:
- API Keys (`GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `AI_SERVICE_API_KEY`)
- Bearer tokens and raw Authorization headers
- Aadhaar numbers (12-digit patterns)
- Permanent Account Numbers (PAN)
- Indian phone numbers (+91 / 10-digit mobile)
- Email addresses
- Raw uploaded binary document bytes
- Full OCR raw text extracts
- Internal absolute filesystem paths

---

## 4. Programmatic Interception (`SecretRedactingLoggingFilter`)
A centralized logging filter is attached to Python's logging handlers:
1. Intercepts `record.msg` and `record.args`.
2. Evaluates compiled regular expressions across secrets and citizen PII.
3. Automatically replaces matched patterns with standardized tokens (`[SECRET_REDACTED]`, `[AADHAAR_REDACTED]`, `[PAN_REDACTED]`, `[PHONE_REDACTED]`).
4. Ensures that developer debug messages and third-party library logs are automatically sanitized before output to stdout or file streams.
