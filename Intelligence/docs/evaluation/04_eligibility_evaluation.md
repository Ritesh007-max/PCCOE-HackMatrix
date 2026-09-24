# Deterministic Eligibility Engine Evaluation

## 1. Statutory Authority Invariants
The Deterministic Eligibility Engine (`src/eligibility/engine.py` and `src/rules/evaluator.py`) is the sole statutory decision authority. The evaluation suite enforces the following non-negotiable invariants:

1. **Invariant 1 (Missing Information)**: Missing mandatory facts must NEVER evaluate to `PASS`. It must strictly yield `UNKNOWN`.
2. **Invariant 2 (Contradictory Facts)**: Contradictory evidence (e.g. from discordant documents) must NEVER silently become `PASS` or `FAIL`. It must strictly yield `REVIEW`.
3. **Invariant 3 (Hard Constraint Disqualification)**: A single hard constraint failure immediately causes `FAIL`, irrespective of other matched conditions.
4. **Invariant 4 (Arithmetic Immutability)**: Benefit calculation formulas are pre-compiled static functions; LLM outputs cannot modify calculated amounts.

## 2. Benchmark Results (18 Cases)
- **Total Cases**: 18
- **Passed**: 18 (100.0%)
- **Failed**: 0 (0.0%)

### Evaluated Criteria:
- **Age Boundaries**: Age 18 (PASS), Age 40 (PASS), Age 16 (FAIL), Age 45 (FAIL).
- **Taxpayer Status**: Non-taxpayer (PASS), Taxpayer (FAIL).
- **Missing Facts**: Age missing (UNKNOWN).
- **Contradictory Facts**: Conflicted taxpayer status (REVIEW).
- **Categorical & Gender Constraints**: Male applicant for PMMVY maternity scheme (FAIL).
- **Zero Income Boundary**: Income = 0 evaluated as valid numerical fact, not missing (PASS).
- **Deterministic Benefit Calculation**: PM-KISAN flat DBT of Rs 6,000/year (100% reproducible, 0 deviation).
