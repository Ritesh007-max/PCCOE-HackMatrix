# Phase 10: Immutable Decision Snapshots

## 1. Statutory Immutability Requirement

Government policy decisions carry legal and administrative weight. When an eligibility determination is rendered, the exact context that produced that decision must remain reproducible and auditable indefinitely.

> **Statutory Invariant:**
> $$\text{Policy Source Version} + \text{Rule AST Version} + \text{Applicant Facts} = \text{Reproducible Decision Context}$$

Once a decision is rendered:
1. Historical decision snapshots must **never be modified in place**.
2. New information or updated policy creates a **new snapshot version** (`version_index: 2`).
3. Historical snapshots remain permanently accessible for compliance, grievance redressal, and administrative audit.

---

## 2. Decision Snapshot Schema

```python
class DecisionSnapshot:
    snapshot_id: str                      # Unique UUID4 identifier (e.g. snap_abc123)
    application_id: str                   # Parent application case ID
    scheme_id: str                        # Evaluated statutory scheme ID
    scheme_name: str                      # Official scheme title
    applicant_fact_snapshot: Dict[str, Any] # Exact applicant facts at decision time
    policy_snapshot_version: str          # Attached policy version (e.g. snapshot_20260921_193823)
    rule_version: str                     # Rule AST version (e.g. 1.0.0)
    decision_status: StatutoryDecision    # PASS, FAIL, UNKNOWN, REVIEW
    is_eligible: bool                     # True only for PASS
    matched_rules: List[Dict[str, Any]]   # Verbatim passed statutory criteria
    failed_rules: List[Dict[str, Any]]    # Verbatim failed statutory criteria
    unknown_rules: List[Dict[str, Any]]   # Criteria missing data
    review_fields: List[str]              # Fields requiring human caseworker verification
    benefit_result: Optional[Dict[str, Any]] # Quantitative computed benefit
    evidence_references: Dict[str, List[str]] # Provenance citations to documents
    timestamp: str                        # UTC ISO 8601 creation timestamp
    version_index: int                    # Version number (1, 2, 3...)
    reason_for_evaluation: str            # Trigger (e.g. INITIAL_EVALUATION, NEW_DOCUMENT, POLICY_UPDATE)
```

---

## 3. Enforcement of Immutability

In `src/application/decision.py`, immutability is strictly enforced at runtime by intercepting attribute modifications:

```python
def __setattr__(self, name: str, value: Any) -> None:
    if getattr(self, "_initialized", False):
        raise ImmutableSnapshotError(
            snapshot_id=getattr(self, "snapshot_id", "unknown"),
            field_name=name,
        )
    super().__setattr__(name, value)
```

Attempting to update any field on a persisted snapshot raises `ImmutableSnapshotError`.
Furthermore, `ApplicationRepository.save_decision_snapshot()` verifies that a snapshot ID has not already been written, preventing accidental or malicious overwrite.
