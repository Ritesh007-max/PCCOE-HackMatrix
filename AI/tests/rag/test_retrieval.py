"""
Tests for PolicySetu Hybrid Retriever (AI/src/rag/retriever.py).
Validates end-to-end chunk retrieval, deduplicated scheme-level views,
metadata filtering, and index save/load persistence.
"""

import tempfile
import sys
from pathlib import Path

_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

import unittest
from pathlib import Path
from src.rag.config import RAGConfig
from src.rag.embeddings import DeterministicMockEmbeddingModel
from src.rag.models import (
    ContentType,
    RAGDocument,
    RetrievalQuery,
    SourceTier,
)
from src.rag.retriever import HybridRetriever
from src.rag.provenance import verify_provenance_integrity


class TestHybridRetriever(unittest.TestCase):
    """Test suite for the hybrid retrieval coordinator."""

    def setUp(self):
        self.config = RAGConfig(use_faiss=True, embedding_dimension=32)
        self.embedding_model = DeterministicMockEmbeddingModel(dimension=32)
        self.retriever = HybridRetriever(
            config=self.config,
            embedding_model=self.embedding_model
        )

        # Build sample corpus
        self.docs = [
            RAGDocument(
                id="chk_apy_overview",
                content="Atal Pension Yojana APY is a government pension scheme for workers in the unorganised sector.",
                source_dataset="schemes_canonical",
                source_tier=SourceTier.PRIMARY_SCHEME.value,
                source_url="https://www.myscheme.gov.in/schemes/apy",
                source_document="schemes.csv",
                scheme_slug="apy",
                scheme_name="Atal Pension Yojana",
                section="scheme_overview",
                content_type=ContentType.SCHEME_OVERVIEW.value,
                state="All India",
                category="All",
                beneficiary_type="Senior Citizens"
            ),
            RAGDocument(
                id="chk_apy_eligibility",
                content="The applicant must be an Indian citizen aged between 18 and 40 years with a valid bank account.",
                source_dataset="schemes_canonical",
                source_tier=SourceTier.PRIMARY_SCHEME.value,
                source_url="https://www.myscheme.gov.in/schemes/apy",
                source_document="schemes.csv",
                scheme_slug="apy",
                scheme_name="Atal Pension Yojana",
                section="eligibility",
                content_type=ContentType.ELIGIBILITY.value,
                state="All India"
            ),
            RAGDocument(
                id="chk_pmsvanidhi_overview",
                content="PM SVANidhi PM Street Vendor AtmaNirbhar Nidhi provides affordable collateral-free working capital loan of 10000 rupees to urban street vendors.",
                source_dataset="schemes_canonical",
                source_tier=SourceTier.PRIMARY_SCHEME.value,
                source_url="https://www.myscheme.gov.in/schemes/pmsvanidhi",
                source_document="schemes.csv",
                scheme_slug="pmsvanidhi",
                scheme_name="PM SVANidhi",
                section="scheme_overview",
                content_type=ContentType.SCHEME_OVERVIEW.value,
                state="All India",
                beneficiary_type="Street Vendors"
            ),
            RAGDocument(
                id="chk_assam_housing",
                content="Aponar Apon Ghar provides home loan interest subsidy of up to 2.5 lakh rupees for permanent residents of Assam.",
                source_dataset="schemes_canonical",
                source_tier=SourceTier.PRIMARY_SCHEME.value,
                source_url="https://assam.gov.in/aag",
                source_document="schemes.csv",
                scheme_slug="aag",
                scheme_name="Aponar Apon Ghar",
                section="benefits",
                content_type=ContentType.BENEFITS.value,
                state="Assam",
                beneficiary_type="All"
            ),
            RAGDocument(
                id="chk_apy_faq_1",
                content="Question: What is the minimum monthly pension under APY? Answer: Minimum guaranteed pension is 1000 to 5000 rupees per month depending on contribution.",
                source_dataset="schemes_faqs",
                source_tier=SourceTier.PRIMARY_FAQ.value,
                source_url="https://www.myscheme.gov.in/schemes/apy",
                source_document="schemes_faqs.csv",
                scheme_slug="apy",
                scheme_name="Atal Pension Yojana",
                section="faqs",
                content_type=ContentType.FAQ.value,
                faq_id="apy_q1"
            )
        ]
        self.retriever.index_documents(self.docs)

    def test_retrieve_chunks_basic(self):
        """Basic query retrieves relevant chunks with proper score metrics and provenance."""
        q = RetrievalQuery(query_text="Atal Pension Yojana monthly pension", top_k=3)
        chunks = self.retriever.retrieve(q)

        self.assertGreater(len(chunks), 0)
        top_chunk = chunks[0]
        # Should match APY chunks
        self.assertEqual(top_chunk.scheme_slug, "apy")
        # Check scores exist
        self.assertGreaterEqual(top_chunk.dense_score, -1.0)
        self.assertGreaterEqual(top_chunk.sparse_score, 0.0)
        self.assertGreaterEqual(top_chunk.fused_score, 0.0)
        self.assertGreaterEqual(top_chunk.rerank_score, 0.0)
        # Check provenance
        self.assertTrue(verify_provenance_integrity(top_chunk))
        self.assertIn("source_dataset", top_chunk.provenance)

    def test_retrieve_schemes_deduplication(self):
        """retrieve_schemes aggregates multiple chunks under unique scheme slugs."""
        q = RetrievalQuery(query_text="Atal Pension Yojana", top_k=5)
        scheme_results = self.retriever.retrieve_schemes(q)

        self.assertGreater(len(scheme_results), 0)
        # Each scheme slug appears at most once
        slugs = [s.scheme_slug for s in scheme_results]
        self.assertEqual(len(slugs), len(set(slugs)))

        # APY should be top scheme
        self.assertEqual(scheme_results[0].scheme_slug, "apy")
        self.assertGreater(len(scheme_results[0].best_matching_chunks), 0)
        self.assertIn("total_matching_chunks", scheme_results[0].source_metadata)

    def test_retrieve_with_state_filter(self):
        """Filter restricts results to matching state and central schemes."""
        q = RetrievalQuery(
            query_text="housing subsidy home loan",
            state_filter="Assam",
            top_k=5
        )
        chunks = self.retriever.retrieve(q)
        for chunk in chunks:
            state = chunk.metadata.get("state")
            self.assertIn(str(state).lower(), ["assam", "all india", "central", "none"])

    def test_retrieve_empty_query(self):
        """Empty query string returns empty result list without crashing."""
        q = RetrievalQuery(query_text="")
        chunks = self.retriever.retrieve(q)
        self.assertEqual(chunks, [])

        schemes = self.retriever.retrieve_schemes(q)
        self.assertEqual(schemes, [])

    def test_save_and_load_indexes(self):
        """Indexes can be serialized to disk and reloaded identically."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.retriever.save_indexes(tmpdir)
            self.assertTrue((Path(tmpdir) / "dense").exists())
            self.assertTrue((Path(tmpdir) / "sparse" / "bm25.pkl").exists())

            # Create fresh retriever and load
            new_retriever = HybridRetriever(
                config=self.config,
                embedding_model=self.embedding_model
            )
            new_retriever.load_indexes(tmpdir)

            q = RetrievalQuery(query_text="Atal Pension Yojana", top_k=2)
            orig_chunks = self.retriever.retrieve(q)
            loaded_chunks = new_retriever.retrieve(q)

            self.assertEqual(len(orig_chunks), len(loaded_chunks))
            self.assertEqual(orig_chunks[0].chunk_id, loaded_chunks[0].chunk_id)


if __name__ == "__main__":
    unittest.main()
