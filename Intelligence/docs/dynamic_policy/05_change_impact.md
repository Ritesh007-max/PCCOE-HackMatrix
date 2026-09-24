# FIN Phase 12: Change Classification & Impact Analysis

## 1. The 15 Semantic Change Impact Types

When a live synchronization run detects differences between candidate data and the active baseline, changes are tagged with fine-grained impact classifications:

| Impact Type | Description | System Response |
|---|---|---|
| `NO_CHANGE` | Source content identical to active baseline | Bypasses unnecessary processing |
| `SCHEME_ADDED` | New scheme discovered in source | Stages scheme, extracts rules, adds RAG chunks |
| `SCHEME_REMOVED` | Scheme deleted or withdrawn | Evaluates deletion threshold gate; deactivates RAG chunks |
| `SCHEME_UPDATED` | Existing scheme attributes modified | Triggers detailed field-level diff inspection |
| `ELIGIBILITY_CHANGED` | Scheme eligibility text or criteria altered | Triggers `RuleImpactAnalyzer` for statutory evaluation |
| `BENEFIT_CHANGED` | Benefit amount or formula changed | Updates benefit calculation rules; marks benefit recompile |
| `DOCUMENT_REQUIREMENT_CHANGED` | Required document list changed | Updates application readiness evaluator requirements |
| `APPLICATION_STEP_CHANGED` | Application workflow steps altered | Updates guidance and next action templates |
| `DEADLINE_CHANGED` | Application submission window changed | Updates temporal validity filters |
| `SOURCE_URL_CHANGED` | Government portal link updated | Re-runs strict URL allowlist validation |
| `METADATA_CHANGED` | Ministry, department, or tags updated | Updates catalog filtering and search facets |
| `FAQ_CHANGED` | FAQ questions or answers updated | Triggers incremental RAG chunk update only |
| `SUPPLEMENTARY_ONLY_CHANGE` | Update originates from HF/Supplementary feed | Restricted to RAG; barred from statutory rules |
| `RULE_AFFECTING_CHANGE` | Core deterministic eligibility rule altered | Sets `RULE_RECOMPILE_REQUIRED = True` |
| `CONFLICT_DETECTED` | Incompatible values between sources | Records in `conflicts.json`; retains primary statutory value |

---

## 2. Deterministic Rule-Impact Detection

Recompiling statutory rule ASTs across 4,700+ schemes for every typo or FAQ tweak is inefficient and risky. The `RuleImpactAnalyzer` isolates whether a change genuinely affects applicant fact logic.

### Statutory Constraint Fields
A scheme modification is flagged with `RULE_RECOMPILE_REQUIRED = True` if and only if any of the following fields are modified:
- `annual_family_income` / `family_income` / `income_limit`
- `age` / `age_min` / `age_max`
- `gender`
- `state` / `domicile` / `residence_state`
- `social_category` / `caste` (SC, ST, OBC, General)
- `disability` / `disability_percentage` / `pwd`
- `bpl` / `bpl_status` / `ration_card`
- `taxpayer` / `income_tax_payee`
- `occupation` / `farmer_type` / `artisan`
- `land_ownership` / `cultivable_land_hectares`
- `residency_duration` / `years_of_residence`

If a change only affects `brief_description`, `department`, `tags`, or `faq_content`, `RULE_RECOMPILE_REQUIRED` remains `False`, eliminating unnecessary compiler execution.

---

## 3. Incremental RAG Impact Analysis

For semantic search and Hybrid RAG retrieval, updates are processed incrementally rather than rebuilding the 63,000+ chunk index:

1. **ADD**: New chunks are generated, embedded, and appended to the FAISS index and BM25 corpus.
2. **UPDATE**: Existing chunks matching the scheme slug are soft-deleted/deactivated, and newly embedded chunks are inserted with updated version metadata.
3. **DELETE / DEACTIVATE**: Removed schemes have their corresponding chunk IDs removed from active retrieval filters, guaranteeing that no stale chunks remain retrievable.
