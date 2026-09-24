"""
FIN Official PDF Fetcher and Metadata Extractor.
Extracts document metadata, hashes, publication dates, and text content.
Flags scanned or image-only documents as OCR_REQUIRED rather than silently discarding them.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
from typing import Optional

import sys
from pathlib import Path

_CUR = Path(__file__).resolve()
while _CUR.name != "Intelligence" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_INTELLIGENCE_DIR = _CUR
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

try:
    from .base import BaseFetcher, FetchResult
except (ImportError, ValueError):
    from src.data_pipeline.fetchers.base import BaseFetcher, FetchResult


@dataclass
class PDFDocumentMetadata:
    """Standardized metadata for official policy guideline PDFs."""
    url_or_path: str
    content_hash: str
    file_size_bytes: int
    page_count: Optional[int] = None
    title: Optional[str] = None
    effective_date: Optional[str] = None
    publication_date: Optional[str] = None
    retrieved_at: str = ""
    extracted_text: Optional[str] = None
    status: str = "EXTRACTED"  # "EXTRACTED", "OCR_REQUIRED", "MALFORMED"

    def __post_init__(self):
        if not self.retrieved_at:
            self.retrieved_at = datetime.now(timezone.utc).isoformat()


class PDFFetcher(BaseFetcher):
    """
    Ingests official guideline and gazette PDFs.
    Safely inspects text streams and marks non-extractable PDFs as OCR_REQUIRED.
    """

    def fetch(self, url: str, source_id: str, **kwargs) -> FetchResult:
        """Fetches PDF bytes from local path or remote URL."""
        if url.startswith("http://") or url.startswith("https://"):
            from .web import WebFetcher
            web_fetcher = WebFetcher(timeout_seconds=self.timeout_seconds)
            return web_fetcher.fetch(url=url, source_id=source_id, **kwargs)
        else:
            from .local import LocalBaselineFetcher
            local_fetcher = LocalBaselineFetcher()
            return local_fetcher.fetch(url=url, source_id=source_id, **kwargs)

    def extract_pdf_metadata(self, pdf_bytes: bytes, source_identifier: str) -> PDFDocumentMetadata:
        """
        Extracts structural metadata and text from raw PDF bytes.
        """
        content_hash = hashlib.sha256(pdf_bytes).hexdigest()
        file_size = len(pdf_bytes)

        # Basic PDF header validation
        if not pdf_bytes.startswith(b"%PDF-"):
            return PDFDocumentMetadata(
                url_or_path=source_identifier,
                content_hash=content_hash,
                file_size_bytes=file_size,
                status="MALFORMED",
            )

        # Extract page count via regex count of /Type /Page
        page_count = len(re.findall(rb"/Type\s*/Page\b", pdf_bytes)) or 1

        # Attempt naive stream text extraction from PDF
        extracted_text = self._extract_raw_pdf_text(pdf_bytes)

        # Detect publication / effective date patterns
        pub_date = None
        if extracted_text:
            date_match = re.search(r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}-\d{2}-\d{2})\b", extracted_text)
            if date_match:
                pub_date = date_match.group(0)

        # If text is too short or empty, mark OCR_REQUIRED
        if not extracted_text or len(extracted_text.strip()) < 50:
            return PDFDocumentMetadata(
                url_or_path=source_identifier,
                content_hash=content_hash,
                file_size_bytes=file_size,
                page_count=page_count,
                publication_date=pub_date,
                status="OCR_REQUIRED",
            )

        return PDFDocumentMetadata(
            url_or_path=source_identifier,
            content_hash=content_hash,
            file_size_bytes=file_size,
            page_count=page_count,
            publication_date=pub_date,
            extracted_text=extracted_text,
            status="EXTRACTED",
        )

    @staticmethod
    def _extract_raw_pdf_text(pdf_bytes: bytes) -> str:
        """Lightweight text extraction from uncompressed / standard PDF text streams."""
        text_chunks = []
        # Find BT (Begin Text) ... ET (End Text) blocks
        blocks = re.findall(rb"BT\s*(.*?)\s*ET", pdf_bytes, re.DOTALL)
        for block in blocks:
            # Extract parenthesized string literals (e.g., (Hello World) Tj)
            strings = re.findall(rb"\((.*?)\)\s*Tj", block)
            for s in strings:
                try:
                    text_chunks.append(s.decode("utf-8", errors="ignore"))
                except Exception:
                    pass

        return " ".join(text_chunks).strip()