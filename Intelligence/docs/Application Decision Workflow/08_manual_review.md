# Phase 10: Manual Caseworker Review Model

## 1. Principles of Human Review

Manual review is **not an LLM decision**. When a statutory evaluation encounters ambiguity, contradictory evidence across uploaded documents, or subjective criteria, the system never guesses or converts uncertainty into false eligibility. Instead, it creates a formal `ReviewCase` for human caseworker adjudication.

---

## 2. Review Reasons

A `ReviewCase` is deterministically triggered by one of five reasons:

1. **`FACT_CONFLICT`**: Discordant values across official documents (e.g. Domicile certificate indicates Gujarat, while Ration Card indicates Rajasthan).
2. **`UNSTRUCTURED_RULE`**: Scheme contains subjective policy language that cannot be safely expressed as a deterministic Boolean AST.
3. **`INSUFFICIENT_EVIDENCE`**: Document text is obscured, damaged, or cannot be corroborated.
4. **`POLICY_SOURCE_CONFLICT`**: Multiple official government Gazette notifications or scheme guidelines state contradictory limits.
5. **`DOCUMENT_AMBIGUITY`**: Unclear issuer seal, date discrepancy, or unverified issuing authority.

---

## 3. Review Case Schema & Lifecycle

```python
class ReviewCase:
    review_id: str                      # Unique review case ID (e.g. rev_4a8b1c)
    application_id: str                 # Parent application ID
    reason: ReviewReason                # ReviewReason enum
    scheme_id: Optional[str]            # Targeted scheme ID
    conflicting_fields: List[str]       # Fields requiring adjudication
    unresolved_rules: List[str]         # Rule IDs requiring manual check
    supporting_documents: List[str]     # Attached document IDs for reference
    evidence: Dict[str, Any]            # OCR snippets and contradictory excerpts
    status: ReviewStatus                # OPEN, IN_REVIEW, RESOLVED, REJECTED, ESCALATED
    assigned_to: Optional[str]          # Caseworker officer ID
    resolution_notes: Optional[str]     # Official administrative justification
    created_at: str                     # UTC ISO timestamp
    updated_at: str                     # UTC ISO timestamp
```

### Review Progression:
`OPEN` $\rightarrow$ `IN_REVIEW` (assigned to caseworker) $\rightarrow$ `RESOLVED` (approved with notes) or `REJECTED` or `ESCALATED`.
