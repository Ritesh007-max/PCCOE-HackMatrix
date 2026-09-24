# Hybrid RAG Retrieval Evaluation

## 1. Objective
Evaluate the information retrieval quality of the Hybrid Retriever (Dense Semantic Search + BM25 Sparse Search + Metadata-Aware Reranker) against exact, paraphrased, typo, abbreviation, conversational, and multilingual queries.

## 2. Quantitative Baseline vs Measured Metrics
- **Baseline (Phase 5 Evaluation)**:
  - Hit@1: ~0.450
  - Hit@3: ~0.650
  - Hit@5: ~0.720
  - MRR: ~0.540
- **Phase 13 Measured Results (26 Cases)**:
  - Total Queries: 26
  - Passed (Hit@5 > 0): 18 / 26 (69.23%)
  - Hit@1: 0.5385
  - Hit@3: 0.6538
  - Hit@5: 0.6923
  - MRR: 0.5891
  - Precision@5: 0.1385
  - Recall@5: 0.6923

## 3. Findings & Real Limitations Exposed
1. **Exact & Paraphrased Queries**:
   - `Atal Pension Yojana` -> `apy` (Hit@1 = 1.0, MRR = 1.0)
   - `pension for old age unorganised worker` -> `apy` (Hit@1 = 1.0, MRR = 1.0)
   - `PM Kisan Samman Nidhi` -> `pm-kisan` (Hit@2 = 1.0, MRR = 0.5)
   - `pregnant woman 5000 benefit` -> `pmmvy` (Hit@1 = 1.0, MRR = 1.0)
2. **Exposed Limitations**:
   - **Heavy Typos**: Extremely distorted phonetic queries (`Atle Penshan Yojna`) without phonetic indexing fail to retrieve APY in top-5 under offline mock embeddings.
   - **Cross-Lingual Hindi/Devanagari**: Devanagari queries without a live cross-lingual transformer checkpoint fall back to BM25, which requires Devanagari text tokens in the corpus index.
   - **Adversarial Queries**: Queries mentioning multiple schemes simultaneously (`APY vs PM Kisan`) split relevance signals across candidates.
