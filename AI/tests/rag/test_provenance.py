"""
Tests for PolicySetu Provenance Engine (AI/src/rag/provenance.py).
Validates cryptographic content hashing, deterministic chunk ID generation,
provenance record construction, and integrity verification.
"""

import unittest
from src.rag.provenance import (
    compute_content_hash,
    generate_stable_chunk_id,
    build_provenance_record,
    verify_provenance_integrity,
)
from src.rag.models import RAGDocument, RetrievedChunk, SourceTier, ContentType


class TestRAGProvenance(unittest.TestCase):
    """Test suite for statutory citation, provenance generation, and integrity checks."""

    def test_compute_content_hash_deterministic(self):
        """Identical text (even with whitespace variation) must yield identical SHA-256 hash."""
        text1 = "Pradhan Mantri Awas Yojana provides housing assistance."
        text2 = "  Pradhan  Mantri Awas   Yojana provides housing   assistance. \n"
        self.assertEqual(compute_content_hash(text1), compute_content_hash(text2))

    def test_compute_content_hash_different(self):
        """Different texts must yield different hashes."""
        hash1 = compute_content_hash("Scheme A eligibility criteria")
        hash2 = compute_content_hash("Scheme B eligibility criteria")
        self.assertNotEqual(hash1, hash2)

    def test_generate_stable_chunk_id_determinism(self):
        """Calling generate_stable_chunk_id twice with identical params yields identical IDs."""
        id1 = generate_stable_chunk_id(
            scheme_slug="pm-kisan",
            content_type=ContentType.SCHEME_OVERVIEW.value,
            section="eligibility",
            chunk_index=0,
            source_dataset="schemes_canonical"
        )
        id2 = generate_stable_chunk_id(
            scheme_slug="pm-kisan",
            content_type=ContentType.SCHEME_OVERVIEW.value,
            section="eligibility",
            chunk_index=0,
            source_dataset="schemes_canonical"
        )
        self.assertEqual(id1, id2)
        self.assertTrue(id1.startswith("chk_pm-kisan_"))

    def test_generate_stable_chunk_id_different_index(self):
        """Different chunk indices produce distinct chunk IDs."""
        id1 = generate_stable_chunk_id(scheme_slug="apy", content_type="scheme_overview", section="main", chunk_index=0)
        id2 = generate_stable_chunk_id(scheme_slug="apy", content_type="scheme_overview", section="main", chunk_index=1)
        self.assertNotEqual(id1, id2)

    def test_build_provenance_record(self):
        """Builds structured provenance record preserving statutory origin."""
        doc = RAGDocument(
            id="doc_123",
            content="Eligibility for Atal Pension Yojana: age 18 to 40.",
            source_dataset="schemes_canonical",
            source_tier=SourceTier.PRIMARY_SCHEME.value,
            source_url="https://www.myscheme.gov.in/schemes/apy",
            source_document="schemes.csv",
            scheme_slug="apy",
            scheme_name="Atal Pension Yojana",
            section="eligibility",
            content_type=ContentType.SCHEME_OVERVIEW.value
        )
        prov = build_provenance_record(doc)
        self.assertEqual(prov["source_dataset"], "schemes_canonical")
        self.assertEqual(prov["source_tier"], SourceTier.PRIMARY_SCHEME.value)
        self.assertEqual(prov["source_url"], "https://www.myscheme.gov.in/schemes/apy")
        self.assertIn("text_hash", prov)
        self.assertEqual(len(prov["text_hash"]), 64)

    def test_verify_provenance_integrity(self):
        """Verifies integrity checker catches missing or invalid provenance."""
        valid_chunk = RetrievedChunk(
            chunk_id="c1",
            scheme_slug="apy",
            content="Valid content",
            dense_score=0.9,
            sparse_score=10.0,
            fused_score=0.8,
            rerank_score=0.8,
            source_tier=SourceTier.PRIMARY_SCHEME.value,
            provenance={
                "source_dataset": "schemes_canonical",
                "source_tier": SourceTier.PRIMARY_SCHEME.value,
            }
        )
        self.assertTrue(verify_provenance_integrity(valid_chunk))

        # Missing provenance
        invalid_chunk_empty = RetrievedChunk(
            chunk_id="c2",
            scheme_slug="apy",
            content="No provenance",
            dense_score=0.5,
            sparse_score=5.0,
            fused_score=0.5,
            rerank_score=0.5,
            source_tier=SourceTier.PRIMARY_SCHEME.value,
            provenance={}
        )
        self.assertFalse(verify_provenance_integrity(invalid_chunk_empty))

        # Invalid tier
        invalid_chunk_tier = RetrievedChunk(
            chunk_id="c3",
            scheme_slug="apy",
            content="Invalid tier",
            dense_score=0.5,
            sparse_score=5.0,
            fused_score=0.5,
            rerank_score=0.5,
            source_tier="tier_unauthorized",
            provenance={
                "source_dataset": "schemes_canonical",
                "source_tier": "tier_unauthorized"
            }
        )
        self.assertFalse(verify_provenance_integrity(invalid_chunk_tier))


if __name__ == "__main__":
    unittest.main()
