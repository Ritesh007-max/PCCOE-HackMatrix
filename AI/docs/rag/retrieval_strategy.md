# PolicySetu Retrieval Strategy

## 1. Query Normalization & Intent Extraction

When a citizen query enters the system:
1. **Language Detection**:
   - Detects Devanagari script (`hi`), mixed Devanagari/Latin or transliteration markers (`hi-en` / Hinglish), or standard Latin (`en`).
   - The query text is **never blindly machine-translated**, preserving dialectical terms and acronyms.
2. **Metadata Entity Detection**:
   - Matches state references against the 36 standard Indian States and Union Territories.
   - Detects social categories (`SC`, `ST`, `OBC`, `General`, `EWS`).
   - Detects target beneficiaries (`Student`, `Farmer`, `Women`, `Persons with Disabilities`, `Street Vendors`).
   - Extracts policy intent terms (`scholarship`, `pension`, `subsidy`, `loan`, `grant`).

> [!NOTE]
> Query normalization extracts hints for filtering and candidate scoring. It **never** decides citizen eligibility.

---

## 2. Dense Semantic Search

- Encodes query via `EmbeddingModel.encode_query()`.
- Searches `VectorStore` (FAISS `IndexFlatIP` by default, NumPy fallback) to retrieve top $K_{\text{dense}} = 25$ candidate chunks.
- Computes cosine similarity scores on unit-normalized vectors.
- Captures semantic equivalence across distinct vocabularies (e.g. "financial support for pregnant women" matches "Matru Vandana Yojana").

---

## 3. Sparse Lexical Search (BM25Okapi)

- Evaluates query terms using BM25 with token-level frequency saturation ($k_1=1.5$) and document length normalization ($b=0.75$).
- Searches the inverted index to retrieve top $K_{\text{sparse}} = 25$ candidate chunks.
- Accurately resolves queries with exact titles, acronyms (e.g., "PMMVY", "APY", "SVANidhi"), statutory act names, or specific numbers.

---

## 4. Score Normalization & Fusion

- Dense scores ($-1.0 \le S_{\text{dense}} \le 1.0$) and sparse BM25 scores ($0 \le S_{\text{sparse}} < \infty$) reside on disparate scales.
- Both score distributions are min-max normalized to $[0.0, 1.0]$:
  $$\hat{S} = \frac{S - S_{\min}}{S_{\max} - S_{\min}}$$
- Weighted hybrid score:
  $$S_{\text{fused}} = 0.70 \times \hat{S}_{\text{dense}} + 0.30 \times \hat{S}_{\text{sparse}}$$
- Missing candidate scores default safely to $0.0$, eliminating NaN/Inf values.

---

## 5. Metadata-Aware Content Reranking

Reranking applies deterministic boosts:
- **Title Match Multiplier** ($1.35\times$): Exact or substring match with official scheme name.
- **Section Alignment** ($1.10\times - 1.15\times$): Query intent for criteria boosts `eligibility`; intent for amounts boosts `benefits`.
- **Source Tier Preference** ($0.90\times - 1.05\times$): Subtle ranking boost favoring `PRIMARY_SCHEME` and `PRIMARY_FAQ` over unverified archive text.

---

## 6. Pre- and Post-Filtering

- **State Filtering**: When a state filter is active, returns schemes specifically tied to that state as well as national/central (`All India`) schemes.
- **Category & Beneficiary Filters**: Restricts candidate chunks to matching demographic domains.
