# FIN Retrieval Evaluation Benchmark

## 1. Evaluation Methodology & Metrics

Retrieval performance is evaluated offline using ground-truth query-to-scheme pairs constructed from official administrative FAQs and canonical policy texts.

### Metric Formulations
1. **Hit@K**:
   $$\text{Hit@}K = \frac{1}{|Q|} \sum_{q \in Q} \mathbb{I}(\text{target\_slug} \in \text{Top-}K(q))$$
   Evaluated at $K \in \{1, 3, 5\}$.
2. **Mean Reciprocal Rank (MRR)**:
   $$\text{MRR} = \frac{1}{|Q|} \sum_{q \in Q} \frac{1}{\text{rank}_q}$$
   Where $\text{rank}_q$ is the 1-indexed position of the expected target scheme.

---

## 2. Benchmark Suite Composition

The benchmark suite (`src.rag.evaluation.test_cases`) tests six distinct query types:

| Query Type | Language | Example Query | Expected Slug | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Exact Name** | English | "Atal Pension Yojana" | `apy` | Validates sparse BM25 and title-reranking precision |
| **FAQ Derived** | English | "Who is eligible for maternity financial assistance of 5000 rupees?" | `pmmvy` | Tests natural conversational question matching |
| **Hindi Script** | Hindi (Devanagari) | "अटल पेंशन योजना के तहत न्यूनतम पेंशन क्या है?" | `apy` | Evaluates multilingual embedding alignment |
| **Hinglish** | Code-mixed | "thela lagane wale street vendors ke liye 10000 loan scheme" | `pmsvanidhi` | Tests mixed transliteration and semantic intent |
| **State-Filtered** | English + Filter | "housing subsidy for permanent residents of Assam" | `aag` | Validates geographic scope filter enforcement |

---

## 3. Multilingual Evaluation Note & Design Invariants

> [!IMPORTANT]
> **Multilingual Capability Evaluation**:
> While BM25 supports Unicode tokenization across Devanagari and Latin characters, sparse token-matching alone does not bridge semantic cross-lingual gaps (e.g. matching "पेंशन" to "pension"). Multilingual cross-lingual retrieval relies on dense models (`BAAI/bge-m3`).
> Exact Hit@K and MRR metrics must be measured and reported directly from benchmark executions without fabricated claims.

---

## 4. Running the Benchmark

Execute the offline benchmark runner:

```bash
python -c "
from src.rag.retriever import HybridRetriever
from src.rag.ingestion import RAGIngestionPipeline
from src.rag.evaluation.benchmark import RetrievalBenchmarkRunner

# 1. Ingest sample corpus
pipeline = RAGIngestionPipeline()
docs = pipeline.run_ingestion(scheme_limit=50, faq_limit=100, save_to_disk=False)

# 2. Build Hybrid Retriever
retriever = HybridRetriever()
retriever.index_documents(docs)

# 3. Run Benchmark
runner = RetrievalBenchmarkRunner(retriever)
results = runner.run_benchmark()
print('Overall Metrics:', results['overall'])
"
```
