# FIN API Security, Input Validation & Error Handling

## 1. Input Validation Architecture

FIN implements a multi-layer defense against input tampering, buffer overruns, and injection attacks:

### 1.1 Strict Parameter Validation
- **Null-Byte Rejection**: Null bytes (`\x00`) are blocked across all string inputs to defend against C-level string termination vulnerabilities.
- **Path Traversal Rejection**: Input sequences containing `../` or `..\` are detected and rejected with HTTP 400.
- **String Length Limits**:
  - Scheme search queries: Maximum 1,000 characters.
  - Snapshot IDs / identifiers: Maximum 64 characters (restricted to `^[a-zA-Z0-9_\-\.]{1,64}$`).
  - Text prompts: Maximum 50,000 characters.
- **List Size Bounding**: Maximum 100 items per array input to prevent memory exhaustion and algorithmic complexity attacks.
- **Language Code Validation**: BCP 47 compliant regex validation (e.g., `en`, `hi`, `mr`, `ta`).

---

## 2. Production Error Handling & Leakage Prevention

### 2.1 Error Model
All errors returned by FIN follow a standardized JSON structure:
```json
{
  "error": {
    "code": "BAD_REQUEST",
    "message": "Safe human-readable error description.",
    "request_id": "req_a1b2c3d4e5f6",
    "details": null
  }
}
```

### 2.2 Strict Zero-Leakage Guarantees
1. **No Stack Traces**: Python exception tracebacks are logged internally (via `SecretRedactingLoggingFilter`) but never returned in HTTP responses.
2. **No Secret Reflection**: Any error message or exception containing credentials (`AIzaSy...`, `sk-or-v1-...`, `Bearer ...`) is scrubbed with `[SECRET_REDACTED]`.
3. **No Internal Path Reflection**: Absolute file paths (`C:\Users\...` or `/home/...`) are scrubbed with `[PATH_REDACTED]`.
4. **No Database Details**: Internal SQL strings or connection pool states are never surfaced.

---

## 3. Request Correlation Tracing

- Every incoming HTTP request is assigned a unique `X-Request-ID`.
- If supplied by the caller: validated against `^[a-zA-Z0-9_\-]{1,64}$` to block header injection or CRLF attacks.
- If invalid or absent: a high-entropy UUID identifier (`req_<hex>`) is generated.
- Attached to Starlette `request.state.request_id` and mirrored in the `X-Request-ID` response header.
- Never utilized as an authentication or security token.
