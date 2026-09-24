"""
FIN Health, Readiness, and Version Endpoints.
Provides non-destructive liveness probes, local dependency readiness checks,
and build/version inspection without invoking expensive LLM or network calls.
"""

import json
from pathlib import Path
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import verify_service_api_key
from ..schemas import HealthResponse, ReadinessResponse, VersionResponse
from ..config import DEFAULT_SERVICE_CONFIG
from src.llm.config import LLMConfig

router = APIRouter(tags=["Health & System"])


@router.get(
    "/health/live",
    response_model=HealthResponse,
    summary="Service Liveness Probe",
    description="Fast, non-blocking check to determine if the microservice process is alive. Public.",
)
def get_liveness() -> HealthResponse:
    """Returns 200 OK if the process is responsive. Does not call LLMs or databases."""
    return HealthResponse(status="ok", service="fin-ai")


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    summary="Service Readiness Probe",
    description="Verifies local dependency readiness (corpus, rules, index, config) without live LLM calls. Protected.",
)
def get_readiness(
    _: str = Depends(verify_service_api_key)
) -> ReadinessResponse:
    """Verifies that the microservice has its local policy dataset, rules, and configuration ready."""
    ai_root = Path(__file__).resolve().parents[3]
    checks: Dict[str, str] = {}
    is_ready = True

    # 1. Configuration check
    try:
        llm_cfg = LLMConfig.from_env()
        checks["config"] = "ok"
    except Exception as e:
        checks["config"] = f"error: {e}"
        is_ready = False

    # 2. Scheme corpus check
    corpus_file = ai_root / "data" / "processed" / "schemes_canonical.parquet"
    raw_csv = ai_root / "data" / "raw" / "updated_data.csv"
    if corpus_file.exists() or raw_csv.exists():
        checks["corpus"] = "ok"
    else:
        checks["corpus"] = "missing_corpus_files"
        is_ready = False

    # 3. Rules availability check
    rules_dir = ai_root / "data" / "schemes" / "rules"
    if rules_dir.exists():
        checks["rules"] = "ok"
    else:
        checks["rules"] = "missing_rules_dir"
        is_ready = False

    # 4. RAG knowledge chunks check
    rag_chunks = ai_root / "data" / "processed" / "rag" / "rag_chunks.parquet"
    if rag_chunks.exists() or corpus_file.exists():
        checks["rag"] = "ok"
    else:
        checks["rag"] = "missing_rag_data"
        is_ready = False

    if not is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "checks": checks}
        )

    return ReadinessResponse(status="ready", checks=checks)


@router.get(
    "/version",
    response_model=VersionResponse,
    summary="Service Version & Pipeline Info",
    description="Returns metadata about API version, AI pipeline version, active provider mode, and knowledge base snapshot. Protected.",
)
def get_version(
    _: str = Depends(verify_service_api_key)
) -> VersionResponse:
    """Returns version identifiers and active snapshot without leaking secrets."""
    ai_root = Path(__file__).resolve().parents[3]
    active_snapshot_file = ai_root / "data" / "snapshots" / "active_version.json"
    kb_version = "snapshot_unknown"

    if active_snapshot_file.exists():
        try:
            with open(active_snapshot_file, "r", encoding="utf-8") as f:
                snap_data = json.load(f)
                kb_version = snap_data.get("active_snapshot", "snapshot_unknown")
        except Exception:
            pass

    llm_cfg = LLMConfig.from_env()

    return VersionResponse(
        service="fin-ai",
        api_version="v1",
        pipeline_version="phase-9",
        llm_provider_mode=llm_cfg.provider,
        knowledge_base_version=kb_version,
    )
