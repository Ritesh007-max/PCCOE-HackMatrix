# Phase 11: Statutory Deadline Handling

## 1. Principle

Deadlines are statutory boundaries with legal implications. Phase 11 strictly avoids fabricating dates or assuming deadline rollover.

---

## 2. Deadline States

1. **`KNOWN`**:
   - Dates are explicitly present in active policy metadata or verified gazette notices.
   - Outputs: `open_date`, `close_date`, `deadline_date`.
2. **`UNKNOWN`**:
   - Application window details are mentioned but dates are unparsed or pending official announcement.
3. **`NOT_APPLICABLE`**:
   - Rolling or perpetual open-ended scheme (e.g. continuous welfare entitlements).

---

## 3. Stale Snapshot Detection

When a deadline date in the active snapshot precedes the current operational date, FIN surfaces a warning:
```json
{
  "code": "DEADLINE_EXPIRED_OR_STALE",
  "severity": "HIGH",
  "message": "The statutory application window closed on 2025-08-31 according to snapshot snapshot_20260921_193823. Verify with official portal before applying."
}
```
