# Phase 11: Privacy & Security Protections

## 1. PII Minimization

Phase 11 strictly avoids exposing raw sensitive citizen identifiers:
- **Aadhaar Numbers**: Stored or evaluated only as derived boolean facts (e.g. `has_aadhaar = true`), never echoed into guidance steps or summaries.
- **Bank Account / IFSC**: Represented as derived status (e.g. `has_bank_account = true`).
- **Income Details**: Displayed as aggregate annual figures necessary for statutory justification, never itemized payroll entries.

---

## 2. Prompt Injection & Template Defense

- Guidance generation uses deterministic templates as the primary generator.
- When optional LLM phrasing is enabled, user inputs and extracted strings are passed through the Phase 8 `sanitize_untrusted_text` guard to neutralize prompt injection attacks.
- If generated text contradicts deterministic structured data, the validator rejects the LLM output and falls back to deterministic templates.
