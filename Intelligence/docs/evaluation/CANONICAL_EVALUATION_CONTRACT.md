# FIN Canonical Evaluation Contract
**System Specification for Quantitative Benchmarking & Regression Testing**
**Document ID**: `CANONICAL_EVALUATION_CONTRACT`  
**Effective Date**: Phase 13+ (September 2026)  
**Governing Standard**: Phase 13 Evaluation Pyramid

---

## 1. Purpose & Scope

This contract defines the authoritative specification for all offline, online, and adversarial evaluation within FIN (`Intelligence/`). Any evaluation suite run, regression benchmark, or reporting artifact must adhere strictly to the definitions, datasets, metric formulas, and version controls defined herein.

---

## 2. Canonical Datasets & Suite Composition

The evaluation benchmark is strictly partitioned into 7 evaluation layers comprising exactly **105 golden cases**:

| Suite Name | Physical Dataset Path | Case Count | Primary Evaluation Focus |
| :--- | :--- | :---: | :--- |
| `retrieval` | `Intelligence/data/evaluation/golden_retrieval.jsonl` | **26** | Hybrid RAG dense/sparse candidate generation |
| `eligibility` | `Intelligence/data/evaluation/golden_eligibility.jsonl` | **18** | Deterministic statutory logic (`PASS`/`FAIL`/`UNKNOWN`/`REVIEW`) |
| `extraction` | `Intelligence/data/evaluation/golden_extraction.jsonl` | **7** | Document OCR & key-value field extraction precision |
| `grounding` | `Intelligence/data/evaluation/golden_grounding.jsonl` | **7** | Official citation verification & hallucination defense |
| `multilingual`| `Intelligence/data/evaluation/golden_multilingual.jsonl` | **5** | Linguistic invariance (EN == HI == Hinglish) |
| `red_team` | `Intelligence/data/evaluation/red_team_*.jsonl` (4 files)| **35** | Injections (15), Poisoning (9), HF bounds (6), Docs (5) |
| `security` | `Intelligence/data/evaluation/red_team_api.jsonl` | **7** | SSRF, Auth bypass, PII sanitization at API boundary |
| **TOTAL** | | **105** | **Invariant Evaluation Pyramid Total** |

### Immutability Rules
1. No case may be removed from any golden dataset merely because the system fails it.
2. Expected labels (`expected_scheme_id`, `expected_status`, etc.) may not be altered to artificially inflate benchmark scores.
3. Adding new evaluation cases must be done via explicit versioned expansion (e.g. Phase 14 extensions).

---

## 3. Mathematical Metric Definitions

All metrics are computed deterministically in `Intelligence/src/evaluation/metrics.py`.

### 3.1 Retrieval Metrics
Given a list of retrieved scheme slugs $R = [r_1, r_2, \dots, r_m]$ and expected scheme slug $e$:
* **Normalized Slug Comparison**: All slug comparisons normalize hyphens and underscores:
  $$\text{norm}(s) = s\text{.lower().replace('_', '-').strip()}$$
* **Hit@K**: Binary indicator whether the expected scheme is within the top-$k$ retrieved schemes:
  $$\text{Hit@K}(R, e) = \begin{cases} 1.0 & \text{if } \text{norm}(e) \in \{\text{norm}(r_i) \mid 1 \le i \le k\} \\ 0.0 & \text{otherwise} \end{cases}$$
* **Mean Reciprocal Rank (MRR)**:
  $$\text{MRR}(R, e) = \begin{cases} \frac{1}{\text{rank}(e)} & \text{if } e \in R \\ 0.0 & \text{otherwise} \end{cases}$$
* **Precision@K**:
  $$\text{Precision@K}(R, E) = \frac{|R[:k] \cap E|}{k}$$
* **Recall@K**:
  $$\text{Recall@K}(R, E) = \frac{|R[:k] \cap E|}{|E|}$$

### 3.2 Pass/Fail Criteria
* **Retrieval Case Pass**: A retrieval case passes if and only if:
  $$\text{Hit@5} > 0.0$$
* **Eligibility Case Pass**: Evaluated status must exactly match `expected_status`.
* **Grounding Case Pass**: No unsupported claim or fabricated URL citation is emitted.
* **Red Team Case Pass**: 100% of malicious directives neutralized or rejected.

---

## 4. Architectural Invariants

1. **Decoupling of Retrieval and Decisions**:
   $$\text{AI interprets} \to \text{Rules decide} \to \text{Evidence proves} \to \text{Human reviews uncertainty}$$
   Retrieval produces candidate schemes and evidence chunks only. It **never** decides statutory eligibility.
2. **Deterministic Eligibility**:
   Eligibility decisions are executed 100% deterministically by `src/eligibility/engine.py` without probabilistic LLM inference.
3. **Non-destructive Query Normalization**:
   The user's original input string (`original_query`) must be preserved verbatim. Normalization, transliteration, and concept expansion are internal retrieval representations only.

---

## 5. Versioning & Provenance Metadata

Every evaluation run must record:
```json
{
  "run_id": "eval_YYYYMMDD_HHMMSS",
  "policy_snapshot_version": "snapshot_YYYYMMDD_HHMMSS",
  "rule_version": "1.0.0",
  "rag_version": "1.0.0",
  "model_provider_metadata": "primary/fallback provider details"
}
```

---

## 6. Distinction Between Benchmarks and Unit Tests

* **Golden Evaluation Cases (`105 cases`)**: Evaluated via `python -m src.evaluation.runner --suite <name>`.
* **Unit & Integration Tests (`399 tests`)**: Evaluated via `python -m unittest discover -s tests -p "test_*.py"`.
* Code reviews and audit reports must report these two counts independently.
