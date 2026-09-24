# FIN Phase 6: Prompt Contracts & Structural Schemas

## 1. Safety Boundaries via Structural XML Delimiters

To defend against indirect prompt injection, text originating from untrusted citizens, external OCR documents, or policy chunks is enclosed inside strict structural XML tags:

```xml
<UNTRUSTED_USER_INPUT>
My family income is 4.2 lakh and I am 23 years old.
</UNTRUSTED_USER_INPUT>
```

```xml
<POLICY_EVIDENCE_DATA>
Chunk ID: chunk_pm_sc_01
Content: Annual family income must not exceed 2.5 lakh rupees.
URL: https://scholarships.gov.in/sc_postmatric.pdf
</POLICY_EVIDENCE_DATA>
```

System instructions mandate that the model treats all content within these blocks strictly as **passive data**, never as executable instructions.

---

## 2. Structured Output Schemas

### `QueryIntent` Schema (Search Hints ONLY)
```json
{
  "original_query": "string",
  "normalized_query": "string",
  "language": "en | hi | hinglish | unknown",
  "intent": "SCHEME_DISCOVERY | ELIGIBILITY_QUESTION | BENEFIT_QUESTION | APPLICATION_PROCESS | DOCUMENT_REQUIREMENTS | STATUS_QUERY | COMPARISON | GENERAL_INFORMATION | UNKNOWN",
  "secondary_intent": "string | null",
  "state": "string | null",
  "social_category": "string | null",
  "beneficiary_type": "string | null",
  "policy_domain": "string | null",
  "benefit_type": "string | null",
  "keywords": ["string"],
  "confidence": 0.95,
  "ambiguities": [
    {
      "ambiguity_type": "APPROXIMATE_VALUE | MISSING_UNIT | ENTITY_CONFUSION | TEMPORARY_RESIDENCE",
      "field": "string | null",
      "raw_span": "string",
      "description": "string",
      "suggested_clarification": "string"
    }
  ],
  "is_search_hint_only": true
}
```

### `ApplicantFactCandidate` Schema (Raw Extraction ONLY)
```json
{
  "field": "annual_family_income",
  "raw_value": "4.2 lakh",
  "data_type": "numeric",
  "confidence": 0.90,
  "evidence_text": "family income is 4.2 lakh",
  "extraction_source": "user_text",
  "ambiguity": null,
  "needs_confirmation": false,
  "suggested_verification_status": "SELF_REPORTED"
}
```
*Notice: `normalized_value` is deliberately absent. Normalization is owned strictly by Phase 4.*

### `GroundedExplanation` Schema
```json
{
  "authoritative_decision": "PASS | FAIL | UNKNOWN | REVIEW",
  "scheme_id": "string",
  "answer": "string",
  "claims": [
    {
      "statement": "string",
      "cited_chunk_ids": ["string"],
      "cited_urls": ["string"],
      "support_status": "SUPPORTED | PARTIALLY_SUPPORTED | UNSUPPORTED | UNVERIFIED_CITATION",
      "support_score": 0.85,
      "evidence_excerpt": "string | null"
    }
  ],
  "supporting_chunk_ids": ["string"],
  "supporting_source_urls": ["string"],
  "passed_rules": ["string"],
  "failed_rules": ["string"],
  "missing_fields": ["string"],
  "conflicted_fields": ["string"],
  "review_required": false,
  "rejection_fallback_used": false
}
```
