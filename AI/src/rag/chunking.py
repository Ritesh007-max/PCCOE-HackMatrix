"""
PolicySetu Section-Aware Chunking Engine.
Splits policy schemes and FAQs into semantically cohesive, section-aligned chunks.
Preserves scheme identity, section headers, FAQ atomicity, and provenance.
"""

from typing import Any, Dict, List, Optional
from .models import RAGDocument, ContentType, SourceTier
from .config import RAGConfig, DEFAULT_RAG_CONFIG
from .provenance import compute_content_hash, generate_stable_chunk_id


def split_text_with_overlap(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """
    Splits long text into overlapping chunks, attempting to break at sentence or paragraph boundaries.
    """
    text = text.strip()
    if len(text) <= chunk_size:
        return [text] if text else []

    chunks: List[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size
        if end >= text_len:
            chunks.append(text[start:].strip())
            break

        # Attempt to break cleanly at paragraph or sentence boundary
        split_point = -1
        # Look for double newline (paragraph)
        p_idx = text.rfind("\n\n", start, end)
        if p_idx != -1 and p_idx > start + (chunk_size // 3):
            split_point = p_idx + 2
        else:
            # Look for sentence period
            s_idx = text.rfind(". ", start, end)
            if s_idx != -1 and s_idx > start + (chunk_size // 3):
                split_point = s_idx + 2
            else:
                # Look for single newline or space
                sp_idx = text.rfind(" ", start, end)
                if sp_idx != -1 and sp_idx > start:
                    split_point = sp_idx + 1

        if split_point == -1 or split_point <= start:
            split_point = end

        chunk_text = text[start:split_point].strip()
        if chunk_text:
            chunks.append(chunk_text)

        # Advance start with overlap
        start = max(start + 1, split_point - chunk_overlap)

    return chunks


def chunk_scheme_record(
    record: Dict[str, Any],
    source_tier: str = SourceTier.PRIMARY_SCHEME.value,
    source_dataset: str = "schemes_canonical",
    config: RAGConfig = DEFAULT_RAG_CONFIG
) -> List[RAGDocument]:
    """
    Converts a canonical or supplementary scheme dictionary into section-aligned RAGDocuments.
    Extracts:
      - overview (brief + detailed)
      - eligibility
      - exclusions
      - benefits
      - application_process
      - documents_required
    """
    scheme_id = str(record.get("id", ""))
    scheme_slug = record.get("slug") or record.get("scheme_slug", "")
    scheme_name = record.get("scheme_name", "")
    source_url = record.get("source_url")
    state = record.get("state")
    ministry = record.get("ministry")
    department = record.get("department")
    cat_val = record.get("categories")
    if cat_val is None or (hasattr(cat_val, "__len__") and len(cat_val) == 0):
        cat_val = record.get("category")
    if isinstance(cat_val, (list, tuple)) or hasattr(cat_val, "tolist"):
        if hasattr(cat_val, "tolist"):
            cat_val = cat_val.tolist()
        category = ", ".join(str(c) for c in cat_val) if cat_val else None
    else:
        category = str(cat_val) if cat_val is not None else None

    ben_val = record.get("beneficiary_type")
    if isinstance(ben_val, (list, tuple)) or hasattr(ben_val, "tolist"):
        if hasattr(ben_val, "tolist"):
            ben_val = ben_val.tolist()
        beneficiary_type = ", ".join(str(b) for b in ben_val) if ben_val else None
    else:
        beneficiary_type = str(ben_val) if ben_val is not None else None

    sections: List[tuple[str, str, str]] = []
    # (content_type, section_name, text)

    # 1. Overview
    brief = str(record.get("brief_description") or "").strip()
    detailed = str(record.get("detailed_description") or "").strip()
    overview_parts = []
    if brief:
        overview_parts.append(brief)
    if detailed and detailed != brief:
        overview_parts.append(detailed)
    if overview_parts:
        sections.append((ContentType.SCHEME_OVERVIEW.value, "Overview", "\n\n".join(overview_parts)))

    # 2. Eligibility
    elig = str(record.get("eligibility") or "").strip()
    if elig:
        sections.append((ContentType.ELIGIBILITY.value, "Eligibility Criteria", elig))

    # 3. Exclusions
    excl = str(record.get("exclusions") or "").strip()
    if excl:
        sections.append((ContentType.EXCLUSIONS.value, "Exclusions", excl))

    # 4. Benefits
    ben = str(record.get("benefits") or "").strip()
    if ben:
        sections.append((ContentType.BENEFITS.value, "Benefits", ben))

    # 5. Application Process
    app_proc = str(record.get("application_process") or "").strip()
    if app_proc:
        sections.append((ContentType.APPLICATION_PROCESS.value, "Application Process", app_proc))

    # 6. Documents Required
    docs_req = str(record.get("documents_required") or "").strip()
    if docs_req:
        sections.append((ContentType.DOCUMENTS_REQUIRED.value, "Documents Required", docs_req))

    documents: List[RAGDocument] = []
    chunk_counter = 0

    for content_type, sec_name, sec_text in sections:
        if len(sec_text) < config.min_chunk_length:
            continue

        text_chunks = split_text_with_overlap(sec_text, config.chunk_size, config.chunk_overlap)
        for i, chunk_body in enumerate(text_chunks):
            # Prepend contextual scheme header for dense embedding richness
            header = f"Scheme: {scheme_name}\nSection: {sec_name}\n\n"
            full_content = header + chunk_body

            chunk_id = generate_stable_chunk_id(
                scheme_slug=scheme_slug,
                content_type=content_type,
                section=sec_name.lower().replace(" ", "_"),
                chunk_index=i,
                source_dataset=source_dataset
            )

            doc = RAGDocument(
                id=chunk_id,
                scheme_id=scheme_id,
                scheme_slug=scheme_slug,
                scheme_name=scheme_name,
                content=full_content,
                content_type=content_type,
                source_dataset=source_dataset,
                source_tier=source_tier,
                source_url=source_url,
                section=sec_name,
                state=state,
                ministry=ministry,
                department=department,
                category=category,
                beneficiary_type=beneficiary_type,
                language="en",
                text_hash=compute_content_hash(full_content),
                metadata={
                    "section_chunk_index": i,
                    "total_section_chunks": len(text_chunks),
                    "dbt_scheme": record.get("dbt_scheme", False),
                }
            )
            documents.append(doc)
            chunk_counter += 1

    return documents


def chunk_faq_record(
    record: Dict[str, Any],
    source_tier: str = SourceTier.PRIMARY_FAQ.value,
    source_dataset: str = "schemes_faqs",
    config: RAGConfig = DEFAULT_RAG_CONFIG
) -> List[RAGDocument]:
    """
    Converts a single FAQ pair into an atomic RAGDocument.
    Keeps Question + Answer united as a single retrieval unit.
    """
    scheme_slug = str(record.get("scheme_slug", ""))
    scheme_name = str(record.get("scheme_name", ""))
    faq_num = str(record.get("faq_number", "1"))
    q = str(record.get("question", "")).strip()
    a = str(record.get("answer", "")).strip()

    if not q or not a:
        return []

    faq_body = f"Scheme: {scheme_name}\nQuestion: {q}\nAnswer: {a}"
    if len(faq_body) < config.min_chunk_length:
        return []

    # If FAQ is abnormally huge, split with overlap; otherwise keep atomic
    chunks = split_text_with_overlap(faq_body, config.chunk_size * 2, config.chunk_overlap)
    documents: List[RAGDocument] = []

    for i, c_text in enumerate(chunks):
        chunk_id = generate_stable_chunk_id(
            scheme_slug=scheme_slug,
            content_type=ContentType.FAQ.value,
            section="faq",
            chunk_index=i,
            faq_id=f"{faq_num}_{i}",
            source_dataset=source_dataset
        )

        doc = RAGDocument(
            id=chunk_id,
            scheme_id=None,
            scheme_slug=scheme_slug,
            scheme_name=scheme_name,
            content=c_text,
            content_type=ContentType.FAQ.value,
            source_dataset=source_dataset,
            source_tier=source_tier,
            source_url=record.get("source_url"),
            section="FAQ",
            faq_id=f"faq_{faq_num}",
            language="en",
            text_hash=compute_content_hash(c_text),
            metadata={
                "question": q,
                "answer": a,
                "faq_number": faq_num,
            }
        )
        documents.append(doc)

    return documents
