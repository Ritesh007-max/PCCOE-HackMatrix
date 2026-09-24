# FIN Rule Extraction Guidelines & Methodology

This document outlines the extraction principles, pattern definitions, safety invariants, and quality-control protocols for transforming raw statutory policy text into formal FIN condition rules.

---

## 🧭 1. Core Extraction Principles

### The Conservative Extraction Invariant
When converting legal eligibility text into machine-readable rules:
> **"Never guess an operator, threshold, or applicant field. If a clause contains qualitative, ambiguous, or discretionary legal phrasing, it must be flagged as `UNSTRUCTURED_REQUIRES_LLM_OR_MANUAL_REVIEW`."**

- **Deterministic rules must be mathematically exact**: e.g., *"Age must be between 18 and 40 years"* -> `field: "age", op: "between", val: {min: 18, max: 40}`.
- **Narrative context must not be forced into false simplicity**: e.g., *"Applicant must be in indigent circumstances as certified by the Village Administrative Officer"* -> Do NOT convert to `annual_income <= 50000`. Flag as `unstructured_condition` requiring manual verification.

---

## 👤 2. Target Canonical Applicant Profile Fields

All deterministic rules must evaluate against standardized applicant profile attributes. Below is the authoritative dictionary of canonical applicant fields:

| Field Name | Type | Valid Values / Units | Description |
| :--- | :--- | :--- | :--- |
| `age` | `numeric` | Integer (Years) | Chronological age of applicant |
| `gender` | `string` | `"Male"`, `"Female"`, `"Transgender"` | Legal gender identity |
| `state` | `string` | Indian State / UT Name | State of permanent domicile |
| `is_permanent_resident`| `boolean`| `true` / `false` | Verified resident / domicile status |
| `residency_years` | `numeric` | Integer (Years) | Continuous years of residence |
| `annual_family_income` | `numeric` | Float (INR) | Total gross annual household income |
| `bpl_card_holder` | `boolean`| `true` / `false` | Holds active Below Poverty Line card |
| `social_category` | `string` | `"General"`, `"OBC"`, `"SC"`, `"ST"`, `"EWS"` | Recognized constitutional category |
| `is_minority` | `boolean`| `true` / `false` | Member of notified minority community |
| `is_disabled` | `boolean`| `true` / `false` | Holds Person with Disability (PwD) certificate |
| `disability_percentage`| `numeric`| Float (0.0 - 100.0) | Benchmarked disability percentage |
| `is_student` | `boolean`| `true` / `false` | Currently enrolled in education |
| `enrolled_class` | `string` | e.g. `"Class 9"`, `"11th"`, `"Undergraduate"` | Academic grade / tier |
| `school_attendance_pct` | `numeric`| Float (0.0 - 100.0) | Attendance percentage in school |
| `occupation` | `string` | e.g. `"Farmer"`, `"Street Vendor"`, `"Weaver"` | Primary livelihood occupation |
| `owns_cultivable_land` | `boolean`| `true` / `false` | Holds title to agricultural land |
| `landholding_hectares` | `numeric`| Float (Hectares) | Total cultivable land acreage |
| `has_bank_account` | `boolean`| `true` / `false` | Active Aadhaar-linked bank account |
| `is_taxpayer` | `boolean`| `true` / `false` | Filed Income Tax in preceding AY |
| `is_govt_employee` | `boolean`| `true` / `false` | Regular govt or PSU employee |
| `monthly_pension_amount`| `numeric`| Float (INR/month) | Government pension received |
| `has_pucca_house` | `boolean`| `true` / `false` | Owns all-weather concrete house |

---

## 🛠 3. Pattern Recognition & Extraction Rules

### 1. Age Extraction
- **Range / Bracket**:
  - Pattern: `(?:between|age\s+group\s+of)\s+(\d{1,2})\s*(?:to|and|-)\s*(\d{1,2})\s*years?`
  - Mapping: `field: "age", op: "between", val: {min: X, max: Y}, unit: "years"`
- **Minimum Age**:
  - Pattern: `(?:above|at\s+least|minimum\s+age\s+of)\s+(\d{1,2})\s*years?`
  - Mapping: `field: "age", op: ">=", val: X, unit: "years"`
- **Maximum Age**:
  - Pattern: `(?:not\s+exceeding|below|up\s+to|maximum\s+age\s+of)\s+(\d{1,2})\s*years?`
  - Mapping: `field: "age", op: "<=", val: X, unit: "years"`

### 2. Income Extraction
- **Notations**:
  - Raw texts use currency variations: `₹2,50,000`, `Rs. 2.5 Lakh`, `INR 1,00,000`, `2.50 lac`.
  - Multiplier conversion:
    - `"lakh"` / `"lac"` -> Multiply by `100,000`
    - `"crore"` -> Multiply by `10,000,000`
- **Pattern**: `(?:family\s+income|annual\s+income|income).*?(?:not\s+exceed|below|less\s+than|up\s+to)\s*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)\s*(lakh|lac|crore)?`
- **Mapping**: `field: "annual_family_income", op: "<=", val: converted_amount, unit: "INR"`

### 3. State & Domicile Extraction
- **Pattern**: `(?:resident|native|domicile|permanent resident)\s+(?:of|in)\s+(?:the\s+)?(?:state\s+of\s+)?([A-Za-z\s&]+)`
- Cross-reference matched name against the 36 standard Indian States and UTs.
- **Mapping**: `field: "state", op: "=", val: normalized_state_name`

### 4. Gender & Demographic Extraction
- **Female / Women**:
  - Keywords: `only female`, `women only`, `pregnant women`, `lactating mothers`, `girl child`.
  - **Mapping**: `field: "gender", op: "=", val: "Female"`

### 5. Exclusion Extractions
- When parsing `exclusions` or clauses starting with *"The following are not eligible"*:
  - Income Tax: `field: "is_taxpayer", op: "is_false", val: false`
  - Government Employee: `field: "is_govt_employee", op: "is_false", val: false`
  - Existing Beneficiary: `field: "already_benefited_scheme_x", op: "is_false", val: false`

---

## 🎯 4. Confidence Scoring Matrix

Every candidate rule must be assigned an explicit `confidence` score:

| Score | Category | Criteria |
| :--- | :--- | :--- |
| **1.0** | `VERIFIED_DETERMINISTIC` | Unambiguous numeric threshold, explicit boolean state, or recognized Indian State name. |
| **0.90 - 0.95** | `HEURISTIC_PARSED` | Clear rule with minor contextual interpretation (e.g. converting "2.5 Lakh" to 250,000; inferring student status from attendance rules). |
| **0.70 - 0.85** | `CONDITIONAL_BRANCH` | Contextual rule that depends on prior condition or sub-category selection. |
| **0.50** | `UNSTRUCTURED_REQUIRES_LLM_OR_MANUAL_REVIEW` | Narrative criteria, subjective guidelines, or complex clauses without clean numeric operators. |

---

## 🧪 5. Quality Control & Golden Set Validation

1. **Self-Validation Against JSON Schema**:
   - Every extracted rule set must pass validation against `rule_schema.json`.
2. **Deterministic Round-Trip Testing**:
   - For every deterministic rule, synthesize two edge-case profile inputs:
     - `Input PASS`: Satisfies threshold (`age = 25` for range 18-40).
     - `Input FAIL`: Violates threshold (`age = 45` for range 18-40).
   - Assert that the rule engine evaluates `Input PASS -> PASS` and `Input FAIL -> FAIL`.
3. **Audit Trail Verification**:
   - Confirm that `raw_text` matches character-for-character with an excerpt from the canonical dataset, preserving statutory citation integrity.
