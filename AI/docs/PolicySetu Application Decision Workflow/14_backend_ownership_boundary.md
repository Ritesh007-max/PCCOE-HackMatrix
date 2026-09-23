# Phase 10: Backend vs. AI Ownership Boundary

## 1. Ownership Principles

Phase 10 rigorously maintains architectural boundaries between the **AI Subsystem** and the future **Backend**:

```
+-------------------------------------------------------------+
|                      FUTURE BACKEND                         |
|  - Citizen accounts, authentication, and authorization      |
|  - Multi-tenant relational database (PostgreSQL)            |
|  - User sessions and token issuance (JWT)                   |
|  - Permanent citizen document blob storage (S3 / MinIO)     |
|  - Notification dispatch (SMS, Email, Push)                 |
|  - Formal application submission transactions with portals  |
+-------------------------------------------------------------+
                              |
                              | REST / gRPC API contracts
                              v
+-------------------------------------------------------------+
|                      AI SUBSYSTEM                           |
|  - AI-derived applicant facts & normalization               |
|  - Multi-document evidence corroboration & conflict detect  |
|  - Deterministic statutory rule AST evaluation              |
|  - Deterministic benefit calculations                       |
|  - Application readiness signals & checklist generation     |
|  - Grounded next actions engine                             |
|  - Immutable statutory decision snapshots                   |
|  - Processing-time workflow state machine                   |
+-------------------------------------------------------------+
```

---

## 2. Invariants Enforced in AI Layer

1. **No User Accounts in AI**: The AI subsystem operates purely on `application_id`, `citizen_reference`, and request tokens. It does not manage passwords, password resets, or identity provider federations.
2. **No Raw Document Storage**: The AI pipeline processes documents in-memory or from temporary staging paths; permanent document archive storage belongs to the Backend.
3. **No Direct Submission Side-Effects**: The AI system prepares applications and assesses readiness; executing payments or formal portal HTTP submissions belongs to the Backend.
