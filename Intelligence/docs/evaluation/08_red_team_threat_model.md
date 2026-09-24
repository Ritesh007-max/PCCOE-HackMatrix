# Red Team Threat Model & Adversarial Taxonomy

## 1. Threat Landscape
FIN operates at the intersection of citizen data processing, generative AI interpretation, and statutory financial governance. The adversarial threat model evaluates four primary attack surfaces:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        THREAT MODEL TAXONOMY                           │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Conversational & Document Prompt Injection (Attacker as Citizen)    │
│    - Goal: Force unauthorized PASS or bypass eligibility constraints.   │
├────────────────────────────────────────────────────────────────────────┤
│ 2. Policy Poisoning & Ingestion Attacks (Attacker as Data Source)      │
│    - Goal: Mutate rules, corrupt thresholds, spoof government domains.  │
├────────────────────────────────────────────────────────────────────────┤
│ 3. Supplementary Source Boundary Breach (Hugging Face / Third-Party)   │
│    - Goal: Inject unverified rules or override statutory gazettes.      │
├────────────────────────────────────────────────────────────────────────┤
│ 4. API & Resource Abuse Attacks (Attacker as Network Client)           │
│    - Goal: State mutation without key, leak API secrets, path traversal │
└────────────────────────────────────────────────────────────────────────┘
```

## 2. Severity Classification Matrix
- **CRITICAL**:
  - Unauthorized `PASS`/`FAIL` outcome.
  - Policy override originating from supplementary source.
  - Historical decision mutation.
  - Secret or PII leakage in API response.
  - Unsafe policy activation bypassing gates.
- **HIGH**:
  - Unsupported statutory claim or fabricated requirement.
  - Source authority confusion.
  - Incorrect rule evaluation or boundary violation.
  - Severe document fact extraction failure.
- **MEDIUM**:
  - Hybrid retrieval ranking failure.
  - Multilingual intent misclassification.
  - Citation text mismatch.
- **LOW**:
  - Formatting irregularity or minor metadata typo.
- **INFO**:
  - Baseline latency observations and informational telemetry.
