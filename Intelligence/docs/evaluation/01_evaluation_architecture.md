# Evaluation Architecture & 10-Layer Pyramid

## 1. Structured Evaluation Pyramid
FIN utilizes a 10-layer evaluation pyramid that tests each operational boundary of the AI system from low-level data integrity up to end-to-end statutory workflows:

```
                  ┌─────────────────────────────────────────┐
                  │ Layer 10: End-to-End Application Scenarios│
                  ├─────────────────────────────────────────┤
                  │ Layer 9: Dynamic Policy Resilience      │
                  ├─────────────────────────────────────────┤
                  │ Layer 8: Security & Red Team Attacks    │
                  ├─────────────────────────────────────────┤
                  │ Layer 7: API Hardening & Resource Abuse │
                  ├─────────────────────────────────────────┤
                  │ Layer 6: Guidance & Application Steps   │
                  ├─────────────────────────────────────────┤
                  │ Layer 5: Evidence Grounding Fidelity    │
                  ├─────────────────────────────────────────┤
                  │ Layer 4: Rule Evaluation Correctness    │
                  ├─────────────────────────────────────────┤
                  │ Layer 3: Fact Extraction Quality        │
                  ├─────────────────────────────────────────┤
                  │ Layer 2: Hybrid Retrieval Quality       │
                  ├─────────────────────────────────────────┤
                  │ Layer 1: Canonical Data Integrity       │
                  └─────────────────────────────────────────┘
```

### Layer Details:
- **Layer 1 (Data Quality)**: Parquet schema conformance, canonical schema invariants, zero duplicate slugs or IDs.
- **Layer 2 (Retrieval Quality)**: Hit@1, Hit@3, Hit@5, MRR across exact, paraphrased, typo, abbreviation, and multilingual queries.
- **Layer 3 (Fact Extraction)**: Precision, recall, and F1 across Aadhaar, Income, Domicile, Caste, and Vending certificates.
- **Layer 4 (Rule Correctness)**: Deterministic 4-state outcomes (`PASS`, `FAIL`, `UNKNOWN`, `REVIEW`), boundary checks, compound logic.
- **Layer 5 (Evidence Grounding)**: Claim verification (`SUPPORTED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`, `CONTRADICTED`), official domain whitelist validation.
- **Layer 6 (Guidance Correctness)**: Actionable preparation steps, official office references, zero fabricated requirements.
- **Layer 7 (API Hardening)**: Auth token validation (401), malformed payload handling (422), path traversal rejection (400), rate abuse.
- **Layer 8 (Security Red Team)**: 15 Prompt Injection categories (A–O), policy poisoning gate defenses, Hugging Face boundary isolation.
- **Layer 9 (Dynamic Policy Resilience)**: Snapshot version pinning, rollback safety, zero drift across policy revisions.
- **Layer 10 (End-to-End Workflows)**: Comprehensive integration scenarios (A through J).

## 2. Common Evaluation Data Models (`src/evaluation/models.py`)
- `EvaluationCase`: Captures input payload, expected status, expected scheme ID, language, severity, and tags.
- `EvaluationResult`: Captures pass/fail outcome, actual vs expected outputs, latency in ms, failure classification, and severity.
- `EvaluationRun`: Captures run timestamp, suite name, total/passed/failed counts, aggregated metrics, policy snapshot version, rule version, RAG version, and report paths.
