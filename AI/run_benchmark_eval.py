"""
PolicySetu Phase 5 Retrieval Benchmark & Smoke Test Runner.
Ingests canonical dataset, builds FAISS vector index + BM25 sparse index,
evaluates offline benchmark test suite, and tests sample queries.
"""

import json
import sys
import time
from pathlib import Path

# Fix Windows console UTF-8 printing
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.rag.config import RAGConfig
from src.rag.ingestion import RAGIngestionPipeline
from src.rag.embeddings import DeterministicMockEmbeddingModel
from src.rag.retriever import HybridRetriever
from src.rag.evaluation.benchmark import RetrievalBenchmarkRunner
from src.rag.models import RetrievalQuery


def main():
    print("==================================================")
    print("PolicySetu Phase 5: RAG Subsystem Benchmark")
    print("==================================================")

    # 1. Ingest Canonical Dataset
    print("\n[1/4] Ingesting authoritative canonical dataset...")
    t0 = time.time()
    pipeline = RAGIngestionPipeline()
    # Ingest all canonical schemes (derived from schemes.csv) + top 5,000 FAQs
    docs = pipeline.run_ingestion(scheme_limit=None, faq_limit=5000)
    ingest_time = time.time() - t0
    print(f"  -> Ingested {len(docs):,} document chunks in {ingest_time:.2f}s.")

    # 2. Build Hybrid Indexes (FAISS + BM25)
    print("\n[2/4] Indexing chunks with FAISS vector store & BM25 sparse index...")
    t1 = time.time()
    config = RAGConfig(use_faiss=True, embedding_dimension=32)
    embedding_model = DeterministicMockEmbeddingModel(dimension=32)
    retriever = HybridRetriever(config=config, embedding_model=embedding_model)
    retriever.index_documents(docs, batch_size=1024)
    index_time = time.time() - t1
    print(f"  -> Indexed in {index_time:.2f}s.")

    # 3. Run Benchmark Suite: Pure BM25 Evaluation (Sparse Only)
    print("\n[3/5] Running Ground-Truth Benchmark on Pure BM25 (Sparse Only)...")
    config_bm25 = RAGConfig(use_faiss=True, embedding_dimension=32, dense_weight=0.0, sparse_weight=1.0, rerank_top_k=50)
    retriever_bm25 = HybridRetriever(config=config_bm25, embedding_model=embedding_model, sparse_retriever=retriever.sparse_retriever)
    retriever_bm25.vector_store = retriever.vector_store
    retriever_bm25._doc_metadata_map = retriever._doc_metadata_map
    runner_bm25 = RetrievalBenchmarkRunner(retriever_bm25)
    benchmark_bm25 = runner_bm25.run_benchmark(top_k=5)

    print("\n--- BM25 (Sparse) Overall Metrics ---")
    print(json.dumps(benchmark_bm25["overall"], indent=2))

    print("\n--- BM25 Breakdown By Query Type ---")
    print(json.dumps(benchmark_bm25["by_query_type"], indent=2))

    # 4. Run Benchmark Suite: Hybrid (Dense + Sparse)
    print("\n[4/5] Running Ground-Truth Benchmark on Hybrid Retrieval...")
    runner_hybrid = RetrievalBenchmarkRunner(retriever)
    benchmark_res = runner_hybrid.run_benchmark(top_k=5)

    print("\n--- Hybrid Overall Metrics ---")
    print(json.dumps(benchmark_res["overall"], indent=2))

    print("\n--- Hybrid Breakdown By Query Type ---")
    print(json.dumps(benchmark_res["by_query_type"], indent=2))

    print("\n--- Per-Query Hybrid Predictions & Reciprocal Rank ---")
    for q in benchmark_res["detailed_queries"]:
        print(f"  [{q['query_id']}] ({q['query_type']})")
        print(f"    Query: '{q['query_text']}'")
        print(f"    Target: {q['expected_slug']} | Predicted: {q['predicted_slugs']}")
        print(f"    Hit@1: {q['hit@1']} | Hit@3: {q['hit@3']} | Hit@5: {q['hit@5']} | MRR: {q['mrr']:.4f}")

    # 5. Execute 5 Required Demonstration Queries
    print("\n[5/5] Executing 5 User Demonstration Queries...")
    demo_queries = [
        "scholarship for SC students in Gujarat",
        "farmer subsidy for small land holdings",
        "अटल पेंशन योजना के तहत न्यूनतम पेंशन क्या है?",
        "thela lagane wale street vendors ke liye 10000 loan scheme",
        "Atal Pension Yojana"
    ]

    for dq in demo_queries:
        print(f"\n--------------------------------------------------")
        print(f"Demo Query: '{dq}'")
        q_obj = RetrievalQuery(query_text=dq, top_k=3)
        scheme_bm25 = retriever_bm25.retrieve_schemes(q_obj)
        scheme_hybrid = retriever.retrieve_schemes(q_obj)
        chunk_bm25 = retriever_bm25.retrieve(q_obj)

        print(f"  [BM25 Lexical Top Matches]:")
        for idx, sr in enumerate(scheme_bm25, start=1):
            print(f"    {idx}. [{sr.scheme_slug}] {sr.scheme_name} (Score: {sr.aggregate_score})")

        print(f"  [Hybrid Top Matches]:")
        for idx, sr in enumerate(scheme_hybrid, start=1):
            print(f"    {idx}. [{sr.scheme_slug}] {sr.scheme_name} (Score: {sr.aggregate_score})")

        if chunk_bm25:
            top_c = chunk_bm25[0]
            print(f"  [Top BM25 Evidence Chunk]:")
            print(f"     Chunk ID: {top_c.chunk_id} | Section: {top_c.metadata.get('section')}")
            print(f"     Source Tier: {top_c.source_tier} | Sparse Score: {top_c.sparse_score}")
            preview = top_c.content[:140].replace('\n', ' ')
            print(f"     Excerpt: {preview}...")


if __name__ == "__main__":
    main()
