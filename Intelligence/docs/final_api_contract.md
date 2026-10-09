# FIN / Financial Policy Intelligence Copilot
## Final API Contract Specification

### Base Configuration
- **Protocol**: HTTP/1.1 or HTTP/2 over TLS
- **Format**: `application/json; charset=utf-8`
- **Authentication**: Header `X-AI-Service-Key: <secret_service_key>`

---

### 1. Unified Intelligence Query Endpoint

#### `POST /v1/intelligence/query`
Main unified conversational interface connecting natural language input with applicant context, retrieval, eligibility, explanation, and conflict tracking.

#### Request Headers
| Header | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `X-AI-Service-Key` | String | Yes | Secret service authentication key (min 16 chars). |
| `Content-Type` | String | Yes | `application/json` |

#### Request Body Schema
```json
{
  "applicant_id": "app_user_12345",
  "conversation_id": "conv_98765",
  "message": "Am I eligible for PMJAY?",
  "language": "en"
}
```

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `applicant_id` | String | Yes | Scoped unique identifier of the applicant. |
| `conversation_id` | String | No | Multi-turn conversation identifier. If omitted, generated automatically. |
| `message` | String | Yes | User conversational message / query. |
| `language` | String | No | ISO language code (`en`, `hi`, `gu`). Default: `en`. |

#### Successful Response (`200 OK`) Schema
```json
{
  "request_id": "req_a1b2c3d4e5f6",
  "applicant_id": "app_user_12345",
  "conversation_id": "conv_98765",
  "route": "ELIGIBILITY_QUERY",
  "answer": "You are ELIGIBLE for Ayushman Bharat (PM-JAY). All required conditions are met.",
  "language": "en",
  "eligibility": {
    "decision_id": "dec_34f8101a",
    "scheme_id": "pmjay",
    "scheme_name": "Ayushman Bharat PM-JAY",
    "status": "PASS",
    "eligible": true,
    "evaluated_at": "2026-09-27T03:00:00Z"
  },
  "recommendations": [],
  "explanation": {
    "summary": "You meet all statutory requirements for PMJAY.",
    "rule_trace": [
      {
        "rule_id": "pmjay_inc_1",
        "field": "annual_family_income",
        "operator": "<=",
        "expected_value": 500000,
        "actual_value": 210000,
        "status": "PASS"
      }
    ],
    "citations": ["AB-PMJAY Official Guidelines 2024"]
  },
  "evidence": [
    {
      "source_document": "IncomeCertificate.pdf",
      "field": "annual_family_income",
      "value": 210000,
      "verification_status": "ISSUER_VERIFIED"
    }
  ],
  "citations": ["AB-PMJAY Official Guidelines 2024"],
  "missing_information": [],
  "conflicts": [],
  "next_actions": [
    {
      "action_type": "APPLY",
      "title": "Apply for Scheme",
      "description": "Proceed to the official PMJAY portal to apply."
    }
  ],
  "review": null,
  "grounding_status": "GROUNDED",
  "created_at": "2026-09-27T03:00:01Z"
}
```

---

### 2. Human Review & Conflict Resolution Endpoints

#### `GET /v1/review/conflicts`
List active or resolved conflicts across applicants or for a specific applicant.

#### Request Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `applicant_id` | Query String | No | Filter conflicts by specific applicant ID. |
| `status` | Query String | No | Filter by status (`OPEN`, `RESOLVED`, `REJECTED`, `ESCALATED`). |

#### Response (`200 OK`)
```json
{
  "total": 1,
  "conflicts": [
    {
      "conflict_id": "conf_7f21a0c4",
      "applicant_id": "app_user_12345",
      "field": "annual_family_income",
      "source_a": "DOCUMENT",
      "value_a": 420000.0,
      "source_b": "USER_INPUT",
      "value_b": 800000.0,
      "status": "OPEN",
      "detected_at": "2026-09-27T02:45:00Z"
    }
  ]
}
```

---

#### `GET /v1/review/conflicts/{conflict_id}`
Retrieve full details and evidence history for a specific conflict.

#### Response (`200 OK`)
```json
{
  "conflict_id": "conf_7f21a0c4",
  "applicant_id": "app_user_12345",
  "field": "annual_family_income",
  "source_a": "DOCUMENT",
  "value_a": 420000.0,
  "evidence_a": {
    "document_name": "income_cert.pdf",
    "page": 1,
    "confidence": 1.0
  },
  "source_b": "USER_INPUT",
  "value_b": 800000.0,
  "evidence_b": {
    "message_id": "msg_001",
    "stated_value": 800000
  },
  "status": "OPEN",
  "detected_at": "2026-09-27T02:45:00Z"
}
```

---

#### `POST /v1/review/conflicts/{conflict_id}/resolve`
Caseworker action to resolve a conflicting field by selecting the authoritative source or providing verified value.

#### Request Body
```json
{
  "resolver_id": "caseworker_sharma",
  "selected_source": "DOCUMENT",
  "reason": "Verified authentic barcode and seal on state revenue income certificate.",
  "authoritative_value": 420000.0
}
```

#### Response (`200 OK`)
```json
{
  "conflict_id": "conf_7f21a0c4",
  "applicant_id": "app_user_12345",
  "status": "RESOLVED",
  "selected_source": "DOCUMENT",
  "authoritative_value": 420000.0,
  "resolver_id": "caseworker_sharma",
  "resolved_at": "2026-09-27T03:15:00Z",
  "resolution_reason": "Verified authentic barcode and seal on state revenue income certificate."
}
```

---

#### `POST /v1/review/conflicts/{conflict_id}/reject`
Caseworker action to reject candidate evidence.

#### Request Body
```json
{
  "resolver_id": "caseworker_sharma",
  "reason": "Uploaded document is illegible and unverified."
}
```

#### Response (`200 OK`)
```json
{
  "conflict_id": "conf_7f21a0c4",
  "status": "REJECTED",
  "resolver_id": "caseworker_sharma",
  "resolved_at": "2026-09-27T03:16:00Z"
}
```

---

#### `POST /v1/review/conflicts/{conflict_id}/escalate`
Escalate complex policy interpretation to a senior reviewing officer.

#### Request Body
```json
{
  "resolver_id": "caseworker_sharma",
  "reason": "Requires legal policy clarification on agricultural land lease classification."
}
```

#### Response (`200 OK`)
```json
{
  "conflict_id": "conf_7f21a0c4",
  "status": "ESCALATED",
  "resolver_id": "caseworker_sharma",
  "resolved_at": "2026-09-27T03:17:00Z"
}
```

---

### 3. Error Handling and Status Codes

| HTTP Status | Error Code | Description |
| :--- | :--- | :--- |
| `400 Bad Request` | `VALIDATION_ERROR` | Malformed JSON or invalid parameter syntax. |
| `401 Unauthorized` | `AUTHENTICATION_REQUIRED` | Missing or invalid `X-AI-Service-Key`. |
| `403 Forbidden` | `ACCESS_DENIED` | Tenant or applicant boundary violation. |
| `404 Not Found` | `RESOURCE_NOT_FOUND` | Conflict ID or Scheme ID does not exist. |
| `422 Unprocessable` | `SEMANTIC_ERROR` | Domain error in processing rules or input. |
| `500 Server Error` | `INTERNAL_ERROR` | Unexpected internal exception (scrubbed, no secret or stack trace leakage). |
