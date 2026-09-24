# FIN LLM Provider Security & Prompt Boundary Hardening

## 1. Provider Routing Topology
FIN utilizes a primary-fallback architecture:
$$\text{Gemini 2.5 Flash (Primary)} \longrightarrow \text{OpenRouter / Gemini Fallback}$$

### 1.1 Strict Fallback Rules
1. **Operational Failures Only**: Fallback to OpenRouter is permitted only for transient network errors, HTTP 429 rate limits, HTTP 500/502/503/504 server errors, and provider timeouts.
2. **Authentication / Configuration Failures Must NOT Fallback**: HTTP 401, 403, invalid API keys, or missing credentials strictly abort execution without fallback to avoid burning backup credits or concealing security misconfigurations.
3. **Deterministic Statutory Decisions Must NEVER Fallback**: If an applicant is determined `FAIL`, `UNKNOWN`, or `REVIEW` by Phase 3 rules, the LLM cannot retry or override the statutory outcome.
4. **Prohibition of Mock Provider in Production**: In production mode (`AI_ENV=production`), `MockLLMProvider` is strictly disabled. The system fails closed rather than returning simulated responses.

---

## 2. Prompt Injection & Trust Boundary Isolation

### 2.1 Untrusted Text as Passive Data
All external text (citizen messages, OCR output, policy documents, FAQ content, Hugging Face datasets, retrieved chunks) is classified strictly as **DATA**, never as instructions.

### 2.2 Semantic Trust Labels
When assembling LLM prompts, input text is isolated within semantic XML boundary tags:
- `<USER_DATA>`: Raw citizen prompts.
- `<DOCUMENT_DATA>`: Text extracted from uploaded citizen files.
- `<PRIMARY_POLICY_DATA>`: Official government scheme guidelines.
- `<SUPPLEMENTARY_DATA>`: Secondary dataset annotations (Hugging Face).
- `<SYSTEM_INSTRUCTION>`: Immutable system instructions and role boundaries.

### 2.3 Tag Escaping Neutralization
The `wrap_with_trust_label()` helper sanitizes closing tags inside user data (e.g. `</USER_DATA>` becomes `<\/USER_DATA>`) to prevent prompt boundary breakouts.

### 2.4 Programmatic Invariant Enforcer (`DecisionImmutabilityGuard`)
Even if prompt injection occurs:
- The LLM lacks the authority to change policy version, alter eligibility rules, or modify applicant decisions.
- If generated explanation prose contradicts the authoritative Phase 3 rule status, the explanation is rejected and replaced with a deterministic fallback template.
