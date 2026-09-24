# FIN Phase 12: Source Freshness & Temporal Lifecycle

## 1. Freshness States & Semantics

FIN monitors the operational health and sync currency of registered sources using fine-grained freshness states:

| Status | Condition | System Action |
|---|---|---|
| `FRESH` | Last successful sync within expected refresh interval (e.g. < 7 days). | Normal scheduled polling. |
| `AGING` | Sync interval exceeded, but within stale grace period (e.g. 7–30 days). | Warning flag logged; scheduled for priority poll. |
| `STALE` | No successful sync beyond `stale_after_days` (e.g. > 30 days). | Health alert raised; source flagged as potentially dormant. |
| `EXPIRED` | Source endpoint permanently retired, deprecated, or superseded. | Excluded from future sync attempts. |
| `FAILED` | Last fetch attempt encountered network error, HTTP 4xx/5xx, or parse failure. | Retry with backoff; isolated from healthy sources. |
| `UNKNOWN` | Source newly registered; no fetch has occurred yet. | Enqueued for initial verification fetch. |

---

## 2. Invariant: Operational Freshness ≠ Statutory Authority

A critical architectural distinction in FIN is that **freshness is purely an operational metric**:

> **A fresh blog post is still `UNTRUSTED`.**
> **A three-year-old Central Gazette notification remains binding law until explicitly repealed or superseded.**

The system never promotes an unverified source simply because it was fetched 5 minutes ago, nor does it demote official policy text merely because no revisions were issued in 24 months. Authority is permanent; freshness tracks data pipeline health.

---

## 3. Freshness Tracking Metadata

Every registered source maintains:
```json
{
  "source_id": "myscheme_csv_baseline",
  "authority_tier": "PRIMARY_CANONICALIZED",
  "update_frequency_hours": 168,
  "stale_after_days": 30,
  "last_checked_at": "2026-09-24T04:20:00Z",
  "last_changed_at": "2026-09-21T19:38:23Z",
  "last_successful_sync": "2026-09-24T04:20:05Z",
  "freshness_status": "FRESH"
}
```
This metadata is surfaced via `GET /v1/policy/sources` to provide administrators with complete operational observability.
