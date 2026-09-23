# PolicySetu Phase 9 — Application Analysis Endpoint

## 1. Overview & Architectural Contract

`POST /v1/applications/analyze` is the primary entry point for the end-to-end citizen application lifecycle.

> [!IMPORTANT]
> **Direct Delegation Invariant**: This endpoint calls the authoritative Phase 8 `ApplicationPipeline.process_application()` directly. The API layer only performs HTTP request validation and response serialization.

- **URL**: `/v1/applications/analyze`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Authentication**: Required (`X-AI-Service-Key`)

---

## 2. Request Parameters

| Parameter | Type | In | Description |
| :--- | :--- | :--- | :--- |
| `files` | `List[UploadFile]` | `form-data` | **Required**. One or more citizen documents |
| `query` | `string` | `form-data` | Optional. Citizen inquiry or goal (e.g. "scholarships for OBC") |
| `target_scheme` | `string` | `form-data` | Optional. Target scheme slug or ID (e.g. "pm-kisan") |
| `session_id` | `string` | `form-data` | Optional. Client session ID for tracking |

---

## 3. Authoritative 21-Step Pipeline Execution

The underlying `ApplicationPipeline` executes all 21 steps synchronously in a worker threadpool:

1. **Step 1**: Multi-document upload & path verification
2. **Steps 2–6**: Pre-ingestion validation, deduplication, OCR extraction, document classification
3. **Steps 7–8**: Fact extraction candidate synthesis (Gemini primary -> OpenRouter fallback)
4. **Steps 9–10**: Canonical normalization (income, dates, categories, state codes)
5. **Steps 11–12**: Evidence registration & conflict detection
6. **Step 13**: Query intent understanding & routing
7. **Steps 14–15**: Hybrid RAG retrieval & scheme evidence matching
8. **Steps 16–17**: Deterministic rule AST eligibility evaluation
9. **Step 18**: Pre-compiled statutory benefit calculation
10. **Step 19**: Missing statutory field identification
11. **Step 20**: Grounded explanation generation & citation verification
12. **Step 21**: Final response assembly and audit logging

---

## 4. Response Payload Schema

```json
{
  "request_id": "req_1234567890abcdef",
  "application_id": "app_9f760605",
  "steps_completed": 21,
  "processing_status": "SUCCESS",
  "documents_processed": [
    {
      "file_name": "land_record.pdf",
      "document_type": "LAND_RECORD",
      "mime_type": "application/pdf",
      "page_count": 1,
      "is_scanned": false,
      "extraction_method": "NATIVE_PDF",
      "sha256": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a"
    }
  ],
  "applicant_profile": {
    "annual_income": 120000,
    "occupation": "farmer",
    "owns_cultivable_land": true
  },
  "conflicts_detected": [],
  "query_intent": {
    "intent": "SCHEME_DISCOVERY"
  },
  "retrieved_schemes": [
    {
      "scheme_id": "pm-kisan",
      "scheme_name": "Pradhan Mantri Kisan Samman Nidhi",
      "aggregate_score": 0.98
    }
  ],
  "eligibility_decision": {
    "status": "PASS",
    "eligible": true,
    "matched_rules": ["rule_pm-kisan_01", "rule_pm-kisan_02", "rule_pm-kisan_03", "rule_pm-kisan_04"],
    "failed_rules": [],
    "missing_fields": []
  },
  "benefit_calculation": {
    "status": "CALCULATED",
    "total_financial_benefit": 6000,
    "disbursement_frequency": "ANNUAL_3_INSTALLMENTS"
  },
  "missing_information": {
    "missing_fields": []
  },
  "explanation": {
    "status": "PASS",
    "text": "The applicant satisfies all statutory conditions under PM Kisan Samman Nidhi."
  },
  "security_audit": {
    "prompt_injection_detected": false
  },
  "telemetry": {
    "total_latency_ms": 420.5
  }
}
```
