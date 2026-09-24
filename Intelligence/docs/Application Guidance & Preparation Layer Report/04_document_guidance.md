# Phase 11: Document Guidance & Preparation

## 1. Document Requirements Model

For each required certificate or proof, the Guidance layer determines:
1. **Document Type**: Canonical identifier (e.g., `income_certificate`, `caste_certificate`, `domicile_certificate`).
2. **Display Name**: Human-friendly label (e.g., "Income Certificate", "Caste / Social Category Certificate").
3. **Status**:
   - `AVAILABLE`: Attached, uncorrupted, and successfully processed.
   - `MISSING`: Required by scheme rules or metadata, but not yet uploaded.
   - `CONFLICTED`: Attached document contains facts conflicting with applicant profile.
   - `UNKNOWN`: Document uploaded but illegible or type unrecognized.
   - `NOT_REQUIRED`: Document optional for evaluated profile.
4. **Issuing Authority**: Canonical state/central department responsible for issuance (e.g., "Revenue Department, Taluk / Tehsildar Office").
5. **Preparation Notes**: Concrete verification instructions (e.g., "Must be issued within current financial year").

---

## 2. Checklist Adaptation

Phase 11 reuses Phase 10's `ApplicationChecklist` without recomputing checklist logic. It outputs three distinct presentation arrays:
- `available`: Documents ready for submission.
- `missing`: Documents that must be procured before applying.
- `conflicted`: Documents requiring resolution or administrative clarification.
