# FIN — Multi-Tier Conflict Detection & Resolution Specification

## 1. Statutory Conflict Resolution Principles

When overlapping sources provide contradictory eligibility, benefit, or procedural data for the same scheme, FIN **strictly forbids silent merging or arbitrary LLM selection**.

Core rules:
1. **Never Silently Overwrite**: Any contradictory fact must generate an immutable `Conflict` record.
2. **Authority Rank Outranks Timestamp**: A newer secondary webpage or aggregator cannot override an older statutory Act or Gazette notification unless the legal instrument itself has been amended.
3. **Effective Date supersedes Publication Date**: When comparing two instruments within the same authority tier, the legally effective date (`effective_from`) governs applicability, not the web publication timestamp.
4. **Supplementary Data Has Zero Statutory Precedence**: Tier 5 datasets (HuggingFace, Kaggle) cannot override Tier 0, Tier 1, or Tier 2 official data under any circumstance.
5. **Fail-Closed on Uncertainty**: If two official sources conflict at the exact same tier without verifiable chronological supersession, the status is marked `REVIEW` and requires administrative human adjudication.

---

## 2. Conflict Record Schema

Every discrepancy is recorded in `Intelligence/data/conflicts/`:

```json
{
  "conflict_id": "conf_apy_annual_family_income_7a1b9c",
  "scheme_slug": "apy",
  "field_name": "annual_family_income",
  "source_a": "https://jansuraksha.gov.in/Files/APY/ENGLISH/APY.pdf",
  "value_a": 300000.0,
  "authority_a": "TIER_1_FIRST_PARTY_OPERATIONAL",
  "date_a": "2024-04-01T00:00:00Z",
  "source_b": "https://www.myscheme.gov.in/schemes/apy",
  "value_b": 250000.0,
  "authority_b": "TIER_2_MYSCHEME",
  "date_b": "2023-01-15T00:00:00Z",
  "conflicting_text": "Source A (ministry guideline): 300000.0 vs Source B (myscheme summary): 250000.0",
  "resolution_status": "RESOLVED",
  "resolved_value": 300000.0,
  "notes": "Deterministically resolved to TIER_1_FIRST_PARTY_OPERATIONAL (jansuraksha.gov.in) over lower tier TIER_2_MYSCHEME summary",
  "detected_at": "2026-09-24T08:54:55Z"
}
```

---

## 3. Concrete Case Studies & Decision Paths

### Case Study 1: Statutory Gazette Notification vs. Portal Summary
- **Scenario**:
  - Source A: Gazette of India Notification No. 1234/2022 (`egazette.gov.in`) states that income taxpayers are ineligible for APY starting 01-10-2022. Authority Tier: `TIER_0_LEGAL_STATUTORY`.
  - Source B: Outdated myScheme web summary (`myscheme.gov.in`) omits the taxpayer exclusion. Authority Tier: `TIER_2_MYSCHEME`.
- **Decision Engine Output**:
  - `status`: `RESOLVED`
  - `resolved_value`: Taxpayer exclusion APPLIED.
  - `precedence`: Tier 0 (Statutory Legal Authority, Rank 10) strictly outranks Tier 2 (myScheme Discovery, Rank 6).

### Case Study 2: Supplementary HuggingFace Dataset vs. myScheme
- **Scenario**:
  - Source A: Hugging Face dataset `bharatschemes-v1` lists maximum age for PM-KISAN as 60 years. Authority Tier: `TIER_5_SUPPLEMENTARY`.
  - Source B: myScheme portal (`myscheme.gov.in`) states there is no upper age limit for eligible landholding farmer families. Authority Tier: `TIER_2_MYSCHEME`.
- **Decision Engine Output**:
  - `status`: `RESOLVED`
  - `resolved_value`: No upper age limit.
  - `precedence`: Tier 2 (myScheme, Rank 6) outranks Tier 5 (Supplementary, Rank 2). Tier 5 is strictly prohibited from altering statutory parameters.

### Case Study 3: Discrepancy Between Two State Department Circulars at Same Tier
- **Scenario**:
  - Source A: Department of Social Welfare Circular A (published 2025-06) states income limit is Rs. 1,50,000. Authority Tier: `TIER_1_FIRST_PARTY_OPERATIONAL`.
  - Source B: Department of Minority Affairs Circular B (published 2025-06) states income limit for the same joint initiative is Rs. 2,00,000. Authority Tier: `TIER_1_FIRST_PARTY_OPERATIONAL`.
- **Decision Engine Output**:
  - `status`: `REVIEW`
  - `resolved_value`: `null`
  - `precedence`: Both sources occupy `TIER_1_FIRST_PARTY_OPERATIONAL` (Rank 8) with overlapping effective dates. The system flags the record for human review and preserves uncertainty without making an unsafe assumption.

---

## 4. Reconciled Conflict Audit Ledger Summary

In accordance with truth-in-reporting standards, conflict counts are consistently reported across `Intelligence/data/conflicts/`, `Intelligence/data/coverage/coverage_audit.json`, and all crawl reports:

```
Total Audited Conflicts Detected:       3
Total Audited Conflicts Resolved:       2 (APY Taxpayer Exclusion, PM-KISAN Max Age)
Total Audited Conflicts Pending Review: 1 (PMSY Circular Discrepancy)
Total Audited Conflicts Closed:         2
Conflicts in Active Policy:             1
Unresolved Conflict Count:              1 (Honestly reported as 1, NEVER as 0)
```

