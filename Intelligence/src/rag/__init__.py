"""
FIN RAG Knowledge Base and Hybrid Retrieval Package.
Exports core retrieval coordinator, data models, chunkers, and evaluation harnesses.
"""

from .models import (
    SourceTier,
    ContentType,
    RAGDocument,
    RetrievedChunk,
    RetrievalQuery,
    SchemeRetrievalResult,
    RetrievalIntent,
)
from .config import RAGConfig, DEFAULT_RAG_CONFIG
from .chunking import chunk_scheme_record, chunk_faq_record, split_text_with_overlap
from .ingestion import RAGIngestionPipeline
from .embeddings import (
    EmbeddingModel,
    SentenceTransformerEmbeddingModel,
    DeterministicMockEmbeddingModel,
    get_embedding_model,
)
from .sparse import BM25Retriever, tokenize_text
from .store import VectorStore, FAISSVectorStore, NumpyVectorStore, create_vector_store
from .filters import normalize_query_intent, build_metadata_filter
from .fusion import fuse_results, reciprocal_rank_fusion
from .reranker import BaseReranker, MetadataAwareReranker
from .retriever import HybridRetriever
from .provenance import (
    build_provenance_record,
    compute_content_hash,
    generate_stable_chunk_id,
    verify_provenance_integrity,
)

__all__ = [
    "SourceTier",
    "ContentType",
    "RAGDocument",
    "RetrievedChunk",
    "RetrievalQuery",
    "SchemeRetrievalResult",
    "RetrievalIntent",
    "RAGConfig",
    "DEFAULT_RAG_CONFIG",
    "chunk_scheme_record",
    "chunk_faq_record",
    "split_text_with_overlap",
    "RAGIngestionPipeline",
    "EmbeddingModel",
    "SentenceTransformerEmbeddingModel",
    "DeterministicMockEmbeddingModel",
    "get_embedding_model",
    "BM25Retriever",
    "tokenize_text",
    "VectorStore",
    "FAISSVectorStore",
    "NumpyVectorStore",
    "create_vector_store",
    "normalize_query_intent",
    "build_metadata_filter",
    "fuse_results",
    "reciprocal_rank_fusion",
    "BaseReranker",
    "MetadataAwareReranker",
    "HybridRetriever",
    "build_provenance_record",
    "compute_content_hash",
    "generate_stable_chunk_id",
    "verify_provenance_integrity",
]
