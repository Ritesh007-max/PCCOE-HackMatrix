# Phase 11: Policy Versioning & Historical Traceability

## 1. Version Binding

Every `ApplicationGuidancePackage` binds two distinct version identifiers:
- `policy_snapshot_version`: The underlying Phase 7 dataset/snapshot hash (e.g., `snapshot_20260921_193823`).
- `rule_version`: The specific semantic version of the deterministic SchemeRuleSet (e.g., `1.0.0` or `2.0.0`).

---

## 2. Immutability & Re-evaluation

- When a caseworker or citizen views historical guidance, it reflects the exact policy rules in force at the time of evaluation.
- When Phase 12 activates a new policy snapshot or updates rules, previous guidance packages remain immutable in audit logs, while new requests recompute fresh guidance under the updated version.
