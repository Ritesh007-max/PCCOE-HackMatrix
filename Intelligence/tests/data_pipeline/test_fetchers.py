"""
Unit tests for data pipeline fetchers and parsers.
Executes 100% offline with simulated HTTP status fixtures.
"""

from pathlib import Path
import sys
from typing import Dict, Optional
import unittest

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.data_pipeline.fetchers.base import FetchResult
from src.data_pipeline.fetchers.local import LocalBaselineFetcher, BaselineSourceAdapter
from src.data_pipeline.fetchers.web import WebFetcher
from src.data_pipeline.fetchers.myscheme_parser import MySchemeParser
from src.data_pipeline.fetchers.sitemap import SitemapFetcher
from src.data_pipeline.fetchers.pdf import PDFFetcher
from src.data_pipeline.fetchers.huggingface import HuggingFaceFetcher
from src.data_pipeline.sources.registry import SourceRegistry


class TestFetchers(unittest.TestCase):

    def setUp(self):
        self.registry = SourceRegistry()

    # 1. Local Baseline Fetcher Tests
    def test_local_baseline_fetcher(self):
        fetcher = LocalBaselineFetcher()
        # Test existing file
        res = fetcher.fetch("schemes.csv", source_id="myscheme_csv_baseline")
        self.assertTrue(res.success)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(len(res.content_hash) == 64)

        # Test non-existent file
        missing_res = fetcher.fetch("non_existent_file.csv", source_id="test")
        self.assertFalse(missing_res.success)
        self.assertEqual(missing_res.status_code, 404)

    # 2. Baseline Source Adapter Tests
    def test_baseline_source_adapter(self):
        adapter = BaselineSourceAdapter()
        schemes = adapter.load_baseline_schemes(limit=5)
        self.assertGreaterEqual(len(schemes), 1)
        self.assertIn("slug", schemes[0])
        self.assertIn("provenance", schemes[0])

    # 3. Web Fetcher with Mock HTTP Status Fixtures
    def test_web_fetcher_allowlist_enforcement(self):
        fetcher = WebFetcher(registry=self.registry)
        # Attempting unapproved domain
        res = fetcher.fetch("https://forbidden-domain.com/data", source_id="forbidden")
        self.assertFalse(res.success)
        self.assertEqual(res.status_code, 403)
        self.assertIn("allowlist", (res.error or "").lower())

    def test_web_fetcher_mock_statuses(self):
        """Simulate HTTP 200, 304, 404, 429, 500, and timeout via mock handler."""
        def mock_http_server(url: str, headers: dict) -> FetchResult:
            if "status=200" in url:
                return FetchResult(source_id="mock", url=url, status_code=200, text_content="OK", success=True)
            elif "status=304" in url:
                return FetchResult(source_id="mock", url=url, status_code=304, success=True)
            elif "status=404" in url:
                return FetchResult(source_id="mock", url=url, status_code=404, error="Not Found", success=False)
            elif "status=429" in url:
                return FetchResult(source_id="mock", url=url, status_code=429, error="Rate Limited", success=False)
            elif "status=500" in url:
                return FetchResult(source_id="mock", url=url, status_code=500, error="Server Error", success=False)
            elif "status=timeout" in url:
                return FetchResult(source_id="mock", url=url, status_code=504, error="Gateway Timeout", success=False)
            return FetchResult(source_id="mock", url=url, status_code=200, text_content="Default", success=True)

        fetcher = WebFetcher(registry=self.registry, mock_handler=mock_http_server)

        r200 = fetcher.fetch("https://www.myscheme.gov.in/test?status=200", "test")
        self.assertEqual(r200.status_code, 200)

        r304 = fetcher.fetch("https://www.myscheme.gov.in/test?status=304", "test")
        self.assertEqual(r304.status_code, 304)

        r404 = fetcher.fetch("https://www.myscheme.gov.in/test?status=404", "test")
        self.assertEqual(r404.status_code, 404)

        r429 = fetcher.fetch("https://www.myscheme.gov.in/test?status=429", "test")
        self.assertEqual(r429.status_code, 429)

        r500 = fetcher.fetch("https://www.myscheme.gov.in/test?status=500", "test")
        self.assertEqual(r500.status_code, 500)

        r_to = fetcher.fetch("https://www.myscheme.gov.in/test?status=timeout", "test")
        self.assertEqual(r_to.status_code, 504)

    # 4. MyScheme Source-Specific Parser Tests
    def test_myscheme_parser_json(self):
        json_payload = """
        {
            "scheme_name": "PM Kisan Samman Nidhi",
            "level": "Central",
            "eligibility": "Small and marginal farmer families having cultivable land up to 2 hectares.",
            "benefits": "Financial benefit of Rs 6000 per year in three equal installments.",
            "documents_required": "Aadhaar card, landholding documents, bank passbook.",
            "application_process": "Apply through PM Kisan official portal or nearest CSC centre.",
            "official_url": "https://pmkisan.gov.in",
            "faqs": [{"question": "What is the benefit?", "answer": "Rs 6000 annually"}]
        }
        """
        canonical = MySchemeParser.parse_raw_response(
            raw_text=json_payload,
            source_url="https://www.myscheme.gov.in/schemes/pm-kisan",
            content_type="application/json"
        )
        self.assertEqual(canonical["slug"], "pm-kisan")
        self.assertEqual(canonical["scheme_name"], "PM Kisan Samman Nidhi")
        self.assertEqual(canonical["level"], "Central")
        self.assertEqual(canonical["first_party_url"], "https://pmkisan.gov.in")
        self.assertEqual(canonical["faq_count"], 1)

    def test_myscheme_parser_html(self):
        html_payload = """
        <!DOCTYPE html>
        <html>
        <head><title>Post Matric Scholarship for SC Students | myScheme</title></head>
        <body>
            <h1>Post Matric Scholarship for SC Students</h1>
            <a href="https://scholarships.gov.in/portal">Official Portal</a>
            <h2>Eligibility Criteria</h2>
            <p>Annual family income must not exceed Rs 2.50 lakh. Student must belong to Scheduled Caste.</p>
            <h2>Benefits</h2>
            <p>Compulsory non-refundable fees reimbursement and monthly maintenance allowance.</p>
            <h2>Documents Required</h2>
            <p>Caste certificate, income certificate, bank details, marksheet.</p>
        </body>
        </html>
        """
        canonical = MySchemeParser.parse_raw_response(
            raw_text=html_payload,
            source_url="https://www.myscheme.gov.in/schemes/post-matric-sc",
            content_type="text/html"
        )
        self.assertEqual(canonical["slug"], "post-matric-sc")
        self.assertIn("Post Matric Scholarship", canonical["scheme_name"])
        self.assertEqual(canonical["first_party_url"], "https://scholarships.gov.in/portal")
        self.assertIn("2.50 lakh", canonical["eligibility"])

    # 5. Sitemap Fetcher Tests
    def test_sitemap_fetcher_and_diff(self):
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>https://www.myscheme.gov.in/schemes/pm-kisan</loc>
                <lastmod>2026-09-01</lastmod>
            </url>
            <url>
                <loc>https://www.myscheme.gov.in/schemes/post-matric-sc</loc>
                <lastmod>2026-09-10</lastmod>
            </url>
            <url>
                <loc>https://www.myscheme.gov.in/about-us</loc>
                <lastmod>2026-09-01</lastmod>
            </url>
        </urlset>
        """
        fetcher = SitemapFetcher()
        inventory = fetcher.parse_sitemap(sitemap_xml)

        # Filters out /about-us, keeps /schemes/...
        self.assertEqual(len(inventory), 2)
        self.assertIn("https://www.myscheme.gov.in/schemes/pm-kisan", inventory)
        self.assertNotIn("https://www.myscheme.gov.in/about-us", inventory)

        # Test Diffing
        prev_inventory: Dict[str, Optional[str]] = {
            "https://www.myscheme.gov.in/schemes/pm-kisan": "2026-08-01",  # changed
            "https://www.myscheme.gov.in/schemes/old-scheme": "2026-08-01",  # removed
        }
        diff = fetcher.diff_inventories(current_inventory=inventory, previous_inventory=prev_inventory)
        self.assertEqual(diff.added_urls, ["https://www.myscheme.gov.in/schemes/post-matric-sc"])
        self.assertEqual(diff.removed_urls, ["https://www.myscheme.gov.in/schemes/old-scheme"])
        self.assertEqual(diff.changed_urls, ["https://www.myscheme.gov.in/schemes/pm-kisan"])

    # 6. PDF Fetcher & OCR Flagging Tests
    def test_pdf_fetcher_metadata(self):
        pdf_fetcher = PDFFetcher()

        # Valid text stream PDF simulation
        valid_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Page >>\nendobj\nBT (Ministry of Agriculture Policy Guidelines Date: 2026-05-15 Effective immediately for all rural districts) Tj ET\n%%EOF"
        meta = pdf_fetcher.extract_pdf_metadata(valid_pdf, "guidelines.pdf")
        self.assertEqual(meta.status, "EXTRACTED")
        self.assertEqual(meta.publication_date, "2026-05-15")

        # Scanned PDF (no extractable text) -> must flag OCR_REQUIRED
        scanned_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Page >>\nendobj\n%%EOF"
        scanned_meta = pdf_fetcher.extract_pdf_metadata(scanned_pdf, "scanned.pdf")
        self.assertEqual(scanned_meta.status, "OCR_REQUIRED")

        # Malformed PDF header
        corrupt_pdf = b"NOT_A_PDF_STREAM"
        corrupt_meta = pdf_fetcher.extract_pdf_metadata(corrupt_pdf, "corrupt.pdf")
        self.assertEqual(corrupt_meta.status, "MALFORMED")

    # 7. Hugging Face Fetcher and CSR/NGO Classification Tests
    def test_huggingface_fetcher_classification(self):
        hf_fetcher = HuggingFaceFetcher()
        test_records = [
            {
                "scheme_name": "PM Kisan Samman Nidhi",
                "description": "Government direct income support to small farmers",
                "official_website": "https://pmkisan.gov.in",
            },
            {
                "scheme_name": "Tata Trust Medical Aid Grant",
                "description": "CSR charitable grant provided by Tata Foundation for cancer patients",
                "official_website": "https://tatatrusts.org/health",
            }
        ]
        meta = hf_fetcher.normalize_and_classify_records(test_records, "satyajitdas/bharatschemes-v1")
        self.assertEqual(meta.government_schemes_count, 1)
        self.assertEqual(meta.non_gov_csr_count, 1)
        self.assertEqual(meta.records[0]["classification"], "GOVERNMENT_POLICY")
        self.assertEqual(meta.records[1]["classification"], "CSR_NGO")


if __name__ == "__main__":
    unittest.main()
