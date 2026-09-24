# Phase 11: Application Guidance Architecture

## 1. Architectural Overview

The **FIN Application Guidance Layer** is a dedicated representation and preparation subsystem situated directly on top of the deterministic **Phase 10 Application Decision Workflow** and **Phase 8 Document Intelligence Pipeline**.

Its core mission answers the citizen's quintessential question:
> *"Now that FIN has analyzed my profile, documents, and statutory eligibility, what exact steps must I take next to apply?"*

```
   +-------------------------------------------------------+
   |                Phase 8 Document Pipeline              |
   |   (OCR, Fact Extraction, Conflict Detection, Hybrid RAG)|
   +---------------------------+---------------------------+
                               |
                               v
   +-------------------------------------------------------+
   |            Phase 10 Application Workflow              |
   | (Eligibility Engine, Benefit Calculator, Readiness)  |
   +---------------------------+---------------------------+
                               |
                               v
   +-------------------------------------------------------+
   |           Phase 11 Guidance & Preparation Layer        |
   |                                                       |
   |  +-------------------------------------------------+  |
   |  |        ApplicationGuidanceGenerator             |  |
   |  |   - EligibilitySummaryBuilder                   |  |
   |  |   - DocumentGuidanceBuilder                     |  |
   |  |   - ApplicationStepBuilder                      |  |
   |  |   - BenefitSummaryBuilder                       |  |
   |  |   - WarningGenerator                            |  |
   |  |   - SourceMetadataResolver                      |  |
   |  |   - GuidanceLocalizer (EN / HI / Hinglish)      |  |
   |  +-----------------------+-------------------------+  |
   |                          |                            |
   |                          v                            |
   |  +-------------------------------------------------+  |
   |  |               GuidanceValidator                 |  |
   |  |     (10-Point Immutable Consistency Check)      |  |
   |  +-----------------------+-------------------------+  |
   |                          |                            |
   |                          v                            |
   |  +-------------------------------------------------+  |
   |  |           ApplicationGuidancePackage            |  |
   |  |       (Frontend-Ready Typed Aggregate)          |  |
   |  +-------------------------------------------------+  |
   +-------------------------------------------------------+
```

---

## 2. Strict Boundary Rules

1. **Non-Negotiable Statutory Invariance**:
   - Guidance **MUST NEVER** alter or soften statutory decisions.
   - If Phase 10 produces `PASS`, Guidance emits `PASS`.
   - If Phase 10 produces `FAIL`, Guidance emits `FAIL` (never softened to "maybe eligible").
   - If Phase 10 produces `UNKNOWN`, Guidance explicitly lists missing facts.
   - If Phase 10 produces `REVIEW`, Guidance highlights contradictory evidence or administrative review requirements.
2. **Zero Hallucination / Grounding Rule**:
   - Official URLs must be validated against authoritative allowlists (`.gov.in`, `.nic.in`, `.ac.in`, `.edu.in`).
   - If an official portal is unknown, it defaults strictly to `null` with warning code `OFFICIAL_LINK_UNAVAILABLE`.
   - Steps must be explicitly classified as either `POLICY_SOURCED` or `GENERAL_PREPARATION`.
3. **No External Side-Effects**:
   - Phase 11 prepares, formats, and guides.
   - It performs zero external form submissions, zero payment gateway interactions, and zero authentication against third-party government servers.
