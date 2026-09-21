"""
Unit tests for two-tier grounding verification.
Tests citation existence, lexical claim support, and ungrounded claim isolation.
"""

import unittest
import sys
from pathlib import Path

_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from src.llm.grounding import GroundingVerifier
from src.llm.models import GroundedExplanation, FactualClaim, ClaimSupportStatus


class TestGroundingVerifier(unittest.TestCase):

    def setUp(self):
        self.verifier = GroundingVerifier(token_overlap_threshold=0.30)
        self.retrieved_chunks = [
            {
                "id": "chunk_scheme_sc_01",
                "content": "Applicants belonging to Scheduled Caste category with annual family income below 2.5 lakh rupees are eligible.",
                "source_url": "https://scholarships.gov.in/sc_guidelines.pdf",
            },
            {
                "id": "chunk_scheme_sc_02",
                "content": "Students must be enrolled in recognized post-matric educational institutions in Gujarat.",
                "source_url": "https://gujarat.gov.in/post_matric.pdf",
            },
        ]

    def test_supported_grounded_claim(self):
        claim = FactualClaim(
            statement="Scheduled Caste applicants with family income under 2.5 lakh are eligible.",
            cited_chunk_ids=["chunk_scheme_sc_01"],
            cited_urls=["https://scholarships.gov.in/sc_guidelines.pdf"],
        )
        explanation = GroundedExplanation(
            authoritative_decision="PASS",
            scheme_id="sc_scholarship",
            answer="Grounded answer.",
            claims=[claim],
        )

        verified = self.verifier.verify_explanation(explanation, self.retrieved_chunks)
        self.assertEqual(verified.claims[0].support_status, ClaimSupportStatus.SUPPORTED)
        self.assertGreaterEqual(verified.claims[0].support_score, 0.30)
        self.assertIn("chunk_scheme_sc_01", verified.supporting_chunk_ids)
        self.assertIn("https://scholarships.gov.in/sc_guidelines.pdf", verified.supporting_source_urls)

    def test_unverified_citation_fake_chunk_id(self):
        claim = FactualClaim(
            statement="Beneficiaries receive 50,000 grant.",
            cited_chunk_ids=["chunk_fabricated_999"],  # Does not exist in retrieved set
        )
        explanation = GroundedExplanation(
            authoritative_decision="PASS",
            scheme_id="sc_scholarship",
            answer="Fabricated citation test.",
            claims=[claim],
        )

        verified = self.verifier.verify_explanation(explanation, self.retrieved_chunks)
        self.assertEqual(verified.claims[0].support_status, ClaimSupportStatus.UNVERIFIED_CITATION)
        self.assertEqual(verified.claims[0].support_score, 0.0)
        self.assertNotIn("chunk_fabricated_999", verified.supporting_chunk_ids)

    def test_unsupported_claim_content_mismatch(self):
        claim = FactualClaim(
            statement="All applicants get a free tractor and solar water pump.",  # Completely unrelated
            cited_chunk_ids=["chunk_scheme_sc_01"],
        )
        explanation = GroundedExplanation(
            authoritative_decision="PASS",
            scheme_id="sc_scholarship",
            answer="Mismatched content test.",
            claims=[claim],
        )

        verified = self.verifier.verify_explanation(explanation, self.retrieved_chunks)
        self.assertEqual(verified.claims[0].support_status, ClaimSupportStatus.UNSUPPORTED)


if __name__ == "__main__":
    unittest.main()
