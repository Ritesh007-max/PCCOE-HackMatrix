"""
FIN Hybrid Retrieval Fusion Engine.
Combines dense semantic and sparse lexical search scores using normalized
weighted fusion and Reciprocal Rank Fusion (RRF). Eliminates NaN/Inf errors.
"""

from typing import Any, Dict, List, Optional, Tuple
import sys
from pathlib import Path

_CUR = Path(__file__).resolve()
while _CUR.name != "Intelligence" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_INTELLIGENCE_DIR = _CUR
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

try:
    from .models import RetrievedChunk, SourceTier
except (ImportError, ValueError):
    from src.rag.models import RetrievedChunk, SourceTier


def normalize_scores(scores: Dict[str, float]) -> Dict[str, float]:
    """
    Min-max normalizes a dictionary of scores to [0.0, 1.0].
    Safely handles identical min/max and empty collections.
    """
    if not scores:
        return {}
    vals = list(scores.values())
    min_val = min(vals)
    max_val = max(vals)

    if max_val == min_val:
        return {k: 1.0 if max_val > 0 else 0.0 for k in scores}

    denom = max_val - min_val
    return {k: float(max(0.0, min(1.0, (v - min_val) / denom))) for k, v in scores.items()}


def fuse_results(
    dense_results: List[Tuple[str, float, Dict[str, Any]]],
    sparse_results: List[Tuple[str, float, int]],
    metadata_map: Dict[str, Dict[str, Any]],
    dense_weight: float = 0.70,
    sparse_weight: float = 0.30,
    top_k: int = 10
) -> List[RetrievedChunk]:
    """
    Executes normalized weighted fusion over dense and sparse retrieval results.
    Guarantees deterministic sorting and tie-breaking by chunk_id.
    """
    # Build score dictionaries
    dense_dict = {item[0]: float(item[1]) for item in dense_results}
    sparse_dict = {item[0]: float(item[1]) for item in sparse_results}

    # Normalize scores
    norm_dense = normalize_scores(dense_dict)
    norm_sparse = normalize_scores(sparse_dict)

    # Union of all candidate chunk IDs
    candidate_ids = set(dense_dict.keys()).union(set(sparse_dict.keys()))

    chunks: List[RetrievedChunk] = []

    for cid in candidate_ids:
        d_score = dense_dict.get(cid, 0.0)
        s_score = sparse_dict.get(cid, 0.0)
        nd = norm_dense.get(cid, 0.0)
        ns = norm_sparse.get(cid, 0.0)

        # Weighted combination
        fused = (dense_weight * nd) + (sparse_weight * ns)
        # Avoid NaN / Inf
        if not (0.0 <= fused <= 2.0):
            fused = 0.0

        meta = metadata_map.get(cid, {})
        prov = meta.get("provenance", {})

        chunk = RetrievedChunk(
            chunk_id=cid,
            scheme_id=meta.get("scheme_id"),
            scheme_slug=meta.get("scheme_slug"),
            scheme_name=meta.get("scheme_name"),
            content=meta.get("content", ""),
            dense_score=round(d_score, 4),
            sparse_score=round(s_score, 4),
            fused_score=round(fused, 4),
            rerank_score=round(fused, 4),
            source_tier=meta.get("source_tier", SourceTier.PRIMARY_SCHEME.value),
            provenance=prov,
            metadata=meta
        )
        chunks.append(chunk)

    # Sort deterministically: descending fused_score, then ascending chunk_id for stable tie-breaking
    chunks.sort(key=lambda c: (-c.fused_score, c.chunk_id))

    return chunks[:top_k]


def reciprocal_rank_fusion(
    dense_results: List[Tuple[str, float, Dict[str, Any]]],
    sparse_results: List[Tuple[str, float, int]],
    metadata_map: Dict[str, Dict[str, Any]],
    k: int = 60,
    top_k: int = 10
) -> List[RetrievedChunk]:
    """
    RRF alternative fusion: score = sum(1 / (k + rank)).
    """
    rrf_scores: Dict[str, float] = {}

    for rank, item in enumerate(dense_results, start=1):
        cid = item[0]
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k + rank))

    for rank, item in enumerate(sparse_results, start=1):
        cid = item[0]
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k + rank))

    chunks: List[RetrievedChunk] = []
    dense_dict = {item[0]: float(item[1]) for item in dense_results}
    sparse_dict = {item[0]: float(item[1]) for item in sparse_results}

    for cid, rrf_val in rrf_scores.items():
        meta = metadata_map.get(cid, {})
        chunk = RetrievedChunk(
            chunk_id=cid,
            scheme_id=meta.get("scheme_id"),
            scheme_slug=meta.get("scheme_slug"),
            scheme_name=meta.get("scheme_name"),
            content=meta.get("content", ""),
            dense_score=round(dense_dict.get(cid, 0.0), 4),
            sparse_score=round(sparse_dict.get(cid, 0.0), 4),
            fused_score=round(rrf_val, 5),
            rerank_score=round(rrf_val, 5),
            source_tier=meta.get("source_tier", SourceTier.PRIMARY_SCHEME.value),
            provenance=meta.get("provenance", {}),
            metadata=meta
        )
        chunks.append(chunk)

    chunks.sort(key=lambda c: (-c.fused_score, c.chunk_id))
    return chunks[:top_k]