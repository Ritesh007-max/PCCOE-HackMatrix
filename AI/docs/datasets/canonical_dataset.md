# PolicySetu Canonical Master Scheme Dataset Documentation

This document describes the design, consolidation methodology, schema specification, quality validation, and provenance architecture of the **PolicySetu Canonical Master Scheme Dataset** produced in **Phase 1**.

---

## 🏛 1. Dataset Overview & Total Canonical Schemes

The canonical scheme dataset consolidates India's national and state public welfare policies into a unified, clean, schema-standardized master catalog.

- **Total Canonical Schemes**: **4,749**
- **Primary / Authoritative Schemes (`schemes.csv`)**: **4,670** (98.34%)
- **Supplementary Schemes (`updated_data.csv`)**: **79** (1.66%)
- **Total Linked FAQs**: **51,435** (across 4,647 schemes)
- **Jurisdictional Breakdown**:
  - **Central Government Schemes**: **669**
  - **State / UT Government Schemes**: **4,080** (covering all 36 States and Union Territories)

### Processed Target Artifacts
- **Parquet Format**: [AI/data/processed/schemes_canonical.parquet](file:///c:/Users/ozhad/Desktop/HackMatrix/PCCOE-HackMatrix/AI/data/processed/schemes_canonical.parquet) (8,126,376 bytes ~ 7.75 MB)
- **JSONL Format**: [AI/data/processed/schemes_canonical.jsonl](file:///c:/Users/ozhad/Desktop/HackMatrix/PCCOE-HackMatrix/AI/data/processed/schemes_canonical.jsonl) (23,545,910 bytes ~ 22.45 MB)

---

## 📥 2. Primary Source: `schemes.csv`

The authoritative base for PolicySetu is `schemes.csv`, exported directly from India's official National Scheme Portal ([myScheme.gov.in](https://www.myscheme.gov.in)).

- **Records Ingested**: **4,670**
- **Completeness**: Contains 27 rich administrative, demographic, operational, and statutory fields.
- **Uniqueness**: 100% unique slugs (zero duplicate slugs).
- **Text Integrity**: Preserves clean semicolon-delimited lists (`; `) for multi-clause eligibility criteria and application steps.
- **Flag**: All 4,670 records have `"is_supplementary": false`.

---

## ➕ 3. Supplementary Source: `updated_data.csv`

`updated_data.csv` represents an earlier scrape of the national scheme portal containing 3,400 raw rows.

- **Overlap Analysis**:
  - **3,318 schemes** overlapped by exact slug with `schemes.csv` and were **superseded by `schemes.csv`**.
  - **3 duplicate records (5 rows)** were dropped.
  - **79 schemes** were identified as completely unique to `updated_data.csv` and missing from `schemes.csv`.
- **Inclusion Strategy**:
  - All **79 unique schemes** (e.g. *Agriculture Infrastructure Fund*, *Jagananna Chedodu*, *Airavata Scheme*) have been ingested into the canonical dataset to achieve 100% catalog coverage.
  - Every supplementary record is explicitly flagged with `"is_supplementary": true`.
  - **Strict Honesty**: Missing metadata (such as state, department, or open dates) was preserved as `null` without inventing fictional data.

---

## 🧹 4. Duplicate Record Handling

1. **Within `schemes.csv`**:
   - Audited for exact duplicates and duplicate slugs.
   - Result: **0 duplicates**; all 4,670 slugs are distinct.
2. **Within `updated_data.csv`**:
   - Detected 3 exact duplicate records (5 rows):
     - `Establishment of Goat Unit (10 +1)` (slug: `eogu`) repeated 3 times.
     - `Valmiki Chhatravritti Yojana` (slug: `vcy`) repeated 2 times.
   - De-duplicated prior to matching, reducing rows from 3,400 to 3,397.
3. **Cross-Dataset Deduplication**:
   - 3,318 overlapping records were eliminated by prioritizing `schemes.csv`.
   - Result in canonical catalog: **0 duplicate slugs and 0 duplicate UUIDs across all 4,749 records**.

---

## 🔍 5. Matching Strategy

A 4-stage sequential matching pipeline was executed:

```
[updated_data.csv (3,397 deduped)]
           │
           ▼
[Stage 1: Exact Slug Match] ──────────► 3,318 matched ──► Superseded by schemes.csv
           │ (79 remaining)
           ▼
[Stage 2: Canonical URL Match] ────────► 0 additional matches
           │ (79 remaining)
           ▼
[Stage 3: Normalized Name Match] ──────► 0 additional matches
           │ (79 remaining)
           ▼
[Stage 4: Fuzzy Match Review Signal] ──► 40 candidates reviewed; 0 false merges
           │
           ▼
[Consolidated Supplementary: 79 Schemes]
```

- **Stage 1 (Exact Slug)**: Normalized lowercase stripped slugs matched 3,318 schemes.
- **Stage 2 (Canonical URL)**: Compared generated portal URLs (`https://www.myscheme.gov.in/schemes/<slug>`).
- **Stage 3 (Normalized Scheme Name)**: Normalized lowercase alphanumeric comparison on remaining 79 schemes yielded 0 exact matches.
- **Stage 4 (Fuzzy Match Review Signal)**:
  - SequenceMatcher identified 40 candidate pairs with similarity > 0.65.
  - Every candidate was reviewed and verified to be a **distinct operational scheme** (e.g. *Delhi Family Benefit Scheme* vs *National Family Benefit Scheme*; *Distribution of Gypsum* vs *Distribution of Pulses*).
  - In strict compliance with safety rules, **zero uncertain fuzzy matches were merged**.
  - All 40 signals are cataloged in [AI/data/interim/fuzzy_match_review.csv](file:///c:/Users/ozhad/Desktop/HackMatrix/PCCOE-HackMatrix/AI/data/interim/fuzzy_match_review.csv).

---

## ⚖ 6. Conflicts Resolved

| Conflict Type | Description | Resolution Applied |
| :--- | :--- | :--- |
| **Catalog Precedence** | 3,318 schemes existed in both `schemes.csv` and `updated_data.csv`. | `schemes.csv` was enforced as the sole authoritative source. All 3,318 duplicates from `updated_data.csv` were discarded. |
| **Formatting Degradation** | In `updated_data.csv`, eligibility sentences were merged without delimiters (`Clause A.Clause B`), whereas `schemes.csv` separated clauses with semicolons (`; `). | Preserved pristine delimited text from `schemes.csv` across all 3,318 overlapping records. |
| **Level Casing Inconsistency** | `schemes.csv` contained `'State/ UT'` (3,224 rows) and `'State'` (797 rows). | Normalized all state-level variations to canonical `'State'`. |
| **Category Comma Ambiguity** | Categories like `'Agriculture,Rural & Environment'` contain internal commas. | Categorized against the official 15-category taxonomy to avoid accidental splitting of compound category titles. |

---

## 📋 7. Fields Retained (Canonical Schema)

The canonical dataset contains 30 standardized fields:

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `string` | Deterministic UUIDv5 generated from canonical scheme URL |
| `slug` | `string` | Canonical unique scheme slug (e.g. `"108easuk"`) |
| `scheme_name` | `string` | Full official scheme title |
| `short_title` | `string \| null` | Abbreviated title or popular acronym |
| `level` | `string` | Jurisdiction level: `'Central'` or `'State'` |
| `state` | `string \| null` | State or UT name (null for Central schemes) |
| `ministry` | `string \| null` | Central Union Ministry |
| `department` | `string \| null` | Implementing administrative department |
| `beneficiary_type` | `string \| null` | Target entity (`'Individual'`, `'Family'`, `'Infra'`) |
| `target_beneficiaries`| `list[string]` | Array of demographic groups (`"Farmers"`, `"Women"`, `"Students"`) |
| `benefit_type` | `string \| null` | Modality (`'Cash'`, `'In Kind'`, `'Composite'`) |
| `categories` | `list[string]` | Primary sector taxonomy array |
| `sub_categories` | `list[string]` | Granular sector sub-categories array |
| `tags` | `list[string]` | Discoverability keyword tags array |
| `brief_description` | `string \| null` | Executive summary description |
| `detailed_description`| `string \| null`| Comprehensive operational scheme narrative |
| `benefits` | `string \| null` | Statutory entitlements, subsidy rates, or support provisions |
| `eligibility` | `string \| null` | Mandatory statutory eligibility conditions |
| `exclusions` | `string \| null` | Formal ineligibility / disqualification conditions |
| `application_mode` | `list[string]` | Delivery channels (`["Online"]`, `["Offline"]`, `["Online - via CSC"]`) |
| `application_process`| `string \| null`| Step-by-step procedural guidelines |
| `documents_required` | `string \| null`| Verification documentation checklist |
| `dbt_scheme` | `bool \| null` | Direct Benefit Transfer status (`true`, `false`, or `null`) |
| `faq_count` | `int` | Number of verified FAQs linked to this scheme |
| `source_url` | `string` | Official myScheme portal URL |
| `references` | `list[string]` | Array of official circulars, gazettes, and portal links |
| `scheme_open_date` | `string \| null`| Operational opening date (`YYYY-MM-DD`) |
| `scheme_close_date` | `string \| null`| Sunset / deadline date (`YYYY-MM-DD`) |
| `is_supplementary` | `bool` | `false` for primary schemes; `true` for 79 supplementary schemes |
| `provenance` | `struct / dict` | Source tracking metadata (`source_file`, `provider`, `confidence_tier`) |

---

## 🔄 8. Fields Normalized

1. **Whitespace & String Sanitization**:
   - Stripped leading/trailing whitespace across all text columns.
   - Collapsed internal redundant tabs and duplicate spaces while preserving paragraph breaks.
2. **List Delimiter Parsing**:
   - Semicolon-delimited strings in `categories`, `sub_categories`, `tags`, `target_beneficiaries`, `application_mode`, and `references` were transformed into typed arrays of clean strings (`list[string]`).
3. **Jurisdiction `level`**:
   - Consolidated `'State/ UT'` and `'State'` into a standardized `'State'`.
4. **Direct Benefit Transfer (`dbt_scheme`)**:
   - Cast string representations (`'True'`, `'False'`, `'Yes'`, `'No'`) to native boolean (`True`/`False`), keeping `None` for supplementary schemes.
5. **Deterministic UUIDv5**:
   - Generated using `uuid.uuid5(uuid.NAMESPACE_URL, source_url)`, guaranteeing immutable IDs across pipeline runs.

---

## 🗑 9. Fields Dropped and Rationale

| Dropped Field | Source File | Rationale |
| :--- | :--- | :--- |
| `Unnamed: 9` | `updated_data.csv` | **100% null (3,400 of 3,400 rows)**. Corrupt trailing comma artifact from CSV serialization. |
| `Unnamed: 0` | `indian govt (EN/HI).csv` | Raw index column artifact. |
| `details` (column name) | `updated_data.csv` | Remapped to `brief_description` and `detailed_description` for schema uniformity. |
| `application` (column name) | `updated_data.csv` | Remapped to `application_process`. |
| `documents` (column name) | `updated_data.csv` | Remapped to `documents_required`. |
| `schemeCategory` (column name) | `updated_data.csv` | Remapped and normalized into `categories`. |

---

## 🏷 10. Source & Provenance Strategy

Every record in the canonical dataset carries a structured `provenance` dictionary:

```json
{
  "source_file": "schemes.csv",
  "provider": "myScheme",
  "ingestion_method": "authoritative_primary",
  "confidence_tier": "authoritative"
}
```

For the 79 supplementary schemes:
```json
{
  "source_file": "updated_data.csv",
  "provider": "myScheme",
  "ingestion_method": "supplementary_unique_ingest",
  "confidence_tier": "supplementary"
}
```

This guarantees that downstream RAG pipelines, rule extractors, and end-user UIs can display verified trust badges distinguishing primary authoritative schemes from supplementary catalog entries.

---

## ⚠️ 11. Known Limitations

1. **State Sparsity in Supplementary Records**:
   - The 79 supplementary schemes from `updated_data.csv` did not contain a `state` column in their source. To uphold data integrity, state was set to `null` rather than guessing regional origin.
2. **High Sparsity in `exclusions` (86%)**:
   - Indian government schemes predominantly specify positive qualification criteria rather than formal negative disqualifications.
3. **Open / Close Dates**:
   - `scheme_close_date` is null for 98.8% of schemes. Most Indian welfare schemes operate as ongoing, open-ended entitlements without fixed sunset dates.
4. **FAQ Coverage**:
   - Linked FAQs exist for 4,647 schemes. The 79 supplementary schemes currently have `faq_count = 0`.
