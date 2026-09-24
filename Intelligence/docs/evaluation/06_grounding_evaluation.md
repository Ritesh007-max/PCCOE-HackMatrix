# Evidence Grounding & Hallucination Prevention Evaluation

## 1. Grounding Framework
FIN enforces that every statutory statement, benefit claim, document requirement, and URL presented to citizens is traceable to authoritative evidence.

The `GroundingEvaluator` (`src/evaluation/grounding_eval.py`) classifies claims into four deterministic categories:
- `SUPPORTED`: Claim directly verifiable against cited canonical text.
- `PARTIALLY_SUPPORTED`: Claim consistent with context but lacking specific quantitative/temporal detail.
- `UNSUPPORTED`: Claim without empirical backing in retrieved knowledge.
- `CONTRADICTED`: Claim directly opposing canonical evidence (e.g., claiming a fee when policy states no fee).

## 2. Benchmark Results (7 Golden Cases)
- **Total Cases**: 7
- **Passed**: 7 (100.0%)
- **Supported Claim Detection**: 100.0%
- **Contradiction Detection**: 100.0%
- **Fabricated URL Interception**: 100.0%
- **Nonexistent Scheme Handling**: 100.0%

## 3. Evaluated Scenarios
1. **Statutory Claim Grounding**:
   - Claim: "Subscribers receive guaranteed minimum monthly pension between Rs 1000 and Rs 5000"
   - Evidence: Verbatim text from APY canonical gazette.
   - Result: `SUPPORTED`.
2. **Direct Contradiction Detection**:
   - Claim: "Applicants must pay a mandatory registration fee of Rs 500."
   - Evidence: "There is strictly no application or processing fee for enrolling in this scheme."
   - Result: `CONTRADICTED` (Evaluation failed as required).
3. **Domain Whitelist Enforcement**:
   - Claim: "Register at http://fake-gov-portal-scam.com/apply"
   - Result: Intercepted and rejected as untrusted domain by `SourceRegistry`.
4. **Hallucination Prevention**:
   - Query: "What are the rules for PM 100% Free Car Scheme 2026?"
   - System Response: "I could not verify this from the available authoritative sources."
   - Result: Verified acknowledgment of uncertainty, zero fabricated rules.
