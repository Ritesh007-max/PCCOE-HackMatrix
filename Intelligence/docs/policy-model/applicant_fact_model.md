# FIN Canonical Applicant Fact Model

## 1. Overview & Architecture

The **Applicant Fact Layer** serves as the canonical boundary between unstructured or semi-structured extraction (document parsers, OCR, form inputs, NLP extraction) and the deterministic FIN rule evaluation engine.

```
+------------------------------------+
| Document / Text Extraction Layer   | (Aadhaar, ITR, Domicile, Form)
+------------------------------------+
                  |
                  v
+------------------------------------+
| Applicant Fact & Provenance Model  | (Raw Text, Spans, Confidence, Provenance)
+------------------------------------+
                  |
                  v
+------------------------------------+
| Normalization & Domain Validators  | (INR, Lakh/Crore, State, Age, Category)
+------------------------------------+
                  |
                  v
+------------------------------------+
| Multi-Document Evidence Registry   | (Conflict Detection: Discordant -> CONFLICTED)
+------------------------------------+
                  |
                  v
+------------------------------------+
| Deterministic Eligibility Engine   | (PASS / FAIL / UNKNOWN / REVIEW)
+------------------------------------+
```

### Core Invariants
1. **Verbatim Preservation**: The original extracted text and span are preserved character-for-character.
2. **Conservative Parsing**: Missing values are **never invented** and remain `UNKNOWN`.
3. **Physical Domain Validation**: Impossible domain values (e.g. age < 0 or > 120, negative income, negative landholding, percentage > 100) are strictly rejected.
4. **Deterministic Integrity**: Unverified or contradictory facts must never be converted into `PASS`.

---

## 2. Canonical Applicant Profile Dictionary

All applicant facts map to an authoritative dictionary of canonical fields:

| Field Name | Data Type | Canonical Values / Unit | Physical Bounds | Description |
| :--- | :--- | :--- | :--- | :--- |
| `age` | `numeric` | Integer (Years) | `0 <= age <= 120` | Chronological age in completed years |
| `gender` | `string` | `"Male"`, `"Female"`, `"Transgender"` | Allowed set | Legal gender identity |
| `state` | `string` | Standard 36 Indian States/UTs | Official entity | Permanent domicile state |
| `is_permanent_resident` | `boolean` | `true` / `false` | Boolean | Holds domicile certificate |
| `residency_years` | `numeric` | Float (Years) | `0 <= years <= 120` | Continuous years of residence |
| `annual_family_income` | `numeric` | Float (INR) | `>= 0` | Gross household income per annum |
| `bpl_card_holder` | `boolean` | `true` / `false` | Boolean | Active Below Poverty Line card |
| `social_category` | `string` | `"General"`, `"OBC"`, `"SC"`, `"ST"`, `"EWS"` | Allowed set | Constitutional caste/community category |
| `is_minority` | `boolean` | `true` / `false` | Boolean | Notified religious minority member |
| `is_disabled` | `boolean` | `true` / `false` | Boolean | PwD certificate holder |
| `disability_percentage` | `numeric` | Float (%) | `0.0 <= pct <= 100.0` | Certified disability percentage |
| `is_student` | `boolean` | `true` / `false` | Boolean | Enrolled in recognized educational institution |
| `enrolled_class` | `string` | Standard class title | String | Current academic grade / tier |
| `school_attendance_pct` | `numeric` | Float (%) | `0.0 <= pct <= 100.0` | Certified institutional attendance |
| `occupation` | `string` | Standard occupation title | String | Primary livelihood classification |
| `owns_cultivable_land` | `boolean` | `true` / `false` | Boolean | Holds title to cultivable agricultural land |
| `landholding_hectares` | `numeric` | Float (Hectares) | `>= 0.0` | Cultivable land area in hectares |
| `has_bank_account` | `boolean` | `true` / `false` | Boolean | Aadhaar-linked active bank account |
| `is_taxpayer` | `boolean` | `true` / `false` | Boolean | Filed Income Tax in preceding AY |
| `is_govt_employee` | `boolean` | `true` / `false` | Boolean | Regular government or PSU employee |
| `monthly_pension_amount`| `numeric` | Float (INR/month) | `>= 0` | Monthly government pension received |
| `has_pucca_house` | `boolean` | `true` / `false` | Boolean | Owns permanent all-weather house |

---

## 3. Atomic Applicant Fact Representation

Every applicant fact supports 10 canonical attributes:

```python
@dataclass
class ApplicantFact:
    field: str                              # Canonical or custom field key
    value: Any                              # Raw extracted/stated value
    normalized_value: Any                   # Standardized typed value (None if unknown)
    data_type: str                          # 'numeric', 'string', or 'boolean'
    confidence: float                       # Confidence score (0.0 to 1.0)
    source_document: str                    # Citation or document filename
    page_number: Optional[int] = None       # Document page index (1-indexed)
    text_span: Optional[str] = None         # Exact verbatim text snippet
    extraction_method: str = "EXTRACTED"    # Extraction technique used
    verification_status: FactVerificationStatus = FactVerificationStatus.EXTRACTED
    metadata: Dict[str, Any] = field(default_factory=dict)
```

---

## 4. Fact Verification States

| Status | Trust Level | Definition |
| :--- | :---: | :--- |
| `SELF_REPORTED` | 1 | Manually entered by applicant without documentary proof. |
| `EXTRACTED` | 2 | Parsed via regex, table parser, or OCR from uploaded document. |
| `USER_CONFIRMED` | 3 | Extracted fact reviewed and explicitly confirmed by applicant. |
| `ISSUER_VERIFIED` | 4 | Authenticated via cryptographic verification or issuing API (e.g. DigiLocker, UIDAI, Income Tax portal). |
| `CONFLICTED` | - | Multiple source documents provide discordant values for this fact. |
| `UNKNOWN` | 0 | Fact was not provided, unparseable, or missing from evidence. |

---

## 5. Normalization Specifications

### Currency & INR Normalization
- Removes currency symbols: `₹`, `Rs.`, `INR`, `/-`.
- Recognizes Indian denomination multipliers:
  - `"lakh"`, `"lac"`, `"lacs"` -> `* 100,000`
  - `"crore"`, `"crores"`, `"cr"` -> `* 10,000,000`
  - `"thousand"`, `"k"` -> `* 1,000`
- Example: `"Rs. 2.5 Lakh"` -> `250000.0`, `"₹4,20,000"` -> `420000.0`.

### State & Union Territory Normalization
- Standardizes across all 28 States and 8 Union Territories.
- Resolves historical and common administrative aliases:
  - `"Orissa"` -> `"Odisha"`
  - `"Uttaranchal"` -> `"Uttarakhand"`
  - `"Pondicherry"` -> `"Puducherry"`
  - `"NCT of Delhi"` / `"New Delhi"` -> `"Delhi"`
  - `"J&K"` -> `"Jammu and Kashmir"`
  - `"Daman and Diu"` -> `"Dadra and Nagar Haveli and Daman and Diu"`

### Gender Normalization
- `"Male"`, `"M"`, `"Man"`, `"Purush"` -> `"Male"`
- `"Female"`, `"F"`, `"Woman"`, `"Mahila"` -> `"Female"`
- `"Transgender"`, `"Trans"`, `"TG"`, `"Other"` -> `"Transgender"`

### Social Category Normalization
- Maps variations to canonical set: `{"General", "OBC", "SC", "ST", "EWS"}`.

### Boolean Normalization
- Affirmative (`"yes"`, `"true"`, `"1"`, `"applicable"`, `"eligible"`) -> `True`
- Negative (`"no"`, `"false"`, `"0"`, `"not applicable"`, `"ineligible"`) -> `False`
- Empty, null, or unstated -> `None` (remains `UNKNOWN`)

### Landholding Normalization
- Standard unit is **Hectares**.
- Converts acres using statutory ratio: `1 acre = 0.404686 hectares`.
- Example: `"5 acres"` -> `2.0234` hectares.

---

## 6. Domain Validation Layer

The validator detects and raises `ValidationError` for impossible domain states:
- `age < 0` or `age > 120`
- `annual_family_income < 0`
- `percentage < 0.0` or `percentage > 100.0`
- `landholding_hectares < 0.0`
- `residency_years < 0` or `residency_years > 120`
- `monthly_pension_amount < 0`

Impossible values are never accepted as valid evidence.
