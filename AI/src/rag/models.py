"""
PolicySetu RAG Knowledge Base and Retrieval Data Models.
Defines strongly typed, serialization-friendly models for RAG documents, chunks,
queries, and scheme-level retrieval results with explicit source tiers.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SourceTier(str, Enum):
    """
    Explicit source tier hierarchy preserving authoritative data provenance.
    Higher tiers are preferred for statutory evidence presentation.
    """
    PRIMARY_SCHEME = "PRIMARY_SCHEME"          # Canonicalized schemes derived from schemes.csv
    PRIMARY_FAQ = "PRIMARY_FAQ"                # Authoritative FAQ pairs linked by scheme_slug
    SUPPLEMENTARY_SCHEME = "SUPPLEMENTARY_SCHEME" # Supplementary schemes from updated_data.csv
    EVALUATION_ONLY = "EVALUATION_ONLY"        # Bilingual English/Hindi query-evaluation corpus
    RAG_ARCHIVE = "RAG_ARCHIVE"                # Supplementary long-form state archive documents


class ContentType(str, Enum):
    """Semantic section and content classification for retrieval chunks."""
    SCHEME_OVERVIEW = "scheme_overview"
    ELIGIBILITY = "eligibility"
    EXCLUSIONS = "exclusions"
    BENEFITS = "benefits"
    APPLICATION_PROCESS = "application_process"
    DOCUMENTS_REQUIRED = "documents_required"
    FAQ = "faq"
    SUPPLEMENTARY_DOCUMENT = "supplementary_document"


@dataclass
class RAGDocument:
    """
    Represents an atomic, normalized RAG document chunk with immutable provenance.
    """
    id: str
    content: str
    content_type: str
    source_dataset: str
    source_tier: str
    scheme_id: Optional[str] = None
    scheme_slug: Optional[str] = None
    scheme_name: Optional[str] = None
    source_url: Optional[str] = None
    source_document: Optional[str] = None
    source_page: Optional[int] = None
    section: Optional[str] = None
    state: Optional[str] = None
    ministry: Optional[str] = None
    department: Optional[str] = None
    category: Optional[str] = None
    beneficiary_type: Optional[str] = None
    language: str = "en"
    faq_id: Optional[str] = None
    created_at: Optional[str] = None
    text_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "scheme_id": self.scheme_id,
            "scheme_slug": self.scheme_slug,
            "scheme_name": self.scheme_name,
            "content": self.content,
            "content_type": self.content_type,
            "source_dataset": self.source_dataset,
            "source_tier": self.source_tier,
            "source_url": self.source_url,
            "source_document": self.source_document,
            "source_page": self.source_page,
            "section": self.section,
            "state": self.state,
            "ministry": self.ministry,
            "department": self.department,
            "category": self.category,
            "beneficiary_type": self.beneficiary_type,
            "language": self.language,
            "faq_id": self.faq_id,
            "created_at": self.created_at,
            "text_hash": self.text_hash,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RAGDocument":
        return cls(
            id=data["id"],
            scheme_id=data.get("scheme_id"),
            scheme_slug=data.get("scheme_slug"),
            scheme_name=data.get("scheme_name"),
            content=data["content"],
            content_type=data.get("content_type", ContentType.SCHEME_OVERVIEW.value),
            source_dataset=data.get("source_dataset", "unknown"),
            source_tier=data.get("source_tier", SourceTier.PRIMARY_SCHEME.value),
            source_url=data.get("source_url"),
            source_document=data.get("source_document"),
            source_page=data.get("source_page"),
            section=data.get("section"),
            state=data.get("state"),
            ministry=data.get("ministry"),
            department=data.get("department"),
            category=data.get("category"),
            beneficiary_type=data.get("beneficiary_type"),
            language=data.get("language", "en"),
            faq_id=data.get("faq_id"),
            created_at=data.get("created_at"),
            text_hash=data.get("text_hash", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class RetrievedChunk:
    """
    A single retrieved chunk with dense, sparse, fused, and rerank scores.
    """
    chunk_id: str
    content: str
    scheme_id: Optional[str] = None
    scheme_slug: Optional[str] = None
    scheme_name: Optional[str] = None
    dense_score: float = 0.0
    sparse_score: float = 0.0
    fused_score: float = 0.0
    rerank_score: float = 0.0
    source_tier: str = SourceTier.PRIMARY_SCHEME.value
    provenance: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "scheme_id": self.scheme_id,
            "scheme_slug": self.scheme_slug,
            "scheme_name": self.scheme_name,
            "content": self.content,
            "dense_score": self.dense_score,
            "sparse_score": self.sparse_score,
            "fused_score": self.fused_score,
            "rerank_score": self.rerank_score,
            "source_tier": self.source_tier,
            "provenance": self.provenance,
            "metadata": self.metadata,
        }


@dataclass
class RetrievalQuery:
    """
    Structured query specification supporting multilingual text and metadata filters.
    """
    query_text: str
    language: str = "en"
    top_k: int = 10
    state_filter: Optional[str] = None
    category_filter: Optional[str] = None
    beneficiary_filter: Optional[str] = None
    content_type_filter: Optional[str] = None
    min_score: float = 0.0


@dataclass
class SchemeRetrievalResult:
    """
    Deduplicated scheme-level retrieval result aggregating supporting evidence chunks.
    """
    scheme_slug: str
    scheme_name: str
    aggregate_score: float
    best_matching_chunks: List[RetrievedChunk] = field(default_factory=list)
    source_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scheme_slug": self.scheme_slug,
            "scheme_name": self.scheme_name,
            "aggregate_score": self.aggregate_score,
            "best_matching_chunks": [c.to_dict() for c in self.best_matching_chunks],
            "source_metadata": self.source_metadata,
        }


@dataclass
class RetrievalIntent:
    """
    Preprocessed query intent object containing hints extracted from user query.
    Never decides eligibility; provides retrieval filtering signals only.
    """
    raw_query: str
    normalized_query: str
    language: str = "en"
    detected_state: Optional[str] = None
    detected_category: Optional[str] = None
    detected_beneficiary_type: Optional[str] = None
    intent_terms: List[str] = field(default_factory=list)
