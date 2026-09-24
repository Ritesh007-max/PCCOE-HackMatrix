# FIN Hugging Face Ingestion Policy

## 1. Statutory Role & Authority Ordering

Under FIN's source authority hierarchy:
```
PRIMARY_OFFICIAL > PRIMARY_CANONICALIZED > SUPPLEMENTARY > ARCHIVE > UNTRUSTED
```
**Hugging Face datasets are strictly classified as `SUPPLEMENTARY` sources.**

### Non-Negotiable Invariants:
1. **No Silent Statutory Overrides**: Data from Hugging Face datasets can enrich semantic retrieval, discovery, and benchmark evaluations, but **MUST NEVER** silently overwrite official primary policy facts.
2. **No Direct Statutory Decisions**: Supplementary HF data can never directly decide statutory eligibility (`PASS` or `FAIL`).
3. **Conflict Preservation**: If an HF supplementary record contradicts an authoritative official record (e.g., income ceiling ₹3,00,000 in HF vs ₹2,50,000 in Gazette), the official primary record governs statutory rules, while the conflict is recorded in `conflicts.json` for caseworker awareness.

---

## 2. Approved Active Repositories

| Repository ID | Ingestion Role | Permitted Usages | Prohibited Usages |
|---|---|---|---|
| `smartduketech/indian-government-schemes-2025` | `SCHEME_METADATA_ENRICHMENT` | Additional scheme descriptions, category tags, discovery gap analysis. | Generating statutory rule constraints. |
| `satyajitdas/bharatschemes-v1` | `BENCHMARK_EVALUATION` | Multilingual citizen query benchmarks, evaluation questions. | Generated assistant answers are **forbidden** from entering statutory policy evidence. |
| `shrijayan/gov_myscheme` | `SEMANTIC_TEXT_RETRIEVAL` | Supplementary text chunks for hybrid RAG retrieval. | Overriding canonical scheme records. |

---

## 3. Ingestion Lifecycle & Audit Trail

```
HF Repository Metadata Check
           |
           v
Revision Verification (Commit Hash / Tag)
           |
           v
Candidate Record Download & Content Hashing
           |
           v
Schema Detection & Drift Audit
           |
           v
Normalization into Canonical Schema
           |
           v
Source-Role Filtering (Strip Forbidden Fields)
           |
           v
Diff & Conflict Audit against Canonical Corpus
           |
           v
Staging as Supplementary Snapshot
```

- Every ingestion run records: `repo_id`, `revision`, `commit_hash`, `downloaded_at`, `license`, `total_records`, and `content_hash`.
- Schema drift (e.g. missing expected mandatory keys) raises warnings and halts activation if structure is incompatible.
