"""
Data Lineage Models.
Captures end-to-end data provenance from source record to canonical and RAG representations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class LineageRecord:
    """
    Complete provenance lineage for a canonical scheme record.
    Canonical Scheme -> source_dataset -> source_record_id -> source_url -> retrieved_at -> content_hash -> canonical_version_id
    """
    canonical_scheme_id: str
    scheme_slug: str
    source_dataset: str
    source_record_id: str
    source_url: Optional[str]
    retrieved_at: str
    content_hash: str
    canonical_version_id: str
    created_at: str = ""
    transformations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canonical_scheme_id": self.canonical_scheme_id,
            "scheme_slug": self.scheme_slug,
            "source_dataset": self.source_dataset,
            "source_record_id": self.source_record_id,
            "source_url": self.source_url,
            "retrieved_at": self.retrieved_at,
            "content_hash": self.content_hash,
            "canonical_version_id": self.canonical_version_id,
            "created_at": self.created_at,
            "transformations": self.transformations,
            "metadata": self.metadata,
        }
