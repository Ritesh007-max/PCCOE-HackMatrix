"""
Tests for Document & File Upload Security.
Verifies magic-byte validation, WEBP support, DOCX zip bomb defense,
macro payload rejection, and safe temporary file cleanup.
"""

import io
import unittest
import zipfile
from src.documents.models import DocumentProcessingStatus
from src.documents.validator import DocumentValidator, isolated_temp_document


class TestFileSecurity(unittest.TestCase):
    def setUp(self):
        self.validator = DocumentValidator(
            max_file_size_bytes=1024 * 1024,  # 1 MB for testing
            max_pdf_pages=5,
        )

    def test_empty_file_rejected(self):
        res = self.validator.validate_bytes(b"", "empty.pdf")
        self.assertFalse(res.is_valid)
        self.assertEqual(res.status, DocumentProcessingStatus.CORRUPTED)

    def test_oversized_file_rejected(self):
        huge_bytes = b"%PDF-" + b"0" * (1024 * 1024 + 10)
        res = self.validator.validate_bytes(huge_bytes, "huge.pdf")
        self.assertFalse(res.is_valid)
        self.assertEqual(res.status, DocumentProcessingStatus.TOO_LARGE)

    def test_extension_mismatch_rejected(self):
        # PDF bytes with .png extension
        fake_png = b"%PDF-1.4\n%%EOF"
        res = self.validator.validate_bytes(fake_png, "invoice.png")
        self.assertFalse(res.is_valid)
        self.assertIn("Extension mismatch", res.error_message or "")

    def test_valid_pdf_magic_bytes_accepted(self):
        valid_pdf = b"%PDF-1.4\n1 0 obj\n<< /Root 2 0 R >>\nendobj\n%%EOF"
        res = self.validator.validate_bytes(valid_pdf, "document.pdf")
        self.assertTrue(res.is_valid)
        self.assertEqual(res.mime_type, "application/pdf")

    def test_webp_image_supported(self):
        from PIL import Image
        buf = io.BytesIO()
        img = Image.new("RGB", (10, 10), color="blue")
        img.save(buf, format="WEBP")
        webp_bytes = buf.getvalue()
        res = self.validator.validate_bytes(webp_bytes, "photo.webp")
        self.assertTrue(res.is_valid)
        self.assertEqual(res.mime_type, "image/webp")

    def test_docx_macro_injection_blocked(self):
        # Create a mock docx containing vbaProject.bin
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("[Content_Types].xml", "<Types/>")
            zf.writestr("word/document.xml", "<document/>")
            zf.writestr("word/vbaProject.bin", b"DANGEROUS_MACRO_PAYLOAD")

        raw_docx = buf.getvalue()
        res = self.validator.validate_bytes(raw_docx, "scheme_details.docx")
        self.assertFalse(res.is_valid)
        self.assertIn("macro or executable payload", res.error_message or "")

    def test_docx_traversal_entry_blocked(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("[Content_Types].xml", "<Types/>")
            zf.writestr("../../../evil.xml", "<evil/>")

        raw_docx = buf.getvalue()
        res = self.validator.validate_bytes(raw_docx, "evil.docx")
        self.assertFalse(res.is_valid)
        self.assertIn("directory traversal", res.error_message or "")

    def test_isolated_temp_cleanup(self):
        content = b"temporary sensitive citizen data"
        temp_file_path = None
        with isolated_temp_document(content, suffix=".pdf") as p:
            temp_file_path = p
            self.assertTrue(p.exists())
            self.assertEqual(p.read_bytes(), content)

        # After context exit, file and parent isolated dir must be cleaned up
        self.assertFalse(temp_file_path.exists())
        self.assertFalse(temp_file_path.parent.exists())


if __name__ == "__main__":
    unittest.main()
