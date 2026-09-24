"""
Test Document Ingestion Endpoint.
Verifies POST /v1/documents/process with text, pdf, empty files, and size limits.
"""

import io
import unittest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.config import DEFAULT_SERVICE_CONFIG


class TestDocumentEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.headers = {"X-AI-Service-Key": DEFAULT_SERVICE_CONFIG.service_api_key}

    def test_process_documents_unauthenticated(self):
        """Must reject unauthenticated uploads with 401."""
        files = [("files", ("test.txt", b"Hello citizen", "text/plain"))]
        resp = self.client.post("/v1/documents/process", files=files)
        self.assertEqual(resp.status_code, 401)

    def test_process_single_text_document(self):
        """Successfully processes a valid text document and returns extraction metadata."""
        content = b"Income Certificate\nAnnual Income: Rs 150000\nName: Ramesh Kumar\nState: Maharashtra"
        files = [("files", ("income_cert.txt", content, "text/plain"))]
        resp = self.client.post("/v1/documents/process", headers=self.headers, files=files)

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["document_count"], 1)
        self.assertEqual(len(data["documents"]), 1)
        doc = data["documents"][0]
        self.assertEqual(doc["file_name"], "income_cert.txt")
        self.assertEqual(doc["status"], "VALID")
        self.assertTrue(len(doc["sha256"]) > 0)

    def test_process_empty_file_rejected(self):
        """Empty (0-byte) files must be rejected with 400 Bad Request."""
        files = [("files", ("empty.pdf", b"", "application/pdf"))]
        resp = self.client.post("/v1/documents/process", headers=self.headers, files=files)
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertIn("error", data)
        self.assertIn("empty", data["error"]["message"].lower())

    def test_multiple_documents_batch(self):
        """Processes multiple files in a single request."""
        files = [
            ("files", ("doc1.txt", b"Aadhaar Number: 1234 5678 9012\nDOB: 01/01/1990", "text/plain")),
            ("files", ("doc2.txt", b"Caste Certificate: SC Category", "text/plain")),
        ]
        resp = self.client.post("/v1/documents/process", headers=self.headers, files=files)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["document_count"], 2)


if __name__ == "__main__":
    unittest.main()
