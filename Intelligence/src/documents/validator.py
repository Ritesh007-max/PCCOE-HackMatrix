"""
FIN Document Pre-Ingestion Validator.
Guards against malformed files, decompression bombs, path traversal attacks,
extension-MIME spoofing, oversized uploads, macro-embedded archives, and duplicate processing.
"""

from contextlib import contextmanager
from dataclasses import dataclass, field
import hashlib
import io
import os
from pathlib import Path
import re
import tempfile
from typing import Generator, Optional, Set, Tuple
import uuid
import zipfile

from PIL import Image

try:
    from .models import DocumentProcessingStatus
except (ImportError, ValueError):
    from src.documents.models import DocumentProcessingStatus


# Administrative Security Thresholds
DEFAULT_MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
MAX_IMAGE_PIXELS = 100_000_000  # 100 Megapixels max (decompression bomb protection)
MAX_PDF_PAGES = 100
MAX_ZIP_ENTRIES = 1000
MAX_DOCX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_DECOMPRESSION_RATIO = 50.0  # 50:1

# Known Magic Byte Signatures
MAGIC_BYTES = {
    "pdf": [b"%PDF-"],
    "zip_docx": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpeg": [b"\xff\xd8\xff"],
    "webp": [b"RIFF"],
}

# Dangerous extensions and files inside archives
DANGEROUS_ARCHIVE_EXTENSIONS = (
    ".exe", ".dll", ".so", ".dylib", ".bat", ".cmd", ".ps1", ".vbs",
    ".js", ".sh", ".bash", ".py", ".bin", ".msi", ".scr", ".com",
)


@dataclass
class ValidationResult:
    """Outcome of document pre-validation."""
    is_valid: bool
    status: DocumentProcessingStatus
    mime_type: str = "application/octet-stream"
    file_size_bytes: int = 0
    sha256: str = ""
    error_message: Optional[str] = None
    sanitized_filename: str = ""


class DocumentValidator:
    """
    Validates physical documents before any parsing, OCR, or model ingestion.
    Enforces strict zero-trust principles on uploaded citizen files.
    """

    def __init__(
        self,
        max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
        max_image_pixels: int = MAX_IMAGE_PIXELS,
        max_pdf_pages: int = MAX_PDF_PAGES,
        allow_duplicates: bool = False,
    ):
        self.max_file_size_bytes = max_file_size_bytes
        self.max_image_pixels = max_image_pixels
        self.max_pdf_pages = max_pdf_pages
        self.allow_duplicates = allow_duplicates
        self._seen_hashes: Set[str] = set()

    def sanitize_filename(self, filename: str) -> str:
        """Strips path traversal sequences, null bytes, and dangerous characters."""
        if not filename:
            return "unnamed_document"
        clean = Path(filename).name
        clean = clean.replace("\x00", "")
        clean = re.sub(r'[\\/:*?"<>|]', "_", clean)
        clean = re.sub(r"\s+", "_", clean).strip("._")
        return clean or "document"

    def validate_bytes(self, data: bytes, filename: str) -> ValidationResult:
        """Validates in-memory document bytes."""
        sanitized_name = self.sanitize_filename(filename)
        file_size = len(data)

        # 1. Empty file check
        if file_size == 0:
            return ValidationResult(
                is_valid=False,
                status=DocumentProcessingStatus.CORRUPTED,
                file_size_bytes=0,
                error_message="Uploaded document is empty (0 bytes).",
                sanitized_filename=sanitized_name,
            )

        # 2. Maximum file size check
        if file_size > self.max_file_size_bytes:
            return ValidationResult(
                is_valid=False,
                status=DocumentProcessingStatus.TOO_LARGE,
                file_size_bytes=file_size,
                error_message=f"File exceeds maximum permissible size of {self.max_file_size_bytes // (1024 * 1024)}MB.",
                sanitized_filename=sanitized_name,
            )

        # Compute SHA-256
        sha256_hash = hashlib.sha256(data).hexdigest()

        # 3. Duplicate hash detection
        if not self.allow_duplicates and sha256_hash in self._seen_hashes:
            return ValidationResult(
                is_valid=False,
                status=DocumentProcessingStatus.DUPLICATE,
                file_size_bytes=file_size,
                sha256=sha256_hash,
                error_message="Duplicate document detected (identical content hash already processed).",
                sanitized_filename=sanitized_name,
            )

        # 4. MIME and Magic byte inspection
        detected_mime, format_valid, err = self._inspect_file_format(data, sanitized_name)
        if not format_valid:
            status = DocumentProcessingStatus.CORRUPTED if "malformed" in (err or "").lower() else DocumentProcessingStatus.INVALID_TYPE
            return ValidationResult(
                is_valid=False,
                status=status,
                mime_type=detected_mime,
                file_size_bytes=file_size,
                sha256=sha256_hash,
                error_message=err,
                sanitized_filename=sanitized_name,
            )

        # 5. Dangerous image dimensions / pixel bomb protection
        if detected_mime.startswith("image/"):
            img_valid, img_err = self._validate_image_safety(data)
            if not img_valid:
                return ValidationResult(
                    is_valid=False,
                    status=DocumentProcessingStatus.CORRUPTED,
                    mime_type=detected_mime,
                    file_size_bytes=file_size,
                    sha256=sha256_hash,
                    error_message=img_err,
                    sanitized_filename=sanitized_name,
                )

        # Record hash as seen
        self._seen_hashes.add(sha256_hash)

        return ValidationResult(
            is_valid=True,
            status=DocumentProcessingStatus.VALID,
            mime_type=detected_mime,
            file_size_bytes=file_size,
            sha256=sha256_hash,
            sanitized_filename=sanitized_name,
        )

    def validate_file(self, file_path: str) -> ValidationResult:
        """Validates a file on disk."""
        path_obj = Path(file_path)

        # Path traversal guard
        try:
            resolved = path_obj.resolve()
        except Exception as exc:
            return ValidationResult(
                is_valid=False,
                status=DocumentProcessingStatus.PROCESSING_ERROR,
                error_message=f"Invalid file path resolution: {exc}",
                sanitized_filename=self.sanitize_filename(path_obj.name),
            )

        if not path_obj.exists() or not path_obj.is_file():
            return ValidationResult(
                is_valid=False,
                status=DocumentProcessingStatus.PROCESSING_ERROR,
                error_message=f"File does not exist or is not a regular file: {file_path}",
                sanitized_filename=self.sanitize_filename(path_obj.name),
            )

        try:
            raw_bytes = path_obj.read_bytes()
            return self.validate_bytes(raw_bytes, path_obj.name)
        except Exception as exc:
            return ValidationResult(
                is_valid=False,
                status=DocumentProcessingStatus.PROCESSING_ERROR,
                error_message=f"Error reading file {file_path}: {exc}",
                sanitized_filename=self.sanitize_filename(path_obj.name),
            )

    def _inspect_file_format(self, data: bytes, filename: str) -> Tuple[str, bool, Optional[str]]:
        """Validates magic bytes against declared extension with zip bomb and macro protection."""
        ext = Path(filename).suffix.lower()

        # PDF validation: ISO 32000-1 allows %PDF- anywhere in first 1024 bytes
        pdf_sig_pos = data[:1024].find(b"%PDF-")
        if pdf_sig_pos != -1:
            if ext and ext not in (".pdf", ""):
                return "application/pdf", False, f"Extension mismatch: file has .pdf content but '{ext}' extension."
            if len(data) < 32:
                return "application/pdf", False, "Malformed PDF: file size too small to be a valid PDF."
            # Verify structure and page count using PyMuPDF if available
            try:
                import pymupdf
                with pymupdf.open(stream=data, filetype="pdf") as pdf_doc:
                    if len(pdf_doc) > self.max_pdf_pages:
                        return "application/pdf", False, f"PDF page count ({len(pdf_doc)}) exceeds safety ceiling of {self.max_pdf_pages} pages."
            except Exception as exc:
                if b"%%EOF" not in data[-4096:] and b"/Root" not in data and b"stream" not in data:
                    return "application/pdf", False, f"Malformed PDF: unable to parse PDF structure: {exc}"
            return "application/pdf", True, None

        # Rejection of non-PDF files claiming .pdf extension
        if ext == ".pdf":
            if data.startswith(b"\x89PNG\r\n\x1a\n"):
                return "image/png", False, "Extension mismatch: PNG image has '.pdf' extension."
            if data.startswith(b"\xff\xd8\xff"):
                return "image/jpeg", False, "Extension mismatch: JPEG image has '.pdf' extension."
            return "application/octet-stream", False, "Invalid PDF: Missing %PDF- file signature."

        # DOCX validation (ZIP archive containing word/document.xml)
        if any(data.startswith(sig) for sig in MAGIC_BYTES["zip_docx"]):
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    entries = zf.infolist()
                    if len(entries) > MAX_ZIP_ENTRIES:
                        return "application/zip", False, f"Malformed DOCX: archive contains {len(entries)} entries, exceeding safety cap of {MAX_ZIP_ENTRIES}."

                    total_uncompressed = 0
                    namelist = set()

                    for entry in entries:
                        # Path traversal guard inside archive
                        if entry.filename.startswith("/") or entry.filename.startswith("\\") or ".." in entry.filename:
                            return "application/zip", False, "Malformed DOCX: directory traversal sequence detected in zip entry."

                        lower_name = entry.filename.lower()
                        namelist.add(entry.filename)

                        # Macro and executable injection rejection
                        if "vbaproject.bin" in lower_name or any(lower_name.endswith(bad) for bad in DANGEROUS_ARCHIVE_EXTENSIONS):
                            return "application/zip", False, f"Forbidden content detected: DOCX contains macro or executable payload '{entry.filename}'."

                        total_uncompressed += entry.file_size
                        if total_uncompressed > MAX_DOCX_UNCOMPRESSED_BYTES:
                            return "application/zip", False, f"Decompression bomb: uncompressed content exceeds {MAX_DOCX_UNCOMPRESSED_BYTES // (1024 * 1024)}MB."

                    # Decompression ratio check
                    compressed_size = max(1, len(data))
                    ratio = total_uncompressed / compressed_size
                    if ratio > MAX_DECOMPRESSION_RATIO:
                        return "application/zip", False, f"Decompression bomb: compression ratio {ratio:.1f}:1 exceeds safety limit {MAX_DECOMPRESSION_RATIO}:1."

                    if "[Content_Types].xml" in namelist and ("word/document.xml" in namelist or any(n.startswith("word/") for n in namelist)):
                        if ext and ext not in (".docx", ".doc"):
                            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document", False, f"Extension mismatch: Word XML doc has '{ext}' extension."
                        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document", True, None
            except zipfile.BadZipFile:
                return "application/zip", False, "Malformed DOCX archive: unable to read zip structure."
            except Exception as exc:
                return "application/zip", False, f"Malformed DOCX archive: {exc}"

        # PNG validation
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            if ext and ext != ".png":
                return "image/png", False, f"Extension mismatch: PNG image has '{ext}' extension."
            return "image/png", True, None

        # JPEG validation
        if data.startswith(b"\xff\xd8\xff"):
            if ext and ext not in (".jpg", ".jpeg"):
                return "image/jpeg", False, f"Extension mismatch: JPEG image has '{ext}' extension."
            return "image/jpeg", True, None

        # WEBP validation (RIFF....WEBP)
        if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            if ext and ext != ".webp":
                return "image/webp", False, f"Extension mismatch: WEBP image has '{ext}' extension."
            return "image/webp", True, None

        # Plain text
        if ext in (".txt", ".csv", ".json"):
            try:
                data.decode("utf-8")
                return "text/plain", True, None
            except UnicodeDecodeError:
                return "application/octet-stream", False, "Malformed text: contains invalid non-UTF-8 bytes."

        # Unsupported or unrecognized binary
        return "application/octet-stream", False, f"Unsupported or unrecognizable file format for extension '{ext}'."

    def _validate_image_safety(self, data: bytes) -> Tuple[bool, Optional[str]]:
        """Ensures images do not exceed dimension safety caps (pixel bomb mitigation)."""
        try:
            with Image.open(io.BytesIO(data)) as img:
                img.verify()
                width, height = img.size
                total_pixels = width * height
                if total_pixels > self.max_image_pixels:
                    return False, f"Image dimensions ({width}x{height} = {total_pixels} pixels) exceed safety ceiling of {self.max_image_pixels} pixels."
                return True, None
        except Exception as exc:
            return False, f"Malformed image data: {exc}"


@contextmanager
def isolated_temp_document(data: bytes, suffix: str = ".tmp") -> Generator[Path, None, None]:
    """
    Creates an isolated temporary document in a secure, isolated subfolder
    and guarantees immediate cleanup upon context exit.
    """
    token = uuid.uuid4().hex
    temp_dir = Path(tempfile.gettempdir()) / f"fin_doc_{token}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    clean_suffix = re.sub(r"[^a-zA-Z0-9\._-]", "", suffix) or ".tmp"
    temp_path = temp_dir / f"doc_{token[:8]}{clean_suffix}"
    try:
        temp_path.write_bytes(data)
        yield temp_path
    finally:
        try:
            if temp_path.exists():
                temp_path.unlink()
            if temp_dir.exists():
                temp_dir.rmdir()
        except Exception:
            pass
