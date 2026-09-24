# FIN Phase 12: Activation Gates, Atomic Activation & Rollback

## 1. Candidate Staging & The 14 Activation Gates

Every policy synchronization run creates a temporary staging area (`Intelligence/data/snapshots/candidates/candidate_<sync_id>/`) where all candidate artifacts are compiled. Before any candidate can be promoted to active, it must pass 14 deterministic, fail-closed gates evaluated by `ActivationGateEvaluator`:

| Gate # | Gate Name | Validation Rule | Consequence of Failure |
|---|---|---|---|
| **1** | `SCHEMA_VALIDATION` | Mandatory fields (`slug`, `scheme_name`, `eligibility`) present and typed. | Rejection |
| **2** | `AUTHORITY_VALIDATION` | Sources declare approved `AuthorityTier`. | Rejection |
| **3** | `URL_ALLOWLIST_VALIDATION` | Domains match approved official regex (strict `.gov.in`/`.nic.in` boundaries). | Rejection |
| **4** | `DUPLICATE_ID_VALIDATION` | No colliding scheme identifiers. | Rejection |
| **5** | `DUPLICATE_SLUG_VALIDATION` | Unique scheme URL slugs across corpus. | Rejection |
| **6** | `MISSING_ELIGIBILITY_VALIDATION` | Eligibility description cannot be empty or null. | Rejection |
| **7** | `SOURCE_PROVENANCE_VALIDATION` | Source dataset and fetch timestamp must be traced. | Rejection |
| **8** | `RULE_EXTRACTION_VALIDATION` | Changed schemes must parse into valid AST candidates. | Rejection |
| **9** | `RULE_COMPILATION_VALIDATION` | Compiled rule ASTs must evaluate without runtime syntax errors. | Rejection |
| **10** | `RAG_UPDATE_VALIDATION` | Vector chunks and metadata match schema. | Rejection |
| **11** | `SOURCE_CONFLICT_VALIDATION` | Any conflicting statutory primary claims must be flagged. | Rejection |
| **12** | `CORPUS_INTEGRITY_VALIDATION` | Catastrophic deletion guard: candidate cannot drop >10% of records. | Rejection |
| **13** | `REGRESSION_TEST_VALIDATION` | Standard baseline synthetic profiles must evaluate correctly. | Rejection |
| **14** | `SNAPSHOT_CONSISTENCY_VALIDATION` | File checksums and manifests match candidate layout. | Rejection |

If **any** critical gate fails, the candidate is rejected. The currently active snapshot and `active_version.json` remain untouched.

---

## 2. Atomic Activation

Once all 14 gates pass:
1. Candidate directory is moved into `Intelligence/data/snapshots/<snapshot_id>/`.
2. A temporary pointer file `active_version.json.tmp.<uuid>` is written containing:
   ```json
   {
     "active_snapshot": "snapshot_20260924_042004_123456",
     "activated_at": "2026-09-24T04:20:05.123456Z",
     "previous_snapshot": "snapshot_20260921_193823"
   }
   ```
3. The temporary file is atomically renamed to overwrite `active_version.json` (`os.replace` on POSIX / atomic file move on Windows).
4. **Post-Activation Verification**: The system reads back `active_version.json`, checks that the target snapshot directory exists, and verifies checksums. If verification fails, an automatic rollback is immediately executed.

---

## 3. Atomic Rollback

If operational anomalies occur post-activation, `orchestrator.rollback(target_version=None)` can be called manually or programmatically:

1. **Target Identification**: If `target_version` is specified, the system verifies that `Intelligence/data/snapshots/<target_version>/` exists and is intact. Otherwise, it restores `previous_snapshot` from the active pointer.
2. **State Restoration**:
   - `active_version.json` is atomically pointed back to the target snapshot.
   - Corresponding rule artifacts, canonical schemes, RAG indices, and source manifests are restored.
3. **Audit Trail**: An audit event with status `ROLLED_BACK` is appended to `sync_audit_log.jsonl`.

---

## 4. Historical Decision Immutability

Live policy activations never mutate historical citizen application decisions:
- Each evaluated `ApplicationCase` stores an immutable `DecisionSnapshot` (e.g. `snap_001`).
- The snapshot records the exact `policy_snapshot_version` (e.g. `snapshot_20260921_193823`), `rule_version`, applicant facts, and statutory decision (`PASS` / `FAIL`).
- When a new snapshot (e.g. `snapshot_20260924_042004_123456`) is activated, old application decisions remain pinned to the historical version.
- Re-evaluation creates a new snapshot version (`version_index = 2`) side-by-side, preserving the original for audit and dispute resolution.
