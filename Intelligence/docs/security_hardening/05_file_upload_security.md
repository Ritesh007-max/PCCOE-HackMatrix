# FIN File Upload Security & Document Hardening

## 1. Supported Document Types
FIN supports five explicit citizen document formats:
- **PDF** (`application/pdf`)
- **PNG** (`image/png`)
- **JPEG** (`image/jpeg`)
- **WEBP** (`image/webp`)
- **DOCX** (`application/vnd.openxmlformats-officedocument.wordprocessingml.document`)

All other formats (including executables, scripts, raw binaries, and archives) are rejected with HTTP 415.

---

## 2. Document Hardening Controls

### 2.1 File Size & Quota Limits
- **Maximum File Upload Size**: 25 MB.
- **Maximum Files per Request**: 10 documents.
- **Maximum Request Body Size**: 30 MB.

### 2.2 Magic Byte & Extension Consistency
- File extensions are strictly checked against detected magic-byte headers:
  - PDF: `%PDF-`
  - DOCX: `PK\x03\x04` containing `[Content_Types].xml` and `word/` directory.
  - PNG: `\x89PNG\r\n\x1a\n`
  - JPEG: `\xff\xd8\xff`
  - WEBP: `RIFF....WEBP`
- Files with spoofed extensions (e.g. executable renamed to `.pdf`) are rejected.

### 2.3 Image Pixel Bomb Defense
- All image uploads undergo safety verification via Pillow:
  - Total pixels ($\text{width} \times \text{height}$) must not exceed 100 Megapixels.
  - Defends against image decompression bombs designed to cause Out-Of-Memory (OOM) kernel crashes.

### 2.4 PDF Parsing Safeguards
- **Maximum Page Count**: Hard cap of 100 pages per PDF document.
- Documents exceeding 100 pages are rejected with `DocumentProcessingStatus.TOO_LARGE` before rasterization or OCR execution.
- Malformed PDFs lacking document root or EOF trailers are marked `CORRUPTED`.

### 2.5 DOCX Zip Bomb & Macro Protection
- **Compression Ratio Cap**: Maximum uncompressed-to-compressed ratio of 50:1.
- **Maximum Uncompressed Size**: 50 MB total uncompressed content.
- **Entry Count Limit**: Maximum 1,000 entries inside archive.
- **Macro Blocking**: Any archive containing `vbaProject.bin`, `.exe`, `.dll`, `.bat`, `.cmd`, `.vbs`, or script extensions is rejected.
- **Archive Traversal Check**: File entry paths inside zip archives are validated to ensure no `..` or leading `/` sequences exist.

### 2.6 Ephemeral Isolated Storage
- Uploaded bytes are processed through `isolated_temp_document()` context managers.
- Written to random UUID directories (`/tmp/fin_doc_<uuid>`).
- Guaranteed deletion in `finally:` blocks upon processing completion.
- Filesystem permissions are restricted to the application service user.
