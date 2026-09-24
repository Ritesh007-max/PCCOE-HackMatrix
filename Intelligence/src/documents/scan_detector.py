"""
FIN Scanned Document & Page Detector.
Inspects page layout metrics (text length, character density, embedded images)
to classify pages as NATIVE_TEXT, SCANNED, or HYBRID.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class PageType(str, Enum):
    """Layout classification for an individual page."""
    NATIVE_TEXT = "NATIVE_TEXT"
    SCANNED = "SCANNED"
    HYBRID = "HYBRID"
    EMPTY = "EMPTY"


@dataclass
class ScanDetectionResult:
    """Diagnostic outcome of page scanning inspection."""
    page_number: int
    page_type: PageType
    is_scanned: bool
    char_count: int
    image_count: int
    text_density: float
    confidence: float
    details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "page_type": self.page_type.value,
            "is_scanned": self.is_scanned,
            "char_count": self.char_count,
            "image_count": self.image_count,
            "text_density": round(self.text_density, 4),
            "confidence": round(self.confidence, 2),
            "details": self.details,
        }


class ScanDetector:
    """
    Classifies document pages based on text density and image coverage.
    Ensures that scanned or photocopy certificates receive OCR rather than empty extracts.
    """

    def __init__(
        self,
        min_char_threshold: int = 40,
        min_density_threshold: float = 0.05,
    ):
        self.min_char_threshold = min_char_threshold
        self.min_density_threshold = min_density_threshold

    def analyze_page(
        self,
        page_number: int,
        native_text: str,
        image_count: int = 0,
        page_width: float = 595.0,
        page_height: float = 842.0,
    ) -> ScanDetectionResult:
        """
        Evaluates a page's text layer and embedded images.
        Standard A4 dimensions: 595 x 842 points.
        """
        clean_text = (native_text or "").strip()
        char_count = len(clean_text)

        # Page area in square decipoints for density calculation
        area = max(1.0, (page_width * page_height) / 10000.0)
        text_density = char_count / area

        # 1. Zero or negligible text with embedded image -> Scanned
        if char_count < self.min_char_threshold and image_count > 0:
            return ScanDetectionResult(
                page_number=page_number,
                page_type=PageType.SCANNED,
                is_scanned=True,
                char_count=char_count,
                image_count=image_count,
                text_density=text_density,
                confidence=0.95,
                details=f"Low native text ({char_count} chars) with {image_count} embedded image(s); page is a scan.",
            )

        # 2. Virtually empty page (no text, no image)
        if char_count < 10 and image_count == 0:
            return ScanDetectionResult(
                page_number=page_number,
                page_type=PageType.EMPTY,
                is_scanned=False,
                char_count=char_count,
                image_count=image_count,
                text_density=text_density,
                confidence=0.90,
                details="Empty page: negligible text and zero images.",
            )

        # 3. Substantial text with images -> Hybrid document (e.g. form with photo)
        if char_count >= self.min_char_threshold and image_count > 0:
            return ScanDetectionResult(
                page_number=page_number,
                page_type=PageType.HYBRID,
                is_scanned=False,
                char_count=char_count,
                image_count=image_count,
                text_density=text_density,
                confidence=0.85,
                details=f"Mixed page: {char_count} chars native text and {image_count} image(s).",
            )

        # 4. Standard native text page
        return ScanDetectionResult(
            page_number=page_number,
            page_type=PageType.NATIVE_TEXT,
            is_scanned=False,
            char_count=char_count,
            image_count=image_count,
            text_density=text_density,
            confidence=0.98,
            details=f"Native digital text page ({char_count} chars, density {text_density:.2f}).",
        )
