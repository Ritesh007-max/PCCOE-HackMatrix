# PolicySetu Knowledge Base Specification

## 1. Authoritative Datasets & Explicit Source Tiers

To prevent conflicting policy claims and maintain auditability, knowledge sources are categorized into explicit tiers:

| Tier Identifier | Source Dataset | Record Count | Authority Level | Description |
| :--- | :--- | :--- | :--- | :--- |
| `PRIMARY_SCHEME` | `schemes.csv` -> `schemes_canonical.parquet` | 4,749 | Primary Statutory | Canonical scheme details; statutory eligibility, benefits, application mode, and criteria. |
| `PRIMARY_FAQ` | `schemes_faqs.csv` | 51,435 | Primary FAQ | Official administrative FAQ question/answer pairs linked via `scheme_slug`. |
| `SUPPLEMENTARY_SCHEME` | `updated_data.csv` | 79 distinct | Supplementary | Supplementary schemes not found in primary scheme set; never overrides primary schemes. |
| `EVALUATION_ONLY` | `indian government schemes dataset english and hindi.csv` | ~5,000 | Benchmark Only | Bilingual parallel Q&A used strictly for evaluation and language testing. |
| `RAG_ARCHIVE` | `archive (1).zip` | 1,524 files | Supporting Text | Long-form state archive documents providing supplementary narrative context. |

> [!IMPORTANT]
> **Source Precedence Invariant**:
> `PRIMARY_SCHEME` authority originates from `schemes.csv` and is consolidated into `schemes_canonical.parquet`. Supplementary sources must **never** overwrite canonical scheme thresholds or rules.

---

## 2. Chunk Representation & Metadata Specification

Every knowledge chunk conforms to the `RAGDocument` data contract:

```json
{
  "id": "chk_apy_elig_a1b2c3d4e5f6",
  "scheme_id": "sch_1001",
  "scheme_slug": "apy",
  "scheme_name": "Atal Pension Yojana",
  "content": "Scheme: Atal Pension Yojana\nSection: Eligibility Criteria\n\nApplicant must be a citizen of India between 18 and 40 years of age having an active savings bank account...",
  "content_type": "eligibility",
  "source_dataset": "schemes.csv",
  "source_tier": "PRIMARY_SCHEME",
  "source_url": "https://www.myscheme.gov.in/schemes/apy",
  "source_document": "schemes_canonical.parquet",
  "source_page": null,
  "section": "Eligibility Criteria",
  "state": null,
  "ministry": "Ministry of Finance",
  "department": "Department of Financial Services",
  "category": "Social Security",
  "beneficiary_type": "Citizens",
  "language": "en",
  "faq_id": null,
  "created_at": "2026-09-21T12:00:00Z",
  "text_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "metadata": {
    "section_chunk_index": 0,
    "total_section_chunks": 1,
    "dbt_scheme": true
  }
}
```

---

## 3. Section-Aware Chunking Methodology

Text is segmented along natural statutory boundaries:
1. **`scheme_overview`**: Combines brief and detailed introductory descriptions.
2. **`eligibility`**: Preserves complete legal criteria without splitting mid-condition unless text exceeds `chunk_size` (600 characters).
3. **`exclusions`**: Explicit exclusion clauses.
4. **`benefits`**: Entitlements, cash transfers, insurance cover, and subsidies.
5. **`application_process`**: Procedural steps for citizen application.
6. **`documents_required`**: Mandatory supporting documents.
7. **`faq`**: Atomic question-and-answer pairs; question and answer are never severed.

---

## 4. Deterministic Hashing & Stable IDs

Chunk identifiers are generated deterministically using SHA-256:
$$\text{Chunk ID} = \text{generate\_stable\_chunk\_id}(\text{slug}, \text{content\_type}, \text{section}, \text{index})$$
Re-running the ingestion pipeline on identical raw datasets yields **identical** chunk IDs, preventing vector store churn and cache invalidation.
