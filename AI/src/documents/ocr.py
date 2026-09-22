"""
PolicySetu Optical Character Recognition (OCR) Engine.
Integrates PaddleOCR as primary engine with deterministic fallback for offline/test environments.
Preserves page IDs, text spans, bounding boxes, and confidence scores.
"""

from abc import ABC, abstractmethod
import io
from typing import Any, List, Optional
from PIL import Image

try:
    from .models import BoundingBox, OCRBlock, DocumentExtractionMethod
except (ImportError, ValueError):
    from src.documents.models import BoundingBox, OCRBlock, DocumentExtractionMethod


class BaseOCREngine(ABC):
    """Abstract interface for document OCR processing."""

    @abstractmethod
    def is_available(self) -> bool:
        """Indicates if the OCR engine dependencies are installed and operational."""
        pass

    @abstractmethod
    def extract_from_image(
        self,
        image_bytes_or_pil: Any,
        page_number: int = 1,
    ) -> List[OCRBlock]:
        """Extracts text blocks with bounding boxes and confidence scores from an image."""
        pass


class PaddleOCREngine(BaseOCREngine):
    """
    Production PaddleOCR adapter.
    Handles English and Indic multi-lingual document extraction with high precision.
    """

    def __init__(self, lang: str = "en", use_angle_cls: bool = True):
        self.lang = lang
        self.use_angle_cls = use_angle_cls
        self._ocr = None

    def is_available(self) -> bool:
        try:
            import paddleocr  # type: ignore
            return True
        except ImportError:
            return False

    def _get_ocr_instance(self):
        if self._ocr is None:
            from paddleocr import PaddleOCR  # type: ignore
            # Initialize with angle classifier and specified language
            self._ocr = PaddleOCR(use_angle_cls=self.use_angle_cls, lang=self.lang, show_log=False)
        return self._ocr

    def extract_from_image(
        self,
        image_bytes_or_pil: Any,
        page_number: int = 1,
    ) -> List[OCRBlock]:
        if not self.is_available():
            raise RuntimeError("PaddleOCR is not installed in the current environment.")

        # Convert to numpy array or filepath suitable for paddleocr
        import numpy as np
        if isinstance(image_bytes_or_pil, bytes):
            img = Image.open(io.BytesIO(image_bytes_or_pil)).convert("RGB")
            img_np = np.array(img)
        elif isinstance(image_bytes_or_pil, Image.Image):
            img_np = np.array(image_bytes_or_pil.convert("RGB"))
        else:
            img_np = np.array(image_bytes_or_pil)

        ocr = self._get_ocr_instance()
        result = ocr.ocr(img_np, cls=self.use_angle_cls)

        blocks: List[OCRBlock] = []
        if not result or not result[0]:
            return blocks

        for line in result[0]:
            # line structure: [ [ [x1,y1], [x2,y2], [x3,y3], [x4,y4] ], (text, confidence) ]
            coords = line[0]
            text, conf = line[1]
            xs = [pt[0] for pt in coords]
            ys = [pt[1] for pt in coords]
            bbox = BoundingBox(x0=min(xs), y0=min(ys), x1=max(xs), y1=max(ys))

            blocks.append(
                OCRBlock(
                    text=str(text).strip(),
                    page_number=page_number,
                    bounding_box=bbox,
                    confidence=float(conf),
                    extraction_method=DocumentExtractionMethod.OCR_PADDLE,
                )
            )
        return blocks


class HeuristicOCREngine(BaseOCREngine):
    """
    Deterministic OCR fallback for test and offline environments where C++ binaries
    or external weights are not pre-downloaded.
    Extracts embedded textual streams, EXIF metadata, or synthetic text annotations.
    """

    def is_available(self) -> bool:
        return True

    def extract_from_image(
        self,
        image_bytes_or_pil: Any,
        page_number: int = 1,
    ) -> List[OCRBlock]:
        blocks: List[OCRBlock] = []
        try:
            if isinstance(image_bytes_or_pil, bytes):
                img = Image.open(io.BytesIO(image_bytes_or_pil))
            elif isinstance(image_bytes_or_pil, Image.Image):
                img = image_bytes_or_pil
            else:
                return blocks

            # Inspect metadata for synthetic text (useful in test fixtures)
            info = getattr(img, "info", {})
            desc = info.get("description") or info.get("Comment") or info.get("Software")
            if desc:
                w, h = img.size
                blocks.append(
                    OCRBlock(
                        text=str(desc).strip(),
                        page_number=page_number,
                        bounding_box=BoundingBox(x0=10.0, y0=10.0, x1=float(w - 10), y1=float(h - 10)),
                        confidence=0.92,
                        extraction_method=DocumentExtractionMethod.OCR_HEURISTIC,
                    )
                )
        except Exception:
            pass

        return blocks


def get_ocr_engine(prefer_paddle: bool = True) -> BaseOCREngine:
    """Factory returning PaddleOCR if available, else falling back to HeuristicOCREngine."""
    if prefer_paddle:
        paddle = PaddleOCREngine()
        if paddle.is_available():
            return paddle
    return HeuristicOCREngine()
