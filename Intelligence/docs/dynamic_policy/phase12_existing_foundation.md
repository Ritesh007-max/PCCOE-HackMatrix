# Phase 12 Audit: Existing Phase 7 Foundation & Operationalization Roadmap

## 1. Executive Summary

Phase 12 builds directly on the dynamic synchronization foundation established in **Phase 7** (`Intelligence/src/data_pipeline/`). Phase 7 introduced source registry abstractions, diff calculation, snapshot directory structures, basic rollback pointers, and incremental RAG chunk tracking.

Phase 12 **operationalizes and hardens** these capabilities into a resilient, production-oriented, live policy update engine. In accordance with architectural principles:
- **AI interprets**
- **Rules decide**
- **Evidence proves**
- **Human reviews uncertainty**

---

## 2. Inventory of Phase 7 Assets & Reusability Matrix

| Component | Phase 7 File Path | Current Capabilities | Reusable Status | Phase 12 Operationalization |
|---|---|---|---|---|
| **Source Registry** | `src/data_pipeline/sources/registry.py`<br>`src/data_pipeline/sources/sources.py` | `SourceDefinition`, `AuthorityTier` (1-5), allowlists for official domains and HF datasets. | **Fully Reusable Core** | Add `UNTRUSTED` tier (0). Enforce strict HTTPS and domain boundary sanitization (reject `evil-gov.in`, `gov.in.evil.com`). |
| **Fetchers** | `src/data_pipeline/fetchers/base.py`<br>`fetchers/local.py`<br>`fetchers/huggingface.py`<br>`fetchers/web.py`<br>`fetchers/pdf.py` | `BaseFetcher`, `FetchResult`, `HuggingFaceFetcher` with CSR/NGO classification. | **Fully Reusable Core** | Implement HF revision tracking (commit hash, content hashes, schema drift detection, license metadata). |
| **Change Detection** | `src/data_pipeline/change_detection.py`<br>`src/data_pipeline/diff.py` | SHA256 record hashing, slug diffing, basic field diffs. | **Fully Reusable Core** | Implement multi-label change classification (15 change types) and deterministic rule-impact analysis (`RULE_RECOMPILE_REQUIRED`). |
| **Conflict Engine** | `src/data_pipeline/conflict.py` | `ConflictDetector`, `ConflictRecord`, `ConflictResolution` precedence (Primary > Supplementary). | **Fully Reusable Core** | Enforce: Supplementary sources never silently override statutory rules; equal-primary conflicts flag `POLICY_SOURCE_CONFLICT` and require human review. |
| **Data Quality Validation** | `src/data_pipeline/validation.py` | `DataQualityValidator`, `ValidationReport`, 18 structural and sanity checks. | **Fully Reusable Core** | Upgrade into 14 deterministic **Activation Gates** with fail-closed semantics. |
| **Snapshot & Rollback** | `src/data_pipeline/snapshot.py` | Snapshot directory layout, `metadata.json`, `active_version.json` atomic pointer, rollback pointer switch. | **Fully Reusable Core** | Implement safe candidate snapshot staging, post-activation verification, and multi-artifact rollback (canonical, rules, RAG, lineage). |
| **Incremental RAG** | `src/data_pipeline/incremental_rag.py` | `IncrementalRAGUpdater`, chunk diffing, drop removed/modified, add new chunks. | **Fully Reusable Core** | Ensure vector index and active chunks strictly align with active policy snapshot; zero stale chunks linger. |
| **Lineage Tracker** | `src/data_pipeline/lineage/tracker.py` | `LineageTracker`, `LineageRecord`, JSONL persistence. | **Fully Reusable Core** | Ensure complete traceability: Source -> Raw -> Normalized -> Canonical -> Rule -> RAG Chunk -> Vector Index -> Active Snapshot. |
| **Freshness Model** | `src/data_pipeline/freshness.py` | `FreshnessStatus` (`FRESH`, `AGING`, `STALE`, `FAILED`, `UNKNOWN`). | **Fully Reusable Core** | Formalize operational freshness distinct from statutory authority or legal validity. |
| **Sync Coordinator** | `src/data_pipeline/sync.py` | CLI for baseline synchronization and dry-run flag. | **Needs Major Extension** | Replace with robust `PolicySyncOrchestrator` supporting job models, retry with backoff, source failure isolation, and scheduler. |

---

## 3. What Phase 12 Adds (Genuinely New)

1. **Lightweight Sync Orchestrator & Scheduler**:
   - `PolicySyncOrchestrator`: Coordinates manual, dry-run, scheduled, per-source, and full sync.
   - Source failure isolation: Failure in one healthy source does not invalidate other healthy sources.
   - Bounded retries with exponential backoff and timeouts.
   - Persistent `SyncJob` execution ledger.
2. **Deterministic Change Classification & Rule Impact**:
   - 15 specific change types (e.g., `ELIGIBILITY_CHANGED`, `BENEFIT_CHANGED`, `RULE_AFFECTING_CHANGE`, `CONFLICT_DETECTED`).
   - Identifies if changes touch statutory eligibility constraints (`income`, `age`, `state`, `category`, `disability`, etc.) to trigger `RULE_RECOMPILE_REQUIRED`.
3. **14 Deterministic Activation Gates**:
   - Fail-closed gates executed before candidate promotion to active.
4. **Hugging Face Supplementary Protocol**:
   - Dedicated `sources/huggingface.py` pipeline treating HF datasets as strictly `SUPPLEMENTARY`.
   - Recording immutable commit revisions, schema drift warnings, and license metadata.
   - Directing BharatSchemes QA queries to evaluation benchmarks (not statutory evidence).
5. **Historical Decision Immutability**:
   - Explicit architectural guarantees that historical applications and guidance packages retain exact reproducibility under their original policy snapshots and rule versions.
6. **AI-Only Policy Management & Inspection API**:
   - `GET /v1/policy/status`, `GET /v1/policy/sources`, `GET /v1/policy/sync/latest`, `POST /v1/policy/sync`, `POST /v1/policy/sync/dry-run`, `POST /v1/policy/rollback`.

---

## 4. What Must NOT Be Duplicated
- Do **not** create a second snapshot storage directory (keep `Intelligence/data/snapshots/`).
- Do **not** create a second canonical scheme schema (use existing canonical format).
- Do **not** rewrite `RuleEvaluator`, `EligibilityEngine`, or `ApplicationPipeline`.
- Do **not** introduce Kafka, Airflow, Kubernetes, or heavy distributed schedulers.
