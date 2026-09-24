# Retrieval Remediation Baseline & Architectural Analysis

## 1. Problem Discovered in Phase 13
Phase 13 evaluation tested 26 diverse retrieval queries and revealed 8 genuine retrieval failures:
1. **Severe Phonetic & Spelling Typos** (e.g., `Atle Penshan Yojna` for *Atal Pension Yojana*).
2. **Pure Devanagari Hindi Queries** (e.g., `अटल पेंशन योजना`, `प्रधानमंत्री मातृ वंदना योजना`, `पीएम स्वनिधि योजना`) evaluated against an English-oriented policy corpus.
3. **Multi-Scheme & Comparison Queries** (e.g., `Compare Atal Pension Yojana and PM Kisan Samman Nidhi`, `APY vs National Pension Scheme`).
4. **Abbreviation Variations** (e.g., `PMMVY maternity benefit`).

### Canonical Baseline Performance Metrics (26 Golden Cases):
- **Total Cases**: 26
- **Passed (Hit@5 > 0)**: 18 / 26 (69.23%)
- **Failed**: 8 / 26 (30.77%)
- **Hit@1**: 0.4231 (Canonical) *(Historical report citation: 0.5385 via transcription shift)*
- **Hit@3**: 0.5385 (Canonical) *(Historical report citation: 0.6538)*
- **Hit@5**: 0.6923 (Canonical & Historical invariant)
- **MRR**: 0.5090 (Canonical) *(Historical report citation: 0.5891)*
- **Precision@5**: 0.1385
- **Recall@5**: 0.6923

---

## 2. Current Query Processing Flow
```
User Query (raw_text)
       ↓
normalize_query_intent() [src/rag/filters.py]
  - extracts detected_state, detected_category, detected_beneficiary, intent_terms
  - simple language hint: 'en', 'hi', or 'hi-en'
       ↓
Direct Retrieval [src/rag/retriever.py]
  - Dense: self.embedding_model.encode_query(raw_text)
  - Sparse: self.sparse_retriever.search(raw_text)
       ↓
fuse_results() [src/rag/fusion.py]
       ↓
MetadataAwareReranker.rerank() [src/rag/reranker.py]
       ↓
retrieve_schemes() grouping & damping [src/rag/retriever.py]
```

---

## 3. Root Cause Analysis of the 8 Failures

### A. Severe Phonetic & Spelling Typos (`RET_TYPO_01`: "Atle Penshan Yojna")
- **Root Cause**: `raw_text` is passed verbatim to BM25 and dense query encoder. Neither contains phonetic indexing or fuzzy distance matching. Tokens `atle`, `penshan`, `yojna` have zero exact matches in BM25 vocabulary against `atal`, `pension`, `yojana`.

### B. Pure Devanagari Hindi Queries (`RET_HI_01`, `RET_HI_02`, `RET_HI_03`)
- **Root Cause**: The indexed canonical scheme corpus is in English. While `LanguageDetector` in `src/nlp/language.py` and Devanagari regex exist, the retrieval query string is not translated or transliterated before sparse BM25 and dense search. Consequently, BM25 scores 0.0 against English documents.

### C. Multi-Scheme Queries (`RET_ADV_03`, `RET_ADV_04`, `RET_ADV_05`)
- **Root Cause**: When a user asks "Compare Atal Pension Yojana and PM Kisan Samman Nidhi", the entire concatenated query is searched as a single bag-of-words. One dominant scheme (e.g. PM-KISAN) monopolizes the top-5 slots, completely starving the second scheme (APY). The query is not decomposed per entity.

---

## 4. Existing Components to Reuse (Zero Duplication)
1. **`src/nlp/language.py`**:
   - `LanguageDetector`: Accurately classifies `en`, `hi`, and `hinglish`.
2. **`src/nlp/query_parser.py`**:
   - `QueryParser`: Provides dictionaries `STATES_MAP`, `CATEGORIES_MAP`, `BENEFICIARY_MAP`, and `DOMAIN_MAP` with English and Devanagari representations.
3. **`src/rag/filters.py`**:
   - `normalize_query_intent`: Extracts intent terms and builds filter predicates.
4. **`src/rag/retriever.py`**:
   - `HybridRetriever`: Preserves dense + sparse fusion and metadata reranking.
5. **`src/data/schemes/rules/examples/` & canonical parquet**:
   - Authoritative scheme names, slugs, and keywords.
