"""
PolicySetu Two-Tier Grounding Verifier.
Separates structural citation validation from lexical claim support verification.
NOTE ON LIMITATIONS:
Grounding verification is heuristic and lexical. It checks citation existence and token alignment.
It does NOT claim perfect semantic fact verification or hallucination-free behavior.
Unsupported claims are safely flagged and isolated.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple
from .models import FactualClaim, ClaimSupportStatus, GroundedExplanation
from .errors import UngroundedClaimError


class GroundingVerifier:
    """
    Two-tier grounding verifier:
    1. Structural Provenance Validation: Verifies cited chunk IDs and URLs against retrieved evidence.
    2. Heuristic Claim Support: Evaluates lexical/token overlap between claim text and cited chunks.
    """

    def __init__(self, token_overlap_threshold: float = 0.30):
        self.token_overlap_threshold = token_overlap_threshold

    @staticmethod
    def _tokenize(text: str) -> Set[str]:
        """Extracts normalized alphanumeric token set for lexical comparison."""
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "and", "or", "in", "on", "at",
            "to", "for", "of", "with", "by", "from", "that", "this", "it", "as", "be",
            "applicant", "scheme", "policy", "eligible", "must", "have"
        }
        words = re.findall(r"[\w\u0900-\u097F]+", text.lower())
        return {w for w in words if len(w) > 2 and w not in stopwords}

    def verify_explanation(
        self,
        explanation: GroundedExplanation,
        retrieved_chunks: List[Dict[str, Any]]
    ) -> GroundedExplanation:
        """
        Verifies all claims in a GroundedExplanation against retrieved chunks.
        Updates ClaimSupportStatus and support_score for each claim.
        """
        # Map available chunk IDs to their text content and URLs
        chunk_map: Dict[str, Dict[str, Any]] = {}
        for chunk in retrieved_chunks:
            c_id = chunk.get("id") or chunk.get("chunk_id")
            if c_id:
                chunk_map[c_id] = {
                    "content": chunk.get("content", ""),
                    "source_url": chunk.get("source_url") or chunk.get("provenance", {}).get("source_url", ""),
                }

        valid_supporting_ids: Set[str] = set()
        valid_supporting_urls: Set[str] = set()

        for claim in explanation.claims:
            if not claim.cited_chunk_ids:
                claim.support_status = ClaimSupportStatus.UNSUPPORTED
                claim.support_score = 0.0
                continue

            # 1. Tier 1: Citation existence check
            missing_chunks = [cid for cid in claim.cited_chunk_ids if cid not in chunk_map]
            if missing_chunks:
                claim.support_status = ClaimSupportStatus.UNVERIFIED_CITATION
                claim.support_score = 0.0
                continue

            # 2. Tier 2: Lexical claim support check
            claim_tokens = self._tokenize(claim.statement)
            if not claim_tokens:
                claim.support_status = ClaimSupportStatus.PARTIALLY_SUPPORTED
                claim.support_score = 0.5
                continue

            max_overlap = 0.0
            best_chunk_content = ""
            for cid in claim.cited_chunk_ids:
                chunk_info = chunk_map[cid]
                chunk_tokens = self._tokenize(chunk_info["content"])
                if not chunk_tokens:
                    continue

                overlap = len(claim_tokens & chunk_tokens) / len(claim_tokens)
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_chunk_content = chunk_info["content"]

                valid_supporting_ids.add(cid)
                if chunk_info["source_url"]:
                    valid_supporting_urls.add(chunk_info["source_url"])

            claim.support_score = round(max_overlap, 3)
            claim.evidence_excerpt = best_chunk_content[:200] if best_chunk_content else None

            if max_overlap >= self.token_overlap_threshold:
                claim.support_status = ClaimSupportStatus.SUPPORTED
            elif max_overlap >= 0.15:
                claim.support_status = ClaimSupportStatus.PARTIALLY_SUPPORTED
            else:
                claim.support_status = ClaimSupportStatus.UNSUPPORTED

        # Update explanation with only verified supporting chunk IDs
        explanation.supporting_chunk_ids = sorted(list(valid_supporting_ids))
        explanation.supporting_source_urls = sorted(list(valid_supporting_urls))

        return explanation
