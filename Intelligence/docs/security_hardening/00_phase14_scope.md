# FIN Phase 14 — Security & Production Hardening Scope

## 1. Executive Summary

Phase 14 transitions FIN from a verified functional research prototype into a hardened, production-ready, privacy-preserving AI microservice.

### Core Architecture Principle
```
AI interprets → Rules decide → Evidence proves → Human reviews uncertainty
```

Phase 14 strictly preserves this invariant. The LLM remains an untrusted natural language parser and explainer; statutory eligibility logic, source authority hierarchies, and state-mutating snapshot activations remain 100% deterministic.

---

## 2. Strict Scope Boundaries

1. **Isolation:** All work is strictly confined to `Intelligence/`.
2. **Untouched Systems:** `BackEnd/` and `FrontEnd/` are untouched (0 bytes modified).
3. **Repository Boundaries:** The root `README.md` is untouched; no Git push operations are executed.
4. **Preservation:** All Phase 1–13 behaviors, evaluation cases, red-team guardrails, and the 5,110 live-acquired scheme corpus are preserved.
5. **No Speculative Infrastructure:** No external distributed message queues, microservice meshes, or distributed databases (Redis, Kafka, Vault) are introduced; lightweight, testable in-process abstractions are favored.
6. **Privacy Guarantee:** Zero real citizen PII, production secrets, or uploaded confidential documents are placed in tests, fixtures, logs, or commit histories.

---

## 3. High-Level Workstreams

1. **Security Baseline & Threat Modeling:** Detailed audit of trust boundaries and attack surfaces.
2. **Centralized Security Configuration:** Environment-aware (`DEVELOPMENT`, `TEST`, `PRODUCTION`) configuration with fail-closed production semantics.
3. **Secret Redaction & Management:** Zero secret reflection in logs, exceptions, API errors, or reports.
4. **Authentication & Authorization:** Constant-time service key verification, public vs. protected route separation, and lightweight role-based access control (`CITIZEN`, `SERVICE`, `ADMIN`, `REVIEWER`).
5. **API & File Security:** Strict payload validation, magic-byte document inspection, decompression bomb defense, and path traversal rejection.
6. **Network & SSRF Hardening:** Private IP blocking, cloud metadata defense, timeout enforcement, and redirect validation.
7. **Prompt Injection & LLM Safety:** XML trust boundaries, non-destructive threat flagging, and decision immutability guards.
8. **Operational Reliability:** Rate limiting (public, protected, expensive), bounded resource concurrency, security headers, and structured privacy-aware logging.
9. **Snapshot & Rollback Integrity:** Atomic file writes, checksum verification, and candidate isolation.
10. **Comprehensive Verification:** 14 dedicated security test suites, 25 red-team attack classes, full 423-test regression, and static type analysis with pyright.
