# Tests Directory

Test suites for the PolicySetu AI subsystem covering unit logic, integration flows, retrieval metrics, extraction accuracy, and golden ground-truth verification.

---

## Test Suites

- `unit/`: Isolated unit tests for utility functions, individual rule operators, normalizers, and schemas.
- `integration/`: End-to-end pipeline executions (e.g., parsing raw PDF -> structuring -> rule evaluation).
- `retrieval/`: Precision, Recall@K, and Mean Reciprocal Rank (MRR) tests for vector and hybrid search.
- `rules/`: Unit and property tests verifying deterministic condition execution against known edge cases.
- `extraction/`: Document parsing accuracy and schema validation tests against annotated ground truth.
- `golden/`: Golden dataset validation guaranteeing high-confidence outputs on landmark government schemes.
