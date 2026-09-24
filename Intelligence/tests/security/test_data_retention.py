"""
Tests for Ephemeral Data Retention & Temporary Storage Cleanup.
Verifies that temporary files, document bytes, and extracted text
are deterministically cleared without persistence to disk.
"""

from pathlib import Path
import tempfile
import unittest
from src.documents.validator import isolated_temp_document


class TestDataRetention(unittest.TestCase):
    def test_ephemeral_document_deleted_on_success(self):
        doc_data = b"confidential citizen document content"
        file_path = None
        with isolated_temp_document(doc_data, suffix=".pdf") as p:
            file_path = p
            self.assertTrue(p.exists())
            self.assertEqual(p.read_bytes(), doc_data)

        # File and temporary directory must be removed after context block
        self.assertFalse(file_path.exists())
        self.assertFalse(file_path.parent.exists())

    def test_ephemeral_document_deleted_on_exception(self):
        doc_data = b"confidential citizen document content"
        file_path = None
        try:
            with isolated_temp_document(doc_data, suffix=".pdf") as p:
                file_path = p
                self.assertTrue(p.exists())
                raise RuntimeError("Simulated processing crash")
        except RuntimeError:
            pass

        # Cleanup must occur even when an unhandled processing exception occurs
        self.assertIsNotNone(file_path)
        self.assertFalse(file_path.exists())
        self.assertFalse(file_path.parent.exists())


if __name__ == "__main__":
    unittest.main()
