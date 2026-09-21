# PolicySetu Policy Versioning and Snapshot Management

## 1. Content-Hash Versioning Scheme

Traditional software semantic versioning (`v1.2.3`) is inappropriate for government welfare policies. Government departments release administrative amendments, gazette notifications, financial year budget adjustments, and corrigenda without declaring semver semantics.

PolicySetu enforces **Content-Hash Source Revision Identifiers**:

```python
policy_version_id = f"policy_{content_hash[:12]}_{timestamp_str}"
source_revision   = actual_http_etag or git_commit_sha or sha256_digest
```

### Properties of Content-Hash Versions:
1. **Determinism**: Identical text, eligibility criteria, and benefits produce an identical `policy_version_id`.
2. **Auditability**: Traces directly back to the physical raw bytes of the statutory notification or portal crawl.
3. **Display vs Internal Separation**: The user interface can display friendly labels like "2025 Revision" or "Amendment 2", but all internal decision traces, audit logs, and citations reference `policy_version_id` and `source_revision`.

---

## 2. Decoupled Policy Content and Rule Engine Versioning

Policy content updates and executable rule updates have different lifecycles:

```
Policy Content Update (e.g. FAQ addition, benefit text clarification)
      ↓
Content Version Bump (policy_a1b2c3d4e5f6_20260921)
      ↓
Does Eligibility Criteria AST Differ?
  ├── NO  ──> RETAIN EXISTING RULE VERSION (rules_v1.0.0)
  └── YES ──> REBUILD RULES & EMIT NEW RULE VERSION (rules_v1.1.0)
```

By decoupling content versioning from rule versioning:
- Adding 10 new FAQs or updating department helpline numbers does not trigger rule compilation or risk invalidating tested eligibility logic.
- Phase 3 rule models remain stable and deterministically pinned to statutory eligibility definitions.

---

## 3. Snapshot Directory Layout

Every synchronized corpus generation creates an isolated, immutable snapshot directory under `AI/data/snapshots/`:

```
AI/data/snapshots/
├── active_version.json                     # Atomic pointer to currently active snapshot
├── snapshot_baseline_v0/                   # Initial immutable baseline from AI/data/raw/
│   ├── metadata.json                       # Counts, hashes, timestamp, lineage
│   ├── schemes_canonical.parquet           # Canonical scheme records
│   ├── schemes_faqs.parquet                # Authoritative FAQ pairs
│   ├── rag_chunks.parquet                  # Pre-computed text chunks
│   ├── rag_vectors.npy                     # Dense embedding matrix
│   ├── rules/                              # Compiled Phase 3 rule ASTs
│   ├── conflicts_log.json                  # Multi-source conflict audit
│   └── validation_report.json              # 15 Statutory quality check outputs
└── snapshot_20260921_192153/               # New version staged after synchronization
    ├── metadata.json
    ├── schemes_canonical.parquet
    ├── schemes_faqs.parquet
    ├── rag_chunks.parquet
    ├── rag_vectors.npy
    ├── rules/
    ├── conflicts_log.json
    └── validation_report.json
```

---

## 4. Atomic Pointer Switching and Activation Invariant

Activation of a staged snapshot is strictly governed by `SnapshotManager`:

```python
def activate_snapshot(self, snapshot_id: str, force: bool = False) -> bool:
    # 1. Verify snapshot directory exists
    # 2. Load validation_report.json from target snapshot
    # 3. Check critical_errors == 0 (unless force=True)
    # 4. Atomically write pointer via tempfile swap:
    temp_pointer = self.active_pointer_file.with_suffix(".tmp")
    with open(temp_pointer, "w", encoding="utf-8") as f:
        json.dump({"active_snapshot_id": snapshot_id, "activated_at": ...}, f)
    temp_pointer.replace(self.active_pointer_file)
```

### The Invariant:
```
IF validation_fails OR critical_errors > 0:
    ABORT ACTIVATION
    KEEP EXISTING ACTIVE VERSION
```

An active system will never serve an unverified or corrupted snapshot to citizens or downstream decision engines.
