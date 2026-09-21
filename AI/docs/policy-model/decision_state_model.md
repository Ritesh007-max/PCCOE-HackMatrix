# PolicySetu Four-State Decision Model & Evaluation Logic

This document specifies the **Four-State Ternary Decision Logic**, multi-valued truth tables, missing-information handling protocols, and safety guarantees of the PolicySetu eligibility evaluation engine.

---

## 🚦 1. The Four-State Decision Architecture

Standard binary boolean logic (`True` / `False`) is dangerously inadequate for government welfare assessment because citizen profiles are almost always partially incomplete during early inquiry stages.

PolicySetu enforces a strict **Four-State Decision Model**:

```
                              ┌────────────────────────┐
                              │ Atomic Rule Evaluation │
                              └───────────┬────────────┘
                                          │
            ┌──────────────────┬──────────┴──────────┬──────────────────┐
            ▼                  ▼                     ▼                  ▼
     ┌─────────────┐    ┌─────────────┐       ┌─────────────┐    ┌─────────────┐
     │    PASS     │    │    FAIL     │       │   UNKNOWN   │    │   REVIEW    │
     │  Verified   │    │  Verified   │       │   Missing   │    │  Ambiguous  │
     │ Requirement │    │ Violation   │       │ Information │    │ Discretion  │
     │  Satisfied  │    │ Contradicts │       │   Profile   │    │    Case     │
     └─────────────┘    └─────────────┘       └─────────────┘    └─────────────┘
```

### State Definitions
1. **`PASS`**: Sufficient, verified evidence in the applicant's profile satisfies the statutory criteria (e.g. Applicant Age is 25, statutory rule is `18 <= age <= 40`).
2. **`FAIL`**: Sufficient, verified evidence explicitly violates the statutory condition (e.g. Applicant Age is 48 for a scheme capped at 40; or applicant is an Income Tax Payer for Atal Pension Yojana).
3. **`UNKNOWN`**: The applicant's profile lacks the necessary attribute (e.g. Scheme requires `annual_family_income <= ₹2,50,000`, but applicant has not yet provided income details).
4. **`REVIEW`**: Profile evidence exists but contains contradictory documentation, or the statutory rule relies on manual discretionary administrative approval.

---

## 🛑 2. Critical Safety Invariants: Missing Information Protocol

### Invariant 1: `UNKNOWN != FAIL`
> **Never convert UNKNOWN into FAIL.**
- **Real-World Hazard**: If missing information defaults to `FAIL`, an eligible rural citizen who has simply not yet entered their landholding or category will be told: *"You are Ineligible for PM-Kisan"*. This causes false disqualifications and discourages citizens from seeking benefits they legally qualify for.

### Invariant 2: `UNKNOWN != PASS`
> **Never convert UNKNOWN into PASS.**
- **Real-World Hazard**: If missing information defaults to `PASS`, an applicant who has not disclosed their tax status or government employment will be told: *"Congratulations, you are Eligible for Subsidized Food Grains"*. This causes fraudulent expectations, misallocated resources, and portal compliance failure.

### Downstream Action for `UNKNOWN`
When a hard constraint evaluates to `UNKNOWN`, the PolicySetu engine:
1. Marks the scheme status as **`ACTION_REQUIRED (Missing Information)`**.
2. Automatically generates an interactive follow-up inquiry asking the citizen specifically for the missing attribute (e.g. *"To verify your eligibility for Aponar Apon Ghar, please specify your annual household income"*).

---

## 🧮 3. Multi-Valued Logic Truth Tables (Ternary / Kleene Logic)

The PolicySetu rule engine combines atomic states using an extended Kleene-style multi-valued algebraic logic:

### Extended `AND` Truth Table (Conjunction)
Used when all conditions in a group are mandatory.

| `A` \ `B` | `PASS` | `FAIL` | `UNKNOWN` | `REVIEW` |
| :--- | :--- | :--- | :--- | :--- |
| **`PASS`** | **`PASS`** | `FAIL` | `UNKNOWN` | `REVIEW` |
| **`FAIL`** | `FAIL` | **`FAIL`** | `FAIL` | `FAIL` |
| **`UNKNOWN`**| `UNKNOWN` | `FAIL` | **`UNKNOWN`**| `UNKNOWN` |
| **`REVIEW`** | `REVIEW` | `FAIL` | `UNKNOWN` | **`REVIEW`** |

> **Key Takeaway**: A single verified `FAIL` on a hard constraint immediately short-circuits the entire `AND` conjunction to `FAIL`, regardless of unknown or review fields. If no failure exists, any `UNKNOWN` forces the conjunction to `UNKNOWN`.

---

### Extended `OR` Truth Table (Disjunction)
Used for alternative qualifications (e.g. *"SC/ST category OR BPL cardholder"*).

| `A` \ `B` | `PASS` | `FAIL` | `UNKNOWN` | `REVIEW` |
| :--- | :--- | :--- | :--- | :--- |
| **`PASS`** | **`PASS`** | `PASS` | `PASS` | `PASS` |
| **`FAIL`** | `PASS` | **`FAIL`** | `UNKNOWN` | `REVIEW` |
| **`UNKNOWN`**| `PASS` | `UNKNOWN` | **`UNKNOWN`**| `REVIEW` |
| **`REVIEW`** | `PASS` | `REVIEW` | `REVIEW` | **`REVIEW`** |

> **Key Takeaway**: A single verified `PASS` immediately satisfies the `OR` group, making missing alternative fields irrelevant.

---

### Extended `NOT` Truth Table (Inversion / Negative Exclusions)
Used when evaluating exclusion clauses (*"Those who paid income tax are excluded"*).

| Input `A` (Exclusion Rule Condition) | Output `NOT A` (Eligibility Impact) |
| :--- | :--- |
| **`PASS`** (Applicant matches exclusion) | **`FAIL`** (Applicant is disqualified) |
| **`FAIL`** (Applicant does not match exclusion)| **`PASS`** (Applicant is cleared of exclusion) |
| **`UNKNOWN`** (Exclusion status is unknown) | **`UNKNOWN`** (Requires follow-up) |
| **`REVIEW`** (Exclusion documentation is mixed) | **`REVIEW`** (Escalated to human caseworker) |

---

## 🔒 4. Why LLMs Must NEVER Directly Decide Eligibility

PolicySetu strictly confines Large Language Models (LLMs) to **input interpretation** and **output explainability**, prohibiting them from executing eligibility decisions:

| Failure Mode | LLM Direct Decision Hazard | PolicySetu Rule Engine Defense |
| :--- | :--- | :--- |
| **Numeric Hallucination** | LLMs frequently mix up numbers or evaluate `2,50,000 <= 2,00,000` as true when prompt context is complex. | Mathematical AST operators (`>`, `<=`, `between`) execute with 100% deterministic precision. |
| **Sycophancy Bias** | LLMs tend to agree with user prompts (e.g. if a user says *"I am 42 years old, can I join APY?"*, an LLM often answers *"Yes, you may qualify"*). | Invariant hard constraints instantly flag `age > 40` as statutory `FAIL`. |
| **Non-Determinism** | Identical applicant profiles submitted twice can produce different LLM answers depending on temperature or sampling. | The AST rule engine is purely deterministic and idempotent (same profile always yields the exact same decision). |
| **Legal Auditability** | LLM internal weights cannot be subpoenaed or inspected in an administrative appeal. | Every rule engine decision produces an immutable audit trail pointing to exact section citations from official gazettes. |

### The Correct Division of Responsibilities
```
[Citizen Natural Language Query]
               │
               ▼
   [LLM: Entity Extractor] ──► Extracts clean profile: {age: 38, income: 150000, state: "Kerala"}
               │
               ▼
[Deterministic Rule Engine] ──► Evaluates AST: PASS / FAIL / UNKNOWN / REVIEW
               │
               ▼
[LLM: Explainability Writer] ──► Generates polite, clear rationale citing the statutory rule
```
