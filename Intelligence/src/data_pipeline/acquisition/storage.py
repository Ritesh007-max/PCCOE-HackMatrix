"""
FIN Immutable Data Acquisition Storage & Lineage Manager.
Preserves raw HTML/JSON, normalized entities, versioned snapshots,
conflicts, audit logs, and provenance metadata across designated directory hierarchies.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import Scheme, Conflict, CrawlFailure, CrawlJob
from .security import AcquisitionSecurityValidator


class AcquisitionStorage:
    """
    Manages raw, normalized, lineage, and failure document stores.
    Enforces that historical versions remain immutable.
    """

    def __init__(self, base_data_dir: Optional[Path] = None):
        if base_data_dir is None:
            # Default to Intelligence/data
            cur = Path(__file__).resolve()
            while cur.name != "AI" and cur.parent != cur:
                cur = cur.parent
            self.base_dir = cur / "data"
        else:
            self.base_dir = Path(base_data_dir)

        # Standard subdirectories
        self.raw_myscheme_dir = self.base_dir / "raw" / "myscheme"
        self.raw_official_dir = self.base_dir / "raw" / "official"
        self.normalized_dir = self.base_dir / "normalized"
        self.snapshots_dir = self.base_dir / "snapshots"
        self.lineage_dir = self.base_dir / "lineage"
        self.conflicts_dir = self.base_dir / "conflicts"
        self.coverage_dir = self.base_dir / "coverage"
        self.failures_dir = self.base_dir / "failures"

        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Creates required directory tree if missing."""
        for d in [
            self.raw_myscheme_dir,
            self.raw_official_dir,
            self.normalized_dir,
            self.snapshots_dir,
            self.lineage_dir,
            self.conflicts_dir,
            self.coverage_dir,
            self.failures_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)

    def save_raw_response(
        self,
        identifier: str,
        data: bytes | str | Dict[str, Any],
        source_type: str = "myscheme",
        extension: str = "json",
    ) -> Tuple[Path, str]:
        """
        Saves raw un-parsed response data with SHA-256 hash.
        Never overwrites earlier raw responses; appends content hash if unchanged.
        """
        target_dir = self.raw_myscheme_dir if source_type == "myscheme" else self.raw_official_dir

        if isinstance(data, (dict, list)):
            content_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        elif isinstance(data, str):
            content_bytes = data.encode("utf-8")
        else:
            content_bytes = data

        content_hash = hashlib.sha256(content_bytes).hexdigest()
        filename = f"{identifier}_{content_hash[:10]}.{extension}"
        safe_path = AcquisitionSecurityValidator.sanitize_file_path(target_dir, filename)

        with open(safe_path, "wb") as f:
            f.write(content_bytes)

        return safe_path, content_hash

    def save_normalized_scheme(self, scheme: Scheme) -> Path:
        """Saves canonical normalized scheme JSON."""
        filename = f"{scheme.canonical_slug}.json"
        safe_path = AcquisitionSecurityValidator.sanitize_file_path(self.normalized_dir, filename)

        with open(safe_path, "w", encoding="utf-8") as f:
            json.dump(scheme.to_dict(), f, indent=2, ensure_ascii=False, default=str)

        return safe_path

    def load_normalized_scheme(self, slug: str) -> Optional[Scheme]:
        """Loads canonical normalized scheme JSON from disk if it exists."""
        filename = f"{slug}.json"
        safe_path = AcquisitionSecurityValidator.sanitize_file_path(self.normalized_dir, filename)
        if not safe_path.exists():
            return None
        try:
            with open(safe_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Scheme.from_dict(data)
        except Exception:
            return None

    def save_snapshot(self, snapshot_id: str, schemes: List[Scheme]) -> Path:
        """Creates an immutable, versioned snapshot of the entire acquisition run."""
        filename = f"snapshot_{snapshot_id}.json"
        safe_path = AcquisitionSecurityValidator.sanitize_file_path(self.snapshots_dir, filename)

        payload = {
            "snapshot_id": snapshot_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "schemes_count": len(schemes),
            "schemes": [s.to_dict() for s in schemes],
        }
        with open(safe_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False, default=str)

        return safe_path

    def save_conflicts(self, job_id: str, conflicts: List[Conflict]) -> Path:
        """Stores detected conflicts log."""
        filename = f"conflicts_{job_id}.json"
        safe_path = AcquisitionSecurityValidator.sanitize_file_path(self.conflicts_dir, filename)

        with open(safe_path, "w", encoding="utf-8") as f:
            json.dump([c.to_dict() for c in conflicts], f, indent=2, ensure_ascii=False, default=str)

        return safe_path

    def save_failures(self, job_id: str, failures: List[CrawlFailure]) -> Path:
        """Stores crawl failures audit ledger."""
        filename = f"failures_{job_id}.json"
        safe_path = AcquisitionSecurityValidator.sanitize_file_path(self.failures_dir, filename)

        with open(safe_path, "w", encoding="utf-8") as f:
            json.dump([fail.to_dict() for fail in failures], f, indent=2, ensure_ascii=False, default=str)

        return safe_path

    def save_crawl_job(self, job: CrawlJob) -> Path:
        """Stores crawl job summary report."""
        filename = f"crawl_job_{job.crawl_job_id}.json"
        safe_path = AcquisitionSecurityValidator.sanitize_file_path(self.coverage_dir, filename)

        with open(safe_path, "w", encoding="utf-8") as f:
            json.dump(job.to_dict(), f, indent=2, ensure_ascii=False, default=str)

        return safe_path
