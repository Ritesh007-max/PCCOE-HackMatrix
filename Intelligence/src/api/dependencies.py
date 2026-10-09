"""
FIN API Dependencies.
Dependency injection providers for shared components: ApplicationPipeline,
DocumentPipeline, EligibilityEngine, HybridRetriever, and rate limiting.
"""

import logging
from pathlib import Path
from typing import Optional

from src.pipelines.application_pipeline import ApplicationPipeline
from src.documents.pipeline import DocumentPipeline
from src.documents.validator import DocumentValidator
from src.eligibility.engine import EligibilityEngine
from src.rules.evaluator import RuleEvaluator
from src.rag.retriever import HybridRetriever
from src.rag.config import DEFAULT_RAG_CONFIG, RAGConfig
from src.rag.ingestion import RAGIngestionPipeline
from src.llm.client import LLMClient
from src.llm.config import LLMConfig
from .config import DEFAULT_SERVICE_CONFIG, ServiceConfig
from .middleware import DEFAULT_RATE_LIMITER, InMemoryRateLimiter

from src.context.service import ApplicantContextService
from src.persistence.repository import FactPersistenceRepository

logger = logging.getLogger("fin.api.dependencies")

# Singleton component cache
_application_pipeline: Optional[ApplicationPipeline] = None
_document_pipeline: Optional[DocumentPipeline] = None
_document_validator: Optional[DocumentValidator] = None
_eligibility_engine: Optional[EligibilityEngine] = None
_hybrid_retriever: Optional[HybridRetriever] = None
_llm_client: Optional[LLMClient] = None
_persistence_repo: Optional[FactPersistenceRepository] = None
_applicant_context_service: Optional[ApplicantContextService] = None


def get_service_config() -> ServiceConfig:
    """Returns service configuration."""
    return DEFAULT_SERVICE_CONFIG


def get_rate_limiter() -> InMemoryRateLimiter:
    """Returns in-memory rate limiter instance."""
    return DEFAULT_RATE_LIMITER


def get_document_validator() -> DocumentValidator:
    """Returns singleton DocumentValidator."""
    global _document_validator
    if _document_validator is None:
        _document_validator = DocumentValidator(
            max_file_size_bytes=DEFAULT_SERVICE_CONFIG.max_upload_size_mb * 1024 * 1024,
            allow_duplicates=True,
        )
    return _document_validator


def get_document_pipeline() -> DocumentPipeline:
    """Returns singleton DocumentPipeline."""
    global _document_pipeline
    if _document_pipeline is None:
        _document_pipeline = DocumentPipeline(
            validator=get_document_validator()
        )
    return _document_pipeline


def get_application_pipeline() -> ApplicationPipeline:
    """Returns singleton Phase 8 ApplicationPipeline."""
    global _application_pipeline
    if _application_pipeline is None:
        _application_pipeline = ApplicationPipeline()
    return _application_pipeline


def get_eligibility_engine() -> EligibilityEngine:
    """Returns singleton deterministic EligibilityEngine loaded with statutory rules."""
    global _eligibility_engine
    if _eligibility_engine is None:
        engine = EligibilityEngine()
        # Locate rules directory if available
        ai_root = Path(__file__).resolve().parents[2]
        rules_dir = ai_root / "data" / "schemes" / "rules" / "examples"
        if rules_dir.exists():
            try:
                loaded = engine.load_rules_from_directory(rules_dir)
                logger.info("EligibilityEngine loaded %d statutory rule sets from %s", loaded, rules_dir)
            except Exception as e:
                logger.warning("Could not load rules from directory %s: %s", rules_dir, e)
        _eligibility_engine = engine
    return _eligibility_engine


def get_hybrid_retriever() -> HybridRetriever:
    """Returns singleton HybridRetriever with indexed schemes."""
    global _hybrid_retriever
    if _hybrid_retriever is None:
        retriever = HybridRetriever(config=DEFAULT_RAG_CONFIG)
        ai_root = Path(__file__).resolve().parents[2]
        ingestion = RAGIngestionPipeline(config=DEFAULT_RAG_CONFIG)
        try:
            # 1. Index all canonical schemes into sparse BM25 index and doc metadata map (< 0.5s for 4749 schemes)
            canonical_parquet = ai_root / "data" / "processed" / "schemes_canonical.parquet"
            if canonical_parquet.exists():
                import pandas as pd
                import numpy as np
                df = pd.read_parquet(canonical_parquet)
                docs = []
                for idx, r in df.iterrows():
                    slug = str(r.get("slug", ""))
                    s_id = str(r.get("id", ""))
                    name = str(r.get("scheme_name", ""))
                    desc = str(r.get("brief_description", ""))
                    state = str(r.get("state", "")) if pd.notna(r.get("state")) else None
                    cat = str(r.get("category", "")) if "category" in r and pd.notna(r.get("category")) else None
                    ben = str(r.get("beneficiary_type", "")) if pd.notna(r.get("beneficiary_type")) else None
                    raw_tags = r.get("tags")
                    if isinstance(raw_tags, (list, np.ndarray)):
                        tags = " ".join(str(t) for t in raw_tags)
                    elif pd.notna(raw_tags):
                        tags = str(raw_tags)
                    else:
                        tags = ""

                    content = f"{name}. {desc}. Category: {cat or ''}. Tags: {tags}. State: {state or 'All India'}."
                    from src.rag.models import RAGDocument, SourceTier
                    doc = RAGDocument(
                        id=f"doc_{slug}",
                        content=content,
                        content_type="scheme",
                        source_dataset="schemes_canonical.parquet",
                        source_tier=SourceTier.PRIMARY_SCHEME.value,
                        scheme_id=s_id,
                        scheme_slug=slug,
                        scheme_name=name,
                        state=state,
                        category=cat,
                        beneficiary_type=ben,
                        metadata={
                            "scheme_id": s_id,
                            "scheme_slug": slug,
                            "scheme_name": name,
                            "state": state,
                            "level": str(r.get("level", "")) if pd.notna(r.get("level")) else None,
                            "ministry": str(r.get("ministry", "")) if pd.notna(r.get("ministry")) else None,
                            "department": str(r.get("department", "")) if pd.notna(r.get("department")) else None,
                            "category": cat,
                            "beneficiary_type": ben,
                            "target_beneficiaries": list(r.get("target_beneficiaries")) if isinstance(r.get("target_beneficiaries"), (list, np.ndarray)) else str(r.get("target_beneficiaries") or ""),
                            "brief_description": desc,
                            "tags": tags,
                            "eligibility": str(r.get("eligibility", "")) if pd.notna(r.get("eligibility")) else "",
                        }
                    )
                    docs.append(doc)

                retriever.sparse_retriever.fit(docs)
                for d in docs:
                    meta = d.to_dict()
                    meta.update(d.metadata or {})
                    retriever._doc_metadata_map[d.id] = meta
                logger.info("HybridRetriever loaded BM25 and metadata for %d canonical schemes", len(docs))

            # 2. Check vector store
            raw_cnt = getattr(retriever.vector_store, "count", 0)
            cnt = raw_cnt() if callable(raw_cnt) else raw_cnt
            if cnt and cnt > 0:
                logger.info("HybridRetriever reusing existing index (%d vectors)", cnt)
            else:
                primary_docs = ingestion.load_primary_schemes(limit=5)
                if primary_docs:
                    embeddings = retriever.embedding_model.encode_documents([d.content for d in primary_docs])
                    meta_list = [d.to_dict() for d in primary_docs]
                    retriever.vector_store.add(embeddings, meta_list)
                    for d in primary_docs:
                        retriever._doc_metadata_map[d.id] = d.to_dict()
                    logger.info("HybridRetriever indexed %d vectors into vector store", len(primary_docs))

        except Exception as e:
            logger.warning("Could not pre-index schemes into HybridRetriever: %s", e)
        _hybrid_retriever = retriever
    return _hybrid_retriever




def get_llm_client() -> LLMClient:
    """Returns singleton LLMClient."""
    global _llm_client
    if _llm_client is None:
        config = LLMConfig.from_env()
        _llm_client = LLMClient(config=config)
    return _llm_client


def get_persistence_repository() -> FactPersistenceRepository:
    """Returns singleton FactPersistenceRepository."""
    global _persistence_repo
    if _persistence_repo is None:
        _persistence_repo = FactPersistenceRepository()
    return _persistence_repo


def get_applicant_context_service() -> ApplicantContextService:
    """Returns singleton ApplicantContextService."""
    global _applicant_context_service
    if _applicant_context_service is None:
        _applicant_context_service = ApplicantContextService(
            repository=get_persistence_repository()
        )
    return _applicant_context_service


_query_understanding_service = None


def get_query_understanding_service():
    """Returns singleton QueryUnderstandingService bound to the active ApplicantContextService."""
    global _query_understanding_service
    if _query_understanding_service is None:
        from src.query.service import QueryUnderstandingService
        _query_understanding_service = QueryUnderstandingService(
            applicant_context_service=get_applicant_context_service()
        )
    return _query_understanding_service


def get_scheme_recommendation_service():
    """Returns SchemeRecommendationService bound to shared components."""
    from src.recommendation.service import SchemeRecommendationService
    return SchemeRecommendationService(
        context_service=get_applicant_context_service(),
        query_service=get_query_understanding_service(),
        retriever=get_hybrid_retriever(),
        eligibility_engine=get_eligibility_engine(),
    )


_explanation_service = None


def get_explanation_service():
    """Returns singleton PolicyExplanationService (Phase 21)."""
    global _explanation_service
    if _explanation_service is None:
        from src.explanation.service import PolicyExplanationService
        _explanation_service = PolicyExplanationService(
            llm_client=get_llm_client()
        )
    return _explanation_service


_conflict_resolution_service = None
_unified_orchestrator = None


def get_conflict_resolution_service():
    """Returns singleton ConflictResolutionService."""
    global _conflict_resolution_service
    if _conflict_resolution_service is None:
        from src.review.service import ConflictResolutionService
        _conflict_resolution_service = ConflictResolutionService(
            context_service=get_applicant_context_service()
        )
    return _conflict_resolution_service


def get_unified_orchestrator():
    """Returns singleton UnifiedIntelligenceOrchestrator."""
    global _unified_orchestrator
    if _unified_orchestrator is None:
        from src.orchestration.orchestrator import UnifiedIntelligenceOrchestrator
        _unified_orchestrator = UnifiedIntelligenceOrchestrator(
            context_service=get_applicant_context_service(),
            query_service=get_query_understanding_service(),
            conflict_service=get_conflict_resolution_service(),
            recommendation_service=get_scheme_recommendation_service(),
            eligibility_engine=get_eligibility_engine(),
            explanation_service=get_explanation_service(),
            retriever=get_hybrid_retriever(),
            llm_client=get_llm_client(),
        )
    return _unified_orchestrator



