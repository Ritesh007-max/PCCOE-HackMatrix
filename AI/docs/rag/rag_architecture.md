# PolicySetu RAG Retrieval Architecture

## 1. System Mission & Core Invariant

The **PolicySetu Retrieval-Augmented Generation (RAG)** subsystem is designed for high-precision, multilingual discovery of government welfare schemes and supporting statutory evidence.

### The Critical Architectural Invariant
> **"LLM / RAG retrieval must NEVER decide citizen eligibility. RAG retrieves relevant policy evidence; the Phase 3 Deterministic Rule Engine decides eligibility (PASS / FAIL / UNKNOWN / REVIEW)."**

```
USER QUERY (English / Hindi / Hinglish)
    ↓
QUERY UNDERSTANDING & NORMALIZATION (src/rag/filters.py)
    [Language Hint, State Normalization, Social Category, Beneficiary Type]
    ↓
HYBRID RETRIEVAL (src/rag/retriever.py)
    ├── Dense Semantic Search (VectorStore: FAISS default | Numpy fallback)
    └── Sparse Keyword Search (BM25Okapi: src/rag/sparse.py)
    ↓
HYBRID RESULT FUSION (src/rag/fusion.py)
    [Normalized Weighted Score Fusion / Reciprocal Rank Fusion]
    ↓
METADATA & CONTENT-AWARE RERANKING (src/rag/reranker.py)
    [Title Match, FAQ Match, Intent Alignment, Source Tier Prior]
    ↓
SCHEME-LEVEL DEDUPLICATION (src/rag/retriever.py)
    [View A: Ranked Evidence Chunks | View B: Ranked Deduplicated Schemes]
    ↓
PHASE 4 APPLICANT FACT & EVIDENCE MODEL (src/documents/evidence.py)
    ↓
PHASE 3 DETERMINISTIC ELIGIBILITY ENGINE (src/rules/evaluator.py)
    ↓
STATUTORY DECISION: PASS / FAIL / UNKNOWN / REVIEW
    ↓
GROUNDED EXPLANATION GENERATION
```

---

## 2. Hybrid Retrieval Components

### A. Dense Semantic Search
- **Embedding Model**: `BAAI/bge-m3` or local weights via `SentenceTransformerEmbeddingModel`. Generates 1024-dimensional normalized dense vectors.
- **Offline / Test Mode**: `DeterministicMockEmbeddingModel` generates stable, reproducible vector projections for fast offline tests without multi-gigabyte downloads.
- **Vector Store**: `VectorStore` interface supporting:
  - `FAISSVectorStore`: High-performance index (IndexFlatIP) tailored for large collections (4,700+ schemes and 51,000+ FAQs).
  - `NumpyVectorStore`: Pure NumPy matrix math fallback for environments where FAISS binaries are unavailable.

### B. Sparse Lexical Search (BM25Okapi)
- **Tokenization**: Multilingual Unicode tokenizer preserving Devanagari script, Latin text, acronyms, and digits.
- **BM25 Parameters**: $k_1 = 1.5, b = 0.75$.
- **Strengths**: Excels at exact scheme names (e.g. "Atal Pension Yojana"), statutory acronyms ("PMMVY", "DBT"), and specific document titles ("Aadhaar Card", "ROR").

### C. Hybrid Fusion
- **Score Normalization**: Min-max normalization maps dense cosine similarities and sparse BM25 scores to $[0.0, 1.0]$.
- **Weighted Fusion**:
  $$\text{FusedScore} = 0.70 \times \text{NormDense} + 0.30 \times \text{NormSparse}$$
- **Tie-Breaking**: Guaranteed deterministic sorting via stable `chunk_id` tie-breakers.

---

## 3. Scheme-Level Deduplication

In welfare exploration, returning 8 chunks from the same scheme clutters the UI and obscures alternative programs. PolicySetu provides two distinct views:

1. **Chunk Results View**: Individual section chunks with dense, sparse, and rerank scores for granular evidence inspection.
2. **Scheme Results View**: Groups chunks by `scheme_slug`, ranks schemes by the aggregate evidence score:
   $$\text{AggregateScore} = \text{TopScore} + 0.05 \times \sum_{i=2}^{4} \text{SecondaryScore}_i$$
   Every scheme result retains its top supporting evidence chunks and full provenance.

---

## 4. Integration with Policy Engine

- Retrieval results feed directly into Phase 4 (`ApplicantFact` and `EvidenceRegistry`).
- If an applicant enters information conflicting with retrieved statutory thresholds, the engine outputs `REVIEW`.
- If required criteria are unstated in the applicant's profile, the engine outputs `UNKNOWN`.
- RAG acts purely as an evidence retrieval and candidate ranking pipeline.
