# Phase 10: Application Checklist Engine

## 1. Overview

The `ApplicationChecklist` provides a standardized, real-time checklist for citizens and administrative caseworkers. It transforms low-level AST evaluations and document audits into an intuitive, actionable checklist.

Checklist status is **dynamically derived from actual workflow state**, never hardcoded.

---

## 2. Checklist Categories

A checklist is organized into four distinct sections:

### 1. Documents Checklist
Tracks scheme document prerequisites against uploaded files:
```json
"documents": [
  {"item": "income_certificate", "status": "COMPLETE"},
  {"item": "domicile_certificate", "status": "COMPLETE"},
  {"item": "caste_certificate", "status": "PENDING"}
]
```

### 2. Information Checklist
Audits required profile fields:
```json
"information": [
  {"item": "age", "status": "COMPLETE"},
  {"item": "annual_family_income", "status": "COMPLETE"},
  {"item": "social_category", "status": "MISSING"}
]
```

### 3. Review Checklist
Highlights issues requiring clarification or adjudication:
```json
"review": [
  {"item": "Resolve conflict in 'state'", "status": "REQUIRED"}
]
```

### 4. Application Steps
Provides formal submission guidance:
```json
"application_steps": [
  {"item": "Visit official portal to submit application", "status": "READY"},
  {"item": "Download pre-filled verification summary", "status": "READY"}
]
```
*(If outstanding items remain, status displays `BLOCKED` with instructions to complete preceding items).*
