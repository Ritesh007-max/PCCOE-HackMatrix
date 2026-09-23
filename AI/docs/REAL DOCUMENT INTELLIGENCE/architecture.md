# PolicySetu Phase 8 Architecture — Document-to-Decision Pipeline

## 1. Overview & Core Philosophy

Phase 8 implements the complete AI-side document intelligence and decision pipeline for PolicySetu.
The system is built on a non-negotiable operational principle:

```
DOCUMENTS
    ↓
PARSING / OCR (5-Stage Layered Ingestion)
    ↓
LLM DOCUMENT UNDERSTANDING (Gemini Primary → OpenRouter Fallback)
    ↓
APPLICANT FACT CANDIDATES (Raw Values Only)
    ↓
CANONICAL MAPPING & NORMALIZATION (Phase 4 Deterministic Engine)
    ↓
EVIDENCE AGGREGATION & CONFLICT RESOLUTION
    ↓
APPLICANT PROFILE
    ↓
CITIZEN QUERY UNDERSTANDING (Search Hints Isolated from Facts)
    ↓
HYBRID RAG (Dense Embeddings + BM25 Lexical + Metadata Filters)
    ↓
CROSS-ENCODER RERANKING & POLICY EVIDENCE ASSEMBLY
    ↓
DETERMINISTIC ELIGIBILITY EVALUATION (Phase 3 AST Rule Engine)
    ↓
DETERMINISTIC BENEFIT CALCULATION (Pre-Compiled Structured Rules Only)
    ↓
MISSING INFORMATION IDENTIFICATION (AST Minimal Set Analyzer)
    ↓
GROUNDED EXPLANATION GENERATION (Citations to Policy Chunks)
    ↓
GROUNDING VERIFICATION & DECISION IMMUTABILITY GUARD
    ↓
FINAL APPLICATION RESPONSE & TELEMETRY AUDIT
```

## 2. Invariant Contracts

1. **LLM Never Evaluates Statutory Eligibility**: The deterministic Phase 3 `RuleEvaluator` is the sole authority for PASS / FAIL / UNKNOWN / REVIEW outcomes. The LLM cannot override, contradict, or alter this decision.
2. **Deterministic Benefit Calculations**: Benefits are calculated strictly from pre-compiled structured rules or validated metadata. The LLM NEVER synthesizes mathematical formulas from narrative policy text.
3. **Document Type Coercion Prohibited**: Documents not matching known statutory certificates are classified as `UNKNOWN_DOCUMENT` and safely processed without forced coercion into statutory categories.
4. **Search Hints ≠ Applicant Facts**: Entities extracted from citizen queries (e.g., "scholarships for SC students in Gujarat") are strictly search hints (`is_search_hint_only=True`) and never written to the applicant's profile.
5. **Strict Auth Error Isolation**: Provider fallback triggers ONLY on transient operational failures (429, 5xx, timeouts, network outages). Authentication errors (401, 403, invalid/missing keys) strictly raise `ProviderAuthenticationError` and NEVER fall back.

## 3. The Authoritative 21-Step Pipeline

| Step # | Pipeline Stage | Technical Component | Architectural Invariant |
|---|---|---|---|
| 1 | Document Upload & Path Verification | `ApplicationPipeline` | Verifies existence, bounds, and accessible bytes. |
| 2 | Security Validation & Magic Byte Checks | `DocumentValidator` | Magic byte checks, file size < 25MB, image bombs < 100M pixels. |
| 3 | Duplicate Document Detection | `DocumentValidator` | SHA-256 session deduplication. |
| 4 | Scan / Raster Detection | `ScanDetector` | Classifies pages as `NATIVE_TEXT`, `SCANNED`, `HYBRID`, or `EMPTY`. |
| 5 | Layered Text & OCR Extraction | `LayeredPDFParser`, `DocxParser`, `ImageParser` | 5-stage layered extraction preserving separate streams. |
| 6 | Document Type Classification | `DocumentTypeDetector` | Detects statutory type or safely assigns `UNKNOWN_DOCUMENT`. |
| 7 | Prompt Injection Defense | `PromptInjectionDetector` | Non-destructive scanning for adversarial override phrases. |
| 8 | Document Understanding & Candidate Extraction | `ApplicantFactExtractor` | Extracts candidate facts with raw values only. |
| 9 | Canonical Field Mapping & Normalization | `normalize_field_value` (Phase 4) | Normalization 100% owned by Phase 4 deterministic engine. |
| 10 | Multi-Document Conflict Detection | `EvidenceRegistry` | Identifies contradictory facts across documents. |
| 11 | Evidence Registration & Profile Assembly | `EvidenceRegistry.to_applicant_profile` | Builds clean `ApplicantProfile` with explicit conflict tracking. |
| 12 | Query Understanding & Intent Parsing | `LLMClient` + `QueryIntent` | Extracts query intent, policy domains, and search keywords. |
| 13 | Query Hint Isolation | `QueryIntent` | Enforces search hint isolation from applicant profile. |
| 14 | Hybrid Scheme Retrieval | `HybridRetriever` | Dense embeddings + BM25 sparse lexical matching. |
| 15 | Cross-Encoder Reranking & Context Assembling | `MetadataAwareReranker` | Assembles authoritative policy evidence chunks. |
| 16 | Deterministic Eligibility Evaluation | `RuleEvaluator` (Phase 3) | Evaluates AST condition tree: PASS / FAIL / UNKNOWN / REVIEW. |
| 17 | Deterministic Benefit Calculation | `BenefitCalculator` | Computes benefits using pre-compiled structured rules only. |
| 18 | Missing Information Identification | `RuleASTMissingFieldAnalyzer` | Computes minimal unresolved field set and required documents. |
| 19 | Grounded Explanation Generation | `GroundedExplanationGenerator` | Generates transparent explanation respecting decision immutability. |
| 20 | Grounding Verification & Hallucination Guard | `GroundingVerifier` | Audits factual claims and citations against retrieved policy evidence. |
| 21 | Final Application Response Assembly | `ApplicationResult` | Aggregates all artifacts and emits end-to-end telemetry. |
