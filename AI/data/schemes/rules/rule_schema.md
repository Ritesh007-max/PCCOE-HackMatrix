# PolicySetu Policy Rule Schema Specification

This document details the architecture, fields, logical operators, and state transitions of the **Policy Rule Schema** used in the PolicySetu deterministic eligibility engine.

---

## 🏛 Schema Architecture & Purpose

In government welfare policies, ambiguous natural language text must be converted into rigorous, computable condition trees while preserving the original legal wording for statutory auditing and citation.

The PolicySetu Rule Engine enforces a **strict hybrid architecture**:
1. **Deterministic Rule Layer**: Evaluates hard constraints (Age limits, Income ceilings, Gender, State residency, Social category, Landholding bounds) using formal mathematical and logical operators with **zero LLM hallucinations**.
2. **Provenance & Citation Layer**: Links every extracted rule directly to the original statutory clause, source portal URL, and canonical scheme ID.
3. **Four-State Ternary Decision Protocol**: Distinguishes between verified disqualification (`FAIL`), verified eligibility (`PASS`), missing applicant data (`UNKNOWN`), and ambiguous policy wording (`REVIEW`).

---

## 📋 Schema Definition & Minimum Fields

Every scheme rule is defined by the following top-level schema and atomic `Rule` object.

```
SchemeRuleDefinition
├── scheme_id (UUIDv5)
├── scheme_slug (string)
├── scheme_name (string)
├── version (semver)
├── root_logic ("AND" | "OR")
├── logic_groups [LogicGroup]
└── rules [Rule]
     ├── rule_id (string)
     ├── scheme_id (UUIDv5)
     ├── rule_type ("eligibility" | "exclusion" | "conditional" | "document_requirement" | "benefit_condition")
     ├── field (string)
     ├── operator (">=" | "<=" | "between" | "in" | "is_true" | etc.)
     ├── expected_value (scalar | list | range | null)
     ├── value_type ("numeric" | "string" | "boolean" | "list_string" | "range" | "unstructured")
     ├── logic_group (string)
     ├── required (boolean)
     ├── hard_constraint (boolean)
     ├── condition (AST object: {field, op, val, unit})
     ├── raw_text (exact statutory clause)
     ├── source_url (official portal link)
     ├── source_document (e.g. "schemes_canonical.parquet")
     ├── source_page (integer | null)
     ├── source_section ("eligibility" | "exclusions" | "documents_required" | "benefits")
     ├── confidence (float 0.0 - 1.0)
     └── provenance (tracking struct)
```

---

## 🏷 Valid Enum Values & Semantics

### 1. `rule_type`
- `eligibility`: Positive qualification condition (e.g., *"Applicant must be at least 18 years old"*).
- `exclusion`: Negative disqualification criterion (e.g., *"Institutional landholders and income tax payers are not eligible"*). If an exclusion evaluates to `FAIL` (i.e. applicant matches exclusion condition), applicant is disqualified.
- `conditional`: Contextual condition that triggers secondary rules or optional subsidy bonuses.
- `document_requirement`: Mandatory verification documentation prerequisite.
- `benefit_condition`: Specific threshold determining the quantum or disbursement tier of a financial benefit.

### 2. `operator`
| Operator | Value Type | Semantics | Example |
| :--- | :--- | :--- | :--- |
| `>=` | `numeric` | Greater than or equal to | `age >= 18` |
| `>` | `numeric` | Strictly greater than | `loan_amount > 500000` |
| `<=` | `numeric` | Less than or equal to | `annual_family_income <= 100000` |
| `<` | `numeric` | Strictly less than | `child_age_months < 24` |
| `=` | `numeric`, `string`, `boolean` | Exact equality | `gender = "Female"` |
| `!=` | `numeric`, `string`, `boolean` | Inequality | `state != "Delhi"` |
| `between` | `range` (`{min, max}`) | Inclusive numeric range | `age between {min: 18, max: 40}` |
| `in` | `list_string` | Value must be a member of set | `state in ["Assam", "Meghalaya"]` |
| `not_in` | `list_string` | Value must NOT be in set | `category not_in ["General"]` |
| `contains` | `list_string`, `string` | Collection contains target | `enrolled_classes contains "Class 10"` |
| `contains_any` | `list_string` | Intersection is non-empty | `documents_held contains_any ["Aadhaar", "Voter ID"]` |
| `contains_all` | `list_string` | Subset containment | `documents_held contains_all ["Income Certificate", "Caste Certificate"]` |
| `is_true` | `boolean` | Flag must be true | `is_disabled is_true` |
| `is_false` | `boolean` | Flag must be false | `is_taxpayer is_false` |
| `manual_review` | `unstructured` | Requires case-worker human review | Special discretionary medical quota |
| `unstructured_nlp`| `unstructured` | Semantic verification via LLM/NER | Complex qualitative narrative criteria |

---

## 🚦 Four-State Decision Protocol

The PolicySetu engine evaluates every rule into one of four mutually exclusive states:

| Status | Exact Definition | Action / Downstream Effect |
| :--- | :--- | :--- |
| **`PASS`** | Sufficient, verified evidence in applicant profile satisfies the condition. | Condition met; contributes positively to scheme eligibility. |
| **`FAIL`** | Sufficient, verified evidence directly contradicts the statutory rule. | If `hard_constraint == true`, causes **immediate scheme disqualification**. |
| **`UNKNOWN`** | Required applicant profile field is missing, incomplete, or unverified. | **DO NOT DEFAULT TO FAIL OR PASS**. Triggers an explicit follow-up question asking the citizen for the missing attribute. |
| **`REVIEW`** | Information exists but is ambiguous, conflicting, or statutory text requires human discretion. | Escalated to human operator / civic official review with highlighted clause references. |

---

## 🌳 Logic Groups & Boolean Composition

Atomic rules are combined through hierarchical `logic_groups`:
- **`root_logic: "AND"`**: All primary hard constraints must pass.
- **Nested `OR` Groups**: e.g., Group `GROUP_SOCIAL_CATEGORY_OR`:
  - `Rule A: category in ["SC", "ST"]`
  - `Rule B: annual_income <= 250000`
  - The group passes if either Rule A or Rule B evaluates to `PASS`.
- **Exclusion Groups (`NOT`)**:
  - Exclusions evaluate with inverted polarity: if any hard exclusion is satisfied by the applicant (e.g. `is_taxpayer == true`), the exclusion group produces `FAIL` for scheme eligibility.

---

## 📄 Canonical Example Rule Definition (Atal Pension Yojana)

```json
{
  "scheme_id": "787c8801-ff05-59b3-9c86-13d8544d6da2",
  "scheme_slug": "apy",
  "scheme_name": "Atal Pension Yojana",
  "version": "1.0.0",
  "last_updated": "2026-09-21T16:00:00Z",
  "root_logic": "AND",
  "rules": [
    {
      "rule_id": "rule_apy_01",
      "scheme_id": "787c8801-ff05-59b3-9c86-13d8544d6da2",
      "rule_type": "eligibility",
      "field": "age",
      "operator": "between",
      "expected_value": {"min": 18, "max": 40},
      "value_type": "range",
      "logic_group": "DEFAULT",
      "required": true,
      "hard_constraint": true,
      "condition": {
        "field": "age",
        "op": "between",
        "val": {"min": 18, "max": 40},
        "unit": "years"
      },
      "raw_text": "The minimum age of joining APY is 18 years and maximum is 40 years.",
      "source_url": "https://www.myscheme.gov.in/schemes/apy",
      "source_document": "schemes_canonical.parquet",
      "source_page": null,
      "source_section": "eligibility",
      "confidence": 1.0,
      "provenance": {
        "source_dataset": "schemes_canonical.parquet",
        "extractor": "deterministic_rule_extractor_v1",
        "extraction_timestamp": "2026-09-21T16:00:00Z",
        "review_status": "VERIFIED_DETERMINISTIC"
      }
    },
    {
      "rule_id": "rule_apy_02",
      "scheme_id": "787c8801-ff05-59b3-9c86-13d8544d6da2",
      "rule_type": "exclusion",
      "field": "is_taxpayer",
      "operator": "is_false",
      "expected_value": false,
      "value_type": "boolean",
      "logic_group": "DEFAULT",
      "required": true,
      "hard_constraint": true,
      "condition": {
        "field": "is_taxpayer",
        "op": "is_false",
        "val": false,
        "unit": null
      },
      "raw_text": "From 1st October, 2022, any citizen who is or has been an income tax payer, shall not be eligible to join APY.",
      "source_url": "https://www.myscheme.gov.in/schemes/apy",
      "source_document": "schemes_canonical.parquet",
      "source_page": null,
      "source_section": "exclusions",
      "confidence": 1.0,
      "provenance": {
        "source_dataset": "schemes_canonical.parquet",
        "extractor": "deterministic_rule_extractor_v1",
        "extraction_timestamp": "2026-09-21T16:00:00Z",
        "review_status": "VERIFIED_DETERMINISTIC"
      }
    }
  ]
}
```
