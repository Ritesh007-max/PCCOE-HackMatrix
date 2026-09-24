"""
Unit tests for FIN Embedding Abstraction.
Verifies dimension consistency, deterministic mock generation, and batch handling.
"""

import sys
from pathlib import Path

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

import unittest
import numpy as np
from src.rag.embeddings import (
    DeterministicMockEmbeddingModel,
    SentenceTransformerEmbeddingModel,
    get_embedding_model,
)
from src.rag.config import RAGConfig


class TestEmbeddings(unittest.TestCase):
    """Tests dense embedding models and mock generators."""

    def test_mock_embedding_dimension(self):
        """Tests that mock model generates exact requested dimensions."""
        model = DeterministicMockEmbeddingModel(dimension=64)
        self.assertEqual(model.dimension, 64)

        query_vec = model.encode_query("scholarship for farmers")
        self.assertEqual(query_vec.shape, (64,))
        self.assertEqual(query_vec.dtype, np.float32)

        # Batch encoding
        texts = ["Text one", "Text two", "Text three"]
        doc_vecs = model.encode_documents(texts)
        self.assertEqual(doc_vecs.shape, (3, 64))

    def test_mock_embedding_deterministic_repeatability(self):
        """Tests that identical text yields identical vectors (pure and reproducible)."""
        model = DeterministicMockEmbeddingModel(dimension=128)
        text = "Pradhan Mantri Awas Yojana Rural Housing"
        v1 = model.encode_query(text)
        v2 = model.encode_query(text)
        np.testing.assert_array_almost_equal(v1, v2)

    def test_empty_text_embedding_handling(self):
        """Tests that empty text produces zero vectors safely."""
        model = DeterministicMockEmbeddingModel(dimension=64)
        v_empty = model.encode_query("")
        self.assertEqual(v_empty.shape, (64,))
        self.assertEqual(np.count_nonzero(v_empty), 0)

        docs_empty = model.encode_documents([])
        self.assertEqual(docs_empty.shape, (0, 64))

    def test_get_embedding_model_factory(self):
        """Tests factory selection."""
        config = RAGConfig(embedding_dimension=128)
        model = get_embedding_model(config, force_mock=True)
        self.assertIsInstance(model, DeterministicMockEmbeddingModel)
        self.assertEqual(model.dimension, 128)


if __name__ == "__main__":
    unittest.main()
