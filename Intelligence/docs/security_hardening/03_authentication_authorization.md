# FIN Authentication & Authorization Hardening

## 1. Authentication Architecture

### 1.1 Invariant Principles
- **Timing-Attack Resistance**: All service-to-service key comparisons use `hmac.compare_digest`.
- **Fail-Closed in Production**: The system refuses to boot or serve requests in production if default development keys or empty strings are configured.
- **Minimum Key Length**: Keys must be at least 16 characters. Trivial keys (e.g. `secret`, `admin123`) are rejected with HTTP 401.
- **Zero Key Leakage**: Authentication failure logs and client responses never reflect caller-supplied keys or expected internal keys.

### 1.2 Route Protection Matrix

| Route Category | Endpoints | Security Classification | Required Header |
| :--- | :--- | :--- | :--- |
| **Public Liveness** | `GET /health/live` | Public Anonymous | None |
| **System Readiness** | `GET /health/ready` | Protected Internal | `X-AI-Service-Key` |
| **Pipeline Version** | `GET /version` | Protected Internal | `X-AI-Service-Key` |
| **Citizen APIs** | `POST /v1/eligibility/check`, `POST /v1/chat/message`, `POST /v1/schemes/search` | Protected Service / Citizen | `X-AI-Service-Key` |
| **Expensive Pipelines**| `POST /v1/documents/process`, `POST /v1/applications/analyze` | Protected Service | `X-AI-Service-Key` |
| **Policy Mutation** | `POST /v1/policy/sync`, `POST /v1/policy/rollback` | Strictly Restricted ADMIN | `X-AI-Service-Key` + `Role.ADMIN` |

---

## 2. Authorization Role Hierarchy

```
       [ ADMIN ]
       /   |   \
      /    |    \
 [REVIEWER]|   [SERVICE]
      \    |    /
       \   |   /
       [ CITIZEN ]
```

### 2.1 Role Definitions
1. **`CITIZEN`**: Allowed to execute citizen-facing scheme searches, submit documents for analysis, and query the conversational assistant.
2. **`SERVICE`**: Internal backend microservice caller. Permitted to orchestrate application analysis, document processing, and health readiness inspection.
3. **`REVIEWER`**: Government eligibility officer / human reviewer. Permitted to inspect conflicts, review evaluation cases, and inspect sync reports. Prohibited from live policy activation or rollback.
4. **`ADMIN`**: Platform administrator. Authorized to trigger live policy synchronization, dry-run evaluation, and atomic rollbacks.

### 2.2 Role Extraction & Dependency Injection
- Roles are declared via `X-AI-Role` header.
- Unspecified role defaults to `Role.SERVICE` for authenticated service callers.
- Unrecognized or spoofed role headers fail-safe to `Role.CITIZEN`.
- Sensitive routes use `Depends(require_admin)` which enforces both valid API key authentication and `ADMIN` role privilege.
