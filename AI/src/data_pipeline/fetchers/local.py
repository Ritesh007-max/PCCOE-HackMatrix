"""
PolicySetu Local Baseline Fetcher and BaselineSourceAdapter.
Loads existing static datasets from AI/data/raw/ as immutable baseline version v0.
Computes SHA-256 checksums without network access.
"""

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
import zipfile

import sys
from pathlib import Path

_CUR = Path(__file__).resolve()
while _CUR.name != "AI" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_AI_DIR = _CUR
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

try:
    from .base import BaseFetcher, FetchResult
except (ImportError, ValueError):
    from src.data_pipeline.fetchers.base import BaseFetcher, FetchResult


class LocalBaselineFetcher(BaseFetcher):
    """
    Fetches and hashes local baseline data files.
    Ensures 100% offline reproducibility for local development and testing.
    """

    def __init__(self, base_dir: Optional[Path] = None):
        super().__init__()
        self.base_dir = base_dir or Path(__file__).resolve().parents[3] / "data" / "raw"

    def fetch(self, url: str, source_id: str, **kwargs) -> FetchResult:
        """
        Loads the local file, computes SHA256, and returns a FetchResult.
        'url' here is the relative or absolute filepath.
        """
        start_time = datetime.now(timezone.utc)
        file_path = Path(url)
        if not file_path.is_absolute():
            file_path = self.base_dir / file_path.name

        if not file_path.exists():
            return FetchResult(
                source_id=source_id,
                url=str(file_path),
                status_code=404,
                error=f"Local file not found: {file_path}",
                success=False,
            )

        try:
            content_bytes = file_path.read_bytes()
            content_hash = hashlib.sha256(content_bytes).hexdigest()
            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            text_content = None
            if file_path.suffix.lower() in (".csv", ".json", ".txt"):
                try:
                    text_content = content_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    text_content = content_bytes.decode("latin-1", errors="replace")

            return FetchResult(
                source_id=source_id,
                url=str(file_path),
                status_code=200,
                content=content_bytes,
                text_content=text_content,
                content_type=f"application/{file_path.suffix.lstrip('.')}",
                content_hash=content_hash,
                fetched_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=duration_ms,
                success=True,
            )
        except Exception as exc:
            return FetchResult(
                source_id=source_id,
                url=str(file_path),
                status_code=500,
                error=str(exc),
                success=False,
            )


class BaselineSourceAdapter:
    """
    Treats current static datasets as Version Zero (v0).
    Allows applications to query the baseline snapshot seamlessly without changing business logic.
    """

    def __init__(self, raw_dir: Optional[Path] = None):
        self.raw_dir = raw_dir or Path(__file__).resolve().parents[3] / "data" / "raw"
        self.processed_dir = self.raw_dir.parent / "processed"
        self.fetcher = LocalBaselineFetcher(base_dir=self.raw_dir)

    def load_baseline_schemes(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Loads canonical baseline records.
        Prefers processed schemes_canonical.parquet (with full provenance),
        falling back to raw schemes.csv with default provenance.
        """
        canonical_parquet = self.processed_dir / "schemes_canonical.parquet"
        if canonical_parquet.exists():
            df = pd.read_parquet(canonical_parquet)
            if limit:
                df = df.head(limit)
            records = df.to_dict(orient="records")
            # Parse json strings in provenance if stored as string
            for r in records:
                if isinstance(r.get("provenance"), str):
                    try:
                        import json
                        r["provenance"] = json.loads(r["provenance"])
                    except Exception:
                        pass
            return records

        schemes_csv = self.raw_dir / "schemes.csv"
        if not schemes_csv.exists():
            return []
        df = pd.read_csv(schemes_csv, nrows=limit)
        records = df.to_dict(orient="records")
        for r in records:
            if not r.get("provenance"):
                r["provenance"] = {
                    "source_file": "schemes.csv",
                    "provider": "myScheme",
                    "ingestion_method": "authoritative_primary",
                    "confidence_tier": "authoritative",
                }
        return records

    def load_baseline_faqs(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Loads baseline FAQs from schemes_faqs.csv."""
        faqs_csv = self.raw_dir / "schemes_faqs.csv"
        if not faqs_csv.exists():
            return []
        df = pd.read_csv(faqs_csv, nrows=limit)
        return df.to_dict(orient="records")

    def load_supplementary_schemes(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Loads supplementary schemes from updated_data.csv."""
        supp_csv = self.raw_dir / "updated_data.csv"
        if not supp_csv.exists():
            return []
        df = pd.read_csv(supp_csv, nrows=limit)
        return df.to_dict(orient="records")

    def load_bilingual_qa(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Loads local bilingual English/Hindi dataset."""
        bilingual_csv = self.raw_dir / "indian government schemes dataset english and hindi.csv"
        if not bilingual_csv.exists():
            return []
        df = pd.read_csv(bilingual_csv, nrows=limit)
        return df.to_dict(orient="records")

    def load_archive_docs(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Extracts text documents from archive (1).zip."""
        zip_path = self.raw_dir / "archive (1).zip"
        if not zip_path.exists():
            return []
        docs = []
        with zipfile.ZipFile(zip_path, "r") as z:
            names = [n for n in z.namelist() if n.endswith(".txt")]
            if limit:
                names = names[:limit]
            for name in names:
                try:
                    content = z.read(name).decode("utf-8", errors="replace")
                    docs.append({
                        "filename": name,
                        "content": content,
                        "source": "archive_zip"
                    })
                except Exception:
                    continue
        return docs