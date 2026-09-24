# FIN Phase 6: Applicant Fact Extraction & Normalization Bridge

## 1. Natural Language to Applicant Fact Pipeline

```
Citizen Natural Language Text
("My family earns 4.2 lakh and I live in Gujarat")
                 │
                 ▼
LLM / NLP Extraction (raw_value ONLY)
├── field: "annual_family_income", raw_value: "4.2 lakh"
└── field: "state", raw_value: "Gujarat"
                 │
                 ▼
Phase 4 Normalization & Validation Bridge
├── normalize_field_value("annual_family_income", "4.2 lakh") -> 420000.0
└── normalize_field_value("state", "Gujarat") -> "Gujarat"
                 │
                 ▼
Phase 4 EvidenceRegistry
├── Sets verification_status = SELF_REPORTED
└── Validates against statutory ranges
                 │
                 ▼
Phase 3 Deterministic ApplicantProfile
└── Evaluated against SchemeRuleSet
```

---

## 2. Strict Separation of Responsibilities

| Responsibility | Phase 6 (LLM / NLP) | Phase 4 (Normalization & Evidence) |
| :--- | :--- | :--- |
| **Parsing Text** | Extracts `field` and verbatim `raw_value` | Not involved |
| **Value Normalization** | **Prohibited** (never produces normalized values) | **Sole Authority** (`normalize_inr`, `normalize_area_hectares`) |
| **Statutory Validation** | Suggests field type | **Sole Authority** (validates statutory bounds, allowed enums) |
| **Provenance Tracking** | Suggests `SELF_REPORTED` for user text | **Sole Authority** (enforces verification hierarchy) |
| **Conflict Resolution** | Flags detected ambiguity in text | **Sole Authority** (detects contradictory values across documents) |

---

## 3. Query Entities vs Applicant Facts

A query like:
> *"What scholarship schemes are available for SC students in Gujarat?"*

produces:
- `QueryIntent.social_category = "SC"` (Search Hint)
- `QueryIntent.state = "Gujarat"` (Search Hint)
- `QueryIntent.is_search_hint_only = True`

**CRITICAL RULE:**
These search hints are **NEVER** promoted into `ApplicantFact` entries.
An applicant fact candidate is produced ONLY when the user explicitly makes a first-person statement about their own circumstances (e.g. *"I am an SC student"*, *"mere paas 2 acre khet hai"*).
