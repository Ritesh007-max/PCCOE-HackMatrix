"""
PolicySetu Image Document Parser.
Handles orientation correction (EXIF tags), OCR extraction, bounding box preservation,
and metadata tracking for uploaded certificate and document photos (PNG, JPEG, WEBP).
"""

import hashlib
import io
from pathlib import Path
from typing import Any, Dict, List, Optional
from PIL import Image, ImageOps

try:
    from .models import (
        BoundingBox,
        DocumentContent,
        DocumentExtractionMethod,
        DocumentProcessingStatus,
        OCRBlock,
        PageContent,
    )
    from .provenance import DocumentType
    from .ocr import BaseOCREngine, get_ocr_engine
except (ImportError, ValueError):
    from src.documents.models import (
        BoundingBox,
        DocumentContent,
        DocumentExtractionMethod,
        DocumentProcessingStatus,
        OCRBlock,
        PageContent,
    )
    from src.documents.provenance import DocumentType
    from src.documents.ocr import BaseOCREngine, get_ocr_engine


class ImageParser:
    """
    Image parser for scanned and photographed administrative documents.
    Preserves original bytes, applies EXIF auto-rotation, and extracts text via OCR.
    """

    def __init__(self, ocr_engine: Optional[BaseOCREngine] = None):
        self.ocr_engine = ocr_engine or get_ocr_engine()

    def parse_bytes(
        self,
        image_bytes: bytes,
        filename: str = "document.jpg",
        document_id: Optional[str] = None,
    ) -> DocumentContent:
        """Parses in-memory image bytes."""
        sha256 = hashlib.sha256(image_bytes).hexdigest()
        doc_id = document_id or f"doc_{sha256[:12]}"

        try:
            raw_img = Image.open(io.BytesIO(image_bytes))
            raw_fmt = raw_img.format
            if not raw_fmt and Path(filename).suffix:
                ext = Path(filename).suffix.lstrip(".").upper()
                raw_fmt = "JPEG" if ext == "JPG" else ext
            img_format = raw_fmt or "JPEG"
            # 1. Orientation handling using EXIF transpose
            pil_img = ImageOps.exif_transpose(raw_img) or raw_img
        except Exception as exc:
            return DocumentContent(
                document_id=doc_id,
                file_path=filename,
                file_name=filename,
                mime_type="image/jpeg",
                document_type=DocumentType.UNKNOWN_DOCUMENT,
                status=DocumentProcessingStatus.CORRUPTED,
                sha256=sha256,
                error_message=f"Failed to decode image: {exc}",
            )

        w, h = pil_img.size
        mime_type = "image/jpeg" if img_format.upper() in ("JPEG", "JPG") else f"image/{img_format.lower()}"

        # 2. Run OCR
        ocr_blocks = self.ocr_engine.extract_from_image(pil_img, page_number=1)
        full_text = "\n".join(b.text for b in ocr_blocks).strip()

        page = PageContent(
            page_number=1,
            text=full_text,
            ocr_blocks=ocr_blocks,
            is_scanned=True,
        )

        metadata = {
            "width": w,
            "height": h,
            "format": img_format,
            "mode": pil_img.mode,
        }

        return DocumentContent(
            document_id=doc_id,
            file_path=filename,
            file_name=filename,
            mime_type=mime_type,
            document_type=DocumentType.UNKNOWN_DOCUMENT,
            pages=[page],
            tables=[],
            metadata=metadata,
            status=DocumentProcessingStatus.VALID,
            sha256=sha256,
        )

    def parse_file(self, file_path: str) -> DocumentContent:
        """Parses a local image file path."""
        p = Path(file_path)
        raw_bytes = p.read_bytes()
        sha256 = hashlib.sha256(raw_bytes).hexdigest()
        doc_id = f"doc_{sha256[:12]}"
        return self.parse_bytes(raw_bytes, filename=p.name, document_id=doc_id)
