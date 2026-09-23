"""
PolicySetu Reranker Engine.
Implements metadata- and content-aware reranking to prioritize exact scheme titles,
authoritative FAQs, statutory eligibility sections, and source precedence tiers.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import sys
from pathlib import Path

_CUR = Path(__file__).resolve()
while _CUR.name != "AI" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_AI_DIR = _CUR
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

try:
    from .models import RetrievedChunk, ContentType, SourceTier
except (ImportError, ValueError):
    from src.rag.models import RetrievedChunk, ContentType, SourceTier


class BaseReranker(ABC):
    """Abstract interface for RAG reranking stages."""

    @abstractmethod
    def rerank(
        self,
        query: str,
        candidates: List[RetrievedChunk],
        top_k: int = 10
    ) -> List[RetrievedChunk]:
        pass


class MetadataAwareReranker(BaseReranker):
    """
    Deterministic rule- and metadata-aware reranker.
    Applies calibrated multiplier signals based on:
    - Exact scheme title matches
    - FAQ exact phrase alignment
    - Eligibility/benefit intent relevance
    - Controlled source tier preference
    """

    SOURCE_TIER_PRIORS = {
        SourceTier.PRIMARY_SCHEME.value: 1.05,
        SourceTier.PRIMARY_FAQ.value: 1.03,
        SourceTier.SUPPLEMENTARY_SCHEME.value: 0.98,
        SourceTier.RAG_ARCHIVE.value: 0.95,
        SourceTier.EVALUATION_ONLY.value: 0.90,
    }

    def rerank(
        self,
        query: str,
        candidates: List[RetrievedChunk],
        top_k: int = 10
    ) -> List[RetrievedChunk]:
        if not candidates or not query.strip():
            return candidates[:top_k]

        q_lower = query.strip().lower()
        q_tokens = set(q_lower.split())

        for chunk in candidates:
            score = chunk.fused_score
            scheme_title = (chunk.scheme_name or "").lower()

            # 1. Exact or near-exact scheme title match bonus
            if scheme_title and (scheme_title in q_lower or q_lower in scheme_title):
                score *= 1.35
            elif scheme_title:
                title_tokens = set(scheme_title.split())
                overlap = len(q_tokens.intersection(title_tokens))
                if overlap >= 2:
                    score *= 1.15

            # 2. Section alignment with user query intent
            if "eligible" in q_lower or "criteria" in q_lower or "age" in q_lower or "income" in q_lower:
                if chunk.metadata.get("content_type") == ContentType.ELIGIBILITY.value:
                    score *= 1.15
            elif "benefit" in q_lower or "amount" in q_lower or "money" in q_lower or "pension" in q_lower:
                if chunk.metadata.get("content_type") == ContentType.BENEFITS.value:
                    score *= 1.10
            elif "apply" in q_lower or "how to" in q_lower or "process" in q_lower:
                if chunk.metadata.get("content_type") == ContentType.APPLICATION_PROCESS.value:
                    score *= 1.10

            # 3. Source Tier Controlled Preference
            tier = chunk.source_tier
            tier_mult = self.SOURCE_TIER_PRIORS.get(tier, 1.0)
            score *= tier_mult

            chunk.rerank_score = round(float(score), 4)

        # Sort deterministically
        candidates.sort(key=lambda c: (-c.rerank_score, c.chunk_id))
        return candidates[:top_k]