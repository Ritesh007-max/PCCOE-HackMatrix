# Phase 11: Benefit Guidance & Financial Summaries

## 1. Benefit Presentation Protocol

All financial or qualitative benefits in the Guidance Package are derived strictly from Phase 8 / Phase 10 `BenefitCalculator` results.

### Invariant Rules:
1. **No LLM Calculation**: LLMs are strictly forbidden from calculating, guessing, or estimating benefit amounts.
2. **Deterministic Values**: Amounts are presented in INR (`₹`) with formatted currency groupings.
3. **Cannot Determine Status**: If statutory conditions or income slabs do not permit exact calculation, status is emitted as `CANNOT_DETERMINE` or `CONDITIONAL` with clear explanations.

---

## 2. Benefit Schema Structure

```json
{
  "status": "CALCULATED",
  "benefit_type": "DIRECT_BENEFIT_TRANSFER",
  "amount": 6000.0,
  "currency": "INR",
  "frequency": "ANNUAL",
  "disbursement_structure": "Direct Benefit Transfer into Aadhaar-linked Bank Account",
  "explanation": "Eligible for standard scholarship maintenance allowance.",
  "evidence": ["Rule R2 schedule B"]
}
```
