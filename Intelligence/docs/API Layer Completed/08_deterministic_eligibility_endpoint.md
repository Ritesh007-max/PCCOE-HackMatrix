# FIN Phase 9 — Deterministic Eligibility Check Endpoint

## 1. Overview & Statutory Invariant

`POST /v1/eligibility/check` evaluates normalized applicant facts against government policy rules.

> [!CAUTION]
> **Strict Architectural Invariant**: This endpoint is **100% deterministic**. Zero Gemini, OpenRouter, or other LLM calls are involved in evaluating statutory criteria or deciding outcomes. Evaluation uses the deterministic `RuleEvaluator` AST engine.

- **URL**: `/v1/eligibility/check`
- **Method**: `POST`
- **Content-Type**: `application/json`
- **Authentication**: Required (`X-AI-Service-Key`)

---

## 2. Request Body Schema

```json
{
  "applicant_facts": {
    "owns_cultivable_land": true,
    "is_institutional_landholder": false,
    "is_taxpayer": false,
    "monthly_pension_amount": 0
  },
  "scheme_ids": [
    "pm-kisan"
  ],
  "evidence_references": {
    "owns_cultivable_land": "doc_e3b0c44298fc"
  }
}
```

---

## 3. Four-State Decision Contract

Every scheme evaluation returns one of four explicit states:

| Status | `is_eligible` | Definition |
| :--- | :--- | :--- |
| `PASS` | `true` | Applicant satisfies 100% of statutory criteria and exclusions. |
| `FAIL` | `false` | Applicant fails one or more hard constraints (disqualified). |
| `UNKNOWN` | `false` | Insufficient information provided to determine eligibility. Follow-up input required. |
| `REVIEW` | `false` | Contradictory evidence detected (e.g. discordant documents). Manual administrative review needed. |

> [!IMPORTANT]
> `UNKNOWN != PASS` and `UNKNOWN != FAIL`. Missing fields are never hallucinated or assumed true.

---

## 4. Response Body Schema

```json
{
  "request_id": "req_8a7b6c5d4e3f",
  "evaluated_schemes_count": 1,
  "evaluations": [
    {
      "scheme_id": "9f760605-d17e-5f82-b7cd-a15b625d689f",
      "scheme_name": "Pradhan Mantri Kisan Samman Nidhi",
      "status": "PASS",
      "is_eligible": true,
      "rules_evaluated": [
        {
          "rule_id": "rule_pm-kisan_01",
          "field": "owns_cultivable_land",
          "operator": "is_true",
          "status": "PASS",
          "applicant_value": true,
          "expected_value": true,
          "hard_constraint": true,
          "reason": "owns_cultivable_land is verified True."
        }
      ],
      "matched_rules": ["rule_pm-kisan_01", "rule_pm-kisan_02", "rule_pm-kisan_03", "rule_pm-kisan_04"],
      "failed_rules": [],
      "missing_fields": [],
      "conflicted_fields": []
    }
  ]
}
```
