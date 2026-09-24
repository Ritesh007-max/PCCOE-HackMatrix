# FIN Candidate Fact Extraction & Normalization Boundary

## 1. Architectural Role & Contracts

The applicant fact extraction layer extracts profile attributes from natural-language text and documents without making authoritative eligibility judgments.

```
Citizen Statement / Document Text
       ↓
ApplicantFactExtractor (LLMClient, temperature=0.0)
       ↓
ApplicantFactCandidate (raw_value ONLY, e.g. "4.2 lakh")
       ↓
normalize_field_value (Phase 4 Deterministic Normalizer)
       ↓
ApplicantFact (normalized_value, e.g. 420000.0)
       ↓
EvidenceRegistry (Conflict Resolution & Corroboration)
```

## 2. Invariants of Candidate Fact Extraction

1. **Extraction of `raw_value` Only**: The LLM extracts only the verbatim raw text string as stated in the source document (e.g. `"4.2 lakh"`, `"23 years"`, `"2.5 acres"`).
2. **Phase 4 Exclusively Owns Normalization**: The LLM never computes normalized values. Normalization (converting `"4.2 lakh"` to `420000.0`) is executed 100% deterministically by the Phase 4 normalization engine.
3. **User Statements Map to `SELF_REPORTED`**: Any fact declared directly by a user in text or chat is assigned `FactVerificationStatus.SELF_REPORTED`.
4. **Document Facts Map to `EXTRACTED`**: Facts extracted from verified uploaded documents are assigned `FactVerificationStatus.EXTRACTED`.
5. **No Speculative Inference**: The system strictly forbids inferring:
   - Income from occupation or job title.
   - Caste or social category from applicant surnames.
   - Gender from personal names.
   - Permanent domicile from temporary residence.
