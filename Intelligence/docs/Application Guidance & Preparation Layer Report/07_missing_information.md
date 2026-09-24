# Phase 11: Missing Information Guidance

## 1. Principle

When Phase 10 marks an application or scheme evaluation as `UNKNOWN`, Guidance isolates the missing profile fields without guessing values.

---

## 2. Representation Model

For each missing fact:
- **Field Name**: Machine-stable canonical key (e.g. `annual_family_income`, `social_category`).
- **Why Needed**: Statutory rule citation (e.g. "Rule `rule_sc_02` requires annual family income ceiling verification").
- **Action Required**: Mapped directly to Phase 10 `PROVIDE_INFORMATION` action.
- **Evidence Reference**: Originating policy requirement citation.

---

## 3. Invariants
- Missing fields can **never** be populated with synthesized defaults.
- Guidance must never convert missing information into an affirmative eligibility determination.
