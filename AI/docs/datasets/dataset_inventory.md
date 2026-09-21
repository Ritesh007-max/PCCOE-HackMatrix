# PolicySetu Dataset Inventory & Audit

This document provides a comprehensive inventory, statistical profiling, domain credibility assessment, and capability matrix for all datasets discovered in `AI/data/raw/`.

---

## 📊 High-Level Inventory Summary

| Dataset File Name | Format | Size (MB) | Records / Docs | Fields | Unique Schemes | Source Credibility | Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `schemes.csv` | CSV | 18.63 MB | 4,670 | 27 | 4,669 | **AUTHORITATIVE_SOURCE** | **PRIMARY** |
| `schemes_faqs.csv` | CSV | 13.95 MB | 51,435 | 5 | 4,646 | **AUTHORITATIVE_SOURCE** | **PRIMARY** |
| `updated_data.csv` | CSV | 12.26 MB | 3,400 | 11 | 3,397 | **SECONDARY_SOURCE** | **SUPPLEMENTARY** |
| `indian government schemes dataset english and hindi.csv` | CSV | 20.94 MB | 3,473 | 12 | 96 | **COMMUNITY_DATA** | **EVALUATION_ONLY** |
| `Indian_Government_Scheme_Eligibility_Dataset.csv` | CSV | 0.06 MB | 1,500 | 5 | 7 | **SYNTHETIC_DATA** | **DISCARD** |
| `archive (1).zip` | ZIP (TXT) | 2.16 MB | 1,524 | 3 | ~1,124 | **SECONDARY_SOURCE** | **RAG_DOCUMENT_SOURCE** |

**Total Raw Datasets**: 6  
**Total Records / Documents**: 65,502  
**Total Unique Schemes (Deduplicated Canonical Estimate)**: ~4,748  

---

## 🔍 Detailed Individual Dataset Audits

---

### 1. `schemes.csv`

#### Metadata & File Properties
- **Dataset Name**: National & State Schemes Canonical Catalog (`schemes.csv`)
- **File Name**: `schemes.csv`
- **File Type**: Comma Separated Values (CSV)
- **Size**: 19,535,968 bytes (~18.63 MB)
- **Number of Records (Rows)**: 4,670
- **Number of Fields (Columns)**: 27
- **Exact Duplicate Records**: 0
- **Source Credibility**: **AUTHORITATIVE_SOURCE** (Structured export from India's official National Scheme Portal - `myScheme.gov.in`)
- **Assigned Recommendation**: **PRIMARY**

#### Schema & Data Types
| Field Name | Data Type | Null Count | Null % | Semantic Role |
| :--- | :--- | :--- | :--- | :--- |
| `slug` | `string` | 0 | 0.0% | Primary Unique Identifier (URL slug) |
| `scheme_name` | `string` | 0 | 0.0% | Official Scheme Title |
| `short_title` | `string` | 0 | 0.0% | Abbreviated / Acronym Title |
| `level` | `string` | 0 | 0.0% | Jurisdiction Level (`Central` / `State`) |
| `state` | `string` | 649 | 13.9% | Governing State / UT (null for Central) |
| `ministry` | `string` | 4,021 | 86.1% | Nodal Ministry (null for State schemes) |
| `department` | `string` | 248 | 5.3% | Implementing Department |
| `beneficiary_type` | `string` | 45 | 1.0% | Beneficiary Target Type (e.g. Individual, Group) |
| `target_beneficiaries`| `string` | 56 | 1.2% | Target Demographic Cohorts |
| `benefit_type` | `string` | 0 | 0.0% | Modality of Benefit (`Cash`, `In Kind`, `Composite`) |
| `categories` | `string` | 0 | 0.0% | Primary Policy Sector Taxonomy |
| `sub_categories` | `string` | 436 | 9.3% | Granular Sector Tags |
| `tags` | `string` | 0 | 0.0% | Discoverability Keyword Tags |
| `brief_description` | `string` | 0 | 0.0% | Executive Overview / Pitch |
| `detailed_description`| `string` | 0 | 0.0% | Comprehensive Scheme Architecture |
| `benefits` | `string` | 263 | 5.6% | Financial Entitlements & Quantum |
| `eligibility` | `string` | 0 | 0.0% | Mandatory Criteria & Condition Rules |
| `exclusions` | `string` | 4,016 | 86.0% | Disqualification & Ineligibility Clauses |
| `application_mode` | `string` | 0 | 0.0% | Modality (`Online`, `Offline`, `Both`) |
| `application_process`| `string` | 263 | 5.6% | Procedural Application Steps |
| `documents_required` | `string` | 414 | 8.9% | Required Verification Documentation |
| `references` | `string` | 5 | 0.1% | Supporting Circulars & Portals |
| `scheme_open_date` | `string` | 3,620 | 77.5% | Launch / Application Opening Date |
| `scheme_close_date` | `string` | 4,614 | 98.8% | Application Deadline (most open-ended) |
| `dbt_scheme` | `string` | 0 | 0.0% | Direct Benefit Transfer Flag (`Yes` / `No`) |
| `faq_count` | `int64` | 0 | 0.0% | Number of Linked FAQs on myScheme |
| `source_url` | `string` | 0 | 0.0% | Official Portal Link (`https://www.myscheme.gov.in/schemes/<slug>`) |

#### Scheme Identification & Identifiers
- **Unique Scheme Count**: 4,669 (4,670 rows with 1 duplicate short title, distinct slugs).
- **Primary Key Candidates**: `slug` (100% unique, non-null URL slug) and `source_url`.
- **URL / Source Fields**: `source_url`, `references`.
- **Language**: English (Latin script) with authentic Indian civic terminology.
- **License / Provenance**: Open Government Data (OGD) / myScheme public domain catalog.
- **Approximate Date / Version**: Active catalog through 2023-2024. Contains operational launch dates up to 2024.

#### Sample Record
```json
{
  "slug": "108easuk",
  "scheme_name": "108, Emergency Ambulance Service - Uttarakhand",
  "short_title": "108 EASUK",
  "level": "State",
  "state": "Uttarakhand",
  "department": "Department Of Medical Health And Family Welfare",
  "benefit_type": "In Kind",
  "categories": "Health & Wellness",
  "eligibility": "1. Any person who is a resident of Uttarakhand.; 2. Any person who is in need of emergency medical care.",
  "benefits": "Free ambulance service equipped with life support equipment and trained emergency medical technicians (EMTs).",
  "application_mode": "Offline",
  "documents_required": "No documents are required at the time of availing emergency service.",
  "dbt_scheme": "No",
  "source_url": "https://www.myscheme.gov.in/schemes/108easuk"
}
```

#### Privacy & PII
- No citizen PII. Contains department contact helplines and public nodal official emails.

#### Data Quality Issues
- High null percentage in `exclusions` (86.0%) and `ministry` (86.1%, normal for State-level schemes).
- Semi-structured lists inside text fields use `; ` (semicolon and space) delimiters which must be tokenized during ingestion.

#### Evaluation Against 14 Core Capabilities
- **Scheme Discovery**: EXCELLENT — 4,670 schemes covering 36 States/UTs and Central ministries.
- **Semantic Search**: EXCELLENT — Rich textual descriptions, short titles, and tags.
- **RAG**: EXCELLENT — Discrete fields enable focused prompt context assembly.
- **Eligibility Rule Extraction**: EXCELLENT — Clean delimited criteria sentences ideal for AST/DSL rule parsing.
- **Eligibility Testing**: GOOD — Provides statutory ground truth rules for test profile synthesis.
- **Benefit Information**: EXCELLENT — Dedicated monetary and service entitlement breakdown.
- **Required Documents**: EXCELLENT — Exhaustive documentation checklist for 91.1% of schemes.
- **Application Process**: EXCELLENT — Sequential procedural guidelines and channel mode.
- **Applicant Profile Matching**: EXCELLENT — Contains state, level, beneficiary type, and category filters.
- **Multilingual NLP**: POOR — English only.
- **FAQ/Question Answering**: GOOD — Contains `faq_count`, correlates 1:1 with `schemes_faqs.csv`.
- **ML Training**: HIGH — Superb corpus for classification, NER, and rule parsing.
- **Evaluation/Benchmarking**: EXCELLENT — Gold standard catalog for retrieval recall.
- **Source Evidence**: AUTHORITATIVE_SOURCE — Official Government of India portal data.

---

### 2. `schemes_faqs.csv`

#### Metadata & File Properties
- **Dataset Name**: National Scheme FAQ Knowledge Base (`schemes_faqs.csv`)
- **File Name**: `schemes_faqs.csv`
- **File Type**: CSV
- **Size**: 14,627,678 bytes (~13.95 MB)
- **Number of Records (Rows)**: 51,435
- **Number of Fields (Columns)**: 5
- **Exact Duplicate Records**: 0
- **Source Credibility**: **AUTHORITATIVE_SOURCE** (Official FAQs from myScheme.gov.in)
- **Assigned Recommendation**: **PRIMARY**

#### Schema & Data Types
| Field Name | Data Type | Null Count | Null % | Semantic Role |
| :--- | :--- | :--- | :--- | :--- |
| `scheme_slug` | `string` | 0 | 0.0% | Foreign Key matching `schemes.csv` (`slug`) |
| `scheme_name` | `string` | 0 | 0.0% | Scheme Name Entity |
| `faq_number` | `int64` | 0 | 0.0% | FAQ Ordinal Sequence Number |
| `question` | `string` | 0 | 0.0% | Citizen Query / Question |
| `answer` | `string` | 0 | 0.0% | Grounded Official Answer |

#### Scheme Identification & Linkage
- **Unique Scheme Count**: 4,646 schemes.
- **Linkage**: Exactly 4,646 of 4,646 schemes (100%) match entries in `schemes.csv`.
- **Average FAQs Per Scheme**: 11.07 questions per scheme.
- **Language**: English.
- **License**: Public Domain Government Information (myScheme portal).

#### Sample Record
```json
{
  "scheme_slug": "108easuk",
  "scheme_name": "108, Emergency Ambulance Service - Uttarakhand",
  "faq_number": 1,
  "question": "What is the main objective of the scheme?",
  "answer": "Its main objective is to provide immediate medical assistance by ensuring rapid transportation to hospitals and delivering essential first aid."
}
```

#### Evaluation Against 14 Core Capabilities
- **Scheme Discovery**: GOOD — Secondary discovery via natural language inquiry.
- **Semantic Search**: EXCELLENT — Matches natural search query formulations.
- **RAG**: OUTSTANDING — 51k clean Q&A pairs make ideal micro-chunks for vector indexing.
- **Eligibility Rule Extraction**: MODERATE — Resolves nuanced boundary conditions and edge cases.
- **Eligibility Testing**: GOOD — Natural test cases for question-answering evaluation.
- **Benefit Information**: GOOD — Explains disbursement modes and special provisions.
- **Required Documents**: MODERATE — Clarifies document alternatives and attestations.
- **Application Process**: GOOD — Answers practical applicant hurdles.
- **Applicant Profile Matching**: MODERATE — Implicit contextual matching.
- **Multilingual NLP**: POOR — English only.
- **FAQ/Question Answering**: OUTSTANDING — Authoritative national QA dataset.
- **ML Training**: EXCELLENT — Fine-tuning retrieval, embedding models, and QA rerankers.
- **Evaluation/Benchmarking**: OUTSTANDING — Gold standard benchmark for RAG retrieval hit rate and MRR.
- **Source Evidence**: AUTHORITATIVE_SOURCE — Official government answers.

---

### 3. `updated_data.csv`

#### Metadata & File Properties
- **Dataset Name**: Scheme Catalog Export Subset (`updated_data.csv`)
- **File Name**: `updated_data.csv`
- **File Type**: CSV
- **Size**: 12,855,490 bytes (~12.26 MB)
- **Number of Records (Rows)**: 3,400
- **Number of Fields (Columns)**: 11
- **Exact Duplicate Records**: 3 (affecting 5 rows: `eogu` x3, `vcy` x2)
- **Source Credibility**: **SECONDARY_SOURCE** (Partial scrape/export of myScheme)
- **Assigned Recommendation**: **SUPPLEMENTARY**

#### Schema & Data Types
| Field Name | Data Type | Null Count | Null % | Semantic Role |
| :--- | :--- | :--- | :--- | :--- |
| `scheme_name` | `string` | 0 | 0.0% | Scheme Name Entity |
| `slug` | `string` | 0 | 0.0% | Identifier Slug |
| `details` | `string` | 0 | 0.0% | Overview Narrative |
| `benefits` | `string` | 0 | 0.0% | Benefits Description |
| `eligibility` | `string` | 0 | 0.0% | Eligibility Criteria |
| `application` | `string` | 2 | 0.06% | Application Process |
| `documents` | `string` | 11 | 0.32% | Required Documents |
| `level` | `string` | 0 | 0.0% | Jurisdiction Level (`Central` / `State`) |
| `schemeCategory` | `string` | 0 | 0.0% | Category String |
| `Unnamed: 9` | `float64` | 3,400 | 100.0% | **Corrupted Empty Column Artifact** |
| `tags` | `string` | 29 | 0.85% | Keyword Tags |

#### Data Quality Issues & Critical Observations
- `Unnamed: 9` is 100% null (3,400 of 3,400 rows).
- 3 duplicate rows present.
- Text formatting degradation: bullet delimiters (`; `) present in `schemes.csv` were stripped or merged during scraping, leading to concatenated sentences without whitespace.
- Lacks vital administrative fields (`state`, `ministry`, `department`, `beneficiary_type`, `dbt_scheme`, `source_url`).
- **Valuable Unique Assets**: Contains **79 distinct schemes** not present in `schemes.csv` (e.g. *Agriculture Infrastructure Fund (aif)*, *Jagananna Chedodu (jc)*, *Airavata Scheme*).

#### Evaluation Against 14 Core Capabilities
- **Scheme Discovery**: MODERATE — 3,400 schemes; 79 supplementary unique schemes.
- **Semantic Search**: MODERATE — Adequate text, but less metadata than `schemes.csv`.
- **RAG**: MODERATE — Viable fallback for the 79 unique schemes.
- **Eligibility Rule Extraction**: MODERATE — Incomplete formatting.
- **Eligibility Testing / Benefit / Documents**: MODERATE — Subsumed by `schemes.csv`.
- **Source Evidence**: SECONDARY_SOURCE — Secondary scraping artifacts.

---

### 4. `indian government schemes dataset english and hindi.csv`

#### Metadata & File Properties
- **Dataset Name**: Bilingual Hindi-English Scheme QA Dataset
- **File Name**: `indian government schemes dataset english and hindi.csv`
- **File Type**: CSV
- **Size**: 21,952,283 bytes (~20.94 MB)
- **Number of Records (Rows)**: 3,473
- **Number of Fields (Columns)**: 12
- **Exact Duplicate Records**: 0
- **Source Credibility**: **COMMUNITY_DATA** (Community curated educational/civic dataset)
- **Assigned Recommendation**: **EVALUATION_ONLY**

#### Schema & Data Types
| Field Name | Data Type | Null Count | Null % | Semantic Role |
| :--- | :--- | :--- | :--- | :--- |
| `Unnamed: 0` | `int64` | 0 | 0.0% | Index Artifact Column |
| `question` | `string` | 0 | 0.0% | Question in **Hindi (Devanagari script)** |
| `question_english` | `string` | 0 | 0.0% | Question in **English (Latin script)** |
| `answer` | `string` | 0 | 0.0% | Answer in **Hindi (Devanagari script)** |
| `answer_english` | `string` | 0 | 0.0% | Answer in **English (Latin script)** |
| `category` | `string` | 0 | 0.0% | Policy Domain (`Agriculture`, `Health`, `Finance`) |
| `difficulty_level` | `string` | 0 | 0.0% | Difficulty Bracket (`Easy`, `Medium`, `Hard`) |
| `launched_year` | `int64` | 0 | 0.0% | Scheme Launch Year (1959 - 2023) |
| `official_website` | `string` | 0 | 0.0% | Official Portal URL |
| `scheme_name` | `string` | 0 | 0.0% | Landmark Scheme Name |
| `state_or_central` | `string` | 0 | 0.0% | Scheme Scope (`Central`, `State`) |
| `target_beneficiary` | `string` | 0 | 0.0% | Target Demographic Group |

#### Scheme Coverage & Linguistic Value
- **Unique Schemes**: 96 major landmark national schemes (e.g. *Digital India*, *PM Kisan*, *Ayushman Bharat*, *PMMVY*).
- **Linguistic Coverage**: 100% paired English-Hindi text. Provides 3,473 authentic Hindi citizen queries with Devanagari answers.
- **Launch Year Range**: 1959 to 2023.

#### Evaluation Against 14 Core Capabilities
- **Scheme Discovery**: LOW — Limited to 96 flagship schemes.
- **Semantic Search**: GOOD — Cross-lingual retrieval queries.
- **RAG**: GOOD — Multilingual answer generation benchmark.
- **Eligibility Rule Extraction**: LOW — High-level explanatory answers, not structured rule specs.
- **Multilingual NLP**: OUTSTANDING — Indispensable for testing Devanagari query handling and Indian language RAG.
- **FAQ/Question Answering**: EXCELLENT — High quality paired QA.
- **Evaluation/Benchmarking**: OUTSTANDING — Gold standard benchmark for Multilingual QA evaluation.
- **Source Evidence**: COMMUNITY_DATA — Community educational curation.

---

### 5. `Indian_Government_Scheme_Eligibility_Dataset.csv`

#### Metadata & File Properties
- **Dataset Name**: Synthetic Eligibility Classification Toy Dataset
- **File Name**: `Indian_Government_Scheme_Eligibility_Dataset.csv`
- **File Type**: CSV
- **Size**: 63,138 bytes (~61.6 KB)
- **Number of Records (Rows)**: 1,500
- **Number of Fields (Columns)**: 5
- **Exact Duplicate Records**: 0
- **Source Credibility**: **SYNTHETIC_DATA** (Artificial tabular dataset for toy ML tutorials)
- **Assigned Recommendation**: **DISCARD**

#### Schema & Data Types
| Field Name | Data Type | Null Count | Null % | Semantic Role |
| :--- | :--- | :--- | :--- | :--- |
| `Age` | `int64` | 0 | 0.0% | Citizen Age (Range: 18 - 80) |
| `Annual_Income_INR` | `int64` | 0 | 0.0% | Annual Income (Range: ₹50,245 - ₹1,199,206) |
| `State` | `string` | 0 | 0.0% | State (9 states only) |
| `Category` | `string` | 0 | 0.0% | Social Category (`General`, `OBC`, `SC`, `ST`, `EWS`) |
| `Eligible_Scheme` | `string` | 0 | 0.0% | Target Scheme Label (7 schemes only) |

#### Critical Domain Validity Flaw (Statutory Rule Violation)
- **Target Distribution**:
  - `Atal Pension Yojana`: 568
  - `Mudra Loan`: 205
  - `National Scholarship`: 197
  - `Ayushman Bharat`: 165
  - `PM Kisan`: 160
  - `PM Awas Yojana`: 129
  - `Stand Up India`: 76
- **Critical Violation Detected**:
  - Row 1: `Age = 70, Annual_Income_INR = 1,102,158, Eligible_Scheme = Atal Pension Yojana`.
  - **Statutory Law**: Under Government of India regulations (PFRDA), the *Atal Pension Yojana* mandates an **entry age strictly between 18 and 40 years**, and income taxpayers are completely excluded. Assigning APY eligibility to a 70-year-old with ₹11 Lakhs annual income is legally invalid.
  - Similar severe contradictions occur with PM Kisan (which excludes institutional landholders and high-income taxpayers) and National Scholarship (awarded to 37-year-olds with near million-rupee incomes).
- **Conclusion**: This synthetic dataset must be **DISCARDED** from production eligibility verification, rule testing, and RAG pipelines to prevent severe hallucinations and false positives.

---

### 6. `archive (1).zip`

#### Metadata & File Properties
- **Dataset Name**: State & Central Scheme Document Text Corpus
- **File Name**: `archive (1).zip`
- **File Type**: ZIP Archive containing plain text documents (`.txt`)
- **Size**: 2,260,285 bytes (~2.16 MB compressed)
- **Number of Contained Files**: 1,524 files
- **Directory Hierarchy**: 29 folders (28 State folders + 1 Central folder)
- **Source Credibility**: **SECONDARY_SOURCE** (Scraped portal and news articles)
- **Assigned Recommendation**: **RAG_DOCUMENT_SOURCE**

#### Directory Breakdown (Top Folders)
| Directory Name | File Count | Description |
| :--- | :--- | :--- |
| `central/` | 205 | Central Government Scheme articles |
| `haryana/` | 120 | Haryana State Scheme documents |
| `odisha/` | 105 | Odisha State Scheme documents |
| `delhi/` | 101 | Delhi NCT Scheme documents |
| `uttar-pradesh/` | 94 | Uttar Pradesh Scheme documents |
| `andhra-pradesh/`| 82 | Andhra Pradesh Scheme documents |
| `maharashtra/` | 80 | Maharashtra Scheme documents |
| `madhya-pradesh/`| 74 | Madhya Pradesh Scheme documents |
| `karnataka/` | 55 | Karnataka Scheme documents |
| `rajasthan/` | 53 | Rajasthan Scheme documents |
| *Other 19 States* | 455 | Remaining State & UT folders |

#### Content Characteristics
- Narrative prose describing schemes, objectives, application procedures, and beneficiary benefits.
- Some files contain web-scraping noise (e.g. "Table of Contents", navigation breadcrumbs, and journalist attribution).
- Serves as a supplementary source for unstructured document chunking and long-context RAG evaluation.
