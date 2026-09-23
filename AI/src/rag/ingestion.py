"""
PolicySetu Deterministic Ingestion Pipeline.
Loads audited datasets across explicit source tiers, executes section-aware chunking,
deduplicates content, and persists normalized RAG documents to processed storage.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, cast
import pandas as pd

_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

try:
    from .models import RAGDocument, SourceTier, ContentType
    from .config import RAGConfig, DEFAULT_RAG_CONFIG
    from .chunking import chunk_scheme_record, chunk_faq_record
except (ImportError, ValueError):
    from src.rag.models import RAGDocument, SourceTier, ContentType
    from src.rag.config import RAGConfig, DEFAULT_RAG_CONFIG
    from src.rag.chunking import chunk_scheme_record, chunk_faq_record


class RAGIngestionPipeline:
    """
    Ingests and normalizes government policy schemes, FAQs, and supplementary datasets.
    Preserves explicit source tier hierarchy:
      PRIMARY_SCHEME > PRIMARY_FAQ > SUPPLEMENTARY_SCHEME > RAG_ARCHIVE > EVALUATION_ONLY
    """

    def __init__(self, config: RAGConfig = DEFAULT_RAG_CONFIG):
        self.config = config
        self.ai_root = Path(config.ai_root) if config.ai_root else Path(".")
        self.raw_dir = self.ai_root / "data" / "raw"
        self.processed_dir = self.ai_root / "data" / "processed"
        self.rag_output_dir = Path(config.processed_rag_dir) if config.processed_rag_dir else self.processed_dir / "rag"

    def load_primary_schemes(
        self,
        limit: Optional[int] = None,
        include_slugs: Optional[List[str]] = None
    ) -> List[RAGDocument]:
        """
        Loads canonicalized schemes derived from schemes.csv.
        Reads from schemes_canonical.parquet (or schemes.csv as fallback).
        """
        parquet_path = self.processed_dir / "schemes_canonical.parquet"
        docs: List[RAGDocument] = []

        if parquet_path.exists():
            df = pd.read_parquet(parquet_path)
            if include_slugs:
                slug_df = df[df["slug"].isin(include_slugs)]
                other_df = df[~df["slug"].isin(include_slugs)]
                if limit:
                    other_df = other_df.head(max(0, limit - len(slug_df)))
                df = pd.concat([slug_df, other_df], ignore_index=True)
            elif limit:
                df = df.head(limit)
            records = cast(Any, df).to_dict(orient="records")
        else:
            raw_csv = self.raw_dir / "schemes.csv"
            if not raw_csv.exists():
                return []
            df = pd.read_csv(raw_csv)
            if include_slugs:
                slug_df = df[df["slug"].isin(include_slugs)]
                other_df = df[~df["slug"].isin(include_slugs)]
                if limit:
                    other_df = other_df.head(max(0, limit - len(slug_df)))
                df = pd.concat([slug_df, other_df], ignore_index=True)
            elif limit:
                df = df.head(limit)
            records = cast(Any, df).to_dict(orient="records")

        for rec in records:
            chunks = chunk_scheme_record(
                rec,
                source_tier=SourceTier.PRIMARY_SCHEME.value,
                source_dataset="schemes.csv",
                config=self.config
            )
            docs.extend(chunks)

        return docs

    def load_primary_faqs(
        self,
        limit: Optional[int] = None,
        include_slugs: Optional[List[str]] = None
    ) -> List[RAGDocument]:
        """Loads authoritative FAQs from schemes_faqs.csv."""
        faq_csv = self.raw_dir / "schemes_faqs.csv"
        if not faq_csv.exists():
            return []

        df = pd.read_csv(faq_csv)
        if include_slugs:
            slug_df = df[df["scheme_slug"].isin(include_slugs)]
            other_df = df[~df["scheme_slug"].isin(include_slugs)]
            if limit:
                other_df = other_df.head(max(0, limit - len(slug_df)))
            df = pd.concat([slug_df, other_df], ignore_index=True)
        elif limit:
            df = df.head(limit)
        records = cast(Any, df).to_dict(orient="records")
        docs: List[RAGDocument] = []

        for rec in records:
            chunks = chunk_faq_record(
                rec,
                source_tier=SourceTier.PRIMARY_FAQ.value,
                source_dataset="schemes_faqs.csv",
                config=self.config
            )
            docs.extend(chunks)

        return docs

    def load_supplementary_schemes(self, limit: Optional[int] = None) -> List[RAGDocument]:
        """Loads supplementary scheme data from updated_data.csv without overriding primary."""
        supp_csv = self.raw_dir / "updated_data.csv"
        if not supp_csv.exists():
            return []

        df = pd.read_csv(supp_csv, nrows=limit)
        records = df.to_dict(orient="records")
        docs: List[RAGDocument] = []

        for rec in records:
            chunks = chunk_scheme_record(
                rec,
                source_tier=SourceTier.SUPPLEMENTARY_SCHEME.value,
                source_dataset="updated_data.csv",
                config=self.config
            )
            docs.extend(chunks)

        return docs

    def run_ingestion(
        self,
        scheme_limit: Optional[int] = None,
        faq_limit: Optional[int] = None,
        include_supplementary: bool = True,
        save_to_disk: bool = True,
        include_slugs: Optional[List[str]] = None
    ) -> List[RAGDocument]:
        """
        Executes full deterministic ingestion pipeline with content deduplication.
        """
        all_docs: List[RAGDocument] = []

        # 1. Primary Schemes
        primary_schemes = self.load_primary_schemes(limit=scheme_limit, include_slugs=include_slugs)
        all_docs.extend(primary_schemes)

        # 2. Primary FAQs
        primary_faqs = self.load_primary_faqs(limit=faq_limit, include_slugs=include_slugs)
        all_docs.extend(primary_faqs)

        # 3. Supplementary Schemes
        if include_supplementary:
            supp_schemes = self.load_supplementary_schemes(limit=scheme_limit)
            all_docs.extend(supp_schemes)

        # Deduplicate identical chunks by text_hash
        seen_hashes: Set[str] = set()
        deduped_docs: List[RAGDocument] = []

        for doc in all_docs:
            if doc.text_hash not in seen_hashes:
                seen_hashes.add(doc.text_hash)
                deduped_docs.append(doc)

        if save_to_disk and deduped_docs:
            self.save_processed_chunks(deduped_docs)

        return deduped_docs

    def save_processed_chunks(self, docs: List[RAGDocument]) -> None:
        """Saves RAG documents to Parquet and JSONL in AI/data/processed/rag/."""
        self.rag_output_dir.mkdir(parents=True, exist_ok=True)
        dict_records = [d.to_dict() for d in docs]
        df = pd.DataFrame(dict_records)

        # Parquet
        parquet_path = self.rag_output_dir / "rag_chunks.parquet"
        df.to_parquet(parquet_path, index=False)

        # JSONL
        jsonl_path = self.rag_output_dir / "rag_chunks.jsonl"
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for rec in dict_records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")