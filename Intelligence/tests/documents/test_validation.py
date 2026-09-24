"""
Unit tests for DocumentValidator.
Verifies file validation, MIME and magic byte checking, pixel bomb mitigation,
path traversal sanitization, and duplicate hash tracking.
"""

import io
import unittest
from PIL import Image

from src.documents.validator import DocumentValidator
from src.documents.models import DocumentProcessingStatus


class TestDocumentValidator(unittest.TestCase):

    def setUp(self):
        self.validator = DocumentValidator(max_file_size_bytes=1024 * 1024)  # 1 MB for testing

    def test_empty_file_rejected(self):
        res = self.validator.validate_bytes(b"", "empty.pdf")
        self.assertFalse(res.is_valid)
        self.assertEqual(res.status, DocumentProcessingStatus.CORRUPTED)
        self.assertIn("empty", (res.error_message or "").lower())

    def test_oversized_file_rejected(self):
        big_bytes = b"0" * (1024 * 1024 + 10)
        res = self.validator.validate_bytes(big_bytes, "big.txt")
        self.assertFalse(res.is_valid)
        self.assertEqual(res.status, DocumentProcessingStatus.TOO_LARGE)

    def test_duplicate_hash_rejected(self):
        data = b"Hello statutory policy guidelines unique data"
        res1 = self.validator.validate_bytes(data, "file1.txt")
        self.assertTrue(res1.is_valid)
        self.assertEqual(res1.status, DocumentProcessingStatus.VALID)

        res2 = self.validator.validate_bytes(data, "file2.txt")
        self.assertFalse(res2.is_valid)
        self.assertEqual(res2.status, DocumentProcessingStatus.DUPLICATE)

    def test_pdf_magic_bytes_validation(self):
        valid_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
        res = self.validator.validate_bytes(valid_pdf, "doc.pdf")
        self.assertTrue(res.is_valid)
        self.assertEqual(res.mime_type, "application/pdf")

    def test_extension_mime_mismatch_rejected(self):
        # PDF data with .png extension
        pdf_data = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
        res = self.validator.validate_bytes(pdf_data, "photo.png")
        self.assertFalse(res.is_valid)
        self.assertEqual(res.status, DocumentProcessingStatus.INVALID_TYPE)
        self.assertIn("mismatch", (res.error_message or "").lower())

    def test_pixel_bomb_mitigation(self):
        # Configure validator with tiny pixel threshold
        strict_validator = DocumentValidator(max_image_pixels=100)
        img = Image.new("RGB", (20, 20), color="red")  # 400 pixels > 100
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        res = strict_validator.validate_bytes(buf.getvalue(), "bomb.png")
        self.assertFalse(res.is_valid)
        self.assertEqual(res.status, DocumentProcessingStatus.CORRUPTED)
        self.assertIn("safety ceiling", (res.error_message or "").lower())

    def test_filename_sanitization_path_traversal(self):
        cleaned = self.validator.sanitize_filename("../../etc/passwd.pdf")
        self.assertEqual(cleaned, "passwd.pdf")
        self.assertNotIn("..", cleaned)
        self.assertNotIn("/", cleaned)

        cleaned_win = self.validator.sanitize_filename("..\\..\\windows\\system32\\cmd.exe")
        self.assertNotIn("..", cleaned_win)


if __name__ == "__main__":
    unittest.main()
