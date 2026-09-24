# FIN Multi-Document Conflict Detection & Resolution

## 1. Multi-Document Verification Hierarchy

When multiple documents are submitted by a citizen, the `EvidenceRegistry` aggregates facts per canonical profile field and detects corroboration or contradictions:

```
Tier 4: ISSUER_VERIFIED  (e.g., Digilocker, official issuer API)
Tier 3: USER_CONFIRMED   (Applicant explicitly confirmed pre-filled data)
Tier 2: EXTRACTED        (Parsed from statutory certificate document)
Tier 1: SELF_REPORTED    (Typed into chat or application text box)
Tier 0: UNKNOWN          (Unverified or absent)
```

## 2. Conflict Detection Protocol

A conflict is identified when two or more pieces of evidence for the same canonical field provide non-equivalent normalized values (e.g., Aadhaar states Age 25, while PAN states Age 28).

When a conflict is detected:
1. The field is added to `conflicted_fields`.
2. The field's status becomes `FactVerificationStatus.CONFLICTED`.
3. The conflict is recorded with full provenance in the evidence ledger (`conflicting_values`).
4. In `to_applicant_profile()`, the conflicted field is omitted from valid profile attributes and added to `_conflicts`.

## 3. Impact on Eligibility Evaluation

The Phase 3 `RuleEvaluator` inspects `profile.has_conflict(field)`:
- If a rule depends on a conflicted field, the evaluation outcome for that rule is **STRICTLY `REVIEW`**.
- It **CANNOT BE PASS**.
- It **CANNOT BE FAIL** (as the true value has not been deterministically falsified).
- The pipeline flags the conflict to the citizen and manual reviewer, presenting verbatim citations from both conflicting documents.
