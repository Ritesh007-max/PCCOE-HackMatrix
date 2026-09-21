"""
Unit tests for PolicySetu Vector Store Abstraction.
Verifies FAISS backend and Numpy fallback backend indexing, search, and persistence.
"""

import sys
from pathlib import Path

_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

import unittest
import tempfile
from pathlib import Path
import numpy as np
from src.rag.store import FAISSVectorStore, NumpyVectorStore, create_vector_store


class TestVectorStore(unittest.TestCase):
    """Tests FAISS and Numpy vector store implementations."""

    def test_faiss_vector_store(self):
        """Tests FAISS vector indexing, cosine search, and metadata retrieval."""
        dim = 8
        store = FAISSVectorStore(dimension=dim)

        v1 = np.array([1, 0, 0, 0, 0, 0, 0, 0], dtype=np.float32)
        v2 = np.array([0, 1, 0, 0, 0, 0, 0, 0], dtype=np.float32)
        v3 = np.array([0, 0, 1, 0, 0, 0, 0, 0], dtype=np.float32)

        store.add(np.vstack([v1, v2, v3]), [
            {"id": "c1", "name": "One"},
            {"id": "c2", "name": "Two"},
            {"id": "c3", "name": "Three"},
        ])
        self.assertEqual(store.count, 3)

        # Search with vector close to v2
        q = np.array([0.1, 0.9, 0, 0, 0, 0, 0, 0], dtype=np.float32)
        results = store.search(q, top_k=2)

        self.assertGreater(len(results), 0)
        self.assertEqual(results[0][0], "c2")
        self.assertGreater(results[0][1], 0.8)

    def test_numpy_vector_store(self):
        """Tests Numpy fallback vector indexing, cosine search, and metadata retrieval."""
        dim = 8
        store = NumpyVectorStore(dimension=dim)

        v1 = np.array([1, 0, 0, 0, 0, 0, 0, 0], dtype=np.float32)
        v2 = np.array([0, 1, 0, 0, 0, 0, 0, 0], dtype=np.float32)

        store.add(np.vstack([v1, v2]), [
            {"id": "c1", "name": "One"},
            {"id": "c2", "name": "Two"},
        ])
        self.assertEqual(store.count, 2)

        # Search close to v1
        q = np.array([0.95, 0.05, 0, 0, 0, 0, 0, 0], dtype=np.float32)
        results = store.search(q, top_k=1)
        self.assertEqual(results[0][0], "c1")

    def test_dimension_mismatch_raises_error(self):
        """Tests that adding mismatched vector dimensions raises ValueError."""
        store = NumpyVectorStore(dimension=16)
        bad_vec = np.zeros((1, 8), dtype=np.float32)
        with self.assertRaises(ValueError):
            store.add(bad_vec, [{"id": "bad"}])

    def test_save_and_load_persistence(self):
        """Tests saving and reloading index from disk."""
        dim = 4
        store = NumpyVectorStore(dimension=dim)
        store.add(np.eye(4, dtype=np.float32), [{"id": f"c_{i}"} for i in range(4)])

        with tempfile.TemporaryDirectory() as tmp_dir:
            store.save(tmp_dir)
            reloaded = NumpyVectorStore.load(tmp_dir)
            self.assertEqual(reloaded.count, 4)
            res = reloaded.search(np.array([1, 0, 0, 0], dtype=np.float32), top_k=1)
            self.assertEqual(res[0][0], "c_0")


if __name__ == "__main__":
    unittest.main()
