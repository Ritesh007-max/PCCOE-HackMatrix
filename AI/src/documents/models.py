"""
PolicySetu Document Ingestion Data Models.
Defines normalized, provider-neutral representations for document pages,
text blocks, structured tables, OCR results, and processing statuses.
"""

from dataclasses import dataclass, field
from enum import Enum
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
    from .provenance import DocumentType
    from ..llm.models import ApplicantFactCandidate
except (ImportError, ValueError):
    from src.documents.provenance import DocumentType
    from src.llm.models import ApplicantFactCandidate


class DocumentProcessingStatus(str, Enum):
    """Lifecycle processing states for uploaded or ingested files."""
    VALID = "VALID"
    INVALID_TYPE = "INVALID_TYPE"
    CORRUPTED = "CORRUPTED"
    TOO_LARGE = "TOO_LARGE"
    DUPLICATE = "DUPLICATE"
    UNSUPPORTED = "UNSUPPORTED"
    PROCESSING_ERROR = "PROCESSING_ERROR"


class DocumentExtractionMethod(str, Enum):
    """Specific technical mechanism used to extract text or table content."""
    NATIVE_PDF = "NATIVE_PDF"
    OCR_PADDLE = "OCR_PADDLE"
    OCR_HEURISTIC = "OCR_HEURISTIC"
    DOCX_XML = "DOCX_XML"
    IMAGE_OCR = "IMAGE_OCR"
    MANUAL = "MANUAL"
    UNKNOWN = "UNKNOWN"


@dataclass
class BoundingBox:
    """Coordinates bounding a block or word on a document page (points or pixels)."""
    x0: float
    y0: float
    x1: float
    y1: float

    def to_dict(self) -> Dict[str, float]:
        return {"x0": self.x0, "y0": self.y0, "x1": self.x1, "y1": self.y1}

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "BoundingBox":
        return cls(x0=float(data["x0"]), y0=float(data["y0"]), x1=float(data["x1"]), y1=float(data["y1"]))


@dataclass
class TextBlock:
    """Atomic text element extracted from a document page."""
    text: str
    page_number: int = 1
    bounding_box: Optional[BoundingBox] = None
    confidence: float = 1.0
    extraction_method: DocumentExtractionMethod = DocumentExtractionMethod.NATIVE_PDF

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "page_number": self.page_number,
            "bounding_box": self.bounding_box.to_dict() if self.bounding_box else None,
            "confidence": self.confidence,
            "extraction_method": self.extraction_method.value,
        }


@dataclass
class TableContent:
    """Structured tabular data preserved from PDF, DOCX, or HTML formats."""
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    page_number: int = 1
    bounding_box: Optional[BoundingBox] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "headers": self.headers,
            "rows": self.rows,
            "page_number": self.page_number,
            "bounding_box": self.bounding_box.to_dict() if self.bounding_box else None,
        }


@dataclass
class OCRBlock:
    """Optical character recognition bounding region with confidence score."""
    text: str
    page_number: int = 1
    bounding_box: Optional[BoundingBox] = None
    confidence: float = 1.0
    extraction_method: DocumentExtractionMethod = DocumentExtractionMethod.OCR_HEURISTIC

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "page_number": self.page_number,
            "bounding_box": self.bounding_box.to_dict() if self.bounding_box else None,
            "confidence": self.confidence,
            "extraction_method": self.extraction_method.value,
        }


@dataclass
class PageContent:
    """Page-level container maintaining native text, scanned status, and OCR blocks."""
    page_number: int
    text: str = ""
    text_blocks: List[TextBlock] = field(default_factory=list)
    tables: List[TableContent] = field(default_factory=list)
    ocr_blocks: List[OCRBlock] = field(default_factory=list)
    is_scanned: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "text": self.text,
            "text_blocks": [tb.to_dict() for tb in self.text_blocks],
            "tables": [t.to_dict() for t in self.tables],
            "ocr_blocks": [ob.to_dict() for ob in self.ocr_blocks],
            "is_scanned": self.is_scanned,
        }


@dataclass
class DocumentContent:
    """
    Provider-neutral document container.
    Decouples raw PDF/DOCX/Image byte ingestion from downstream LLM providers (Gemini & OpenRouter).
    """
    document_id: str
    file_path: str
    file_name: str
    mime_type: str
    document_type: DocumentType = DocumentType.UNKNOWN_DOCUMENT
    pages: List[PageContent] = field(default_factory=list)
    tables: List[TableContent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: DocumentProcessingStatus = DocumentProcessingStatus.VALID
    sha256: str = ""
    error_message: Optional[str] = None

    def get_full_text(self) -> str:
        """Concatenates all native and OCR page text into a unified readable string."""
        parts = []
        for p in self.pages:
            p_text = p.text.strip()
            if not p_text and p.ocr_blocks:
                p_text = "\n".join(b.text for b in p.ocr_blocks).strip()
            if p_text:
                parts.append(f"--- [Page {p.page_number}] ---\n{p_text}")
        return "\n\n".join(parts) if parts else ""

    def get_table_markdown(self) -> str:
        """Renders extracted tables as Markdown for structured LLM prompting."""
        if not self.tables:
            return ""
        table_lines = []
        for i, t in enumerate(self.tables):
            table_lines.append(f"### Table {i+1} (Page {t.page_number})")
            if t.headers:
                table_lines.append("| " + " | ".join(t.headers) + " |")
                table_lines.append("| " + " | ".join(["---"] * len(t.headers)) + " |")
            for row in t.rows:
                table_lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
            table_lines.append("")
        return "\n".join(table_lines)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def full_text(self) -> str:
        return self.get_full_text()

    @property
    def is_scanned(self) -> bool:
        return any(p.is_scanned for p in self.pages)

    @property
    def sha256_hash(self) -> str:
        return self.sha256

    @property
    def extraction_method(self) -> DocumentExtractionMethod:
        if self.is_scanned:
            return DocumentExtractionMethod.OCR_HEURISTIC
        if "wordprocessingml" in self.mime_type:
            return DocumentExtractionMethod.DOCX_XML
        if self.mime_type.startswith("image/"):
            return DocumentExtractionMethod.IMAGE_OCR
        return DocumentExtractionMethod.NATIVE_PDF

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "mime_type": self.mime_type,
            "document_type": self.document_type.value if isinstance(self.document_type, DocumentType) else str(self.document_type),
            "status": self.status.value,
            "sha256": self.sha256,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "pages": [p.to_dict() for p in self.pages],
            "tables": [t.to_dict() for t in self.tables],
        }


__all__ = [
    "DocumentProcessingStatus",
    "DocumentExtractionMethod",
    "BoundingBox",
    "TextBlock",
    "TableContent",
    "OCRBlock",
    "PageContent",
    "DocumentContent",
    "ApplicantFactCandidate",
]
