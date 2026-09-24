"""
FIN RAG Knowledge Base Synchronizer.
Converts normalized scheme entities into versioned, section-aware RAG chunks
with comprehensive provenance metadata and statutory authority rankings.
"""

from typing import Any, Dict, List, Optional
import hashlib
import uuid

from .models import Scheme, AuthorityTierName


class AcquisitionRAGSynchronizer:
    """
    Transforms canonical acquired schemes into RAG documents for sparse/dense retrieval.
    Enforces that statutory facts retain exact evidence spans and authority tier tags.
    """

    @classmethod
    def generate_rag_chunks_for_scheme(
        cls,
        scheme: Scheme,
        policy_version: str = "v1.0.0",
    ) -> List[Dict[str, Any]]:
        """
        Emits section-aware RAG chunks with full statutory provenance.
        """
        chunks: List[Dict[str, Any]] = []

        # 1. Scheme Overview Chunk
        overview_text = f"{scheme.scheme_name} ({scheme.canonical_slug})\n"
        if scheme.ministry:
            overview_text += f"Ministry: {scheme.ministry}\n"
        if scheme.state_or_ut:
            overview_text += f"State/UT: {scheme.state_or_ut}\n"
        overview_text += f"Category: {scheme.category}\n"
        overview_text += f"Type: {scheme.scheme_type}\n"
        if scheme.brief_description:
            overview_text += f"Summary: {scheme.brief_description}\n"

        chunks.append(
            cls._create_chunk(
                scheme=scheme,
                content=overview_text.strip(),
                content_type="scheme_overview",
                section="Overview",
                policy_version=policy_version,
                evidence_span=scheme.brief_description[:200] if scheme.brief_description else scheme.scheme_name,
            )
        )

        # 2. Eligibility Chunk
        if scheme.raw_eligibility_text or scheme.eligibility_criteria:
            elig_text = f"{scheme.scheme_name} - Eligibility Criteria:\n"
            if scheme.raw_eligibility_text:
                elig_text += scheme.raw_eligibility_text
            else:
                for crit in scheme.eligibility_criteria:
                    elig_text += f"- {crit.field} {crit.operator} {crit.value} ({crit.raw_text})\n"

            chunks.append(
                cls._create_chunk(
                    scheme=scheme,
                    content=elig_text.strip(),
                    content_type="eligibility",
                    section="Eligibility",
                    policy_version=policy_version,
                    evidence_span=scheme.raw_eligibility_text[:200] if scheme.raw_eligibility_text else "Eligibility criteria",
                )
            )

        # 3. Benefits Chunk
        if scheme.raw_benefits_text or scheme.benefits:
            ben_text = f"{scheme.scheme_name} - Benefits:\n"
            if scheme.raw_benefits_text:
                ben_text += scheme.raw_benefits_text
            else:
                for b in scheme.benefits:
                    ben_text += f"- {b.benefit_type}: {b.raw_text}\n"

            chunks.append(
                cls._create_chunk(
                    scheme=scheme,
                    content=ben_text.strip(),
                    content_type="benefits",
                    section="Benefits",
                    policy_version=policy_version,
                    evidence_span=scheme.raw_benefits_text[:200] if scheme.raw_benefits_text else "Benefits details",
                )
            )

        # 4. Application Process Chunk
        if scheme.application_steps:
            app_text = f"{scheme.scheme_name} - Application Procedure:\n"
            for step in scheme.application_steps:
                app_text += f"{step.step_number}. {step.title} ({step.mode}): {step.description}\n"

            chunks.append(
                cls._create_chunk(
                    scheme=scheme,
                    content=app_text.strip(),
                    content_type="application_process",
                    section="Application",
                    policy_version=policy_version,
                    evidence_span=scheme.application_steps[0].description[:200] if scheme.application_steps else "Application steps",
                )
            )

        # 5. Required Documents Chunk
        if scheme.required_documents:
            doc_text = f"{scheme.scheme_name} - Required Documents:\n"
            for doc in scheme.required_documents:
                doc_text += f"- {doc.document_name} ({'Mandatory' if doc.is_mandatory else 'Optional'})\n"

            chunks.append(
                cls._create_chunk(
                    scheme=scheme,
                    content=doc_text.strip(),
                    content_type="documents_required",
                    section="Documents",
                    policy_version=policy_version,
                    evidence_span=scheme.required_documents[0].document_name,
                )
            )

        # 6. FAQ Chunks (Atomic FAQ pairs)
        for idx, faq in enumerate(scheme.faqs):
            faq_text = f"Q: {faq.question}\nA: {faq.answer}"
            chunks.append(
                cls._create_chunk(
                    scheme=scheme,
                    content=faq_text,
                    content_type="faq",
                    section=f"FAQ_{idx + 1}",
                    policy_version=policy_version,
                    evidence_span=faq.question,
                    language=faq.language,
                )
            )

        return chunks

    @classmethod
    def _create_chunk(
        cls,
        scheme: Scheme,
        content: str,
        content_type: str,
        section: str,
        policy_version: str,
        evidence_span: str,
        language: str = "en",
    ) -> Dict[str, Any]:
        """Creates a single RAG chunk dictionary with full provenance."""
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        chunk_id = f"chunk_{scheme.canonical_slug}_{section.lower()}_{content_hash[:8]}"

        return {
            "id": chunk_id,
            "scheme_id": scheme.scheme_id,
            "scheme_slug": scheme.canonical_slug,
            "slug": scheme.canonical_slug,
            "scheme_name": scheme.scheme_name,
            "source_id": scheme.source_id,
            "source_url": scheme.myscheme_url or scheme.source_url,
            "authority_tier": scheme.authority_tier,
            "acquisition_run_id": getattr(scheme, "acquisition_run_id", "") or "",
            "snapshot_id": scheme.snapshot_id or "",
            "document_type": content_type,
            "section": section,
            "language": language,
            "policy_version": policy_version,
            "effective_from": scheme.effective_from,
            "effective_until": scheme.effective_until,
            "content": content,
            "content_hash": content_hash,
            "evidence_span": evidence_span,
            "state": scheme.state_or_ut,
            "ministry": scheme.ministry,
            "category": scheme.category,
        }
