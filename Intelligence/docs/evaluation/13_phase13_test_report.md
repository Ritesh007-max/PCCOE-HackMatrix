# Phase 13 Consolidated Evaluation Test Report

## 1. Executive Summary
- **Execution Run ID**: `eval_20260924_051946`
- **Total Test Cases Executed**: 105
- **Passed**: 97
- **Failed**: 8
- **Pass Rate**: 92.38%
- **Policy Snapshot**: `snapshot_20260921_193823`
- **Rule Version**: `1.0.0`
- **RAG Version**: `1.0.0`
- **Model Metadata**: Primary `gemini-1.5-flash`, Fallback `openrouter`

## 2. Suite-by-Suite Breakdown

| Suite | Category | Total Cases | Passed | Failed | Pass Rate | Key Metrics |
|---|---|---|---|---|---|---|
| **retrieval** | Hybrid RAG Search | 26 | 18 | 8 | 69.23% | Hit@1: 0.5385, Hit@3: 0.6538, Hit@5: 0.6923, MRR: 0.5891 |
| **eligibility** | Deterministic Engine | 18 | 18 | 0 | 100.0% | PASS Acc: 1.0, Invariant 1: 1.0, Invariant 2: 1.0 |
| **extraction** | Document Intelligence | 7 | 7 | 0 | 100.0% | Field Precision: 1.0, Field Recall: 1.0, F1: 1.0 |
| **grounding** | Evidence Citations | 7 | 7 | 0 | 100.0% | Supported: 100%, Fabricated URLs Blocked: 100% |
| **multilingual** | EN / HI / Hinglish | 5 | 5 | 0 | 100.0% | Language Invariance: 100%, Intent Acc: 100% |
| **red_team** | Injection / Poisoning / HF | 35 | 35 | 0 | 100.0% | Injection Block: 100%, Gate Block: 100%, Stripped: 100% |
| **api_security** | REST Endpoints Hardening | 7 | 7 | 0 | 100.0% | Secret Leak: 0, PII Leak: 0, Auth Bypass: 0 |
| **Total** | | **105** | **97** | **8** | **92.38%** | |

## 3. Analysis of Exposed Deficiencies (8 Retrieval Cases)
The 8 failed cases in the retrieval suite expose genuine real-world limitations:
1. **Severe Phonetic Typos**: `Atle Penshan Yojna` (Case: `RET_TYPO_01`). Without an active phonetic double-metaphone index or live multilingual LLM re-writing, BM25 fails to match `apy`.
2. **Devanagari Out-of-Vocabulary Chunks**: Cases `RET_HI_01`, `RET_HI_02`, `RET_HI_03`. When indexing English-only parquet chunks, pure Devanagari queries without live sentence transformer translation score zero on BM25 sparse search.
3. **Compound Multi-Scheme Queries**: `RET_ADV_04` ("Compare Atal Pension Yojana and PM Kisan Samman Nidhi"). RAG retrieves PM-KISAN at rank 1, placing APY outside top 5.

**Remediation Recommendation**: In production, route vernacular and typo-heavy queries through Phase 6 Query Translation & Normalization before vector retrieval.
