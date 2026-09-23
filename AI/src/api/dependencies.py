"""
PolicySetu API Dependencies.
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

logger = logging.getLogger("policysetu.api.dependencies")

# Singleton component cache
_application_pipeline: Optional[ApplicationPipeline] = None
_document_pipeline: Optional[DocumentPipeline] = None
_document_validator: Optional[DocumentValidator] = None
_eligibility_engine: Optional[EligibilityEngine] = None
_hybrid_retriever: Optional[HybridRetriever] = None
_llm_client: Optional[LLMClient] = None


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
            max_file_size_bytes=DEFAULT_SERVICE_CONFIG.max_upload_size_mb * 1024 * 1024
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
            docs = ingestion.load_primary_schemes(limit=150)
            if docs:
                retriever.index_documents(docs)
                logger.info("HybridRetriever indexed %d scheme documents", len(docs))
        except Exception as e:
            logger.warning("Could not pre-index primary schemes into HybridRetriever: %s", e)
        _hybrid_retriever = retriever
    return _hybrid_retriever


def get_llm_client() -> LLMClient:
    """Returns singleton LLMClient."""
    global _llm_client
    if _llm_client is None:
        config = LLMConfig.from_env()
        _llm_client = LLMClient(config=config)
    return _llm_client
