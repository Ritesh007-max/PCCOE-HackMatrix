# Multilingual Quality & Decision Invariance Evaluation

## 1. Objective
Verify that citizen interactions across English, Hindi (Devanagari), and Hinglish (Romanized Hindi) correctly resolve user intent, retrieve target schemes, and preserve statutory decision invariance.

### The Non-Negotiable Invariance Axiom:
```
Eligibility(Profile, Language=EN) == Eligibility(Profile, Language=HI) == Eligibility(Profile, Language=Hinglish)
```
Citizen language choice is purely a presentation-layer medium; it must **NEVER** alter deterministic statutory eligibility semantics.

## 2. Benchmark Results (5 Golden Cases)
- **Total Cases**: 5
- **Passed**: 5 (100.0%)
- **Statutory Decision Invariance**: 100.0% (`PASS` across EN, HI, Hinglish)
- **Devanagari Intent Resolution**: 100.0%
- **Transliterated Hinglish Resolution**: 100.0%

## 3. Verified Scenarios
1. **English Query Understanding**:
   - Query: "What are the documents needed for Atal Pension Yojana?"
   - Detected Intent: `DOCUMENT_REQUIREMENTS`, Scheme: `apy`.
2. **Hindi Devanagari Understanding**:
   - Query: "अटल पेंशन योजना के लिए कौन से दस्तावेज चाहिए?"
   - Orthographic Handling: Normalizes Devanagari nukta variations (`दस्तावेज` vs `दस्तावेज़`).
   - Detected Intent: `DOCUMENT_REQUIREMENTS`, Scheme: `apy`.
3. **Hinglish Understanding**:
   - Query: "atal pension yojana ke liye kaun kaun se documents lagte hain?"
   - Detected Intent: `DOCUMENT_REQUIREMENTS`, Scheme: `apy`.
4. **Statutory Decision Invariance**:
   - Profile: Age 28, Bank Account: True, Taxpayer: False.
   - Queries evaluated across all 3 languages.
   - Outcome: Identical 3-way `PASS` decision, zero semantic divergence.
5. **Transliterated Semantic Discovery**:
   - Query: "garbhavati mahilaon ko 5000 rupaye milne wali scheme"
   - Correctly resolves to `pmmvy` (Pradhan Mantri Matru Vandana Yojana).
