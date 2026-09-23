# PolicySetu Phase 9 — Microservice Architecture Overview

## 1. Objective & Scope

Phase 9 converts the completed Phase 8 internal AI pipelines into a production-oriented AI microservice with a clean, stable HTTP interface. The microservice serves as the single AI intelligence engine for the PolicySetu ecosystem, decoupling high-compute document OCR, hybrid RAG retrieval, AST eligibility evaluation, and grounded generative explanations from external caller implementations.

> [!IMPORTANT]
> **Scope Guardrail**: Phase 9 delivers production-oriented API infrastructure. Actual cloud production deployment, TLS certificate management, and infrastructure security hardening are reserved for subsequent operational phases. No code claims "production-ready" status at this stage.

---

## 2. Structural Architecture

```
HTTP Clients / Caller Services (e.g. Backend Orchestrators)
         |
         | [X-AI-Service-Key, X-Request-ID]
         v
+-------------------------------------------------------------+
|               FastAPI Microservice (src.api)                |
|                                                             |
|  +-------------------------------------------------------+  |
|  | Middleware Stack:                                     |  |
|  | - RequestCorrelationMiddleware (X-Request-ID)        |  |
|  | - StructuredLoggingMiddleware (Latency, No Secrets)   |  |
|  | - CORSMiddleware                                      |  |
|  | - InMemoryRateLimiter (Configurable, Dev-Friendly)    |  |
|  +-------------------------------------------------------+  |
|                                                             |
|  +-------------------------------------------------------+  |
|  | Centralized Error Handling (Consistent ApiError)      |  |
|  +-------------------------------------------------------+  |
|                                                             |
|  +-------------------------------------------------------+  |
|  | Route Endpoints:                                      |  |
|  |  - /health/live        (Public Liveness)              |  |
|  |  - /health/ready       (Protected Dependency Audit)   |  |
|  |  - /version            (Protected Build Info)         |  |
|  |  - /v1/documents/process (Multi-format Ingestion)     |  |
|  |  - /v1/schemes/search  (Dense-Sparse Hybrid RAG)      |  |
|  |  - /v1/eligibility/check (100% Deterministic AST)     |  |
|  |  - /v1/chat            (Grounded RAG Q&A)             |  |
|  |  - /v1/applications/analyze (21-Step Pipeline)        |  |
|  +-------------------------------------------------------+  |
+-------------------------------------------------------------+
         |
         | Direct Dependency Injection (FastAPI Depends)
         v
+-------------------------------------------------------------+
|             Authoritative Phase 8 Internal Engines          |
|                                                             |
|  - DocumentPipeline (PDF, DOCX, Image, OCR, Unknown Type)   |
|  - HybridRetriever (Dense Embeddings + Sparse BM25 + Tiers) |
|  - EligibilityEngine & RuleEvaluator (Zero LLM, Pure AST)   |
|  - GroundedExplanationGenerator (Citation Verification)      |
|  - ApplicationPipeline (Authoritative 21-step Coordinator)  |
|  - LLMRouter (Gemini Primary -> OpenRouter Fallback)         |
+-------------------------------------------------------------+
```

---

## 3. Core Architectural Invariants

1. **Direct Pipeline Invocation**:
   `/v1/applications/analyze` calls the authoritative `ApplicationPipeline.process_application()` directly. The API layer only validates/transforms incoming HTTP requests and serializes results.

2. **100% Deterministic Statutory Eligibility**:
   `/v1/eligibility/check` runs strictly through `RuleEvaluator` and `EligibilityEngine`. Zero Gemini or OpenRouter calls are permitted when determining `PASS`, `FAIL`, `UNKNOWN`, or `REVIEW`.

3. **Strict Grounding in Chat**:
   `/v1/chat` queries the verified RAG policy repository (`HybridRetriever`) and cites chunk provenance. It cannot act as an ungrounded, hallucinating chatbot.

4. **Dev-Friendly Rate Limiting**:
   Rate limiting defaults to disabled in development mode (`AI_RATE_LIMIT_ENABLED=false`) and is configurable via environment variables without requiring external cache infrastructure (e.g. Redis).

5. **Zero Secret Leakage**:
   API keys and tokens are never reflected in headers, log messages, exception payloads, or trace diagnostics.
