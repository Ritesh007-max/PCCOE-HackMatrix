# FIN — Master Coverage Audit

## 1. High-Level Acquisition Metrics

- **Portal Reported Universe:** 5,111 schemes
- **Unique Catalogue Slugs:** 5,110 schemes
- **Duplicate Slug Collisions:** 1 (`tufs` - mapped to 2 distinct portal scheme IDs)
- **Live Detail Attempted:** 5,110 schemes (100.0%)
- **Live Detail Successful:** 5,110 schemes (100.0%)
- **FULL_DETAIL Count:** 5,105 schemes
- **PARTIAL_DETAIL Count:** 5 schemes (`cmchis`, `mmgsy`, `mmuy`, `cmegp`, `nari-adalat`)
- **CATALOG_ONLY Count:** 0 schemes (All 5,110 live schemes deep-detailed)
- **FAILED Fetch Count:** 0
- **NOT_AVAILABLE Count:** 0
- **REMOVED_ON_PORTAL Count:** 7 schemes (Retained from historical baseline)

---

## 2. Field Coverage Matrix

Audited completeness across all 5,110 unique live catalogue schemes:

| Field Name | Available Schemes | Missing Schemes | Completeness (%) |
|---|---|---|---|
| `scheme_name` | 5,110 | 0 | 100.00% |
| `description` | 5,110 | 0 | 100.00% |
| `eligibility` | 5,110 | 0 | 100.00% |
| `benefits` | 4,843 | 267 | 94.77% |
| `application` | 5,110 | 0 | 100.00% |
| `documents` | 5,084 | 26 | 99.49% |
| `FAQs` | 5,080 | 30 | 99.41% |
| `official_reference` | 5,095 | 15 | 99.71% |
| `ministry` | 5,110 | 0 | 100.00% |
| `category` | 5,110 | 0 | 100.00% |
| `state_or_ut` | 799 | 4,311 | 15.64% |

**Composite Field Coverage Summary:** `91.73%`

---

## 3. Strict Distinction: Catalogue vs Detail

The pipeline enforces an absolute architectural separation between:
1. **Catalogue Enumeration:** Discovering the existence of a scheme via portal search/category listings.
2. **Deep Detail Acquisition:** Fetching the authoritative AST/JSON containing statutory eligibility criteria, quantified benefits, step-by-step application instructions, required documentation evidence, and FAQs.

No scheme is marked `FULL_DETAIL` or indexed in RAG without a verifiable, cryptographically hashed raw response artifact on disk and an entry in `request_ledger.json`.
