"""
FIN Resumable Acquisition Queue & Checkpoint Manager.
Manages persistent state across scheme acquisition runs, ensuring uninterrupted,
idempotent, and resumable execution across all portal catalogue items.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional

from .models import (
    AcquisitionQueueItem,
    DetailStatus,
    ProvenanceStatus,
    QueueStatus,
)


class AcquisitionQueue:
    """
    Thread-safe persistent queue for government scheme data acquisition.
    Saves state to Intelligence/data/coverage/acquisition_queue.json so interrupted
    crawls can resume seamlessly without lost work or duplicate fetches.
    """

    def __init__(self, queue_file: Path):
        self.queue_file = queue_file
        self._lock = threading.Lock()
        # Keyed by (slug, scheme_id) to handle duplicate slug collisions (e.g. tufs)
        self.items: Dict[str, AcquisitionQueueItem] = {}
        self._modified_since_save: int = 0
        self.checkpoint_interval: int = 50

    def _make_key(self, slug: str, scheme_id: str) -> str:
        return f"{slug}::{scheme_id}"

    def load_or_initialize(self, catalog_items: List[Dict[str, Any]]) -> int:
        """
        Loads queue state from disk if available, and enqueues any newly
        discovered items from the master catalogue.
        """
        with self._lock:
            if self.queue_file.exists():
                try:
                    with open(self.queue_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    for raw in data:
                        item = AcquisitionQueueItem(
                            acquisition_id=raw.get("acquisition_id", ""),
                            scheme_id=raw.get("scheme_id", ""),
                            slug=raw.get("slug", ""),
                            status=raw.get("status", QueueStatus.QUEUED.value),
                            attempts=raw.get("attempts", 0),
                            last_attempt=raw.get("last_attempt"),
                            next_retry=raw.get("next_retry"),
                            detail_status=raw.get("detail_status", DetailStatus.CATALOG_ONLY.value),
                            document_status=raw.get("document_status", "NOT_AVAILABLE"),
                            faq_status=raw.get("faq_status", "NOT_AVAILABLE"),
                            language_status=raw.get("language_status", "NOT_AVAILABLE"),
                            provenance_status=raw.get("provenance_status", ProvenanceStatus.NOT_LIVE_VERIFIED.value),
                            error=raw.get("error"),
                        )
                        k = self._make_key(item.slug, item.scheme_id)
                        self.items[k] = item
                except Exception:
                    pass

            # Enqueue any catalogue item not yet tracked
            new_added = 0
            for it in catalog_items:
                slug = it.get("slug", "").strip()
                sid = str(it.get("_id", "")).strip()
                if not slug:
                    continue
                k = self._make_key(slug, sid)
                if k not in self.items:
                    acq_id = f"acq_{slug}_{sid[:8]}" if sid else f"acq_{slug}"
                    self.items[k] = AcquisitionQueueItem(
                        acquisition_id=acq_id,
                        scheme_id=sid,
                        slug=slug,
                        status=QueueStatus.QUEUED.value,
                        attempts=0,
                        last_attempt=None,
                        next_retry=None,
                        detail_status=DetailStatus.CATALOG_ONLY.value,
                        document_status="NOT_AVAILABLE",
                        faq_status="NOT_AVAILABLE",
                        language_status="NOT_AVAILABLE",
                        provenance_status=ProvenanceStatus.NOT_LIVE_VERIFIED.value,
                        error=None,
                    )
                    new_added += 1

            self._save_disk_unlocked()
            return new_added

    def get_pending_items(self, retry_failed: bool = False) -> List[AcquisitionQueueItem]:
        """Returns items that require processing or retry."""
        with self._lock:
            pending = []
            for item in self.items.values():
                if item.status in (QueueStatus.QUEUED.value, QueueStatus.IN_PROGRESS.value, QueueStatus.RETRY_PENDING.value):
                    pending.append(item)
                elif retry_failed and item.status in (QueueStatus.FAILED.value, QueueStatus.BLOCKED.value):
                    pending.append(item)
            return pending

    def get_all_items(self) -> List[AcquisitionQueueItem]:
        """Returns all queue items."""
        with self._lock:
            return list(self.items.values())

    def update_item(
        self,
        slug: str,
        scheme_id: str,
        status: Optional[str] = None,
        detail_status: Optional[str] = None,
        document_status: Optional[str] = None,
        faq_status: Optional[str] = None,
        language_status: Optional[str] = None,
        provenance_status: Optional[str] = None,
        error: Optional[str] = None,
        increment_attempts: bool = False,
    ) -> None:
        """Thread-safe update of a single queue entry."""
        k = self._make_key(slug, scheme_id)
        with self._lock:
            if k not in self.items:
                acq_id = f"acq_{slug}_{scheme_id[:8]}" if scheme_id else f"acq_{slug}"
                self.items[k] = AcquisitionQueueItem(
                    acquisition_id=acq_id,
                    scheme_id=scheme_id,
                    slug=slug,
                )

            item = self.items[k]
            now_iso = datetime.now(timezone.utc).isoformat()
            item.last_attempt = now_iso
            if increment_attempts:
                item.attempts += 1
            if status is not None:
                item.status = status
            if detail_status is not None:
                item.detail_status = detail_status
            if document_status is not None:
                item.document_status = document_status
            if faq_status is not None:
                item.faq_status = faq_status
            if language_status is not None:
                item.language_status = language_status
            if provenance_status is not None:
                item.provenance_status = provenance_status
            if error is not None:
                item.error = error

            self._modified_since_save += 1
            if self._modified_since_save >= self.checkpoint_interval:
                self._save_disk_unlocked()

    def save_checkpoint(self, force: bool = False) -> None:
        """Flushes in-memory queue state to disk."""
        with self._lock:
            if force or self._modified_since_save > 0:
                self._save_disk_unlocked()

    def _save_disk_unlocked(self) -> None:
        """Internal helper; caller must hold self._lock."""
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
        records = [item.to_dict() for item in self.items.values()]
        with open(self.queue_file, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        self._modified_since_save = 0

    def get_summary(self) -> Dict[str, int]:
        """Returns counts grouped by status and detail_status."""
        with self._lock:
            summary: Dict[str, int] = {
                "total": len(self.items),
                "queued": 0,
                "in_progress": 0,
                "complete": 0,
                "failed": 0,
                "not_available": 0,
                "full_detail": 0,
                "partial_detail": 0,
                "catalog_only": 0,
                "live_acquired": 0,
                "live_revalidated": 0,
            }
            for it in self.items.values():
                s = it.status.lower()
                if s in summary:
                    summary[s] += 1
                ds = it.detail_status.lower()
                if ds in summary:
                    summary[ds] += 1
                ps = it.provenance_status.lower()
                if ps in summary:
                    summary[ps] += 1
            return summary
