"""
PolicySetu RAG Configuration.
Centralized, configurable parameters for chunking, embeddings, dense/sparse search,
fusion weighting, reranking, and file paths.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class RAGConfig:
    """Configuration container for RAG retrieval and indexing."""

    # Chunking parameters
    chunk_size: int = 600
    chunk_overlap: int = 100
    min_chunk_length: int = 30

    # Retrieval candidate counts
    dense_top_k: int = 50
    sparse_top_k: int = 50
    final_top_k: int = 10
    rerank_top_k: int = 50

    # Hybrid fusion weights (normalized)
    dense_weight: float = 0.70
    sparse_weight: float = 0.30

    # Embedding settings
    embedding_model_name: str = "BAAI/bge-m3"
    embedding_dimension: int = 1024
    embedding_batch_size: int = 64
    normalize_embeddings: bool = True

    # Vector store settings
    use_faiss: bool = True
    vector_metric: str = "cosine"  # "cosine" or "inner_product"

    # Storage paths
    processed_rag_dir: str = "data/processed/rag"
    index_dir: str = "data/indexes"

    # Base workspace path (calculated relative to AI root)
    ai_root: Optional[str] = None

    def __post_init__(self):
        if self.ai_root is None:
            # Resolves AI directory
            self.ai_root = str(Path(__file__).resolve().parents[2])

        # Normalize relative paths against ai_root
        processed_path = Path(self.processed_rag_dir)
        if not processed_path.is_absolute():
            self.processed_rag_dir = str(Path(self.ai_root) / processed_path)

        index_path = Path(self.index_dir)
        if not index_path.is_absolute():
            self.index_dir = str(Path(self.ai_root) / index_path)

        # Ensure directories exist
        Path(self.processed_rag_dir).mkdir(parents=True, exist_ok=True)
        Path(self.index_dir).mkdir(parents=True, exist_ok=True)


# Default global configuration instance
DEFAULT_RAG_CONFIG = RAGConfig()
