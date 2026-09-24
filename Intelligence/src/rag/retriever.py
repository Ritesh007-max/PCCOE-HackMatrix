"""
FIN Hybrid Retrieval Engine.
Unifies dense semantic search, sparse BM25 keyword matching, metadata filtering,
fusion scoring, content reranking, and scheme-level deduplication.
"""

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

import sys

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

try:
    from .models import (
        RAGDocument,
        RetrievedChunk,
        RetrievalQuery,
        SchemeRetrievalResult,
        RetrievalIntent,
        SourceTier,
    )
    from .config import RAGConfig, DEFAULT_RAG_CONFIG
    from .embeddings import EmbeddingModel, get_embedding_model
    from .sparse import BM25Retriever
    from .store import VectorStore, create_vector_store
    from .filters import normalize_query_intent, build_metadata_filter
    from .fusion import fuse_results
    from .reranker import BaseReranker, MetadataAwareReranker
    from .provenance import build_provenance_record
    from .query_normalization import QueryNormalizer, NormalizedQueryRecord
    from .entity_decomposition import MultiSchemeDecomposer
except (ImportError, ValueError):
    from src.rag.models import (
        RAGDocument,
        RetrievedChunk,
        RetrievalQuery,
        SchemeRetrievalResult,
        RetrievalIntent,
        SourceTier,
    )
    from src.rag.config import RAGConfig, DEFAULT_RAG_CONFIG
    from src.rag.embeddings import EmbeddingModel, get_embedding_model
    from src.rag.sparse import BM25Retriever
    from src.rag.store import VectorStore, create_vector_store
    from src.rag.filters import normalize_query_intent, build_metadata_filter
    from src.rag.fusion import fuse_results
    from src.rag.reranker import BaseReranker, MetadataAwareReranker
    from src.rag.provenance import build_provenance_record
    from src.rag.query_normalization import QueryNormalizer, NormalizedQueryRecord
    from src.rag.entity_decomposition import MultiSchemeDecomposer


class HybridRetriever:
    """
    Production hybrid retrieval coordinator.
    Supports chunk-level and deduplicated scheme-level views with strict provenance.
    CRITICAL INVARIANT: Retrieval never makes statutory eligibility decisions.
    """

    def __init__(
        self,
        config: RAGConfig = DEFAULT_RAG_CONFIG,
        embedding_model: Optional[EmbeddingModel] = None,
        vector_store: Optional[VectorStore] = None,
        sparse_retriever: Optional[BM25Retriever] = None,
        reranker: Optional[BaseReranker] = None,
        query_normalizer: Optional[QueryNormalizer] = None,
        decomposer: Optional[MultiSchemeDecomposer] = None
    ):
        self.config = config
        self.embedding_model = embedding_model or get_embedding_model(config)
        self.vector_store = vector_store or create_vector_store(
            dimension=self.embedding_model.dimension,
            use_faiss=config.use_faiss
        )
        self.sparse_retriever = sparse_retriever or BM25Retriever()
        self.reranker = reranker or MetadataAwareReranker()
        self.query_normalizer = query_normalizer or QueryNormalizer()
        self.decomposer = decomposer or MultiSchemeDecomposer()
        self._doc_metadata_map: Dict[str, Dict[str, Any]] = {}

    def index_documents(self, documents: List[RAGDocument], batch_size: int = 64) -> None:
        """
        Indexes a list of RAGDocuments into both dense vector store and sparse BM25 index.
        """
        if not documents:
            return

        # 1. Fit Sparse Index
        self.sparse_retriever.fit(documents)

        # 2. Populate metadata map
        self._doc_metadata_map = {}
        contents: List[str] = []
        meta_list: List[Dict[str, Any]] = []

        for doc in documents:
            meta = doc.to_dict()
            meta["provenance"] = build_provenance_record(doc)
            self._doc_metadata_map[doc.id] = meta
            contents.append(doc.content)
            meta_list.append(meta)

        # 3. Dense Embeddings & Vector Index
        embeddings = self.embedding_model.encode_documents(contents, batch_size=batch_size)
        self.vector_store.add(embeddings, meta_list)

    def retrieve(self, query: RetrievalQuery) -> List[RetrievedChunk]:
        """
        Executes hybrid retrieval returning ranked, deduplicated RAG chunks.
        Applies deterministic query normalization, cross-lingual expansion,
        and typo resolution while preserving original user query text.
        """
        raw_text = query.query_text.strip()
        if not raw_text:
            return []

        # 1. Query Normalization & Filter Construction
        norm_rec = self.query_normalizer.normalize(raw_text)
        search_text = norm_rec.search_query if norm_rec.search_query.strip() else raw_text

        intent = normalize_query_intent(norm_rec.normalized_query)
        filter_fn = build_metadata_filter(query)

        # 2. Dense Semantic Retrieval
        q_vec = self.embedding_model.encode_query(search_text)
        dense_results = self.vector_store.search(
            query_vector=q_vec,
            top_k=self.config.dense_top_k,
            filter_fn=filter_fn
        )

        # 3. Sparse Keyword Retrieval (BM25)
        sparse_results = self.sparse_retriever.search(
            query=search_text,
            top_k=self.config.sparse_top_k,
            filter_fn=filter_fn
        )

        # 4. Result Fusion
        fused_candidates = fuse_results(
            dense_results=dense_results,
            sparse_results=sparse_results,
            metadata_map=self._doc_metadata_map,
            dense_weight=self.config.dense_weight,
            sparse_weight=self.config.sparse_weight,
            top_k=self.config.rerank_top_k
        )

        # 5. Metadata-Aware Reranking with Normalization Signals
        reranked_chunks = self.reranker.rerank(
            query=search_text,
            candidates=fused_candidates,
            top_k=query.top_k or self.config.final_top_k,
            matched_schemes=norm_rec.matched_schemes,
        )

        # Attach normalization metadata to chunks
        primary_match_method = (
            norm_rec.matched_schemes[0].match_method if norm_rec.matched_schemes else "STANDARD"
        )
        for rank_idx, chunk in enumerate(reranked_chunks, start=1):
            if "normalization_method" not in chunk.metadata:
                chunk.metadata["normalization_method"] = primary_match_method
            chunk.metadata["detected_language"] = norm_rec.detected_language
            chunk.metadata["retrieval_query"] = search_text
            chunk.metadata["rank"] = rank_idx

        # Apply minimum score threshold if set
        if query.min_score > 0.0:
            reranked_chunks = [c for c in reranked_chunks if c.rerank_score >= query.min_score]

        return reranked_chunks

    def retrieve_schemes(self, query: RetrievalQuery) -> List[SchemeRetrievalResult]:
        """
        Scheme-level deduplication view.
        Aggregates retrieved chunks by scheme_slug and ranks schemes by supporting evidence.
        For multi-scheme / comparison queries, decomposes into atomic per-entity sub-queries
        and merges via fair interleaving.
        """
        raw_text = query.query_text.strip()
        if not raw_text:
            return []

        norm_rec = self.query_normalizer.normalize(raw_text)

        # Multi-Scheme Query Handling
        if norm_rec.is_multi_entity and norm_rec.decomposition and len(norm_rec.decomposition.entities) > 1:
            per_entity_results: List[List[SchemeRetrievalResult]] = []
            entity_metadata_list: List[Dict[str, Any]] = []

            for entity in norm_rec.decomposition.entities:
                sub_query_text = entity.sub_query or entity.entity_text
                sub_q = RetrievalQuery(
                    query_text=sub_query_text,
                    language=query.language,
                    top_k=max(5, query.top_k or 10),
                    state_filter=query.state_filter,
                    category_filter=query.category_filter,
                    beneficiary_filter=query.beneficiary_filter,
                    content_type_filter=query.content_type_filter,
                    min_score=query.min_score
                )
                entity_schemes = self._retrieve_schemes_single(sub_q, original_query_text=raw_text)
                per_entity_results.append(entity_schemes)
                entity_metadata_list.append({
                    "query_entity": entity.entity_text,
                    "scheme_ids": [entity.scheme_slug] if entity.scheme_slug else [s.scheme_slug for s in entity_schemes[:2]],
                })

            merged_schemes = self.decomposer.interleave_results(
                per_entity_results=per_entity_results,
                total_top_k=query.top_k or self.config.final_top_k
            )

            for rank_idx, scheme in enumerate(merged_schemes, start=1):
                scheme.source_metadata["is_multi_entity"] = True
                scheme.source_metadata["comparison_type"] = norm_rec.decomposition.comparison_type
                scheme.source_metadata["entities"] = entity_metadata_list
                scheme.source_metadata["normalization_method"] = "MULTI_ENTITY_DECOMPOSITION"
                scheme.source_metadata["rank"] = rank_idx

            return merged_schemes

        return self._retrieve_schemes_single(query, original_query_text=raw_text, norm_record=norm_rec)

    def _retrieve_schemes_single(
        self,
        query: RetrievalQuery,
        original_query_text: str = "",
        norm_record: Optional[NormalizedQueryRecord] = None
    ) -> List[SchemeRetrievalResult]:
        """Executes single-entity scheme-level aggregation."""
        # Retrieve larger chunk pool for aggregation
        chunk_query = RetrievalQuery(
            query_text=query.query_text,
            language=query.language,
            top_k=max(20, (query.top_k or 10) * 3),
            state_filter=query.state_filter,
            category_filter=query.category_filter,
            beneficiary_filter=query.beneficiary_filter,
            content_type_filter=query.content_type_filter,
            min_score=query.min_score
        )
        chunks = self.retrieve(chunk_query)
        if not chunks:
            return []

        # Group chunks by scheme_slug
        scheme_groups: Dict[str, List[RetrievedChunk]] = defaultdict(list)
        for chunk in chunks:
            slug = chunk.scheme_slug or "unknown_scheme"
            scheme_groups[slug].append(chunk)

        scheme_results: List[SchemeRetrievalResult] = []

        norm_method = (
            norm_record.matched_schemes[0].match_method
            if (norm_record and norm_record.matched_schemes)
            else "STANDARD"
        )
        conf_score = (
            norm_record.matched_schemes[0].confidence
            if (norm_record and norm_record.matched_schemes)
            else 1.0
        )

        for slug, group in scheme_groups.items():
            # Sort group chunks descending by score
            group.sort(key=lambda c: (-c.rerank_score, c.chunk_id))
            primary_chunk = group[0]
            scheme_name = primary_chunk.scheme_name or slug

            # Aggregate score: top chunk score + damped contribution from secondary chunks
            best_score = primary_chunk.rerank_score
            secondary_sum = sum(c.rerank_score for c in group[1:4])
            aggregate = round(best_score + 0.05 * secondary_sum, 4)

            source_meta = {
                "total_matching_chunks": len(group),
                "sections_matched": list({c.metadata.get("section") for c in group if c.metadata.get("section")}),
                "content_types_matched": list({c.metadata.get("content_type") for c in group if c.metadata.get("content_type")}),
                "highest_source_tier": group[0].source_tier,
                "source_url": primary_chunk.metadata.get("source_url"),
                "state": primary_chunk.metadata.get("state"),
                "ministry": primary_chunk.metadata.get("ministry"),
                "normalization_method": norm_method,
                "confidence": conf_score,
                "original_query": original_query_text or query.query_text,
                "retrieval_query": primary_chunk.metadata.get("retrieval_query", query.query_text),
            }

            scheme_results.append(SchemeRetrievalResult(
                scheme_slug=slug,
                scheme_name=scheme_name,
                aggregate_score=aggregate,
                best_matching_chunks=group[:3],
                source_metadata=source_meta
            ))

        # Sort schemes descending by aggregate score
        scheme_results.sort(key=lambda s: (-s.aggregate_score, s.scheme_slug))
        results_slice = scheme_results[:query.top_k or self.config.final_top_k]
        for rank_idx, s in enumerate(results_slice, start=1):
            s.source_metadata["rank"] = rank_idx
        return results_slice

    def save_indexes(self, index_dir: Optional[str] = None) -> None:
        """Persists dense vector store and sparse BM25 index to disk."""
        target_dir = Path(index_dir or self.config.index_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        self.vector_store.save(str(target_dir / "dense"))
        self.sparse_retriever.save(str(target_dir / "sparse" / "bm25.pkl"))

    def load_indexes(self, index_dir: Optional[str] = None) -> None:
        """Loads dense and sparse indexes from disk."""
        target_dir = Path(index_dir or self.config.index_dir)
        dense_path = target_dir / "dense"
        sparse_path = target_dir / "sparse" / "bm25.pkl"

        if not dense_path.exists() or not sparse_path.exists():
            raise FileNotFoundError(f"Indexes not found at {target_dir}")

        # Vector Store load
        if self.config.use_faiss:
            try:
                from .store import FAISSVectorStore
                self.vector_store = FAISSVectorStore.load(str(dense_path))
            except Exception:
                from .store import NumpyVectorStore
                self.vector_store = NumpyVectorStore.load(str(dense_path))
        else:
            from .store import NumpyVectorStore
            self.vector_store = NumpyVectorStore.load(str(dense_path))

        # Sparse Load
        self.sparse_retriever = BM25Retriever.load(str(sparse_path))
        self._doc_metadata_map = {meta["id"]: meta for meta in self.vector_store._metadata}
