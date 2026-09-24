# Phase 11: Multi-Dimensional Caching Strategy

## 1. Cache Key Composition

The `ApplicationGuidanceService` uses a multi-dimensional tuple key to guarantee instant retrieval without stale reads:

```python
cache_key = (
    case.application_id,       # Unique case identifier
    scheme_id,                 # Target scheme evaluated
    policy_snapshot_version,   # Active dataset snapshot
    rule_version,              # Active ruleset semantic version
    language,                  # Target language ('en', 'hi', 'hinglish')
    facts_repr,                # Serialized string representation of profile facts
    case.updated_at,           # ISO timestamp of latest case state change
)
```

---

## 2. Invalidation Rules

- **Profile Update**: Any change to applicant facts updates `case.updated_at` and alters `facts_repr`, causing an immediate cache miss and recomputation.
- **Document Addition**: Attaching new documents updates `case.updated_at`.
- **Policy Snapshot Update**: Activating a new snapshot in Phase 7/12 immediately invalidates all previous keys by changing `policy_snapshot_version`.
- **Manual Eviction**: `service.invalidate_cache(application_id)` purges cached packages for that specific case.
