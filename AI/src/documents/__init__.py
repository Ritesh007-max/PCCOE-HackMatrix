"""
PolicySetu Documents & Evidence Package.
Exports normalized document representations, multi-format parsers, OCR abstractions,
validation guards, and evidence registries.
"""

from .provenance import DocumentProvenance, DocumentType
from .evidence import EvidenceRegistry, VERIFICATION_HIERARCHY
from .models import (
    DocumentContent,
    PageContent,
    TextBlock,
    TableContent,
    OCRBlock,
    BoundingBox,
    DocumentProcessingStatus,
    DocumentExtractionMethod,
    ApplicantFactCandidate,
)
from .validator import DocumentValidator, ValidationResult
from .scan_detector import ScanDetector, ScanDetectionResult, PageType
from .detector import DocumentTypeDetector
from .pdf_parser import LayeredPDFParser
from .docx_parser import DocxParser
from .image_parser import ImageParser
from .ocr import BaseOCREngine, PaddleOCREngine, HeuristicOCREngine, get_ocr_engine
from .pipeline import DocumentPipeline

__all__ = [
    "DocumentProvenance",
    "DocumentType",
    "EvidenceRegistry",
    "VERIFICATION_HIERARCHY",
    "DocumentContent",
    "PageContent",
    "TextBlock",
    "TableContent",
    "OCRBlock",
    "BoundingBox",
    "DocumentProcessingStatus",
    "DocumentExtractionMethod",
    "ApplicantFactCandidate",
    "DocumentValidator",
    "ValidationResult",
    "ScanDetector",
    "ScanDetectionResult",
    "PageType",
    "DocumentTypeDetector",
    "LayeredPDFParser",
    "DocxParser",
    "ImageParser",
    "BaseOCREngine",
    "PaddleOCREngine",
    "HeuristicOCREngine",
    "get_ocr_engine",
    "DocumentPipeline",
]
