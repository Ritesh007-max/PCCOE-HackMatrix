# Phase 10: Deterministic Next Action Engine

## 1. Zero-Hallucination Action Generation

LLMs must **never** invent or hallucinate citizen action items. In PolicySetu, all actions are deterministically synthesized directly from:
1. Missing document requirements (`DocumentCompletenessReport`).
2. Missing applicant profile facts (`missing_fields` from rule evaluation).
3. Detected evidence contradictions (`conflicted_fields`).
4. Statutory review requirements (`StatutoryDecision.REVIEW`).
5. Calculated benefit availability (`BenefitResult`).
6. Readiness status (`ReadinessStatus.READY_TO_APPLY`).

---

## 2. Action Types and Priority Mapping

| Action Type | Trigger | Priority | Objective |
|---|---|---|---|
| **`RESOLVE_CONFLICT`** | Multiple documents disagree on a field (e.g. State: Gujarat vs Rajasthan) | `HIGH` | Guide citizen to submit correct proof or caseworker to arbitrate |
| **`UPLOAD_DOCUMENT`** | Scheme requires a document not yet attached (e.g. Income Certificate) | `HIGH` | Prompt citizen to upload specific required certificate |
| **`PROVIDE_INFORMATION`** | Rule requires an applicant field not present in profile | `MEDIUM` | Prompt citizen for missing profile fact |
| **`REVIEW_ELIGIBILITY`** | Statutory decision is `REVIEW` due to unstructured or ambiguous criteria | `MEDIUM` | Flag case for human caseworker review |
| **`VIEW_BENEFIT`** | Statutory decision is `PASS` and financial benefit is calculated | `LOW` | Display computed entitlement and disbursement terms |
| **`READY_TO_APPLY`** | All criteria and documents complete | `HIGH` | Unlock application submission workflow |
| **`VISIT_OFFICIAL_PORTAL`** | Application is ready | `HIGH` | Provide verified direct link to official portal (e.g. `pmkisan.gov.in`) |
| **`CHECK_APPLICATION_STEPS`** | Application is ready | `MEDIUM` | Guide citizen through formal portal filing steps |

---

## 3. Action Structure

```python
class NextAction:
    action_id: str                      # Unique ID (e.g. act_7f9b8c)
    action_type: ActionType             # ActionType enum
    priority: ActionPriority            # HIGH, MEDIUM, LOW
    title: str                          # Human-readable instruction title
    reason: str                         # Policy-grounded explanation of why action is required
    related_scheme_id: Optional[str]    # Relevant scheme ID
    required_document_type: Optional[str] # Specific document type if UPLOAD_DOCUMENT
    required_field: Optional[str]       # Specific profile field if PROVIDE_INFORMATION / RESOLVE_CONFLICT
    evidence_reference: Optional[str]   # Citation to source text or contradictory docs
    action_metadata: Dict[str, Any]     # Extended metadata (e.g. portal_url)
    created_at: str                     # UTC ISO timestamp
```
