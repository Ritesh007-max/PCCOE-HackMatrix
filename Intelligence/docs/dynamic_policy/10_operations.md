# FIN Phase 12: Operations & API Reference

## 1. Policy Operations API Endpoints

The FIN microservice exposes internal management endpoints under `/v1/policy/`. All state-mutating operations require internal authentication via the `X-Service-Key` header.

### Endpoint Matrix

| Method | Path | Auth Required | Purpose |
|---|---|---|---|
| `GET` | `/v1/policy/status` | No | Retrieves current active policy version, last sync time, and total schemes. |
| `GET` | `/v1/policy/sources` | No | Lists all registered sources, authority tiers, and operational freshness states. |
| `GET` | `/v1/policy/sync/latest` | No | Returns the audit payload of the most recent sync job. |
| `POST` | `/v1/policy/sync` | **Yes** (`X-Service-Key`) | Executes live synchronization, gate evaluation, and atomic activation. |
| `POST` | `/v1/policy/sync/dry-run` | **Yes** (`X-Service-Key`) | Executes full fetch, diff, and gate audit without mutating active state. |
| `POST` | `/v1/policy/rollback` | **Yes** (`X-Service-Key`) | Atomically rolls back to a specified or previous known-good snapshot. |

---

## 2. API Request & Response Examples

### Dry-Run Synchronization Request
```http
POST /v1/policy/sync/dry-run HTTP/1.1
Host: localhost:8000
X-Service-Key: <INTERNAL_SERVICE_API_KEY>
Content-Type: application/json

{
  "source_id": "smartduketech/indian-government-schemes-2025"
}
```

#### Response (200 OK)
```json
{
  "sync_id": "sync_20260924_042004",
  "status": "DRY_RUN",
  "activation_status": "BYPASSED_DRY_RUN",
  "previous_version": "snapshot_20260921_193823",
  "candidate_version": "snapshot_20260924_042004_123456",
  "records_seen": 4750,
  "records_added": 1,
  "records_updated": 0,
  "records_removed": 0,
  "records_unchanged": 4749,
  "validation_errors": [],
  "warnings": [],
  "conflicts": []
}
```

### Rollback Request
```http
POST /v1/policy/rollback HTTP/1.1
Host: localhost:8000
X-Service-Key: <INTERNAL_SERVICE_API_KEY>
Content-Type: application/json

{
  "target_version": "snapshot_20260921_193823"
}
```

#### Response (200 OK)
```json
{
  "status": "ROLLED_BACK",
  "restored_version": "snapshot_20260921_193823",
  "timestamp": "2026-09-24T04:25:00Z"
}
```

---

## 3. Programmatic Python Usage

For background worker processes or internal scheduled jobs:

```python
from src.data_pipeline.orchestrator import PolicySyncOrchestrator

orchestrator = PolicySyncOrchestrator()

# Execute dry-run
dry_job = orchestrator.sync(dry_run=True)
print(f"Dry run result: {dry_job.records_added} added, {len(dry_job.conflicts)} conflicts")

# Execute live sync
live_job = orchestrator.sync(dry_run=False)
if live_job.status == "SUCCEEDED":
    print(f"Successfully activated: {live_job.candidate_version}")
else:
    print(f"Sync rejected by gates: {live_job.validation_errors}")
```
