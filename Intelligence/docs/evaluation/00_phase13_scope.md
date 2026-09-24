# Phase 13 — Evaluation & Red Team Scope Specification

## 1. Executive Mission
Phase 13 establishes the rigorous evaluation, verification, and adversarial red-team testing layer for **FIN — Evidence-First Financial Policy Copilot**.

Phases 1 through 12 implemented the functional components:
- Phase 1: Dataset Discovery & Audit
- Phase 2: Policy Rule Extraction
- Phase 3: Deterministic Eligibility Engine
- Phase 4: Applicant Fact + Evidence Model
- Phase 5: Hybrid RAG
- Phase 6: LLM + NLP
- Phase 7: Dynamic Data Sync & Versioned Knowledge Base
- Phase 8: Document Intelligence
- Phase 9: AI Microservice / API Layer
- Phase 10: Application Decision Workflow
- Phase 11: Application Guidance
- Phase 12: Dynamic Policy Operations

Phase 13 evaluates and adversarially challenges the existing system **without redesigning or rewriting completed phases**.

## 2. Core Architectural Principle
```
AI interprets -> Rules decide -> Evidence proves -> Human reviews uncertainty
```
- **AI interprets**: Transforms unstructured citizen input, OCR text, and vernacular queries into structured candidate attributes.
- **Rules decide**: Deterministic logic engines evaluate statutory criteria using mathematical comparisons; LLMs never decide eligibility.
- **Evidence proves**: Every claim and decision is backed by verbatim text citations, document provenance, and canonical gazette references.
- **Human reviews uncertainty**: Missing facts produce `UNKNOWN`; contradictory evidence produces `REVIEW`. Incomplete data never silently passes.

## 3. Strict Scope Boundaries
1. **Work Exclusively Inside `Intelligence/`**: Zero modifications to `BackEnd/` or `FrontEnd/`.
2. **No Rewrites for Test Convenience**: Completed Phase 1–12 behavior must not be altered simply to force benchmark numbers to pass.
3. **Expose Genuine Defects**: Real failures (e.g. out-of-vocabulary retrieval, ambiguous statutory text) must be surfaced honestly, not concealed.
4. **No Git Push**: Zero pushes to remote repository.
5. **Preserve Invariants**:
   - Invariant 1: Missing information must never evaluate to `PASS`.
   - Invariant 2: Conflicting evidence must trigger `REVIEW`, never silent `PASS` or `FAIL`.
   - Invariant 3: Supplementary sources (e.g. Hugging Face) cannot create statutory rules.
   - Invariant 4: Historical decisions remain strictly immutable.
