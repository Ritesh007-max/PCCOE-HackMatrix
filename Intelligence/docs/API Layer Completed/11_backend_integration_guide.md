# FIN Phase 9 — Backend Integration Guide

## 1. Overview for Backend Developers

This guide explains how external services (such as Node.js/Express, Python/Django, Go, or Java backends) consume the FIN AI Microservice.

> [!NOTE]
> Zero changes have been made to `BackEnd/` during Phase 9. This document serves as the implementation blueprint for backend developers connecting to the microservice.

---

## 2. Environment Setup

Configure your backend service with the following environment variables:

```ini
AI_SERVICE_URL=http://localhost:8000
AI_SERVICE_API_KEY=fin_internal_dev_key
AI_SERVICE_TIMEOUT_MS=60000
```

---

## 3. Integration Patterns

### Pattern A: Deterministic Eligibility Check (Node.js Example)

```javascript
import axios from 'axios';

async function checkSchemeEligibility(applicantFacts, schemeIds) {
  const response = await axios.post(
    `${process.env.AI_SERVICE_URL}/v1/eligibility/check`,
    {
      applicant_facts: applicantFacts,
      scheme_ids: schemeIds
    },
    {
      headers: {
        'X-AI-Service-Key': process.env.AI_SERVICE_API_KEY,
        'Content-Type': 'application/json'
      },
      timeout: 10000
    }
  );

  return response.data.evaluations;
}
```

### Pattern B: Multi-Document Application Analysis (Node.js Example)

```javascript
import axios from 'axios';
import FormData from 'form-data';
import fs from 'fs';

async function submitApplicationAnalysis(filePaths, userQuery, targetScheme) {
  const form = new FormData();
  
  for (const filePath of filePaths) {
    form.append('files', fs.createReadStream(filePath));
  }
  
  if (userQuery) form.append('query', userQuery);
  if (targetScheme) form.append('target_scheme', targetScheme);

  const response = await axios.post(
    `${process.env.AI_SERVICE_URL}/v1/applications/analyze`,
    form,
    {
      headers: {
        ...form.getHeaders(),
        'X-AI-Service-Key': process.env.AI_SERVICE_API_KEY
      },
      timeout: 60000
    }
  );

  return response.data;
}
```

### Pattern C: Grounded Citizen Chat (Node.js Example)

```javascript
import axios from 'axios';

async function askPolicyAssistant(question, conversationId) {
  const response = await axios.post(
    `${process.env.AI_SERVICE_URL}/v1/chat`,
    {
      query: question,
      conversation_id: conversationId,
      language: 'en'
    },
    {
      headers: {
        'X-AI-Service-Key': process.env.AI_SERVICE_API_KEY,
        'Content-Type': 'application/json'
      },
      timeout: 15000
    }
  );

  return response.data;
}
```
