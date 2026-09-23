# PolicySetu Phase 9 — Grounded Chat Endpoint

## 1. Overview & Architectural Contract

`POST /v1/chat` provides conversational citizen assistance grounded exclusively in verified policy records.

> [!IMPORTANT]
> **Strict Grounding Invariant**: The chat endpoint is not a generic conversational chatbot. Every claim must be backed by retrieved RAG evidence chunks and cited with chunk references.

- **URL**: `/v1/chat`
- **Method**: `POST`
- **Content-Type**: `application/json`
- **Authentication**: Required (`X-AI-Service-Key`)

---

## 2. Request Body Schema

```json
{
  "query": "How many installments do farmers receive under PM Kisan?",
  "conversation_id": "conv_999",
  "language": "en",
  "applicant_facts": {
    "occupation": "farmer"
  }
}
```

---

## 3. Defense & Grounding Lifecycle

1. **Prompt Injection Inspection**: The user query is scanned by `PromptInjectionDetector`. If malicious instruction overrides are detected, the request is immediately rejected with `intent: "INJECTION_BLOCKED"`.
2. **Hybrid RAG Retrieval**: The query is matched against the dense-sparse policy corpus using `HybridRetriever`.
3. **Empty Corpus Guard**: If no relevant statutory documents are retrieved, a transparent fallback notice is returned without invoking the LLM.
4. **Isolated Grounded Generation**: The retrieved evidence chunks and isolated query are submitted to the LLM (Gemini with automatic OpenRouter fallback).
5. **Citation Synthesis**: Response includes exact chunk excerpts, source URLs, and matched scheme metadata.

---

## 4. Response Body Schema

```json
{
  "request_id": "req_1a2b3c4d5e6f",
  "conversation_id": "conv_999",
  "answer": "Under the PM Kisan Samman Nidhi scheme [chunk_chat_01], eligible farmers receive a total financial assistance of Rs 6,000 per year, disbursed in three equal installments of Rs 2,000 every four months.",
  "intent": "SCHEME_DISCOVERY",
  "citations": [
    {
      "chunk_id": "chunk_chat_01",
      "scheme_id": "pm-kisan",
      "url": "https://pmkisan.gov.in",
      "excerpt": "Under the Scheme an amount of Rs. 6000/- per year is released by the Central Government online directly into the bank accounts of the eligible farmer families in three equal installments..."
    }
  ],
  "suggested_schemes": [
    {
      "scheme_id": "pm-kisan",
      "scheme_name": "PM Kisan Samman Nidhi",
      "score": 0.98,
      "ministry": "Ministry of Agriculture and Farmers Welfare",
      "state": "All-India"
    }
  ],
  "provider_telemetry": {
    "provider": "gemini",
    "model": "gemini-2.5-flash",
    "latency_ms": 115.4,
    "fallback_used": false
  }
}
```
