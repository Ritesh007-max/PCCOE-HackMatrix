# Phase 11: Testing & Verification Strategy

## 1. Test Suite Composition

The Phase 11 verification suite consists of:
- **39 Unit Tests** (`Intelligence/tests/guidance/`):
  - `test_models.py`: Pydantic & Dataclass serialization/deserialization.
  - `test_eligibility_summary.py`: Four-state statutory explanations.
  - `test_document_guidance.py`: Requirement mapping and issuing authorities.
  - `test_application_steps.py`: Step ordering and source type tagging.
  - `test_benefit_guidance.py`: Benefit calculator translation.
  - `test_warnings.py`: Warning generation and codes.
  - `test_sources.py`: Metadata lookup, domain allowlisting, and deadlines.
  - `test_localization.py`: Multi-language translations and identifier stability.
  - `test_validator.py`: 10-point consistency and rejection rules.
  - `test_service.py`: Guidance generation and Markdown/JSON export.
  - `test_cache.py`: Multi-dimensional cache hits and invalidation.
- **9 Integration Tests** (`Intelligence/tests/integration/test_application_guidance.py`):
  - End-to-end Gujarat student scholarship.
  - Missing caste certificate and document action required.
  - Conflicting state evidence (Gujarat vs Rajasthan).
  - Failed statutory eligibility (income exceeded).
  - Unknown eligibility (missing income).
  - Ready-to-apply case with verified portal.
  - Policy version update (V1 -> V2) and cache invalidation.
  - Multilingual localization (Hindi and Hinglish).
  - Deterministic offline / no-LLM execution.

---

## 2. Regression Results

- **Total Test Count**: 346 tests.
- **Passed**: 346 tests.
- **Failures / Errors**: 0.
- **Pyright Static Type Checking**: 0 errors, 0 warnings.
