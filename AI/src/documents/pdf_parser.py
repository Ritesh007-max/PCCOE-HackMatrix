"""
PolicySetu Layered PDF Document Parser.
Implements the 5-stage PDF ingestion pipeline:
  Stage A: Native text extraction via PyMuPDF
  Stage B: Scan detection (character density & image presence)
  Stage C: Page rasterization for scanned pages only
  Stage D: Optical Character Recognition on scanned pages
  Stage E: Separate preservation of native text and OCR blocks with full provenance
"""

import hashlib
import io
from pathlib import Path
from typing import Any, Dict, List, Optional
import pymupdf  # type: ignore

try:
    from .models import (
        BoundingBox,
        DocumentContent,
        DocumentExtractionMethod,
        DocumentProcessingStatus,
        OCRBlock,
        PageContent,
        TableContent,
        TextBlock,
    )
    from .provenance import DocumentType
    from .scan_detector import ScanDetector
    from .ocr import BaseOCREngine, get_ocr_engine
except (ImportError, ValueError):
    from src.documents.models import (
        BoundingBox,
        DocumentContent,
        DocumentExtractionMethod,
        DocumentProcessingStatus,
        OCRBlock,
        PageContent,
        TableContent,
        TextBlock,
    )
    from src.documents.provenance import DocumentType
    from src.documents.scan_detector import ScanDetector
    from src.documents.ocr import BaseOCREngine, get_ocr_engine


class LayeredPDFParser:
    """
    High-performance, layered PDF parser.
    Avoids expensive OCR when clean digital text is present; selectively rasterizes
    and OCRs scanned certificate pages.
    """

    def __init__(
        self,
        scan_detector: Optional[ScanDetector] = None,
        ocr_engine: Optional[BaseOCREngine] = None,
        render_dpi: int = 150,
    ):
        self.scan_detector = scan_detector or ScanDetector()
        self.ocr_engine = ocr_engine or get_ocr_engine()
        self.render_dpi = render_dpi

    def parse_bytes(
        self,
        pdf_bytes: bytes,
        filename: str = "document.pdf",
        document_id: Optional[str] = None,
    ) -> DocumentContent:
        """Parses in-memory PDF bytes through the 5-stage pipeline."""
        sha256 = hashlib.sha256(pdf_bytes).hexdigest()
        doc_id = document_id or f"doc_{sha256[:12]}"

        try:
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        except Exception as exc:
            return DocumentContent(
                document_id=doc_id,
                file_path=filename,
                file_name=filename,
                mime_type="application/pdf",
                document_type=DocumentType.UNKNOWN_DOCUMENT,
                status=DocumentProcessingStatus.CORRUPTED,
                sha256=sha256,
                error_message=f"Failed to open PDF stream: {exc}",
            )

        pages: List[PageContent] = []
        all_tables: List[TableContent] = []

        for page_idx in range(len(doc)):
            page_num = page_idx + 1
            page = doc[page_idx]
            rect = page.rect
            width, height = rect.width, rect.height

            # Stage A: Native text extraction
            text_blocks: List[TextBlock] = []
            raw_blocks = page.get_text("blocks")
            native_text_parts = []

            for b in raw_blocks:
                # b: (x0, y0, x1, y1, text, block_no, block_type)
                # block_type == 0 is text
                if len(b) >= 5 and (len(b) < 7 or b[6] == 0):
                    b_text = str(b[4]).strip()
                    if b_text:
                        bbox = BoundingBox(x0=float(b[0]), y0=float(b[1]), x1=float(b[2]), y1=float(b[3]))
                        text_blocks.append(
                            TextBlock(
                                text=b_text,
                                page_number=page_num,
                                bounding_box=bbox,
                                confidence=1.0,
                                extraction_method=DocumentExtractionMethod.NATIVE_PDF,
                            )
                        )
                        native_text_parts.append(b_text)

            full_native_page_text = "\n".join(native_text_parts)

            # Extract structured tables if available in PyMuPDF
            try:
                tabs = page.find_tables()
                if tabs and tabs.tables:
                    for t in tabs.tables:
                        df_tab = t.extract()
                        if df_tab and len(df_tab) > 1:
                            headers = [str(c or "").strip() for c in df_tab[0]]
                            rows = [[str(c or "").strip() for c in r] for r in df_tab[1:]]
                            all_tables.append(TableContent(headers=headers, rows=rows, page_number=page_num))
            except Exception:
                pass

            # Stage B: Scan detection
            images_on_page = len(page.get_images())
            scan_res = self.scan_detector.analyze_page(
                page_number=page_num,
                native_text=full_native_page_text,
                image_count=images_on_page,
                page_width=width,
                page_height=height,
            )

            ocr_blocks: List[OCRBlock] = []

            # Stage C & D: Rasterize and OCR if page is scanned or hybrid
            if scan_res.is_scanned:
                try:
                    pix = page.get_pixmap(dpi=self.render_dpi)
                    img_bytes = pix.tobytes("png")
                    ocr_blocks = self.ocr_engine.extract_from_image(img_bytes, page_number=page_num)
                except Exception:
                    pass

            # Stage E: Preserved separate native and OCR streams
            pages.append(
                PageContent(
                    page_number=page_num,
                    text=full_native_page_text,
                    text_blocks=text_blocks,
                    ocr_blocks=ocr_blocks,
                    is_scanned=scan_res.is_scanned,
                )
            )

        metadata = {
            "page_count": len(doc),
            "author": doc.metadata.get("author") if doc.metadata else None,
            "title": doc.metadata.get("title") if doc.metadata else None,
            "format": "PDF",
        }
        doc.close()

        return DocumentContent(
            document_id=doc_id,
            file_path=filename,
            file_name=filename,
            mime_type="application/pdf",
            document_type=DocumentType.UNKNOWN_DOCUMENT,
            pages=pages,
            tables=all_tables,
            metadata=metadata,
            status=DocumentProcessingStatus.VALID,
            sha256=sha256,
        )

    def parse_file(self, file_path: str) -> DocumentContent:
        """Parses a PDF file from a local filesystem path."""
        p = Path(file_path)
        raw_bytes = p.read_bytes()
        sha256 = hashlib.sha256(raw_bytes).hexdigest()
        doc_id = f"doc_{sha256[:12]}"
        return self.parse_bytes(raw_bytes, filename=p.name, document_id=doc_id)
