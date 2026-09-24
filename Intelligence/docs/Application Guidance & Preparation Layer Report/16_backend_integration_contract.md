# Phase 11: Backend Integration Contract (Preparation for Phase 15)

## 1. Zero-Change Invariant for Current Phase

In strict compliance with Phase 11 boundaries:
- `BackEnd/` directory: **ZERO modifications**.
- `FrontEnd/` directory: **ZERO modifications**.
- Root `README.md`: **ZERO modifications**.

---

## 2. API Contract for Future Integration (Phase 15)

When Phase 15 (Backend Integration) connects the Go/Node/Python backend to the AI Microservice, it will consume the following endpoints without altering the internal AI guidance models:

### `GET /v1/applications/{application_id}/guidance`
- **Query Parameters**:
  - `scheme_id` (optional): Defaults to candidate selected scheme.
  - `language` (optional): `en`, `hi`, `hinglish` (default: `en`).
- **Response**: Full `ApplicationGuidancePackage` JSON payload.

### `GET /v1/applications/{application_id}/guidance/markdown`
- **Response**: Pre-formatted Markdown document ready for direct rendering in documentation viewers or email summaries.
