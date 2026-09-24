# FIN — Complete Data Acquisition Schema & Entity Specification

## 1. Schema Design Principles

1. **No Orphan Facts**: Every normalized field must link back to an immutable `SourceEvidence` span and `source_url`.
2. **Dual Representation for Rules**: Every statutory condition preserves both verbatim `raw_text` and machine-executable `normalized_condition`.
3. **Immutability**: Historical policy versions are never mutated in place; new acquisitions emit versioned snapshots.
4. **Graph-Aware**: Captures typed relationships between umbrella programs and component schemes (`PARENT_OF`, `COMPONENT_OF`, etc.).

---

## 2. Canonical Scheme Entity Specification

```json
{
  "scheme_id": "628b41a2c9b440ca7f31ff6c",
  "canonical_slug": "apy",
  "scheme_name": "Atal Pension Yojana",
  "alternate_names": ["APY"],
  "local_names": {
    "hi": "अटल पेंशन योजना",
    "gu": "અટલ પેન્શન યોજના"
  },
  "scheme_type": "Central Sector",
  "scheme_status": "ACTIVE",
  "ministry": "Ministry Of Finance",
  "department": "Department of Financial Services",
  "implementing_agency": "Pension Fund Regulatory and Development Authority (PFRDA)",
  "central_or_state": "Central",
  "state_or_ut": null,
  "sponsoring_authority": "Government of India",
  "nodal_department": "Department of Financial Services",
  "category": "Banking,Financial Services and Insurance",
  "subcategory": null,
  "tags": ["Social Security", "Pension", "Unorganised Workers"],
  "sectors": ["Financial Inclusion"],
  "beneficiary_groups": ["Citizens in Unorganised Sector"],
  "brief_description": "Atal Pension Yojana (APY) provides a guaranteed minimum pension of Rs. 1,000 to Rs. 5,000 per month upon attaining 60 years of age.",
  "detailed_description": "Detailed statutory rules and contribution charts for APY subscribers...",
  "eligibility_criteria": [
    {
      "criterion_id": "crit_628b41a2_min_age",
      "field": "age",
      "operator": ">=",
      "value": 18,
      "unit": "years",
      "raw_text": "The minimum age of joining APY is 18 years and maximum is 40 years.",
      "normalized_condition": {
        "field": "age",
        "operator": ">=",
        "value": 18,
        "unit": "years"
      },
      "source_url": "https://www.myscheme.gov.in/schemes/apy",
      "authority_tier": "TIER_2_MYSCHEME",
      "effective_from": "2015-05-09",
      "extraction_confidence": 1.0
    },
    {
      "criterion_id": "crit_628b41a2_max_age",
      "field": "age",
      "operator": "<=",
      "value": 40,
      "unit": "years",
      "raw_text": "The minimum age of joining APY is 18 years and maximum is 40 years.",
      "normalized_condition": {
        "field": "age",
        "operator": "<=",
        "value": 40,
        "unit": "years"
      },
      "source_url": "https://www.myscheme.gov.in/schemes/apy",
      "authority_tier": "TIER_2_MYSCHEME",
      "effective_from": "2015-05-09",
      "extraction_confidence": 1.0
    }
  ],
  "raw_eligibility_text": "1. The minimum age of joining APY is 18 years and maximum is 40 years.\n2. The age of exit and start of pension is 60 years.\n3. Subscriber must possess an active savings bank account.",
  "benefits": [
    {
      "benefit_id": "ben_628b41a2_0",
      "benefit_type": "Cash",
      "monetary_benefit": 5000.0,
      "percentage_subsidy": null,
      "fixed_subsidy": null,
      "benefit_frequency": "Monthly",
      "benefit_duration": "Lifelong",
      "formula": "Guaranteed pension based on entry age and monthly contribution amount",
      "caps": "Maximum Rs. 5,000 per month",
      "exclusions": "Subscribers who are income tax payers as of 01-10-2022 are not eligible to join APY.",
      "raw_text": "The subscriber shall receive a guaranteed minimum monthly pension of Rs. 1,000 to Rs. 5,000 upon attaining 60 years of age.",
      "source_url": "https://www.myscheme.gov.in/schemes/apy",
      "authority_tier": "TIER_2_MYSCHEME"
    }
  ],
  "raw_benefits_text": "The subscriber shall receive a guaranteed minimum monthly pension of Rs. 1,000 to Rs. 5,000 upon attaining 60 years of age.",
  "application_mode": ["Online", "Offline"],
  "application_steps": [
    {
      "step_number": 1,
      "title": "Application Step 1 (Online)",
      "description": "Open an APY account online using your Bank Net banking facility or mobile banking.",
      "mode": "Online",
      "url": "https://www.npscra.nsdl.co.in/"
    },
    {
      "step_number": 2,
      "title": "Application Step 2 (Offline)",
      "description": "Approach the bank branch or post office where your savings account is held and submit the APY registration form with Aadhaar.",
      "mode": "Offline",
      "url": null
    }
  ],
  "required_documents": [
    {
      "document_id": "doc_628b41a2_0",
      "document_name": "Aadhaar Card",
      "is_mandatory": true,
      "document_type": "Identity Proof",
      "issuing_authority": "UIDAI",
      "raw_text": "Aadhaar card details for KYC verification.",
      "source_url": "https://www.myscheme.gov.in/schemes/apy"
    },
    {
      "document_id": "doc_628b41a2_1",
      "document_name": "Active Savings Bank Account Passbook",
      "is_mandatory": true,
      "document_type": "Bank Proof",
      "issuing_authority": "Bank / Post Office",
      "raw_text": "Active Bank/Post Office Savings account for auto-debit of monthly contributions.",
      "source_url": "https://www.myscheme.gov.in/schemes/apy"
    }
  ],
  "raw_documents_text": "KYC details are fetched from active Bank/Post Office Savings account.\n1. Aadhaar Card\n2. Bank Account Details",
  "deadlines": {
    "application_start": null,
    "application_end": null,
    "recurring_deadline": "Continuous / Open round the year",
    "academic_year": null,
    "financial_year": null,
    "benefit_period": "Lifelong post age 60",
    "deadline_notes": "Enrolment is open continuously for citizens aged 18 to 40."
  },
  "faqs": [
    {
      "faq_id": "faq_628b41a2_0",
      "question": "When will I receive my Pension?",
      "answer": "Age of start of pension is 60 years.",
      "language": "en",
      "source_url": "https://www.myscheme.gov.in/schemes/apy",
      "source_section": "Eligibility & Pension"
    }
  ],
  "source_information": {
    "myscheme_url": "https://www.myscheme.gov.in/schemes/apy",
    "official_scheme_url": "https://jansuraksha.gov.in/Files/APY/ENGLISH/APY.pdf",
    "official_application_url": "https://www.npscra.nsdl.co.in/",
    "official_guideline_url": "https://jansuraksha.gov.in/Files/APY/ENGLISH/APY.pdf",
    "official_pdf_urls": [
      "https://jansuraksha.gov.in/Files/APY/ENGLISH/APY.pdf",
      "https://www.npscra.nsdl.co.in/nsdl/scheme-details/APY_Subscribers_Contribution_Chart_1.pdf"
    ],
    "gazette_url": null,
    "notification_url": null,
    "ministry_url": "https://financialservices.gov.in/",
    "department_url": "https://financialservices.gov.in/"
  },
  "temporal": {
    "published_at": "2015-05-09T00:00:00Z",
    "effective_from": "2015-06-01T00:00:00Z",
    "effective_until": null,
    "last_updated": "2026-09-24T08:54:46Z",
    "fetched_at": "2026-09-24T08:54:46Z",
    "content_hash": "b4bdc119df77685f737fe96ad488f8cde1983213314ae0a385a84687e788270e"
  },
  "provenance": {
    "source_id": "myscheme",
    "source_url": "https://www.myscheme.gov.in/schemes/apy",
    "source_domain": "www.myscheme.gov.in",
    "authority_tier": "TIER_2_MYSCHEME",
    "extraction_method": "apisetu_rest",
    "parser_version": "2.0.0",
    "ingestion_version": "v1",
    "snapshot_id": "snap_exhaustive_20260924"
  },
  "relationships": [],
  "language_variants": []
}
```

---

## 3. Normalized Relational & Graph Entities

1. **`Scheme`**: Core canonical entity with complete provenance, dual rule representation, and content hashes.
2. **`SchemeAlias`**: Maps alternate titles, acronyms, and historical names.
3. **`Authority`**: Represents Central Ministries, State Departments, and Statutory Regulators with verified domain allowlists.
4. **`EligibilityCriterion`**: Atomic statutory condition with structured `field`, `operator`, `value`, and raw evidence span.
5. **`Benefit`**: Entitlement details, formulas, caps, and subsidy percentages.
6. **`RequiredDocument`**: Supporting identity, income, caste, and residency proofs.
7. **`ApplicationStep`**: Sequential, mode-aware citizen application journey.
8. **`FAQ`**: Atomic question-answer pairs linked directly to scheme and language code.
9. **`PolicyDocument`**: First-party PDF guidelines, gazettes, circulars, and forms.
10. **`PolicyVersion`**: Point-in-time immutable snapshot metadata.
11. **`Source`**: Registry definition of ingested data endpoints.
12. **`SourceEvidence`**: Immutable trace attaching an extracted fact to its exact source URL, offset span, and content hash.
13. **`SchemeRelationship`**: Directed graph relationships (`PARENT_OF`, `COMPONENT_OF`, `SUPERSEDES`, `SUPERSEDED_BY`, `RENAMED_TO`, `MERGED_INTO`, `RELATED_TO`).
14. **`Conflict`**: Discrepancy record preserving both values, authorities, dates, and resolution notes.
15. **`CrawlJob`**: Auditable execution log of an acquisition run.
16. **`CrawlFailure`**: Error ledger tracking HTTP status codes, reasons, and next actions.
17. **`LanguageVariant`**: Multilingual manifestation preserving native localized text.
