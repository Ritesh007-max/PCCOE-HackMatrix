# Phase 11: Application Guidance Package Schema

## 1. Overview

The `ApplicationGuidancePackage` is a strictly typed aggregate designed for direct consumption by future frontend rendering frameworks without requiring textual parsing or regex extraction.

---

## 2. Complete JSON Schema Specification

```json
{
  "application_id": "app_e2a39fd84c71",
  "scheme_id": "sc_post_matric_scholarship",
  "scheme_name": "Post Matric Scholarship for SC Students",
  "statutory_decision": "PASS",
  "readiness_status": "READY_TO_APPLY",
  "readiness": {
    "status": "READY_TO_APPLY",
    "reason": "All statutory criteria satisfied and required documents attached."
  },
  "eligibility": {
    "status": "PASS",
    "summary": "Your available profile information and verified documents satisfy the evaluated statutory eligibility criteria for Post Matric Scholarship for SC Students.",
    "criteria": [
      {
        "criterion": "social_category",
        "satisfied": true,
        "reason": "SC matches required SC"
      },
      {
        "criterion": "annual_family_income",
        "satisfied": true,
        "reason": "120000.0 <= 250000.0"
      },
      {
        "criterion": "state",
        "satisfied": true,
        "reason": "Gujarat matches required Gujarat"
      }
    ],
    "satisfied_criteria": ["social_category", "annual_family_income", "state"],
    "failed_criteria": [],
    "unresolved_criteria": [],
    "conflicting_evidence": [],
    "missing_information": []
  },
  "documents": {
    "available": ["Income Certificate", "Caste / Social Category Certificate", "Domicile / Residence Certificate"],
    "missing": [],
    "conflicted": [],
    "items": [
      {
        "document_type": "income_certificate",
        "display_name": "Income Certificate",
        "status": "AVAILABLE",
        "required": true,
        "why_needed": "Statutory verification of annual family income limits.",
        "already_provided": true,
        "issuing_authority": "Revenue Department, Taluk / Tehsildar Office",
        "preparation_notes": "Certificate must be valid for the current fiscal year.",
        "source_reference": null
      }
    ]
  },
  "information": {
    "known": ["state: Gujarat", "annual_family_income: 120000", "social_category: SC"],
    "missing": [],
    "conflicted": []
  },
  "benefit": {
    "status": "CALCULATED",
    "benefit_type": "DIRECT_BENEFIT_TRANSFER",
    "amount": 6000.0,
    "currency": "INR",
    "frequency": "ANNUAL",
    "disbursement_structure": "Direct Benefit Transfer into Aadhaar-linked Bank Account",
    "explanation": "Eligible for standard scholarship maintenance allowance.",
    "evidence": ["Rule R2 schedule B"]
  },
  "application": {
    "mode": "ONLINE",
    "official_portal_url": "https://scholarships.gov.in",
    "deadlines": {
      "status": "NOT_APPLICABLE",
      "open_date": null,
      "close_date": null,
      "deadline_date": null,
      "notes": "No fixed statutory deadline published in current active snapshot."
    },
    "steps": [
      {
        "step_number": 1,
        "instruction": "Gather and verify all mandatory certificates.",
        "source_type": "GENERAL_PREPARATION",
        "source_reference": "Application Checklist",
        "mandatory": true,
        "notes": "Ensure certificates are legible and unexpired."
      },
      {
        "step_number": 2,
        "instruction": "Open the official government portal: https://scholarships.gov.in",
        "source_type": "POLICY_SOURCED",
        "source_reference": "canonical/schemes.jsonl",
        "mandatory": true,
        "notes": "Only access verified government links."
      }
    ]
  },
  "actions": [
    {
      "action_id": "act_89df71",
      "action_type": "VISIT_OFFICIAL_PORTAL",
      "priority": "HIGH",
      "title": "Visit Official Government Portal",
      "reason": "Complete application form online.",
      "required_field": null,
      "required_document_type": null
    }
  ],
  "warnings": [],
  "sources": [
    {
      "scheme_id": "sc_post_matric_scholarship",
      "scheme_name": "Post Matric Scholarship for SC Students",
      "source_authority": "Ministry of Social Justice and Empowerment",
      "official_url": "https://scholarships.gov.in",
      "section": "application_process",
      "chunk_id": null,
      "policy_snapshot_version": "snapshot_20260921_193823"
    }
  ],
  "policy_snapshot_version": "snapshot_20260921_193823",
  "rule_version": "1.0.0",
  "language": "en",
  "generated_at": "2026-09-24T09:00:00Z",
  "is_deterministic_fallback": true
}
```
