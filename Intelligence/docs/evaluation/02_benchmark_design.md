# Benchmark Design & Dataset Governance

## 1. Golden Evaluation Datasets (`Intelligence/data/evaluation/`)
All datasets are stored in versioned JSONL format with strictly synthetic and anonymized citizen profiles. Zero real citizen PII or API secrets are allowed.

| Dataset File | Target Domain | Case Count | Primary Metrics |
|---|---|---|---|
| `golden_retrieval.jsonl` | Hybrid RAG Scheme Retrieval | 26 | Hit@1, Hit@3, Hit@5, MRR, Precision, Recall |
| `golden_eligibility.jsonl` | Deterministic Statutory Engine | 18 | PASS/FAIL/UNKNOWN/REVIEW Accuracy |
| `golden_extraction.jsonl` | Document Intelligence | 7 | Field Precision, Recall, F1, Type Accuracy |
| `golden_grounding.jsonl` | Evidence Citation & Grounding | 7 | Grounding Score, Contradiction Rate |
| `golden_multilingual.jsonl` | Multilingual Invariance | 5 | Language Detection, Invariance Rate |
| `red_team_injections.jsonl` | Prompt Injection Attacks (Cat A–O) | 15 | Injection Block Rate, Zero Rule Mutation |
| `red_team_policy_poisoning.jsonl` | Policy Poisoning & Gates | 8 | Gate Interception Rate |
| `red_team_hf.jsonl` | Hugging Face Authority Boundaries | 6 | Boundary Defense Rate, Field Stripping |
| `red_team_documents.jsonl` | Adversarial Document Injections | 6 | Data-Only Isolation Rate |
| `red_team_api.jsonl` | API Hardening & Secret Protection | 7 | HTTP Error Conformance, Zero Secret Leakage |
| **Total** | | **105** | |

## 2. Benchmark Execution Principles
1. **Zero Fabrication**: Metrics represent empirical computation over active indexes and code paths.
2. **Reproducibility**: Every evaluation run records the active policy snapshot (`snapshot_20260921_193823`), rule catalog version (`1.0.0`), RAG index version (`1.0.0`), and model configuration.
3. **Multi-Format Reporting**: Automatically emits dual JSON (machine-readable) and Markdown (human-readable) artifacts to `Intelligence/data/evaluation/reports/`.
