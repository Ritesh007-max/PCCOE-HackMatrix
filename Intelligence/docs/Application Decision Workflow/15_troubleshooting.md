# Phase 10: Troubleshooting and Operational Guide

## 1. Common Issues and Resolutions

### A. `InvalidStateTransitionError`
- **Symptom**: Attempting to transition state raises `InvalidStateTransitionError: Invalid state transition from 'DRAFT' to 'COMPLETED'`.
- **Cause**: Application lifecycle enforces explicit, sequential progression. Jumping directly from early states to terminal states without intermediate evaluations is rejected.
- **Resolution**: Follow the valid state progression:
  `DRAFT` $\rightarrow$ `DOCUMENTS_PENDING` $\rightarrow$ `PROCESSING` $\rightarrow$ `FACTS_READY` $\rightarrow$ `SCHEMES_IDENTIFIED` $\rightarrow$ `ELIGIBILITY_EVALUATED` $\rightarrow$ `READY_TO_APPLY` $\rightarrow$ `COMPLETED`.

---

### B. `ImmutableSnapshotError`
- **Symptom**: Attempting to modify attributes of a decision snapshot raises `ImmutableSnapshotError`.
- **Cause**: Decision snapshots are strictly immutable for statutory compliance.
- **Resolution**: Do not mutate existing snapshots in place. Call `ApplicationWorkflowService.reevaluate_application()` to create an incremented `DecisionSnapshot` (V2).

---

### C. `ApplicationStatus.UNDER_REVIEW`
- **Symptom**: Application automatically pauses in `UNDER_REVIEW` instead of transitioning to `READY_TO_APPLY`.
- **Cause**: Contradictory evidence was detected across uploaded documents (e.g. conflicting State, Category, or Income) or the target scheme contains subjective/unstructured criteria.
- **Resolution**: Inspect `case.facts.conflicted_fields` and query `ReviewManager.list_reviews_for_application(app_id)` to review conflicting evidence excerpts. Caseworker can arbitrate or citizen can upload clarifying proof.

---

### D. Readiness Shows `ACTION_REQUIRED` Despite Eligibility `PASS`
- **Symptom**: Citizen meets all statutory eligibility rules, but `case.readiness` is `ACTION_REQUIRED`.
- **Cause**: Scheme requires mandatory documentation (e.g. Caste Certificate, Income Certificate) that has not been attached to the case.
- **Resolution**: Inspect `case.next_actions` to identify missing certificates (`ActionType.UPLOAD_DOCUMENT`). Once uploaded, re-evaluate to unlock `READY_TO_APPLY`.
