"""
Tests for PolicySetu RAG Fusion Engine (AI/src/rag/fusion.py).
Validates min-max normalization, weighted hybrid fusion, RRF, and tie-breaking.
"""

import sys
from pathlib import Path

_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

import unittest
from src.rag.fusion import normalize_scores, fuse_results, reciprocal_rank_fusion
from src.rag.models import SourceTier


class TestRAGFusion(unittest.TestCase):
    """Test suite for dense-sparse result fusion algorithms."""

    def test_normalize_scores_empty(self):
        """Empty input dict should safely return empty dict."""
        self.assertEqual(normalize_scores({}), {})

    def test_normalize_scores_uniform(self):
        """Uniform scores should normalize cleanly to 1.0 if positive."""
        scores = {"chunk_1": 5.0, "chunk_2": 5.0}
        norm = normalize_scores(scores)
        self.assertEqual(norm["chunk_1"], 1.0)
        self.assertEqual(norm["chunk_2"], 1.0)

    def test_normalize_scores_range(self):
        """Scores with a range should scale linearly to [0.0, 1.0]."""
        scores = {"c1": 10.0, "c2": 20.0, "c3": 30.0}
        norm = normalize_scores(scores)
        self.assertAlmostEqual(norm["c1"], 0.0)
        self.assertAlmostEqual(norm["c2"], 0.5)
        self.assertAlmostEqual(norm["c3"], 1.0)

    def test_fuse_results_weights(self):
        """Validates that weighted score fusion correctly weights dense and sparse scores."""
        dense_results = [("c1", 0.9, {}), ("c2", 0.1, {})]
        sparse_results = [("c1", 5.0, 0), ("c2", 15.0, 1)]
        metadata_map = {
            "c1": {"id": "c1", "scheme_slug": "scheme_a", "content": "alpha"},
            "c2": {"id": "c2", "scheme_slug": "scheme_b", "content": "beta"},
        }

        # c1 dense norm = 1.0, sparse norm = 0.0 -> fused = 0.70 * 1.0 + 0.30 * 0.0 = 0.70
        # c2 dense norm = 0.0, sparse norm = 1.0 -> fused = 0.70 * 0.0 + 0.30 * 1.0 = 0.30
        fused = fuse_results(
            dense_results=dense_results,
            sparse_results=sparse_results,
            metadata_map=metadata_map,
            dense_weight=0.70,
            sparse_weight=0.30,
            top_k=5
        )

        self.assertEqual(len(fused), 2)
        self.assertEqual(fused[0].chunk_id, "c1")
        self.assertAlmostEqual(fused[0].fused_score, 0.70, places=2)
        self.assertEqual(fused[1].chunk_id, "c2")
        self.assertAlmostEqual(fused[1].fused_score, 0.30, places=2)

    def test_fuse_results_deterministic_tiebreak(self):
        """Verifies deterministic sorting by chunk_id on score ties."""
        dense_results = [("chunk_z", 0.5, {}), ("chunk_a", 0.5, {})]
        sparse_results = [("chunk_z", 10.0, 0), ("chunk_a", 10.0, 1)]
        metadata_map = {
            "chunk_z": {"id": "chunk_z", "scheme_slug": "slug_z"},
            "chunk_a": {"id": "chunk_a", "scheme_slug": "slug_a"},
        }

        fused = fuse_results(
            dense_results=dense_results,
            sparse_results=sparse_results,
            metadata_map=metadata_map,
            top_k=2
        )
        self.assertEqual(len(fused), 2)
        # Identical fused score -> tie break alphabetically by chunk_id
        self.assertEqual(fused[0].chunk_id, "chunk_a")
        self.assertEqual(fused[1].chunk_id, "chunk_z")

    def test_reciprocal_rank_fusion(self):
        """Verifies RRF computes sum of reciprocal ranks."""
        dense_results = [("c1", 0.9, {}), ("c2", 0.8, {})]
        sparse_results = [("c2", 10.0, 0), ("c1", 5.0, 1)]
        metadata_map = {
            "c1": {"id": "c1", "scheme_slug": "scheme_1"},
            "c2": {"id": "c2", "scheme_slug": "scheme_2"},
        }

        # For k=60:
        # c1: dense rank 1 (1/61) + sparse rank 2 (1/62) = 0.016393 + 0.016129 = 0.032522
        # c2: dense rank 2 (1/62) + sparse rank 1 (1/61) = 0.032522
        rrf = reciprocal_rank_fusion(
            dense_results=dense_results,
            sparse_results=sparse_results,
            metadata_map=metadata_map,
            k=60,
            top_k=5
        )
        self.assertEqual(len(rrf), 2)
        self.assertAlmostEqual(rrf[0].fused_score, 0.03252, places=4)


if __name__ == "__main__":
    unittest.main()
