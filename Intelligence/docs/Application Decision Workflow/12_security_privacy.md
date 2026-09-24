# Phase 10: Security and Data Privacy

## 1. Zero Direct PII Ingestion

The Application Decision Workflow layer handles highly sensitive documents (e.g. Income Certificates, Caste Certificates, Domicile Certificates). To protect citizen privacy:

1. **No Raw Bytes in Domain Models**: `DocumentReference` stores only metadata (`filename`, `document_type`, `sha256_hash`, `provenance_refs`). Raw binary bytes are never serialized into `ApplicationCase` or logged.
2. **Fact References Over Duplication**: Application snapshots refer to `fact_id`, `document_id`, and `evidence_reference` rather than repeatedly copying sensitive personally identifiable data.
3. **Redaction of Sensitive Identifiers**: Aadhaar numbers, PAN numbers, and bank account numbers are redacted or masked during normalization (Phase 4 / Phase 8), ensuring only derived attributes (e.g. `has_bank_account: True`) reach the rule engine.

---

## 2. Safe Logging and Telemetry

Application logs and event histories strictly adhere to security boundaries:
- **Never Log Secrets**: API keys, bearer tokens, and credentials are redacted by existing middleware.
- **Auditable Request Lineage**: All events record `request_id`, `application_id`, and `actor` for complete traceability.
- **Prompt Injection Neutralization**: Invocations via Phase 8 pass through `PromptInjectionDetector` to prevent prompt hijacking without altering deterministic rule evaluation.
