# Phase 10: Application Re-evaluation Workflow

## 1. Need for Re-evaluation

An application case evolves through its lifecycle:
- A citizen uploads a revised or newer income certificate.
- A caseworker resolves an evidence contradiction.
- The underlying government scheme eligibility criteria are updated (Phase 12 dynamic updates).

When new facts or policy updates occur, the application must be re-evaluated **without rewriting history**.

---

## 2. Re-evaluation Guarantees

1. **Prior Snapshots are Immutable**: `DecisionSnapshot V1` remains permanently intact in the repository.
2. **New Snapshot Created**: A new snapshot `DecisionSnapshot V2` is appended with:
   - `version_index = 2`
   - Updated policy version attached
   - Updated applicant fact snapshot
   - `reason_for_evaluation: "APPLICANT_INCOME_UPDATE"`
3. **Application Case Pointer Updated**: `case.active_decision_snapshot_id` points to the new snapshot ID.
4. **Readiness and Next Actions Recalculated**: Readiness and actions adapt to the new decision.
5. **Audit Event Appended**: `EventType.APPLICATION_REEVALUATED` is logged in the append-only history.

---

## 3. Workflow Example

```python
# Initial evaluation: income = 150,000 -> PASS (Snapshot V1 created)
service.evaluate_scheme(app_id, "scheme_scholarship")

# Citizen uploads updated certificate: income = 450,000
service.update_applicant_profile(app_id, {"annual_family_income": 450000})

# Trigger re-evaluation
service.reevaluate_application(
    application_id=app_id,
    reason="UPDATED_INCOME_CERTIFICATE",
)

# Repository now contains:
# - Snapshot V1: decision_status = PASS, income = 150,000 (UNTOUCHED)
# - Snapshot V2: decision_status = FAIL, income = 450,000 (ACTIVE)
```
