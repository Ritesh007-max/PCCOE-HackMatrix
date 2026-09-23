# Phase 10: Application Lifecycle State Machine

## 1. Lifecycle States

The application state machine defines the end-to-end procedural status of a citizen case:

1. **`DRAFT`**: Initial state upon case creation. Waiting for documents or manual profile entry.
2. **`DOCUMENTS_PENDING`**: One or more documents uploaded or requested; awaiting ingestion batch.
3. **`PROCESSING`**: Documents actively being parsed, scanned, OCR'd, and extracted via the 21-step pipeline.
4. **`FACTS_READY`**: Facts extracted, corroborated through the `EvidenceRegistry`, and canonicalized.
5. **`SCHEMES_IDENTIFIED`**: Candidate schemes retrieved via Hybrid RAG based on citizen profile and intent.
6. **`ELIGIBILITY_EVALUATED`**: Deterministic rule AST evaluation executed for target and candidate schemes.
7. **`ACTION_REQUIRED`**: Outstanding actions required (e.g. upload missing documents, provide missing fields).
8. **`READY_TO_APPLY`**: All statutory criteria satisfied (PASS) with complete documentation and no conflicts.
9. **`UNDER_REVIEW`**: Contradictory evidence or subjective policy rules flagged for human caseworker intervention.
10. **`COMPLETED`**: Case marked complete after successful submission or terminal archival.
11. **`FAILED`**: Unrecoverable parsing error, corrupted file, or system exception.
12. **`CANCELLED`**: Case abandoned or withdrawn by the citizen.

---

## 2. Transition Matrix

The `ApplicationStateMachine` strictly permits only the following transitions:

| From State | Allowed Target States |
|---|---|
| `DRAFT` | `DOCUMENTS_PENDING`, `PROCESSING`, `CANCELLED` |
| `DOCUMENTS_PENDING` | `PROCESSING`, `ACTION_REQUIRED`, `CANCELLED` |
| `PROCESSING` | `FACTS_READY`, `UNDER_REVIEW`, `FAILED` |
| `FACTS_READY` | `SCHEMES_IDENTIFIED`, `ACTION_REQUIRED`, `UNDER_REVIEW`, `FAILED`, `CANCELLED` |
| `SCHEMES_IDENTIFIED` | `ELIGIBILITY_EVALUATED`, `ACTION_REQUIRED`, `UNDER_REVIEW`, `FAILED`, `CANCELLED` |
| `ELIGIBILITY_EVALUATED` | `READY_TO_APPLY`, `ACTION_REQUIRED`, `UNDER_REVIEW`, `COMPLETED`, `FAILED`, `CANCELLED` |
| `ACTION_REQUIRED` | `DOCUMENTS_PENDING`, `PROCESSING`, `READY_TO_APPLY`, `UNDER_REVIEW`, `CANCELLED` |
| `READY_TO_APPLY` | `COMPLETED`, `ACTION_REQUIRED`, `UNDER_REVIEW`, `CANCELLED` |
| `UNDER_REVIEW` | `FACTS_READY`, `ELIGIBILITY_EVALUATED`, `READY_TO_APPLY`, `ACTION_REQUIRED`, `FAILED`, `CANCELLED` |
| `COMPLETED` | `PROCESSING` (Allows controlled re-evaluation upon new evidence/policy update) |
| `FAILED` | `DRAFT`, `PROCESSING`, `CANCELLED` (Recovery retry paths) |
| `CANCELLED` | `DRAFT` (Re-opening a cancelled case) |

---

## 3. Transition Guards and Validation

Attempting an illegal transition raises `InvalidStateTransitionError`:

```python
from src.application.lifecycle import ApplicationStateMachine
from src.application.status import ApplicationStatus
from src.application.exceptions import InvalidStateTransitionError

# Illegal jump raises exception
try:
    ApplicationStateMachine.validate_transition(
        ApplicationStatus.DRAFT,
        ApplicationStatus.COMPLETED,
    )
except InvalidStateTransitionError as e:
    print(f"Rejected: {e}")
```

### Contextual Guards
- **`READY_TO_APPLY` Guard**: Requires `has_decision: True`. An application cannot transition to ready without evaluated statutory eligibility.
- **`COMPLETED` Guard**: Requires `is_ready: True`. An application cannot be marked completed if unresolved action requirements remain.
