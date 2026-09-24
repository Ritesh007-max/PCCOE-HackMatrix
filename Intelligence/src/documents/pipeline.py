"""
FIN Document Ingestion Pipeline Coordinator.
Validates, parses, and normalizes multi-format citizen documents (PDF, DOCX, Images, Text)
into provider-neutral DocumentContent containers.
"""

from pathlib import Path
from typing import Any, List, Optional, Union

try:
    from .models import (
        DocumentContent,
        DocumentExtractionMethod,
        DocumentProcessingStatus,
        PageContent,
        TextBlock,
    )
    from .provenance import DocumentType
    from .validator import DocumentValidator, ValidationResult
    from .detector import DocumentTypeDetector
    from .pdf_parser import LayeredPDFParser
    from .docx_parser import DocxParser
    from .image_parser import ImageParser
    from .ocr import BaseOCREngine, get_ocr_engine
except (ImportError, ValueError):
    from src.documents.models import (
        DocumentContent,
        DocumentExtractionMethod,
        DocumentProcessingStatus,
        PageContent,
        TextBlock,
    )
    from src.documents.provenance import DocumentType
    from src.documents.validator import DocumentValidator, ValidationResult
    from src.documents.detector import DocumentTypeDetector
    from src.documents.pdf_parser import LayeredPDFParser
    from src.documents.docx_parser import DocxParser
    from src.documents.image_parser import ImageParser
    from src.documents.ocr import BaseOCREngine, get_ocr_engine


class DocumentPipeline:
    """
    End-to-end document preprocessor.
    Decouples raw uploaded files from downstream LLM models.
    """

    def __init__(
        self,
        validator: Optional[DocumentValidator] = None,
        type_detector: Optional[DocumentTypeDetector] = None,
        ocr_engine: Optional[BaseOCREngine] = None,
    ):
        self.validator = validator or DocumentValidator()
        self.type_detector = type_detector or DocumentTypeDetector()
        self.ocr_engine = ocr_engine or get_ocr_engine()

        self.pdf_parser = LayeredPDFParser(ocr_engine=self.ocr_engine)
        self.docx_parser = DocxParser()
        self.image_parser = ImageParser(ocr_engine=self.ocr_engine)

    def process(self, input_item: Union[str, Path, bytes], file_name: Optional[str] = None) -> DocumentContent:
        """Polymorphic entry point accepting file path or raw bytes."""
        if isinstance(input_item, bytes):
            return self.process_bytes(input_item, filename=file_name or "document.bin")
        return self.process_file(input_item)

    def process_file(self, file_path: Union[str, Path]) -> DocumentContent:
        """Processes a single document file on disk."""
        path_obj = Path(file_path)
        val_res = self.validator.validate_file(str(path_obj))
        if not val_res.is_valid:
            return DocumentContent(
                document_id=f"doc_{val_res.sha256[:12]}" if val_res.sha256 else "doc_invalid",
                file_path=str(path_obj),
                file_name=val_res.sanitized_filename,
                mime_type=val_res.mime_type,
                document_type=DocumentType.UNKNOWN_DOCUMENT,
                status=val_res.status,
                sha256=val_res.sha256,
                error_message=val_res.error_message,
            )

        raw_bytes = path_obj.read_bytes()
        return self._parse_validated_bytes(raw_bytes, val_res)

    def process_bytes(self, raw_bytes: bytes, filename: str) -> DocumentContent:
        """Processes in-memory bytes."""
        val_res = self.validator.validate_bytes(raw_bytes, filename)
        if not val_res.is_valid:
            return DocumentContent(
                document_id=f"doc_{val_res.sha256[:12]}" if val_res.sha256 else "doc_invalid",
                file_path=filename,
                file_name=val_res.sanitized_filename,
                mime_type=val_res.mime_type,
                document_type=DocumentType.UNKNOWN_DOCUMENT,
                status=val_res.status,
                sha256=val_res.sha256,
                error_message=val_res.error_message,
            )

        return self._parse_validated_bytes(raw_bytes, val_res)

    def _parse_validated_bytes(self, data: bytes, val_res: ValidationResult) -> DocumentContent:
        """Routes validated bytes to format-specific parser and runs type detection."""
        mime = val_res.mime_type
        filename = val_res.sanitized_filename
        doc_id = f"doc_{val_res.sha256[:12]}"

        # 1. Format-specific parsing
        if mime == "application/pdf":
            doc_content = self.pdf_parser.parse_bytes(data, filename=filename, document_id=doc_id)
        elif "wordprocessingml" in mime:
            doc_content = self.docx_parser.parse_bytes(data, filename=filename, document_id=doc_id)
        elif mime.startswith("image/"):
            doc_content = self.image_parser.parse_bytes(data, filename=filename, document_id=doc_id)
        elif mime == "text/plain":
            text_str = data.decode("utf-8", errors="replace")
            tb = TextBlock(
                text=text_str,
                page_number=1,
                confidence=1.0,
                extraction_method=DocumentExtractionMethod.NATIVE_PDF,
            )
            page = PageContent(page_number=1, text=text_str, text_blocks=[tb])
            doc_content = DocumentContent(
                document_id=doc_id,
                file_path=filename,
                file_name=filename,
                mime_type=mime,
                pages=[page],
                status=DocumentProcessingStatus.VALID,
                sha256=val_res.sha256,
            )
        else:
            return DocumentContent(
                document_id=doc_id,
                file_path=filename,
                file_name=filename,
                mime_type=mime,
                status=DocumentProcessingStatus.UNSUPPORTED,
                sha256=val_res.sha256,
                error_message=f"Unsupported MIME type for document ingestion: {mime}",
            )

        # 2. Administrative Document Type Classification
        full_text = doc_content.get_full_text()
        detected_type, conf = self.type_detector.detect(full_text, filename=filename)
        doc_content.document_type = detected_type
        doc_content.metadata["detected_type_confidence"] = conf
        doc_content.sha256 = val_res.sha256

        return doc_content

    def process_documents(self, file_paths: List[Union[str, Path]]) -> List[DocumentContent]:
        """Batch-processes a list of file paths."""
        return [self.process_file(fp) for fp in file_paths]
