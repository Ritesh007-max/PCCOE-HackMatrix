"""
Tests for Phase 13 Retrieval Evaluator.
"""

import unittest
from pathlib import Path
import sys

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.evaluation.models import EvaluationCase, EvaluationCategory, Severity
from src.evaluation.retrieval_eval import RetrievalEvaluator
from src.rag.retriever import HybridRetriever
from src.rag.config import RAGConfig
from src.rag.embeddings import DeterministicMockEmbeddingModel
from src.rag.models import RAGDocument, SourceTier, ContentType


class TestRetrievalEvaluator(unittest.TestCase):
    """Verifies retrieval evaluation against golden cases."""

    def setUp(self):
        config = RAGConfig(use_faiss=False, embedding_dimension=32)
        retriever = HybridRetriever(
            config=config,
            embedding_model=DeterministicMockEmbeddingModel(dimension=32),
        )
        docs = [
            RAGDocument(
                id="doc_apy_en",
                content="Atal Pension Yojana APY national old age pension scheme for unorganised workers.",
                source_dataset="schemes_canonical",
                source_tier=SourceTier.PRIMARY_SCHEME.value,
                scheme_slug="apy",
                scheme_name="Atal Pension Yojana",
                content_type=ContentType.SCHEME_OVERVIEW.value,
            ),
            RAGDocument(
                id="doc_apy_hi",
                content="अटल पेंशन योजना APY असंगठित क्षेत्र के कामगारों के लिए राष्ट्रीय वृद्धावस्था पेंशन योजना।",
                source_dataset="schemes_canonical",
                source_tier=SourceTier.PRIMARY_SCHEME.value,
                scheme_slug="apy",
                scheme_name="Atal Pension Yojana",
                content_type=ContentType.SCHEME_OVERVIEW.value,
            ),
            RAGDocument(
                id="doc_pmmvy",
                content="Pradhan Mantri Matru Vandana Yojana PMMVY maternity financial support.",
                source_dataset="schemes_canonical",
                source_tier=SourceTier.PRIMARY_SCHEME.value,
                scheme_slug="pmmvy",
                scheme_name="Pradhan Mantri Matru Vandana Yojana",
                content_type=ContentType.SCHEME_OVERVIEW.value,
            ),
        ]
        retriever.index_documents(docs)
        self.evaluator = RetrievalEvaluator(retriever=retriever)

    def test_evaluate_single_retrieval_case(self):
        case = EvaluationCase(
            case_id="TEST_RET_01",
            category=EvaluationCategory.RETRIEVAL,
            input_data={"query": "Atal Pension Yojana", "language": "en"},
            expected_scheme_id="apy",
            expected_status="MATCH",
        )
        res = self.evaluator.evaluate_case(case, top_k=5)
        self.assertTrue(res.passed)
        self.assertIn("retrieved_slugs", res.actual_output)
        self.assertGreaterEqual(res.actual_output["hit@5"], 1.0)
        self.assertGreater(res.actual_output["mrr"], 0.0)

    def test_evaluate_hindi_retrieval_case(self):
        case = EvaluationCase(
            case_id="TEST_RET_HI_01",
            category=EvaluationCategory.RETRIEVAL,
            input_data={"query": "अटल पेंशन योजना", "language": "hi"},
            expected_scheme_id="apy",
            expected_status="MATCH",
        )
        res = self.evaluator.evaluate_case(case, top_k=5)
        self.assertTrue(res.passed)
        self.assertGreaterEqual(res.actual_output["hit@5"], 1.0)
