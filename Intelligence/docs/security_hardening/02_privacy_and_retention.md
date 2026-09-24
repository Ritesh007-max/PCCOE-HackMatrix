# FIN Data Classification, Privacy & Retention Policy

## 1. Objective & Core Principles
FIN operates as an intelligent public benefit discovery and evaluation engine. It handles both public government policy metadata and highly sensitive citizen documents (certificates, income statements, identity credentials).

The system enforces three non-negotiable architectural privacy invariants:
1. **Data Minimization**: Collect only what is strictly necessary to evaluate eligibility.
2. **Ephemeral Document Lifecycle**: Raw uploaded binary files and rasterized OCR artifacts are strictly temporary and never persisted to permanent storage.
3. **Zero-PII Telemetry**: Logs, metric ledgers, exception reports, and evaluation audits must never store citizen identity numbers, biometric records, or full OCR transcripts.

---

## 2. Data Classification Matrix

| Classification Level | Definition | Examples in FIN | Storage Mechanism | Retention Window | Access Controls |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PUBLIC** | Openly accessible statutory and government information. | Scheme titles, criteria guidelines, benefits summaries, portal links, FAQs. | Static Parquet, FAISS Index, ChromaDB. | Indefinite (versioned by snapshot). | Public anonymous read access. |
| **INTERNAL** | System operational state, health metrics, and sync metadata. | Policy sync run ledgers, activation gate logs, model latency telemetry. | File-backed JSON logs, metrics store. | 90 days rolling window. | `SERVICE` and `ADMIN` roles. |
| **SENSITIVE** | Extracted applicant facts required for deterministic rule evaluation. | Age, annual income, caste category, residence state, occupation, disability status. | In-memory session state, evaluation audit records. | Duration of evaluation session (ephemeral). | `CITIZEN` (own data) and authorized `SERVICE`. |
| **HIGHLY_SENSITIVE** | Real citizen identity credentials, raw documents, and cryptographic keys. | Aadhaar numbers, PAN numbers, raw uploaded PDF/DOCX/images, `AI_SERVICE_API_KEY`, Gemini/OpenRouter keys. | Isolated temp directory (`fin_doc_*`), ephemeral memory buffers. | Immediate cleanup on request completion ($< 60$s). | Strict programmatic isolation; zero client access. |

---

## 3. Data Retention Lifecycle

### 3.1 Uploaded Documents (PDF, PNG, JPEG, WEBP, DOCX)
- **Ingestion**: Uploaded bytes are validated in memory and passed into `isolated_temp_document()`.
- **Isolation**: Written to a dedicated temporary directory (`/tmp/fin_doc_<uuid>`) with randomized filesystem tokens.
- **Cleanup**: Handled via Python context managers (`finally:` block). Immediately unlinked upon extraction completion. Maximum disk residency is bounded by request timeout (60 seconds).
- **Zero Raw Document Persistence**: The AI microservice never writes citizen uploads to database tables or permanent disks.

### 3.2 Extracted Text & OCR Blocks
- **Processing**: Rasterized images and raw OCR bounding boxes exist only within memory during request execution.
- **Filtering**: All extracted text is sanitized before model context assembly.
- **Telemetry Safeguard**: `SecretRedactingLoggingFilter` strips any accidental PAN or Aadhaar tokens before logging.

### 3.3 Extracted Applicant Facts
- Facts extracted from documents (e.g. `{"annual_income": 120000, "state": "Maharashtra"}`) are returned to the caller (BackEnd) and are not retained inside the AI microservice state.

### 3.4 Operational & Sync Audit Logs
- Sync execution logs (`sync_report_<timestamp>.json`) and HTTP request ledgers record timing, scheme counts, status codes, and hashes.
- PII and credentials are comprehensively redacted using `redact_secrets()`.
- Retention period is 90 days for operational auditability.

---

## 4. Sensitive Field Redaction Rules

| Identifier Type | Pattern Signature | Redaction Replacement |
| :--- | :--- | :--- |
| **Aadhaar Number** | 12 digits, spaced or hyphenated | `[AADHAAR_REDACTED]` |
| **PAN Number** | 5 letters + 4 digits + 1 letter | `[PAN_REDACTED]` |
| **Indian Phone** | 10 digits with optional +91 / 0 prefix | `[PHONE_REDACTED]` |
| **Email Address** | Standard RFC 5322 format | `[EMAIL_REDACTED]` |
| **API Keys** | Gemini, OpenRouter, OpenAI, HF tokens | `[SECRET_REDACTED]` |
| **Bearer Tokens** | `Bearer <token>` in auth headers | `[BEARER_TOKEN_REDACTED]` |
| **Filesystem Paths** | Local machine paths (`C:\Users\...`) | `[PATH_REDACTED]` |

---

## 5. Security Invariant Enforcement
1. **No Cold Storage of Citizen PII**: The AI component functions statelessly regarding citizen identity.
2. **Immutable Audit Trails**: Operational mutations (e.g., policy snapshots) record cryptographic SHA-256 digests rather than raw document files.
3. **Fail-Closed on Unsafe Persistence**: Any file write that escapes the designated working directory is blocked with `StorageSecurityError`.
