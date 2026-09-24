"""
FIN Dynamic Policy Operations API Routes.
Phase 12: Exposes status inspection, dry-run synchronization, live update triggers,
and atomic rollback endpoints.
Protected mutation operations require X-AI-Service-Key authentication and ADMIN role.
"""

import re
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.api.auth import verify_service_api_key
from src.api.authorization import Role, require_admin
from src.data_pipeline.orchestrator import PolicySyncOrchestrator

router = APIRouter(prefix="/v1/policy", tags=["Dynamic Policy Operations"])

_orchestrator: Optional[PolicySyncOrchestrator] = None

# Validation regex for internal snapshot IDs (alphanumeric, underscore, hyphen)
SNAPSHOT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def get_orchestrator() -> PolicySyncOrchestrator:
    """Dependency provider for PolicySyncOrchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = PolicySyncOrchestrator()
    return _orchestrator


class SyncTriggerRequest(BaseModel):
    """Payload for manual or targeted policy synchronization."""
    source_id: Optional[str] = Field(None, description="Optional specific source ID to sync; omit for full sync")
    force_rebuild: bool = Field(False, description="Forces full baseline rebuild rather than incremental diff")


class RollbackRequest(BaseModel):
    """Payload for policy rollback."""
    target_version: Optional[str] = Field(None, description="Optional target snapshot ID; defaults to previous snapshot")


@router.get("/status", summary="Get Active Policy Snapshot Status")
def get_policy_status(
    orchestrator: PolicySyncOrchestrator = Depends(get_orchestrator),
) -> Dict[str, Any]:
    """Returns active policy version, last sync timestamp, and operational readiness."""
    active_version = orchestrator.get_active_policy_version()
    last_sync = orchestrator.get_last_sync()
    return {
        "active_policy_version": active_version or "snapshot_baseline_v0",
        "has_active_snapshot": active_version is not None,
        "last_sync": last_sync.to_dict() if last_sync else None,
        "available_rollback_versions": orchestrator.get_rollback_versions(),
    }


@router.get("/sources", summary="List Registered Sources & Health")
def get_registered_sources(
    orchestrator: PolicySyncOrchestrator = Depends(get_orchestrator),
) -> Dict[str, Any]:
    """Exposes all registered data sources, authority tiers, and health metrics."""
    sources = orchestrator.list_sources()
    health = orchestrator.get_source_health()
    return {
        "total_sources": len(sources),
        "sources": [s.to_dict() for s in sources],
        "source_health": health,
    }


@router.get("/sync/latest", summary="Get Latest Sync Execution Report")
def get_latest_sync(
    orchestrator: PolicySyncOrchestrator = Depends(get_orchestrator),
) -> Dict[str, Any]:
    """Retrieves metadata of the most recent synchronization job."""
    last_sync = orchestrator.get_last_sync()
    if not last_sync:
        return {"status": "NO_SYNC_RECORDED", "job": None}
    return {"status": "SUCCESS", "job": last_sync.to_dict()}


@router.post("/sync/dry-run", summary="Execute Dry-Run Synchronization")
def execute_dry_run_sync(
    payload: Optional[SyncTriggerRequest] = None,
    orchestrator: PolicySyncOrchestrator = Depends(get_orchestrator),
    _role: Role = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Executes change detection, diff classification, and 14 activation gates in DRY RUN mode.
    Guaranteed NOT to mutate active policy snapshot or RAG state.
    Requires ADMIN role authorization.
    """
    source_id = payload.source_id if payload else None
    force_rebuild = payload.force_rebuild if payload else False

    if source_id and not SNAPSHOT_ID_PATTERN.match(source_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid source_id format: '{source_id}'",
        )

    job = orchestrator.sync(dry_run=True, source_id=source_id, force_rebuild=force_rebuild)
    return {
        "message": "Dry-run synchronization completed successfully.",
        "dry_run": True,
        "job": job.to_dict(),
    }


@router.post("/sync", summary="Trigger Live Policy Synchronization")
def trigger_live_sync(
    payload: Optional[SyncTriggerRequest] = None,
    orchestrator: PolicySyncOrchestrator = Depends(get_orchestrator),
    _role: Role = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Triggers live synchronization, staging candidate snapshot, evaluating 14 activation gates,
    and atomically promoting to active snapshot on pass.
    Requires ADMIN role authorization.
    """
    source_id = payload.source_id if payload else None
    force_rebuild = payload.force_rebuild if payload else False

    if source_id and not SNAPSHOT_ID_PATTERN.match(source_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid source_id format: '{source_id}'",
        )

    job = orchestrator.sync(dry_run=False, source_id=source_id, force_rebuild=force_rebuild)
    return {
        "message": f"Synchronization finished with status {job.status.value}",
        "activated": job.activation_status == "ACTIVATED",
        "job": job.to_dict(),
    }


@router.post("/rollback", summary="Rollback Active Policy Version")
def rollback_policy(
    payload: Optional[RollbackRequest] = None,
    orchestrator: PolicySyncOrchestrator = Depends(get_orchestrator),
    _role: Role = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Rolls back the active policy snapshot to the previous known good version.
    Requires ADMIN role authorization. Target snapshot ID is strictly validated
    to prevent path traversal and arbitrary filesystem injection.
    """
    target = payload.target_version if payload else None

    # Strict snapshot ID validation (rejection of directory traversal, null bytes, etc.)
    if target:
        if not SNAPSHOT_ID_PATTERN.match(target):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid target_version format: '{target}'. Snapshot IDs must be alphanumeric.",
            )

    rolled_back_id = orchestrator.rollback(target_version=target)
    if not rolled_back_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rollback failed: No previous snapshot found to restore.",
        )
    return {
        "message": f"Successfully rolled back active policy version to {rolled_back_id}",
        "active_policy_version": rolled_back_id,
    }
