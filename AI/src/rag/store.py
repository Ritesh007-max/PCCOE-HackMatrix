"""
PolicySetu Vector Store Abstraction Layer.
Provides vector indexing and search with FAISS (MVP / Production Default) and
Numpy (fallback / testing) backends. Decoupled from proprietary platforms.
"""

from abc import ABC, abstractmethod
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast
import numpy as np


class VectorStore(ABC):
    """Abstract Vector Store Interface."""

    @abstractmethod
    def add(self, vectors: np.ndarray, metadata: List[Dict[str, Any]]) -> None:
        """Adds dense vectors and associated metadata to the index."""
        pass

    @abstractmethod
    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        filter_fn: Optional[Any] = None
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Searches for top_k nearest vectors.
        Returns: List of tuples (chunk_id, similarity_score, metadata)
        """
        pass

    @property
    @abstractmethod
    def count(self) -> int:
        """Returns total number of indexed vectors."""
        pass

    @abstractmethod
    def save(self, directory: str) -> None:
        """Persists index and metadata to disk."""
        pass

    @classmethod
    @abstractmethod
    def load(cls, directory: str) -> "VectorStore":
        """Loads index and metadata from disk."""
        pass


class FAISSVectorStore(VectorStore):
    """
    Production-grade FAISS vector index backend.
    Uses IndexFlatIP on L2-normalized embeddings for exact inner-product (cosine) search.
    """

    def __init__(self, dimension: int = 1024):
        self.dimension = dimension
        self._index = None
        self._metadata: List[Dict[str, Any]] = []
        self._init_index()

    def _init_index(self):
        try:
            import faiss
            # IndexFlatIP computes inner product (cosine similarity on normalized vectors)
            self._index = faiss.IndexFlatIP(self.dimension)
        except ImportError:
            raise RuntimeError("FAISS is not installed. Install faiss-cpu or use NumpyVectorStore fallback.")

    @property
    def count(self) -> int:
        return self._index.ntotal if self._index is not None else 0

    def add(self, vectors: np.ndarray, metadata: List[Dict[str, Any]]) -> None:
        if len(vectors) == 0:
            return
        if vectors.shape[1] != self.dimension:
            raise ValueError(
                f"Vector dimension mismatch: expected {self.dimension}, got {vectors.shape[1]}"
            )
        # Ensure float32 and C-contiguous
        vec_f32 = np.ascontiguousarray(vectors, dtype=np.float32)
        # Normalize vectors for cosine similarity
        norms = np.linalg.norm(vec_f32, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        vec_normalized = vec_f32 / norms

        if self._index is None:
            self._init_index()
        assert self._index is not None
        cast(Any, self._index).add(vec_normalized)
        self._metadata.extend(metadata)

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        filter_fn: Optional[Any] = None
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        if self.count == 0 or query_vector is None or self._index is None:
            return []

        # Format and normalize query vector
        q_vec = np.ascontiguousarray(query_vector.reshape(1, -1), dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 0:
            q_vec = (q_vec / q_norm).astype(np.float32)

        # Search more candidates if post-filtering is active
        fetch_k = min(self.count, top_k * 5 if filter_fn else top_k)
        scores, indices = cast(Any, self._index).search(q_vec, fetch_k)

        results: List[Tuple[str, float, Dict[str, Any]]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._metadata):
                continue
            meta = self._metadata[idx]
            if filter_fn and not filter_fn(meta):
                continue

            chunk_id = meta.get("id") or meta.get("chunk_id", f"chk_{idx}")
            # Clamp cosine score between -1.0 and 1.0
            clamped_score = float(max(-1.0, min(1.0, score)))
            results.append((chunk_id, round(clamped_score, 4), meta))
            if len(results) >= top_k:
                break

        return results

    def save(self, directory: str) -> None:
        import faiss
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)

        index_file = str(dir_path / "faiss_index.bin")
        meta_file = str(dir_path / "faiss_meta.json")

        assert self._index is not None
        faiss.write_index(cast(Any, self._index), index_file)
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({
                "dimension": self.dimension,
                "metadata": self._metadata
            }, f, ensure_ascii=False)

    @classmethod
    def load(cls, directory: str) -> "FAISSVectorStore":
        import faiss
        dir_path = Path(directory)
        index_file = str(dir_path / "faiss_index.bin")
        meta_file = str(dir_path / "faiss_meta.json")

        with open(meta_file, "r", encoding="utf-8") as f:
            meta_data = json.load(f)

        store = cls(dimension=meta_data["dimension"])
        store._index = faiss.read_index(index_file)
        store._metadata = meta_data["metadata"]
        return store


class NumpyVectorStore(VectorStore):
    """
    Lightweight, portable in-memory vector store using pure NumPy matrix math.
    Serves as fallback backend and for deterministic unit testing.
    """

    def __init__(self, dimension: int = 1024):
        self.dimension = dimension
        self._vectors: np.ndarray = np.empty((0, dimension), dtype=np.float32)
        self._metadata: List[Dict[str, Any]] = []

    @property
    def count(self) -> int:
        return len(self._metadata)

    def add(self, vectors: np.ndarray, metadata: List[Dict[str, Any]]) -> None:
        if len(vectors) == 0:
            return
        if vectors.shape[1] != self.dimension:
            raise ValueError(
                f"Vector dimension mismatch: expected {self.dimension}, got {vectors.shape[1]}"
            )
        vec_f32 = np.ascontiguousarray(vectors, dtype=np.float32)
        # Normalize
        norms = np.linalg.norm(vec_f32, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        vec_normalized = vec_f32 / norms

        if self._vectors.shape[0] == 0:
            self._vectors = vec_normalized
        else:
            self._vectors = np.vstack([self._vectors, vec_normalized])
        self._metadata.extend(metadata)

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        filter_fn: Optional[Any] = None
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        if self.count == 0 or query_vector is None:
            return []

        q_vec = np.ascontiguousarray(query_vector.flatten(), dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 0:
            q_vec = q_vec / q_norm

        # Matrix-vector dot product computes cosine similarities
        similarities = np.dot(self._vectors, q_vec)

        # Sort indices descending
        sorted_indices = np.argsort(-similarities)

        results: List[Tuple[str, float, Dict[str, Any]]] = []
        for idx in sorted_indices:
            meta = self._metadata[idx]
            if filter_fn and not filter_fn(meta):
                continue
            chunk_id = meta.get("id") or meta.get("chunk_id", f"chk_{idx}")
            score = float(max(-1.0, min(1.0, similarities[idx])))
            results.append((chunk_id, round(score, 4), meta))
            if len(results) >= top_k:
                break

        return results

    def save(self, directory: str) -> None:
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        npz_file = dir_path / "numpy_index.npz"
        meta_file = dir_path / "numpy_meta.json"

        np.savez_compressed(npz_file, vectors=self._vectors)
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({
                "dimension": self.dimension,
                "metadata": self._metadata
            }, f, ensure_ascii=False)

    @classmethod
    def load(cls, directory: str) -> "NumpyVectorStore":
        dir_path = Path(directory)
        npz_file = dir_path / "numpy_index.npz"
        meta_file = dir_path / "numpy_meta.json"

        with open(meta_file, "r", encoding="utf-8") as f:
            meta_data = json.load(f)

        data = np.load(npz_file)
        store = cls(dimension=meta_data["dimension"])
        store._vectors = data["vectors"]
        store._metadata = meta_data["metadata"]
        return store


def create_vector_store(
    dimension: int = 1024,
    use_faiss: bool = True
) -> VectorStore:
    """Factory selecting FAISS by default with graceful fallback to Numpy."""
    if use_faiss:
        try:
            return FAISSVectorStore(dimension=dimension)
        except RuntimeError:
            return NumpyVectorStore(dimension=dimension)
    return NumpyVectorStore(dimension=dimension)
