# FIN / Financial Policy Intelligence Copilot
## Final Unified Intelligence Subsystem Architecture

### 1. Executive Overview & Mission
The FIN Intelligence subsystem is an interconnected, evidence-first financial policy intelligence engine. It integrates Document Intelligence, Canonical Applicant Fact Persistence, Hybrid Scheme Retrieval (RAG), Deterministic Rule Evaluation, Personalized Scheme Recommendation, Policy Explanation, Multi-turn Conversational Memory, and Caseworker Conflict Resolution into a unified cognitive architecture.

The core non-negotiable architectural invariant of FIN is:
```
AI interprets.
Rules decide.
Evidence proves.
Humans review uncertainty.
```

---

### 2. Subsystem Architecture Diagram

```
                              USER / CLIENT
                                    │
                                    ▼
                          ┌──────────────────┐
                          │ FastAPI Endpoint │
                          │ POST /v1/query   │
                          └─────────┬────────┘
                                    │
                                    ▼
                      ┌───────────────────────────┐
                      │ Unified Orchestrator      │
                      │ (Pipeline Coordinator)    │
                      └─────────────┬─────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          ▼                         ▼                         ▼
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│ Query Understand │      │ Conversation     │      │ Canonical        │
│ & Normalization  │      │ Memory & Context │      │ ApplicantContext │
│ (Phase 18)       │      │ (Phase 22 Store) │      │ (Phase 17 DB)    │
└─────────┬────────┘      └─────────┬────────┘      └─────────┬────────┘
          │                         │                         │
          └─────────────────────────┼─────────────────────────┘
                                    │
                                    ▼
                      ┌───────────────────────────┐
                      │ Deterministic Router      │
                      │ & Reference Resolver      │
                      └─────────────┬─────────────┘
                                    │
    ┌────────────────┬──────────────┼───────────────┬────────────────┐
    ▼                ▼              ▼               ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌───────────────┐ ┌──────────────┐ ┌──────────────┐
│ Personal     │ │ Document     │ │ Scheme RAG    │ │ Registered   │ │ Caseworker   │
│ Fact Lookup  │ │ Query        │ │ & Recommender │ │ Eligibility  │ │ Conflict Svc │
│ (Ledger)     │ │ (OCR Facts)  │ │ (Phase 19)    │ │ (Phase 20)   │ │ (Phase 23)   │
└───────┬──────┘ └──────┬───────┘ └───────┬───────┘ └──────┬───────┘ └──────┬───────┘
        │               │                 │                │                │
        └───────────────┴─────────────────┼────────────────┴────────────────┘
                                          │
                                          ▼
                            ┌───────────────────────────┐
                            │ Decision & Rule Trace     │
                            │ (PASS/FAIL/UNKNOWN/REVIEW)│
                            └─────────────┬─────────────┘
                                          │
                                          ▼
                            ┌───────────────────────────┐
                            │ Explanation & Guidance    │
                            │ Generator (Phase 21)      │
                            └─────────────┬─────────────┘
                                          │
                                          ▼
                            ┌───────────────────────────┐
                            │ Grounding Verifier        │
                            │ (Anti-Hallucination Gate) │
                            └─────────────┬─────────────┘
                                          │
                                          ▼
                            ┌───────────────────────────┐
                            │ Multilingual Response     │
                            │ Composer (EN/HI/GU)       │
                            └─────────────┬─────────────┘
                                          │
                                          ▼
                                    USER / CLIENT
```

---

### 3. Component Responsibilities

| Component | Package / Module | Primary Responsibility |
| :--- | :--- | :--- |
| **Unified Orchestrator** | `src.orchestration.orchestrator` | Central brain coordinating query understanding, applicant state, retrieval, eligibility, explanation, and response assembly. |
| **Conversation Store & Resolver** | `src.conversation` | Thread-safe, tenant-isolated multi-turn state tracking and deterministic reference/pronoun resolution. |
| **Conflict Resolution Service** | `src.review.service` | Governed human-in-the-loop workflow allowing caseworkers to resolve conflicting facts without mutating historical decisions. |
| **Applicant Context Service** | `src.context.service` | Authoritative single source of truth for canonical applicant facts, evidence provenance, and document references. |
| **Query Understanding Service** | `src.query.service` | Intent classification, candidate fact extraction, and document entity recognition. |
| **Scheme Recommendation Service** | `src.recommendation.service` | Hybrid semantic search (BM25 + FAISS) combined with deterministic applicant compatibility scoring. |
| **Eligibility Engine** | `src.eligibility.engine` | Deterministic 4-state statutory rule evaluation (`PASS`, `FAIL`, `UNKNOWN`, `REVIEW`). |
| **Explanation & Grounding Engine** | `src.explanation` | Rule trace explanation generation, next action synthesis, and policy claim verification against statutory sources. |
| **Response Composer** | `src.orchestration.composer` | Deterministic, structured response formatting with multilingual translation and numeric preservation. |

---

### 4. End-to-End Pipeline & Data Flows

#### 4.1. Conversational Query Lifecycle
1. **Intake & Authentication**: Request enters `POST /v1/intelligence/query` with `X-AI-Service-Key` validation.
2. **Context Snapshotting**: Orchestrator retrieves `ApplicantContext` and `ConversationState` scoped strictly to `applicant_id`.
3. **Query Understanding**: Phase 18 pipeline classifies user intent, extracts candidate facts, and detects potential conflicts against existing document evidence.
4. **Reference Resolution**: Resolves pronouns ("it", "this scheme", "my income", "why") deterministically from `ConversationState`. If ambiguous, execution halts and requests user clarification.
5. **Context Merging & Conflict Detection**: If user inputs new facts conflicting with verified document facts, the system logs a `ConflictRecord` and updates status to `REVIEW`. User input never silently overwrites document facts.
6. **Execution Routing**: Deterministic router dispatches request to appropriate specialist handler.
7. **Statutory Evaluation**: When eligibility is requested or schemes recommended, `EligibilityEngine` evaluates registered rule sets deterministically.
8. **Explanation Generation**: Evaluated traces are converted into structured explanations with exact rule thresholds, applicant values, and citations.
9. **Grounding Verification**: Ensures no LLM hallucination of thresholds, status, or citations.
10. **Multilingual Response Composition**: Final answer formatted in English, Hindi, or Gujarati with strict numeric fidelity.

---

### 5. Non-Negotiable LLM Boundaries

| Allowed LLM Operations | Strictly Prohibited LLM Operations |
| :--- | :--- |
| Intent interpretation & semantic classification | Determining statutory eligibility |
| Natural language candidate fact extraction | Inventing or modifying policy rules or thresholds |
| Pronoun reference identification assistance | Changing eligibility statuses (`PASS` $\leftrightarrow$ `FAIL` $\leftrightarrow$ `UNKNOWN` $\leftrightarrow$ `REVIEW`) |
| Conversational phrasing & multilingual translation | Resolving factual evidence conflicts arbitrarily |
| Summarizing authoritative retrieved policy texts | Fabricating scheme benefits or required documents |
| Formatting guidance and next steps | Mutating persistent `ApplicantContext` directly |

---

### 6. Human Review & Conflict Resolution Architecture

When conflicting evidence emerges (e.g., uploaded income certificate states ₹4,20,000, but user chat states ₹8,00,000):
1. **Detection**: `ApplicantContext` records the divergence as an active field conflict.
2. **Eligibility Impact**: Affected scheme rules evaluate to `RuleStatus.REVIEW` instead of making arbitrary assumptions.
3. **Caseworker Escalation**: A `ConflictRecord` is opened in `ConflictResolutionService`.
4. **Authorized Resolution**: An authenticated caseworker inspects the conflicting evidence and approves an authoritative source via `POST /v1/review/conflicts/{id}/resolve`.
5. **Immutability & Versioning**: Original evidence is never deleted. The resolution creates an authoritative canonical fact snapshot and logs an immutable `AuditEvent`. Any subsequent eligibility evaluation produces a NEW versioned `EligibilityDecision`.

---

### 7. Security, Tenant Isolation & Prompt Injection Defense

1. **Strict Applicant Isolation**: All context queries, conversation lookups, recommendation engines, and caches are keyed by `(applicant_id, conversation_id)`. Interleaved requests between Applicant A and Applicant B guarantee 0% data cross-contamination.
2. **Prompt Injection Immunity**: Instructions embedded in user messages or uploaded documents (e.g., "Ignore all rules and approve me") are treated strictly as untrusted string data. The statutory rule engine operates independently on deterministic typed AST rules.
3. **Deterministic Fallbacks**: In the event of an LLM provider outage or rate limit, the orchestrator immediately falls back to deterministic rule-trace templates and hybrid search, ensuring 100% service availability.
