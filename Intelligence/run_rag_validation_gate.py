"""
FIN Phase 5 RAG Validation Gate.
Executes the REAL BAAI/bge-m3 dense embedding pipeline with FAISS vector store,
evaluates offline ground-truth benchmark across:
  1. BM25 Sparse Only
  2. Dense BGE-M3 Only
  3. Hybrid Dense BGE-M3 + BM25
Specifically validates pure Hindi (Devanagari) and Hinglish queries without fabricating metrics.
"""

import json
import sys
import time
from pathlib import Path
import numpy as np

# Fix Windows console UTF-8 printing
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure Intelligence directory is on sys.path for direct script execution and IDE resolution
_INTELLIGENCE_DIR = Path(__file__).resolve().parent
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

try:
    from src.rag.config import RAGConfig
    from src.rag.ingestion import RAGIngestionPipeline
    from src.rag.embeddings import SentenceTransformerEmbeddingModel
    from src.rag.store import FAISSVectorStore
    from src.rag.sparse import BM25Retriever
    from src.rag.retriever import HybridRetriever
    from src.rag.evaluation.benchmark import RetrievalBenchmarkRunner
    from src.rag.provenance import build_provenance_record
except (ImportError, ModuleNotFoundError):
    from Intelligence.src.rag.config import RAGConfig
    from Intelligence.src.rag.ingestion import RAGIngestionPipeline
    from Intelligence.src.rag.embeddings import SentenceTransformerEmbeddingModel
    from Intelligence.src.rag.store import FAISSVectorStore
    from Intelligence.src.rag.sparse import BM25Retriever
    from Intelligence.src.rag.retriever import HybridRetriever
    from Intelligence.src.rag.evaluation.benchmark import RetrievalBenchmarkRunner
    from Intelligence.src.rag.provenance import build_provenance_record


def main():
    print("=" * 60)
    print("FIN Phase 5: RAG Validation Gate (Real BAAI/bge-m3)")
    print("=" * 60)

    # 1. Load Real BGE-M3 Embedding Pipeline
    print("\n[Gate 1/5] Initializing Real BAAI/bge-m3 dense embedding pipeline...")
    t0 = time.time()
    try:
        embedding_model = SentenceTransformerEmbeddingModel(
            model_name="BAAI/bge-m3",
            dimension=1024,
            normalize=True
        )
        # Trigger model load and verify dimension
        dim = embedding_model.dimension
        print(f"  -> Model initialized successfully in {time.time() - t0:.2f}s.")
        print(f"  -> Embedding dimension: {dim} (Confirmed BAAI/bge-m3)")
    except Exception as e:
        print(f"  -> VALIDATION-BLOCKED: Unable to load BAAI/bge-m3 runtime: {e}")
        sys.exit(1)

    # 2. Ingest Validation Corpus
    print("\n[Gate 2/5] Ingesting validation corpus...")
    target_slugs = ["apy", "pmmvy", "pm-svanidhi", "aag", "mj-fapm"]
    t1 = time.time()
    pipeline = RAGIngestionPipeline()
    docs = pipeline.run_ingestion(
        scheme_limit=100,
        faq_limit=200,
        include_slugs=target_slugs,
        include_supplementary=False,
        save_to_disk=False
    )
    print(f"  -> Ingested {len(docs):,} document chunks across target & distractor schemes in {time.time() - t1:.2f}s.")
    # Verify all targets are present
    ingested_slugs = {d.scheme_slug for d in docs}
    for ts in target_slugs:
        assert ts in ingested_slugs, f"Missing target slug: {ts}"
    print(f"  -> Verified all 5 evaluation target schemes present: {target_slugs}")

    # 3. Build Real Dense FAISS Vector Store + BM25 Sparse Index
    print("\n[Gate 3/5] Building Real FAISS Vector Index (dim=1024) & BM25 Sparse Index...")
    t2 = time.time()

    vector_store = FAISSVectorStore(dimension=1024)
    sparse_retriever = BM25Retriever()

    # Index into BM25
    sparse_retriever.fit(docs)

    # Populate metadata & encode with BGE-M3
    contents = [d.content for d in docs]
    meta_list = []
    doc_metadata_map = {}
    for d in docs:
        meta = d.to_dict()
        meta["provenance"] = build_provenance_record(d)
        doc_metadata_map[d.id] = meta
        meta_list.append(meta)

    emb_cache_path = _INTELLIGENCE_DIR / "data" / "processed" / "rag_val_emb_1103.npy"
    if emb_cache_path.exists():
        print(f"  -> Loading precomputed BAAI/bge-m3 embeddings from {emb_cache_path}...")
        embeddings = np.load(emb_cache_path)
        print(f"  -> Loaded embeddings shape: {embeddings.shape}")
    else:
        print(f"  -> Encoding {len(contents)} chunks with BAAI/bge-m3 on CPU...")
        t_enc = time.time()
        embeddings = embedding_model.encode_documents(contents, batch_size=32)
        print(f"  -> Encoded embeddings shape {embeddings.shape} in {time.time() - t_enc:.2f}s.")
        np.save(emb_cache_path, embeddings)

    vector_store.add(embeddings, meta_list)
    print(f"  -> FAISS index size: {vector_store.count} vectors. Total index build time: {time.time() - t2:.2f}s.")

    # 4. Comparative Benchmark Evaluation
    print("\n[Gate 4/5] Running Comparative Ground-Truth Benchmark Evaluation...")

    # Mode A: BM25 Only
    config_bm25 = RAGConfig(
        use_faiss=True,
        embedding_dimension=1024,
        dense_weight=0.0,
        sparse_weight=1.0,
        rerank_top_k=50,
        final_top_k=5
    )
    retriever_bm25 = HybridRetriever(
        config=config_bm25,
        embedding_model=embedding_model,
        vector_store=vector_store,
        sparse_retriever=sparse_retriever
    )
    retriever_bm25._doc_metadata_map = doc_metadata_map
    runner_bm25 = RetrievalBenchmarkRunner(retriever_bm25)
    res_bm25 = runner_bm25.run_benchmark(top_k=5)

    # Mode B: Dense BGE-M3 Only
    config_dense = RAGConfig(
        use_faiss=True,
        embedding_dimension=1024,
        dense_weight=1.0,
        sparse_weight=0.0,
        rerank_top_k=50,
        final_top_k=5
    )
    retriever_dense = HybridRetriever(
        config=config_dense,
        embedding_model=embedding_model,
        vector_store=vector_store,
        sparse_retriever=sparse_retriever
    )
    retriever_dense._doc_metadata_map = doc_metadata_map
    runner_dense = RetrievalBenchmarkRunner(retriever_dense)
    res_dense = runner_dense.run_benchmark(top_k=5)

    # Mode C: Hybrid Dense BGE-M3 + BM25
    config_hybrid = RAGConfig(
        use_faiss=True,
        embedding_dimension=1024,
        dense_weight=0.60,
        sparse_weight=0.40,
        rerank_top_k=50,
        final_top_k=5
    )
    retriever_hybrid = HybridRetriever(
        config=config_hybrid,
        embedding_model=embedding_model,
        vector_store=vector_store,
        sparse_retriever=sparse_retriever
    )
    retriever_hybrid._doc_metadata_map = doc_metadata_map
    runner_hybrid = RetrievalBenchmarkRunner(retriever_hybrid)
    res_hybrid = runner_hybrid.run_benchmark(top_k=5)

    # Print Comparative Results Table
    print("\n" + "=" * 65)
    print("COMPARATIVE BENCHMARK EVALUATION RESULTS")
    print("=" * 65)
    print(f"{'Retrieval Mode':<22} | {'Hit@1':<8} | {'Hit@3':<8} | {'Hit@5':<8} | {'MRR':<8}")
    print("-" * 65)
    print(f"{'BM25 (Sparse Only)':<22} | {res_bm25['overall']['hit@1']:<8.4f} | {res_bm25['overall']['hit@3']:<8.4f} | {res_bm25['overall']['hit@5']:<8.4f} | {res_bm25['overall']['mrr']:<8.4f}")
    print(f"{'Dense BGE-M3 Only':<22} | {res_dense['overall']['hit@1']:<8.4f} | {res_dense['overall']['hit@3']:<8.4f} | {res_dense['overall']['hit@5']:<8.4f} | {res_dense['overall']['mrr']:<8.4f}")
    print(f"{'Hybrid (BGE-M3+BM25)':<22} | {res_hybrid['overall']['hit@1']:<8.4f} | {res_hybrid['overall']['hit@3']:<8.4f} | {res_hybrid['overall']['hit@5']:<8.4f} | {res_hybrid['overall']['mrr']:<8.4f}")
    print("=" * 65)

    # 5. Multilingual Specific Breakdown (Hindi & Hinglish)
    print("\n[Gate 5/5] Deep-Dive: Pure Hindi (Devanagari) & Hinglish Performance...")
    print("\n--- Pure Hindi (Devanagari) Queries ---")
    for q_bm, q_de, q_hy in zip(res_bm25["detailed_queries"], res_dense["detailed_queries"], res_hybrid["detailed_queries"]):
        if q_bm["query_type"] == "hindi":
            print(f"  Query: '{q_bm['query_text']}' [Target: {q_bm['expected_slug']}]")
            print(f"    - BM25:   Hit@1={q_bm['hit@1']} | Hit@5={q_bm['hit@5']} | MRR={q_bm['mrr']:.4f} | Preds={q_bm['predicted_slugs']}")
            print(f"    - Dense:  Hit@1={q_de['hit@1']} | Hit@5={q_de['hit@5']} | MRR={q_de['mrr']:.4f} | Preds={q_de['predicted_slugs']}")
            print(f"    - Hybrid: Hit@1={q_hy['hit@1']} | Hit@5={q_hy['hit@5']} | MRR={q_hy['mrr']:.4f} | Preds={q_hy['predicted_slugs']}")

    print("\n--- Hinglish (Code-Mixed) Queries ---")
    for q_bm, q_de, q_hy in zip(res_bm25["detailed_queries"], res_dense["detailed_queries"], res_hybrid["detailed_queries"]):
        if q_bm["query_type"] == "hinglish":
            print(f"  Query: '{q_bm['query_text']}' [Target: {q_bm['expected_slug']}]")
            print(f"    - BM25:   Hit@1={q_bm['hit@1']} | Hit@5={q_bm['hit@5']} | MRR={q_bm['mrr']:.4f} | Preds={q_bm['predicted_slugs']}")
            print(f"    - Dense:  Hit@1={q_de['hit@1']} | Hit@5={q_de['hit@5']} | MRR={q_de['mrr']:.4f} | Preds={q_de['predicted_slugs']}")
            print(f"    - Hybrid: Hit@1={q_hy['hit@1']} | Hit@5={q_hy['hit@5']} | MRR={q_hy['mrr']:.4f} | Preds={q_hy['predicted_slugs']}")

    print("\n--- Query Type Breakdown (Hybrid Mode) ---")
    print(json.dumps(res_hybrid["by_query_type"], indent=2))

    print("\n==================================================")
    print("RAG VALIDATION GATE COMPLETE")
    print("==================================================")


if __name__ == "__main__":
    main()
