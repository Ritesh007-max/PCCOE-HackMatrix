"""
Tests for FIN Multi-Scheme Query Decomposition & Interleaving (Intelligence/src/rag/entity_decomposition.py).
Validates comparison parsing, sub-query generation, round-robin interleaving,
and multi-entity result metadata grouping.
"""

import sys
from pathlib import Path
import unittest

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.rag.config import RAGConfig
from src.rag.embeddings import DeterministicMockEmbeddingModel
from src.rag.models import (
    ContentType,
    RAGDocument,
    RetrievalQuery,
    SchemeRetrievalResult,
    SourceTier,
)
from src.rag.entity_decomposition import MultiSchemeDecomposer
from src.rag.retriever import HybridRetriever


class TestMultiSchemeRetrieval(unittest.TestCase):
    """Test suite for multi-scheme query decomposition and interleaved ranking."""

    def setUp(self):
        self.decomposer = MultiSchemeDecomposer()
        self.config = RAGConfig(use_faiss=False, embedding_dimension=32)
        self.retriever = HybridRetriever(
            config=self.config,
            embedding_model=DeterministicMockEmbeddingModel(dimension=32)
        )

        # Index two competing schemes: APY and PM-KISAN
        docs = [
            RAGDocument(
                id="chk_apy_1",
                content="Atal Pension Yojana APY is an unorganized pension scheme offering monthly pension after 60.",
                source_dataset="schemes_canonical",
                source_tier=SourceTier.PRIMARY_SCHEME.value,
                source_url="https://myscheme.gov.in/apy",
                scheme_slug="apy",
                scheme_name="Atal Pension Yojana",
                content_type=ContentType.SCHEME_OVERVIEW.value,
            ),
            RAGDocument(
                id="chk_pmkisan_1",
                content="Pradhan Mantri Kisan Samman Nidhi PM-KISAN provides 6000 rupees income support to landholding farmers.",
                source_dataset="schemes_canonical",
                source_tier=SourceTier.PRIMARY_SCHEME.value,
                source_url="https://myscheme.gov.in/pm-kisan",
                scheme_slug="pm-kisan",
                scheme_name="Pradhan Mantri Kisan Samman Nidhi",
                content_type=ContentType.SCHEME_OVERVIEW.value,
            )
        ]
        self.retriever.index_documents(docs)

    def test_comparison_pattern_detection(self):
        """Validates that various comparison expressions decompose into distinct sub-entities."""
        test_queries = [
            ("APY vs PM Kisan", 2),
            ("Compare Atal Pension and PM Kisan", 2),
            ("Atal Pension aur PM Kisan ka difference", 2),
            ("Which is better: Atal Pension Yojana or PM Kisan Samman Nidhi", 2),
            ("Which is better for pension vs farmer support", 2),
        ]
        for query, expected_entities_count in test_queries:
            decomp = self.decomposer.decompose(query)
            self.assertTrue(decomp.is_multi_entity, f"Failed to detect multi-entity intent for: '{query}'")
            self.assertEqual(len(decomp.entities), expected_entities_count)

    def test_interleaved_fairness_no_starvation(self):
        """Interleave prevents high-scoring scheme from starving lower-scoring competitor."""
        list_a = [
            SchemeRetrievalResult(scheme_slug="apy", scheme_name="Atal Pension Yojana", aggregate_score=0.95),
            SchemeRetrievalResult(scheme_slug="apy_sub", scheme_name="APY Secondary", aggregate_score=0.90),
        ]
        list_b = [
            SchemeRetrievalResult(scheme_slug="pm-kisan", scheme_name="PM Kisan", aggregate_score=0.85),
            SchemeRetrievalResult(scheme_slug="pmk_sub", scheme_name="PMK Secondary", aggregate_score=0.80),
        ]

        merged = self.decomposer.interleave_results([list_a, list_b], total_limit=4)
        slugs = [item.scheme_slug for item in merged]

        # First item from A, then first item from B
        self.assertEqual(slugs[0], "apy")
        self.assertEqual(slugs[1], "pm-kisan")
        self.assertIn("apy", slugs)
        self.assertIn("pm-kisan", slugs)

    def test_multi_scheme_retrieve_schemes_end_to_end(self):
        """Full HybridRetriever.retrieve_schemes returns both schemes with structured metadata."""
        query = RetrievalQuery(
            query_text="Compare Atal Pension Yojana and PM Kisan Samman Nidhi",
            top_k=5
        )
        results = self.retriever.retrieve_schemes(query)
        retrieved_slugs = [r.scheme_slug for r in results]

        self.assertIn("apy", retrieved_slugs)
        self.assertIn("pm-kisan", retrieved_slugs)

        # Check multi-entity metadata structure (Part 9 requirement)
        first_res = results[0]
        self.assertTrue(first_res.source_metadata.get("is_multi_entity"))
        self.assertIn("entities", first_res.source_metadata)
        entities_meta = first_res.source_metadata["entities"]
        self.assertGreaterEqual(len(entities_meta), 2)
        entity_texts = [e["query_entity"] for e in entities_meta]
        self.assertTrue(any("Atal Pension" in t for t in entity_texts))
        self.assertTrue(any("PM Kisan" in t for t in entity_texts))


if __name__ == "__main__":
    unittest.main()
