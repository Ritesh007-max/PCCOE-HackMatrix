"""
PolicySetu Incremental RAG Update Engine.
Integrates with Phase 5 RAG architecture.
Handles ADD, UPDATE, and DELETE / DEACTIVATE operations cleanly:
- Purges stale / removed scheme chunks so they never appear in active retrieval.
- Retains pre-computed embeddings for unchanged chunks, computing embeddings ONLY for new/changed content.
- Re-indexes FAISS and BM25 using active chunks to guarantee index integrity.
"""

from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import numpy as np

import sys
from pathlib import Path

_CUR = Path(__file__).resolve()
while _CUR.name != "AI" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_AI_DIR = _CUR
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

try:
    from .models import RecordDiff, ChangeType
except (ImportError, ValueError):
    from src.data_pipeline.models import RecordDiff, ChangeType


class IncrementalRAGUpdater:
    """
    Coordinates incremental chunk regeneration and index updates.
    Prevents stale or deleted chunks from lingering in FAISS and BM25 retrievers.
    """

    def __init__(
        self,
        embedding_fn: Optional[Callable[[List[str]], np.ndarray]] = None,
    ):
        self.embedding_fn = embedding_fn

    def compute_incremental_chunks(
        self,
        existing_chunks: List[Any],  # List[RAGDocument]
        diffs: List[RecordDiff],
        all_canonical_records: List[Dict[str, Any]],
        chunk_fn: Optional[Callable[[Dict[str, Any]], List[Any]]] = None
    ) -> Tuple[List[Any], Set[str], Set[str]]:
        """
        Updates the chunk corpus based on diffs:
        - DELETE: drops chunks belonging to removed schemes.
        - UPDATE: drops old chunks for modified schemes, generates new chunks.
        - ADD: generates new chunks for added schemes.
        - UNCHANGED: retains existing chunks with stable IDs.

        Returns: (updated_active_chunks, purged_chunk_ids, newly_added_chunk_ids)
        """
        modified_slugs: Set[str] = {
            d.scheme_slug for d in diffs if d.change_type == ChangeType.MODIFIED
        }
        removed_slugs: Set[str] = {
            d.scheme_slug for d in diffs if d.change_type == ChangeType.REMOVED
        }
        added_slugs: Set[str] = {
            d.scheme_slug for d in diffs if d.change_type == ChangeType.ADDED
        }

        purged_slugs = modified_slugs | removed_slugs

        # 1. Retain unchanged chunks, purge modified and removed
        retained_chunks: List[Any] = []
        purged_chunk_ids: Set[str] = set()

        for chunk in existing_chunks:
            # Handle RAGDocument or dict
            slug = getattr(chunk, "scheme_slug", None) or (chunk.get("scheme_slug") if isinstance(chunk, dict) else None)
            chunk_id = getattr(chunk, "chunk_id", None) or (chunk.get("chunk_id") if isinstance(chunk, dict) else None)

            if slug in purged_slugs:
                if chunk_id:
                    purged_chunk_ids.add(chunk_id)
            else:
                retained_chunks.append(chunk)

        # 2. Re-chunk added and modified schemes
        schemes_to_chunk = added_slugs | modified_slugs
        new_chunks: List[Any] = []
        new_chunk_ids: Set[str] = set()

        if schemes_to_chunk and chunk_fn:
            slug_to_rec = {
                str(r.get("slug", "")).strip().lower(): r
                for r in all_canonical_records if r.get("slug")
            }
            for slug in schemes_to_chunk:
                rec = slug_to_rec.get(slug)
                if rec:
                    generated = chunk_fn(rec)
                    for c in generated:
                        c_id = getattr(c, "chunk_id", None) or (c.get("chunk_id") if isinstance(c, dict) else None)
                        if c_id:
                            new_chunk_ids.add(c_id)
                        new_chunks.append(c)

        final_chunks = retained_chunks + new_chunks

        # Strict invariant verification: NO removed scheme chunks exist in final_chunks
        for c in final_chunks:
            c_slug = getattr(c, "scheme_slug", None) or (c.get("scheme_slug") if isinstance(c, dict) else None)
            assert c_slug not in removed_slugs, f"CRITICAL: Removed scheme '{c_slug}' lingering in active chunks!"

        return final_chunks, purged_chunk_ids, new_chunk_ids

    def update_vector_index(
        self,
        active_chunks: List[Any],
        cached_embeddings: Dict[str, np.ndarray],
        new_chunk_ids: Set[str],
        vector_store: Any,
    ) -> Dict[str, np.ndarray]:
        """
        Updates FAISS/Numpy vector store without recalculating unchanged embeddings:
        - Calculates embeddings ONLY for new_chunk_ids.
        - Purges stale embeddings from cached_embeddings.
        - Re-indexes vector_store with exactly the active_chunks vectors.
        """
        # 1. Identify chunks that need embeddings
        chunks_needing_emb = [
            c for c in active_chunks
            if (getattr(c, "chunk_id", None) or c.get("chunk_id")) in new_chunk_ids
            or (getattr(c, "chunk_id", None) or c.get("chunk_id")) not in cached_embeddings
        ]

        if chunks_needing_emb and self.embedding_fn:
            texts = [
                getattr(c, "text", None) or c.get("text", "")
                for c in chunks_needing_emb
            ]
            new_embs = self.embedding_fn(texts)
            for chunk, emb in zip(chunks_needing_emb, new_embs):
                cid = getattr(chunk, "chunk_id", None) or chunk.get("chunk_id")
                cached_embeddings[cid] = emb

        # 2. Assemble vector matrix strictly for active chunks
        active_ids = [getattr(c, "chunk_id", None) or c.get("chunk_id") for c in active_chunks]
        # Purge stale keys from cached_embeddings
        stale_keys = set(cached_embeddings.keys()) - set(active_ids)
        for k in stale_keys:
            del cached_embeddings[k]

        if not active_chunks or not cached_embeddings:
            return cached_embeddings

        vec_list = [cached_embeddings[cid] for cid in active_ids if cid in cached_embeddings]
        if vec_list:
            if hasattr(vector_store, "_init_index"):
                vector_store._init_index()
                vector_store._metadata = []
            elif hasattr(vector_store, "_vectors"):
                vector_store._vectors = np.empty((0, vector_store.dimension), dtype=np.float32)
                vector_store._metadata = []

            vectors_array = np.vstack(vec_list)
            meta_list = [
                getattr(c, "to_dict", lambda: c)() if hasattr(c, "to_dict") else c
                for c in active_chunks if (getattr(c, "chunk_id", None) or c.get("chunk_id")) in cached_embeddings
            ]
            vector_store.add(vectors_array, meta_list)

        return cached_embeddings