# Phase 11: Citizen-Readable Eligibility Explanations

## 1. Core Principle

The Eligibility Explanation component translates deterministic four-state statutory decisions (`PASS`, `FAIL`, `UNKNOWN`, `REVIEW`) into unambiguous natural-language summaries tailored for citizens.

---

## 2. Decision State Mapping

### PASS
- **Citizen Message**: "Your available profile information and verified documents satisfy the evaluated statutory eligibility criteria for `<Scheme Name>`."
- **Criteria Breakdown**: Enumerate all satisfied conditions with concrete evidence citations (e.g., "Annual family income of ₹1,20,000 is within the statutory ceiling of ₹2,50,000").
- **Constraint**: Never overstate qualification beyond what the deterministic rules have evaluated.

### FAIL
- **Citizen Message**: "Based on evaluated statutory criteria for `<Scheme Name>`, you are not eligible because: `<Field Name>` (`<Actual Value>`) violates condition (`<Constraint>`). Government guidelines strictly enforce these mandatory thresholds."
- **Constraint**: **NO SOFTENING**. Never emit phrases like "you may still qualify" or "we recommend applying anyway".

### UNKNOWN
- **Citizen Message**: "Statutory eligibility for `<Scheme Name>` cannot be determined yet because mandatory information is missing: `<Fields>`. Please provide this information to complete your assessment."
- **Constraint**: Never treat an `UNKNOWN` status as permission to proceed to application.

### REVIEW
- **Citizen Message**: "Your application for `<Scheme Name>` requires administrative caseworker review. Contradictory evidence was detected across submitted documents, or the policy contains subjective conditions needing departmental verification."
- **Constraint**: Never auto-resolve conflicting facts (e.g. Gujarat vs Rajasthan). Expose both documents to caseworker review.
