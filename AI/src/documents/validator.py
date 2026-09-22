"""
PolicySetu Document Pre-Ingestion Validator.
Guards against malformed files, decompression bombs, path traversal attacks,
extension-MIME spoofing, oversized uploads, and duplicate processing.
"""

from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
import re
from typing import Optional, Set, Tuple
import zipfile

from PIL import Image

try:
    from .models import DocumentProcessingStatus
except (ImportError, ValueError):
    from src.documents.models import DocumentProcessingStatus


# Administrative Security Thresholds
DEFAULT_MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
MAX_IMAGE_PIXELS = 100_000_000  # 100 Megapixels max (decompression bomb protection)

# Known Magic Byte Signatures
MAGIC_BYTES = {
    "pdf": [b"%PDF-"],
    "zip_docx": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpeg": [b"\xff\xd8\xff"],
    "webp": [b"RIFF"],
}


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
    ):
        self.max_file_size_bytes = max_file_size_bytes
        self.max_image_pixels = max_image_pixels
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
        if sha256_hash in self._seen_hashes:
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
        """Validates magic bytes against declared extension."""
        ext = Path(filename).suffix.lower()

        # PDF validation
        if data.startswith(b"%PDF-"):
            if ext and ext != ".pdf":
                return "application/pdf", False, f"Extension mismatch: file has .pdf content but '{ext}' extension."
            # Check for basic PDF structure
            if len(data) < 32 or (b"%%EOF" not in data[-1024:] and b"/Root" not in data):
                return "application/pdf", False, "Malformed PDF: missing document catalog or end-of-file trailer."
            return "application/pdf", True, None

        # DOCX validation (ZIP archive containing word/document.xml)
        if any(data.startswith(sig) for sig in MAGIC_BYTES["zip_docx"]):
            try:
                import io
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    namelist = zf.namelist()
                    if "[Content_Types].xml" in namelist and ("word/document.xml" in namelist or "word/" in "".join(namelist)):
                        if ext and ext not in (".docx", ".doc"):
                            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document", False, f"Extension mismatch: Word XML doc has '{ext}' extension."
                        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document", True, None
            except Exception:
                return "application/zip", False, "Malformed DOCX archive: unable to read zip structure."

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
        import io
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
