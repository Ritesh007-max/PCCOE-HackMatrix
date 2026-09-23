# Phase 10: Application Case Model

## 1. Domain Entities

The application domain layer defines clean, decoupled aggregates without redundant data duplication.

```
AI/src/application/case.py
├── DocumentReference
├── FactSnapshot
├── SchemeEvaluation
└── ApplicationCase
```

---

## 2. Entity Specifications

### A. `DocumentReference`
Stores metadata and cryptographic provenance of attached citizen files:
- `document_id`: Unique identifier (e.g. `doc_<uuid4>`).
- `filename`: Original uploaded filename.
- `document_type`: Canonical document classification (e.g. `INCOME_CERTIFICATE`, `CASTE_CERTIFICATE`).
- `sha256_hash`: SHA-256 digest of file bytes for integrity and deduplication.
- `processing_status`: `PENDING`, `PROCESSED`, or `FAILED`.
- `provenance_refs`: Citations to OCR page numbers and bounding text spans.
- `facts_extracted`: Profile fields derived from this specific document.

> [!IMPORTANT]
> `DocumentReference` never stores raw file bytes to prevent memory bloat and protect PII.

---

### B. `FactSnapshot`
Captures the exact verified state of applicant profile fields used at decision time:
- `facts`: Dictionary of field values (e.g. `{"age": 20, "state": "Gujarat"}`).
- `verification_status`: Status per field (`EXTRACTED`, `USER_CONFIRMED`, `ISSUER_VERIFIED`, `CONFLICTED`).
- `evidence_references`: Map of field name to source document IDs.
- `conflicted_fields`: List of fields with contradictory evidence across multiple documents.
- `missing_fields`: Missing mandatory fields required by target scheme AST rules.
- `snapshot_timestamp`: UTC ISO 8601 timestamp.

---

### C. `SchemeEvaluation`
Represents the evaluation of a single candidate scheme:
- `scheme_id`: Statutory scheme identifier.
- `scheme_name`: Human-readable scheme name.
- `retrieval_relevance_score`: Float between 0.0 and 1.0 from hybrid RAG retrieval.
- `retrieval_rank`: Integer rank in candidate list.
- `decision_status`: Statutory decision enum (`PASS`, `FAIL`, `UNKNOWN`, `REVIEW`).
- `is_eligible`: Boolean flag (True ONLY for `PASS`).
- `matched_rules`: List of statutory rules satisfied.
- `failed_rules`: List of rules failed with hard constraint disqualifications.
- `unknown_rules`: Rules that cannot be evaluated due to missing applicant facts.
- `benefit_summary`: Computed financial/non-monetary benefits from `BenefitCalculator`.
- `policy_snapshot_version`: Bound policy version (e.g. `snapshot_20260921_193823`).
- `rule_version`: AST rule version.

---

### D. `ApplicationCase` (Aggregate Root)
The master orchestrating case object:
- `application_id`: Unique UUID4 case identifier (`app_<uuid4>`).
- `citizen_reference`: External citizen handle or anonymized ID.
- `current_status`: `ApplicationStatus` enum.
- `documents`: Dictionary of `DocumentReference` objects keyed by `document_id`.
- `facts`: `FactSnapshot` of applicant profile.
- `candidate_schemes`: Dictionary of `SchemeEvaluation` objects keyed by `scheme_id`.
- `selected_scheme_id`: ID of target scheme selected for application.
- `active_decision_snapshot_id`: Reference to currently active immutable `DecisionSnapshot`.
- `readiness`: `ReadinessStatus` enum.
- `next_actions`: Ordered list of deterministic `NextAction` dictionaries.
- `metadata`: Extensible metadata.
