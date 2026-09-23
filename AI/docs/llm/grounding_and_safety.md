# PolicySetu Phase 6: Grounding, Safety & Decision Immutability

## 1. Structural Decision Immutability

> [!IMPORTANT]
> **THE LLM MUST NEVER MAKE OR OVERRIDE STATUTORY ELIGIBILITY DECISIONS.**
>
> Eligibility decisions are produced exclusively by the **Phase 3 Deterministic Rule Engine**:
> `PASS`, `FAIL`, `UNKNOWN`, `REVIEW`.
>
> The LLM provides natural-language explanations *around* the authoritative decision.

### Rejection on Contradiction (No Prose Sanitization)
- If the Phase 3 status is `FAIL`, `UNKNOWN`, or `REVIEW`, and the LLM explanation prose states that the citizen is eligible (e.g. *"you are eligible"*, *"you qualify"*, *"aap eligible ho"*):
  1. The generated explanation is **rejected**.
  2. The system falls back to an auditable, deterministic template referencing the exact failed rules, missing fields, or conflicting documents.
  3. The system **never** silently rewrites or mutates words behind the scenes. This guarantees complete auditability.

---

## 2. Two-Tier Grounding Verification

Grounding verification operates in two distinct tiers:

### Tier 1: Structural Citation Validation
- Checks that every `chunk_id` cited in a claim actually exists in the retrieved Phase 5 candidate pool.
- Validates that cited `source_urls` match official policy documentation.
- If a chunk ID is fabricated or not in the retrieved set, the claim is marked `UNVERIFIED_CITATION` and stripped from final citations.

### Tier 2: Lexical Claim Support Analysis
- Computes token overlap and keyword alignment between the claim text and the cited chunk's verbatim content:
  - $\ge 30\%$ token overlap: `SUPPORTED`
  - $15\% - 30\%$ overlap: `PARTIALLY_SUPPORTED`
  - $< 15\%$ overlap: `UNSUPPORTED`

### Explicit Limitations & Disclaimers
- Grounding verification in Phase 6 is **lexical and citation-based**.
- It does **not** claim perfect semantic truth verification or hallucination-free behavior.
- Claims flagged as `UNSUPPORTED` or `UNVERIFIED_CITATION` are safely isolated and excluded from official citations.

---

## 3. Non-Destructive Prompt Injection Defense

1. **Threat Scanning**: `PromptInjectionDetector` scans inputs for known instruction override signatures (e.g., *"ignore previous instructions"*, *"override system"*, *"bypass rules"*).
2. **Non-Destructive Metadata Recording**:
   - The original raw text is **never modified, truncated, or rewritten**.
   - Preserves 100% of the verbatim text for security audits and dispute resolution.
   - Sets `is_injection_risk = True` and records `detected_threats = [...]`.
3. **Isolation**: When passed to an LLM, the raw text is wrapped inside `<UNTRUSTED_USER_INPUT>` tags with escaping of closing tag sequences.
