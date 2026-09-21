"""
PolicySetu Policy Versioning Engine.
Manages immutable content-hash-based policy revisions.
Avoids pretend semantic versions by tracking actual source revisions and content digests.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys
from pathlib import Path

_CUR = Path(__file__).resolve()
while _CUR.name != "AI" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_AI_DIR = _CUR
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

try:
    from ..models import PolicyVersionMetadata, PolicyStatus
except (ImportError, ValueError):
    from src.data_pipeline.models import PolicyVersionMetadata, PolicyStatus


class PolicyVersionManager:
    """
    Tracks policy revisions tied to source content hashes.
    Never overwrites historical versions.
    """

    def __init__(self, persistence_dir: Optional[Path] = None):
        self.persistence_dir = persistence_dir or Path(__file__).resolve().parents[3] / "data" / "snapshots" / "versions"
        self._versions_by_slug: Dict[str, List[PolicyVersionMetadata]] = {}

    def create_version(
        self,
        scheme_slug: str,
        record: Dict[str, Any],
        source_revision: str,
        valid_from: Optional[str] = None,
        supersedes_version: Optional[str] = None,
        published_at: Optional[str] = None,
    ) -> PolicyVersionMetadata:
        """
        Creates an immutable content revision metadata entry for a scheme.
        """
        now = datetime.now(timezone.utc)
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")

        # Stable content hash
        stable_data = {
            k: v for k, v in record.items()
            if k not in ("retrieved_at", "created_at", "last_successful_fetch", "provenance")
        }
        content_hash = hashlib.sha256(
            json.dumps(stable_data, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

        # Revision ID: policy_<hash_prefix>_<timestamp>
        policy_version_id = f"policy_{content_hash[:12]}_{timestamp_str}"

        # If previous active version exists, mark it superseded
        if scheme_slug in self._versions_by_slug:
            for v in self._versions_by_slug[scheme_slug]:
                if v.status == PolicyStatus.ACTIVE:
                    v.status = PolicyStatus.SUPERSEDED
                    v.valid_until = now.isoformat()
                    if not supersedes_version:
                        supersedes_version = v.policy_version_id

        meta = PolicyVersionMetadata(
            policy_version_id=policy_version_id,
            source_revision=source_revision,
            content_hash=content_hash,
            created_at=now.isoformat(),
            valid_from=valid_from or now.isoformat(),
            published_at=published_at,
            retrieved_at=now.isoformat(),
            supersedes_version=supersedes_version,
            status=PolicyStatus.ACTIVE,
        )

        if scheme_slug not in self._versions_by_slug:
            self._versions_by_slug[scheme_slug] = []
        self._versions_by_slug[scheme_slug].append(meta)

        return meta

    def get_active_version(self, scheme_slug: str) -> Optional[PolicyVersionMetadata]:
        """Returns currently active policy revision for a scheme."""
        versions = self._versions_by_slug.get(scheme_slug, [])
        for v in reversed(versions):
            if v.status == PolicyStatus.ACTIVE:
                return v
        return versions[-1] if versions else None

    def get_version_history(self, scheme_slug: str) -> List[PolicyVersionMetadata]:
        """Returns complete historical audit trail for a scheme."""
        return self._versions_by_slug.get(scheme_slug, [])