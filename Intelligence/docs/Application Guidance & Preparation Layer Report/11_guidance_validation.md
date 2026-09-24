# Phase 11: Guidance Validation & Anti-Contradiction Engine

## 1. 10-Point Consistency Invariants

The `GuidanceValidator` runs prior to emitting any `ApplicationGuidancePackage`. If an invariant is violated, the generated package is rejected and rebuilt using deterministic templates.

1. **Eligibility Status Invariance**:
   - `package.eligibility.status` MUST exactly equal `package.statutory_decision`.
2. **Readiness Invariance**:
   - `package.readiness_status` MUST exactly equal `package.readiness["status"]`.
3. **No Softened Disqualification**:
   - If `statutory_decision == "FAIL"`, summary MUST NOT contain phrases like "you are eligible" or "we recommend applying".
4. **Mandatory Missing Documents**:
   - If `readiness_status == "READY_TO_APPLY"`, `documents["missing"]` MUST be empty.
5. **Conflict Consistency**:
   - If `readiness_status == "READY_FOR_REVIEW"`, `information["conflicted"]` or `warnings` MUST contain conflict details.
6. **URL Authority Allowlist**:
   - If `official_portal_url` is provided, its hostname must end in an approved government or academic TLD (`.gov.in`, `.nic.in`, `.ac.in`, `.edu.in`).
7. **Benefit Calculation Consistency**:
   - If `benefit.status == "CALCULATED"`, `amount` MUST NOT be null or negative.
8. **Application Step Grounding**:
   - Every step MUST have an integer `step_number` and valid `source_type`.
9. **Snapshot & Version Tracking**:
   - `policy_snapshot_version` and `rule_version` MUST NOT be empty.
10. **Provenance Citations**:
    - At least one authoritative source citation MUST be present.
