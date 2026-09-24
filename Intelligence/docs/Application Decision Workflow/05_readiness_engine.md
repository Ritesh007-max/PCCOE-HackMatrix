# Phase 10: Application Readiness Engine

## 1. Readiness vs. Statutory Eligibility

A critical architectural distinction enforced in Phase 10:

- **Statutory Decision** (`PASS`, `FAIL`, `UNKNOWN`, `REVIEW`): Does the citizen satisfy the legal eligibility rules of the scheme?
- **Application Readiness** (`NOT_READY`, `ACTION_REQUIRED`, `READY_FOR_REVIEW`, `READY_TO_APPLY`, `COMPLETED`): Is the application package complete with all mandatory certificates and ready to be filed on the government portal?

An applicant may be statutory `PASS`, but if their mandatory caste certificate is missing, declaring them `READY_TO_APPLY` would cause rejection on the government portal. The readiness engine correctly signals `ACTION_REQUIRED`.

---

## 2. Deterministic Readiness Matrix

The `ApplicationReadinessEvaluator` applies the following deterministic rules:

| Statutory Decision | Document Completeness | Fact Completeness | Conflicts | Resulting Readiness |
|---|---|---|---|---|
| `PASS` | Complete (all required docs available) | Complete | None | **`READY_TO_APPLY`** |
| `PASS` | Incomplete (missing required certificates) | Any | None | **`ACTION_REQUIRED`** |
| `PASS` | Any | Missing fields | None | **`ACTION_REQUIRED`** |
| `UNKNOWN` | Any | Missing facts | None | **`ACTION_REQUIRED`** |
| `REVIEW` | Any | Any | Conflicts or unstructured rules | **`READY_FOR_REVIEW`** |
| Any | Any | Any | Contradictory evidence across docs | **`READY_FOR_REVIEW`** |
| `FAIL` | Any | Any | Any | **`NOT_READY`** |

---

## 3. Completeness Evaluation Reports

### A. Document Completeness Report
Evaluates required document types against attached documents:
- `required_documents`: Dict mapping document name to status (`AVAILABLE`, `MISSING`, `CONFLICTED`, `UNKNOWN`).
- `missing_documents`: List of missing required certificates.
- `available_documents`: List of satisfied certificates.
- `is_complete`: Boolean indicator.

### B. Fact Completeness Report
Audits required profile fields:
- `known_fields`: Profile facts verified and present.
- `missing_fields`: AST rule requirements without values.
- `conflicted_fields`: Contradictory facts.
- `is_complete`: True only if zero missing and zero conflicts.
