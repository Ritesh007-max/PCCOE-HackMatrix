# PolicySetu Grounded Explanation & Decision Immutability

## 1. Decision Immutability Guardrail

The PolicySetu explanation engine produces natural-language explanations of eligibility outcomes while strictly enforcing decision immutability.

```
Deterministic Rule Engine Decision (PASS / FAIL / UNKNOWN / REVIEW)
                    ↓
GroundedExplanationGenerator (LLMClient, system prompts)
                    ↓
DecisionImmutabilityGuard (Safety Inspection)
                    ↓
Pass: Emit Explanation | Fail: Reject & Fallback to Auditable Template
```

### Invariants
1. If the decision is `FAIL`, the explanation MUST NOT state or imply that the applicant is eligible or qualified.
2. If the decision is `PASS`, the explanation MUST NOT claim the applicant is rejected.
3. If the decision is `UNKNOWN`, the explanation must clearly explain what information or documents are required.
4. If the decision is `REVIEW`, the explanation must detail the contradictory facts detected.

## 2. Citation Grounding & Hallucination Guard

Every factual claim in an explanation is decomposed into atomic `FactualClaim` structures:
- Each claim must cite specific `chunk_ids` and official source URLs from `<POLICY_EVIDENCE_DATA>`.
- The `GroundingVerifier` inspects all claims against the retrieved policy chunks.
- Unsupported claims are flagged and filtered before response delivery.
- The system never invents government URLs, deadlines, contact numbers, or benefit formulas.
