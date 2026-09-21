# PolicySetu Multi-Document Evidence Model

## 1. Overview & Purpose

In government welfare eligibility, an applicant rarely relies on a single document. Information is gathered across multiple heterogeneous artifacts:
- Proof of Identity (Aadhaar, Voter ID, Passport)
- Proof of Income (Income Certificate from Tahsildar / Revenue Authority, Form 16, ITR Acknowledgement, Salary Slip)
- Proof of Statutory Domicile (State Domicile Certificate, Permanent Resident Certificate [PRC] issued by District Magistrate / Tahsildar)
- Supporting Physical Address Proof (Electricity Bill, Water Bill, LPG Connection — corroborative secondary proof, not automatically authoritative for permanent state domicile)
- Proof of Category (Caste / Tribe Certificate, Disability Certificate)
- Self-Declarations / Application Forms

> [!IMPORTANT]
> **Statutory Document Distinctions**:
> 1. **Aadhaar is not proof of income**: Aadhaar is strictly a proof of identity and residential address issued by UIDAI. It must never be accepted or treated as evidence of income.
> 2. **Authoritative Domicile vs Supporting Utility Bills**: A government-issued Domicile Certificate or PRC is the primary authoritative evidence for state permanent residence (`ISSUER_VERIFIED`). An Electricity Bill serves only as supporting evidence of current physical address/occupancy and must not be treated as automatically authoritative for statutory state domicile.

The **PolicySetu Evidence Model** aggregates facts extracted across all provided documents, performs cross-document corroboration, detects contradictory evidence, and safely bridges into the deterministic eligibility engine.

---

## 2. Document Provenance Tracking

Every piece of evidence is bound to an audit-grade `DocumentProvenance` record:

```python
@dataclass
class DocumentProvenance:
    source_document: str                    # Filename or document identifier
    document_type: DocumentType             # AADHAAR, INCOME_CERTIFICATE, PAN, etc.
    issuer: Optional[str]                   # Issuing authority (e.g. UIDAI, Tahsildar)
    issue_date: Optional[str]               # Date of statutory issuance
    page_number: Optional[int]              # Page where evidence was detected
    text_span: Optional[str]                # Verbatim source string
    extraction_timestamp: str               # ISO-8601 UTC timestamp
```

### Supported Document Types & Evidentiary Roles
- `AADHAAR`: Authoritative proof of Identity & residential address (never income).
- `PAN`: Proof of financial identity and tax identifier.
- `INCOME_CERTIFICATE`: Primary authoritative statutory proof of household income.
- `DOMICILE_CERTIFICATE`: Primary authoritative statutory proof of permanent state domicile.
- `ELECTRICITY_BILL`: Supporting/secondary proof of physical premise connection (not authoritative for statutory domicile).
- `CASTE_CERTIFICATE`: Primary statutory proof of constitutional social category.
- `DISABILITY_CERTIFICATE`: Primary statutory proof of disability percentage.
- `RATION_CARD`: Supporting household composition and entitlement proof.
- `LAND_RECORD_ROR`: Primary statutory proof of landholding and title.
- `BANK_PASSBOOK`: Supporting proof of active account and DBT eligibility.
- `STUDENT_ID`: Supporting proof of educational enrollment.
- `SELF_DECLARATION`: Declarative baseline (`SELF_REPORTED`).
- `OTHER`: Unspecified supporting documents.

---

## 3. Evidence Aggregation & Reconcilation

The `EvidenceRegistry` gathers all applicant facts keyed by canonical field:

```
EvidenceRegistry
  └── evidence_by_field["annual_family_income"]
        ├── Fact 1 (Self-Reported Application Form): 4,20,000 INR
        └── Fact 2 (Tahsildar Income Certificate):   6,10,000 INR
```

When multiple facts are recorded for the same field:

### Case A: Corroborating (Harmonious) Evidence
When all normalized values agree:
- Example:
  - Document A (Self-Reported Application Form): `"Rs. 4.2 Lakh"` -> normalized: `420000.0` (`SELF_REPORTED`)
  - Document B (Tahsildar Income Certificate): `"₹4,20,000"` -> normalized: `420000.0` (`ISSUER_VERIFIED`)
- **Result**: The evidence is corroborating.
- The consolidated fact retains the highest verification tier available (`ISSUER_VERIFIED` > `USER_CONFIRMED` > `EXTRACTED` > `SELF_REPORTED`).

### Case B: Contradictory (Discordant) Evidence
When two or more documents provide conflicting values:
- Example:
  - Document A (Self-Reported Application Form): `"420000"`
  - Document B (Tahsildar Income Certificate / Tax Assessment): `"610000"`
- **Result**: **CONFLICT DETECTED**.
- Status is immediately set to `CONFLICTED`.
- Field is recorded in `EvidenceRegistry.conflicted_fields`.
- **Absolute Safety Rule**: The system **never** averages, selects by recency, or silently tie-breaks contradictory values.

---

## 4. Deterministic Engine Bridge & Critical Invariants

The `EvidenceRegistry.to_applicant_profile()` method compiles evidence into the deterministic `ApplicantProfile`:

### The Critical Invariant
> **"UNKNOWN or CONFLICTED facts must never be converted into PASS; conflicting facts must produce REVIEW."**

```
                     +---------------------------------------+
                     |         Applicant Fact State          |
                     +---------------------------------------+
                                    |         |
                  +-----------------+         +-----------------+
                  |                                             |
                  v                                             v
        [ MISSING / UNKNOWN ]                            [ CONFLICTED ]
                  |                                             |
                  v                                             v
     RuleEvaluator returns:                         RuleEvaluator returns:
           UNKNOWN                                        REVIEW
   (never PASS, never FAIL)                             (never PASS)
```

1. **Conflicted Fields**:
   - Conflicted field names are supplied to `ApplicantProfile(conflicts=[...])`.
   - Any eligibility or exclusion rule evaluating this field returns `RuleStatus.REVIEW` with the reason:
     `"Conflicting/contradictory evidence for field '<field>'."`
2. **Missing Fields**:
   - Fields without evidence remain absent.
   - Any rule evaluating this field returns `RuleStatus.UNKNOWN` with the reason:
     `"Applicant profile missing attribute '<field>'."`
3. **Valid Fields**:
   - Fields with unanimous, validated evidence evaluate deterministically to `PASS` or `FAIL`.

---

## 5. Audit Trail & Provenance Verification

When decisions are rendered:
- Every evaluated rule links back to the underlying `ApplicantFact`.
- The audit trail retains the exact `text_span`, `source_document`, `page_number`, and `confidence` score.
- Review officers can immediately inspect the exact competing document snippets that triggered a `REVIEW` state.
