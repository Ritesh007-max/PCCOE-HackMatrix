"""
Tests for PolicySetu RAG Evaluation Suite (AI/src/rag/evaluation/).
Validates Hit@K, MRR, batch evaluation, and benchmark execution harness.
"""

import unittest
from src.rag.evaluation.metrics import compute_hit_at_k, compute_mrr, evaluate_batch
from src.rag.evaluation.test_cases import RetrievalTestCase
from src.rag.evaluation.benchmark import RetrievalBenchmarkRunner
from src.rag.retriever import HybridRetriever
from src.rag.config import RAGConfig
from src.rag.embeddings import DeterministicMockEmbeddingModel
from src.rag.models import RAGDocument, SourceTier, ContentType


class TestRAGEvaluation(unittest.TestCase):
    """Test suite for offline information retrieval evaluation metrics and runner."""

    def test_compute_hit_at_k(self):
        """Validates Hit@K binary metric."""
        retrieved = ["slug_a", "slug_b", "slug_c", "slug_d"]
        self.assertEqual(compute_hit_at_k(retrieved, "slug_a", 1), 1.0)
        self.assertEqual(compute_hit_at_k(retrieved, "slug_b", 1), 0.0)
        self.assertEqual(compute_hit_at_k(retrieved, "slug_b", 3), 1.0)
        self.assertEqual(compute_hit_at_k(retrieved, "slug_d", 3), 0.0)
        self.assertEqual(compute_hit_at_k(retrieved, "slug_d", 5), 1.0)
        self.assertEqual(compute_hit_at_k(retrieved, "slug_not_there", 5), 0.0)

    def test_compute_mrr(self):
        """Validates Mean Reciprocal Rank computation."""
        retrieved = ["slug_1", "slug_2", "slug_3"]
        self.assertEqual(compute_mrr(retrieved, "slug_1"), 1.0)
        self.assertEqual(compute_mrr(retrieved, "slug_2"), 0.5)
        self.assertEqual(compute_mrr(retrieved, "slug_3"), 1.0 / 3.0)
        self.assertEqual(compute_mrr(retrieved, "slug_missing"), 0.0)

    def test_evaluate_batch(self):
        """Validates batch metric aggregation across multiple queries."""
        predictions = [
            ["a", "b", "c"],  # target 'a': hit@1=1, hit@3=1, rr=1.0
            ["b", "a", "c"],  # target 'a': hit@1=0, hit@3=1, rr=0.5
            ["x", "y", "z"],  # target 'a': hit@1=0, hit@3=0, rr=0.0
        ]
        ground_truths = ["a", "a", "a"]
        res = evaluate_batch(predictions, ground_truths, k_list=(1, 3))
        # Hit@1 = 1 / 3 = 0.3333
        # Hit@3 = 2 / 3 = 0.6667
        # MRR = (1.0 + 0.5 + 0.0) / 3 = 0.5
        self.assertAlmostEqual(res["hit@1"], 0.3333, places=3)
        self.assertAlmostEqual(res["hit@3"], 0.6667, places=3)
        self.assertAlmostEqual(res["mrr"], 0.5, places=3)
        self.assertEqual(res["total_queries"], 3)

    def test_benchmark_runner_mock(self):
        """Validates benchmark runner runs test cases and computes report."""
        config = RAGConfig(use_faiss=False, embedding_dimension=32)
        retriever = HybridRetriever(
            config=config,
            embedding_model=DeterministicMockEmbeddingModel(dimension=32)
        )

        # Index two sample docs
        docs = [
            RAGDocument(
                id="doc_apy",
                content="Atal Pension Yojana APY national old age pension scheme for unorganised workers.",
                source_dataset="schemes_canonical",
                source_tier=SourceTier.PRIMARY_SCHEME.value,
                scheme_slug="apy",
                scheme_name="Atal Pension Yojana",
                content_type=ContentType.SCHEME_OVERVIEW.value
            ),
            RAGDocument(
                id="doc_pmmvy",
                content="Pradhan Mantri Matru Vandana Yojana PMMVY maternity financial support.",
                source_dataset="schemes_canonical",
                source_tier=SourceTier.PRIMARY_SCHEME.value,
                scheme_slug="pmmvy",
                scheme_name="Pradhan Mantri Matru Vandana Yojana",
                content_type=ContentType.SCHEME_OVERVIEW.value
            ),
        ]
        retriever.index_documents(docs)

        test_cases = [
            RetrievalTestCase(
                query_id="TEST_01",
                query_text="Atal Pension Yojana pension",
                expected_scheme_slug="apy",
                query_type="exact_name"
            ),
            RetrievalTestCase(
                query_id="TEST_02",
                query_text="maternity support PMMVY",
                expected_scheme_slug="pmmvy",
                query_type="exact_name"
            ),
        ]

        runner = RetrievalBenchmarkRunner(retriever)
        report = runner.run_benchmark(test_cases=test_cases, top_k=5)

        self.assertEqual(report["status"], "SUCCESS")
        self.assertIn("overall", report)
        self.assertIn("hit@1", report["overall"])
        self.assertIn("mrr", report["overall"])
        self.assertEqual(report["overall"]["total_queries"], 2)


if __name__ == "__main__":
    unittest.main()
