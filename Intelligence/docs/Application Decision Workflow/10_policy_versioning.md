# Phase 10: Policy Versioning and Temporal Lineage

## 1. Statutory Policy Version Attachment

Government welfare schemes change over time (e.g. annual budget revisions changing income ceilings from ₹2,00,000 to ₹2,50,000, or expanding age brackets).

A citizen's application evaluated under **Policy Version 2026-09** must remain traceable to the exact rules that were legally active on that date. Future Phase 12 dynamic updates must **never retroactively invalidate or rewrite past statutory determinations**.

---

## 2. Integration with Phase 7 Knowledge Base Snapshots

Phase 7 establishes immutable data sync snapshots under `Intelligence/data/snapshots/` with atomic pointer management in `active_version.json`:

```json
{
  "active_snapshot": "snapshot_20260921_193823",
  "previous_snapshot": "snapshot_20260921_193719",
  "activated_at": "2026-09-21T19:38:24.793106+00:00",
  "status": "ACTIVE"
}
```

In Phase 10:
1. `ApplicationWorkflowService.get_active_policy_version()` resolves the active snapshot ID.
2. Every `DecisionSnapshot` permanently records `policy_snapshot_version` (e.g. `"snapshot_20260921_193823"`).
3. If Phase 12 activates a new snapshot (`"snapshot_20261101_180000"`), existing decision snapshots retain their historical binding.
4. Subsequent re-evaluations explicitly record the new snapshot version in V2 while leaving V1 bound to the previous version.
