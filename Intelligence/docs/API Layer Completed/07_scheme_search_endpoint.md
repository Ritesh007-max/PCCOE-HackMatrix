# FIN Phase 9 — Scheme Search Endpoint

## 1. Overview

`POST /v1/schemes/search` provides high-speed hybrid search across the 4,749 canonical government schemes and 51,435 FAQs using dense vector representations and sparse BM25 indexing.

- **URL**: `/v1/schemes/search`
- **Method**: `POST`
- **Content-Type**: `application/json`
- **Authentication**: Required (`X-AI-Service-Key`)

---

## 2. Request Body Schema

```json
{
  "query": "irrigation and solar pump subsidy for small farmers",
  "language": "en",
  "state": "Maharashtra",
  "social_category": "OBC",
  "beneficiary_type": "farmer",
  "top_k": 5
}
```

### Parameter Details
- `query` (`string`, required): Citizen search text (1 to 1000 characters).
- `language` (`string`, optional, default: `"en"`): Query language code.
- `state` (`string`, optional): State filter (e.g. `"Maharashtra"`, `"All-India"`).
- `social_category` (`string`, optional): Social category filter (`SC`, `ST`, `OBC`, `General`).
- `beneficiary_type` (`string`, optional): Beneficiary segment (`student`, `farmer`, `women`).
- `top_k` (`integer`, optional, default: `10`): Maximum results to return (1 to 50).

---

## 3. Response Body Schema

```json
{
  "request_id": "req_5a1f2b3c4d5e",
  "query": "irrigation and solar pump subsidy for small farmers",
  "total_results": 1,
  "results": [
    {
      "scheme_id": "pm-kusum",
      "scheme_name": "PM KUSUM Scheme",
      "relevance_score": 0.945,
      "source_authority": "Ministry of New and Renewable Energy",
      "source_url": "https://pmkusum.mnre.gov.in",
      "evidence_snippets": [
        "Component B: Individual farmers will be supported to install standalone solar Agriculture pumps of capacity up to 7.5 HP..."
      ],
      "state": "All-India",
      "details": {
        "total_matching_chunks": 4,
        "sections_matched": ["scheme_overview", "benefits", "eligibility"]
      }
    }
  ]
}
```

---

## 4. Invariant Reminder

> [!NOTE]
> Retrieval relevance scores indicate semantic proximity to policy documents. **Search results never constitute statutory eligibility decisions.** Eligibility must be evaluated via `/v1/eligibility/check` or `/v1/applications/analyze`.
