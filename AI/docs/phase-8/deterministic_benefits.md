# PolicySetu Deterministic Benefit Calculator

## 1. Core Architectural Principle

The `BenefitCalculator` calculates quantitative financial amounts (subsidies, scholarships, direct benefit transfers) and catalogs non-monetary provisions.

### Strict Negative Invariant
**The system STRICTLY FORBIDS runtime extraction or synthesis of new mathematical formulas from narrative policy text via LLMs or naive regex heuristics.**

- Formulas must exist as pre-compiled, verified static rules or structured metadata attributes.
- If a scheme contains only narrative, discretionary, or unstructured benefit descriptions (e.g. *"Financial assistance will be provided as determined by the District Committee"*), the calculator **MUST NOT** hallucinate an amount or guess math.
- In such cases, the calculator strictly sets `status = CANNOT_DETERMINE` or `MANUAL_REVIEW_REQUIRED`, with `amount = None` and `verbatim_policy_evidence = <verbatim_text>`.

## 2. Supported Structured Calculation Types

1. **Flat Direct Benefit Transfers**:
   - Fixed statutory grants (e.g., PM-KISAN: Rs. 6,000 / year in 3 equal installments of Rs. 2,000).
   - Accidental risk coverage (e.g., PMSBY: Rs. 2,00,000).
2. **Tiered / Bracketed Scholarships**:
   - Maintenance allowances calculated from demographic and institutional attributes (e.g., Post-Matric SC Scholarship: Hosteller = Rs. 13,500/year; Day Scholar = Rs. 7,000/year).
3. **Percentage Subsidies with Statutory Caps**:
   - Computes percentage of verified project cost and caps at the statutory maximum limit (e.g., Solar Rooftop: 40% of project cost, capped at Rs. 30,000).

## 3. BenefitResult Data Contract

```python
@dataclass
class BenefitResult:
    scheme_id: str
    scheme_name: str
    benefit_type: BenefitType  # DBT, SUBSIDY, SCHOLARSHIP, FEE_CONCESSION, IN_KIND
    amount: Optional[float]    # None if cannot determine
    currency: str = "INR"
    disbursement_frequency: Optional[str] = None  # ANNUAL, MONTHLY, ONE_TIME
    formula_applied: Optional[str] = None         # ID of pre-compiled rule
    status: BenefitCalculationStatus              # CALCULATED, CONDITIONAL, CANNOT_DETERMINE
    reasoning: str
    verbatim_policy_evidence: Optional[str] = None
    unstructured_note: Optional[str] = None
```
