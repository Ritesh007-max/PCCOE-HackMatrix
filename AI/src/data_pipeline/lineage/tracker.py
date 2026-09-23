"""
PolicySetu Data Lineage Tracker.
Records and queries the lineage graph from source records to canonical policies,
ensuring zero loss of statutory provenance during data transformations.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
import sys
from pathlib import Path

_CUR = Path(__file__).resolve()
while _CUR.name != "AI" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_AI_DIR = _CUR
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

try:
    from .models import LineageRecord
except (ImportError, ValueError):
    from src.data_pipeline.lineage.models import LineageRecord


class LineageTracker:
    """
    Manages and persists end-to-end lineage records.
    """

    def __init__(self, persistence_path: Optional[Path] = None):
        self.persistence_path = persistence_path
        self._records_by_id: Dict[str, LineageRecord] = {}
        self._records_by_slug: Dict[str, List[LineageRecord]] = {}

        if self.persistence_path and self.persistence_path.exists():
            self.load()

    def record_lineage(
        self,
        canonical_scheme_id: str,
        scheme_slug: str,
        source_dataset: str,
        source_record_id: str,
        source_url: Optional[str],
        retrieved_at: str,
        content_hash: str,
        canonical_version_id: str,
        transformations: Optional[List[str]] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> LineageRecord:
        """Records an atomic transformation step in the lineage registry."""
        rec = LineageRecord(
            canonical_scheme_id=canonical_scheme_id,
            scheme_slug=scheme_slug,
            source_dataset=source_dataset,
            source_record_id=source_record_id,
            source_url=source_url,
            retrieved_at=retrieved_at,
            content_hash=content_hash,
            canonical_version_id=canonical_version_id,
            transformations=transformations or [],
            metadata=metadata or {},
        )
        self._records_by_id[canonical_scheme_id] = rec
        if scheme_slug not in self._records_by_slug:
            self._records_by_slug[scheme_slug] = []
        self._records_by_slug[scheme_slug].append(rec)

        return rec

    def get_by_id(self, canonical_scheme_id: str) -> Optional[LineageRecord]:
        """Retrieves lineage by canonical ID."""
        return self._records_by_id.get(canonical_scheme_id)

    def get_by_slug(self, scheme_slug: str) -> List[LineageRecord]:
        """Retrieves lineage history by scheme slug."""
        return self._records_by_slug.get(scheme_slug, [])

    def total_records(self) -> int:
        """Returns total recorded lineage items."""
        return len(self._records_by_id)

    def save(self, target_path: Optional[Path] = None) -> None:
        """Persists lineage records to JSON Lines."""
        path = target_path or self.persistence_path
        if not path:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for rec in self._records_by_id.values():
                f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")

    def load(self, source_path: Optional[Path] = None) -> None:
        """Loads lineage records from JSON Lines."""
        path = source_path or self.persistence_path
        if not path or not path.exists():
            return
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    d = json.loads(line)
                    rec = LineageRecord(**d)
                    self._records_by_id[rec.canonical_scheme_id] = rec
                    if rec.scheme_slug not in self._records_by_slug:
                        self._records_by_slug[rec.scheme_slug] = []
                    self._records_by_slug[rec.scheme_slug].append(rec)