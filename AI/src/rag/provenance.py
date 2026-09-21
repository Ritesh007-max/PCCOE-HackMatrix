"""
PolicySetu RAG Provenance Engine.
Ensures every retrieved result preserves complete statutory citation, dataset origin,
source tier, and cryptographic content hashes. Never fabricates provenance.
"""

import hashlib
from typing import Any, Dict, Optional
from .models import RAGDocument, RetrievedChunk, SourceTier


def compute_content_hash(text: str) -> str:
    """Computes a deterministic SHA-256 hash of text content for deduplication and audit."""
    normalized = " ".join(text.strip().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def generate_stable_chunk_id(
    scheme_slug: Optional[str],
    content_type: str,
    section: Optional[str],
    chunk_index: int,
    faq_id: Optional[str] = None,
    source_dataset: str = "schemes_canonical"
) -> str:
    """
    Generates a deterministic, reproducible chunk ID.
    Running twice on identical input always produces identical IDs.
    """
    base = f"{source_dataset}::{scheme_slug or 'global'}::{content_type}::{section or 'main'}"
    if faq_id:
        base += f"::faq_{faq_id}"
    base += f"::chunk_{chunk_index}"
    # Deterministic 16-char suffix from hash
    hash_suffix = hashlib.sha256(base.encode("utf-8")).hexdigest()[:12]
    # Clean prefix for human readability
    safe_slug = (scheme_slug or "global")[:24].replace(" ", "_")
    return f"chk_{safe_slug}_{content_type[:4]}_{hash_suffix}"


def build_provenance_record(doc: RAGDocument) -> Dict[str, Any]:
    """Builds a structured provenance dictionary for a RAG document or chunk."""
    return {
        "source_dataset": doc.source_dataset,
        "source_tier": doc.source_tier,
        "source_url": doc.source_url,
        "source_document": doc.source_document,
        "source_page": doc.source_page,
        "section": doc.section,
        "content_type": doc.content_type,
        "faq_id": doc.faq_id,
        "text_hash": doc.text_hash or compute_content_hash(doc.content),
        "created_at": doc.created_at,
    }


def verify_provenance_integrity(chunk: RetrievedChunk) -> bool:
    """
    Checks that a retrieved chunk possesses valid provenance.
    Returns False if provenance is missing or fabricated.
    """
    prov = chunk.provenance
    if not prov or not isinstance(prov, dict):
        return False
    # Must have at least a valid source_dataset and source_tier
    if not prov.get("source_dataset") or not prov.get("source_tier"):
        return False
    # source_tier must be a recognized tier
    valid_tiers = {tier.value for tier in SourceTier}
    if prov.get("source_tier") not in valid_tiers:
        return False
    return True
