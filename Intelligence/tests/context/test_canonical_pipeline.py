"""
Comprehensive Test Suite for Phase 17 Canonical Applicant Context, Facts, and Evidence Pipeline.
Verifies:
- Basic fact extraction and raw value preservation
- OCR block provenance (page, bbox, confidence, method)
- Deterministic statutory normalization
- Origin source types (DOCUMENT vs USER_INPUT vs PROFILE)
- Document idempotency and SHA-256 deduplication
- Contradictory evidence and conflict detection
- Strict applicant isolation
- Unified ApplicantContext building and bridge to RuleEvaluator
- Explicit persistence error handling
- End-to-end synthetic document ingestion and fact query
- New Applicant API endpoints
"""

import io
import unittest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from src.extraction.models import (
    ApplicantFact,
    Evidence,
    FactSourceType,
    FactVerificationStatus,
    ExtractionMethod,
)
from src.documents.models import (
    DocumentContent,
    DocumentType,
    DocumentProcessingStatus,
    DocumentExtractionMethod,
    PageContent,
    TextBlock,
    OCRBlock,
    BoundingBox,
)
from src.context.models import DocumentContext, ApplicantContext
from src.context.fact_mapper import (
    canonicalize_fact_key,
    find_block_provenance,
    extract_document_canonical_facts,
)
from src.context.service import ApplicantContextService
from src.persistence.repository import FactPersistenceRepository, PersistenceError
from src.rules.evaluator import RuleEvaluator
from src.rules.models import Rule, RuleStatus
from src.api.app import app
from src.api.config import DEFAULT_SERVICE_CONFIG


class TestCanonicalApplicantDataLayer(unittest.TestCase):

    def setUp(self):
        # Isolated in-memory repository for each test
        self.repo = FactPersistenceRepository(db_path=":memory:")
        self.context_service = ApplicantContextService(repository=self.repo)
        self.client = TestClient(app)
        self.headers = {"X-AI-Service-Key": DEFAULT_SERVICE_CONFIG.service_api_key}

    # ------------------------------------------------------------
    # A. BASIC FACT EXTRACTION & RAW VALUE PRESERVATION
    # ------------------------------------------------------------
    def test_basic_fact_extraction_and_raw_preservation(self):
        """Input 'Annual Family Income: Rs. 4,20,000' -> annual_family_income=420000, raw preserved."""
        text = "Income Certificate\nAnnual Family Income: Rs. 4,20,000\nState: Gujarat"
        doc = DocumentContent(
            document_id="doc_test_01",
            file_path="synthetic_income.pdf",
            file_name="synthetic_income.pdf",
            mime_type="application/pdf",
            document_type=DocumentType.INCOME_CERTIFICATE,
            pages=[
                PageContent(
                    page_number=1,
                    text=text,
                    text_blocks=[
                        TextBlock(
                            text="Annual Family Income: Rs. 4,20,000",
                            page_number=1,
                            bounding_box=BoundingBox(10.0, 20.0, 150.0, 40.0),
                            confidence=0.98,
                            extraction_method=DocumentExtractionMethod.NATIVE_PDF,
                        )
                    ],
                )
            ],
            sha256="hash_test_basic_extraction_01",
        )

        facts, evidence_list, raw_fields = extract_document_canonical_facts(doc, "applicant_001")

        # Find annual_family_income fact
        inc_fact = next((f for f in facts if f.field == "annual_family_income"), None)
        self.assertIsNotNone(inc_fact, "annual_family_income fact should be extracted")
        self.assertEqual(inc_fact.normalized_value, 420000.0)
        self.assertIn("4,20,000", str(inc_fact.raw_value))
        self.assertEqual(inc_fact.data_type, "numeric")
        self.assertEqual(inc_fact.source_type, FactSourceType.DOCUMENT)

        # Raw value must NEVER be overwritten by normalized value
        self.assertNotEqual(inc_fact.raw_value, inc_fact.normalized_value)
        self.assertEqual(inc_fact.raw_value, "Rs. 4,20,000")

    # ------------------------------------------------------------
    # B. OCR PROVENANCE PRESERVATION
    # ------------------------------------------------------------
    def test_ocr_provenance_preservation(self):
        """Verify page number, bounding box, OCR confidence, extraction method remain attached."""
        bbox = BoundingBox(x0=50.5, y0=120.0, x1=200.0, y1=145.5)
        ocr_block = OCRBlock(
            text="Annual Family Income: Rs. 4,20,000",
            page_number=2,
            bounding_box=bbox,
            confidence=0.965,
            extraction_method=DocumentExtractionMethod.OCR_PADDLE,
        )

        doc = DocumentContent(
            document_id="doc_ocr_02",
            file_path="scanned_cert.png",
            file_name="scanned_cert.png",
            mime_type="image/png",
            document_type=DocumentType.INCOME_CERTIFICATE,
            pages=[
                PageContent(
                    page_number=1,
                    text="",
                    is_scanned=True,
                ),
                PageContent(
                    page_number=2,
                    text="",
                    ocr_blocks=[ocr_block],
                    is_scanned=True,
                ),
            ],
            sha256="hash_ocr_provenance_02",
        )

        facts, evidence_list, _ = extract_document_canonical_facts(doc, "applicant_002")
        inc_fact = next(f for f in facts if f.field == "annual_family_income")
        inc_ev = next(e for e in evidence_list if e.applicant_fact_id == inc_fact.id)

        # Verify page number
        self.assertEqual(inc_fact.page_number, 2)
        self.assertEqual(inc_ev.page_number, 2)

        # Verify bounding box
        self.assertIsNotNone(inc_fact.bounding_box)
        self.assertEqual(inc_fact.bounding_box["x0"], 50.5)
        self.assertEqual(inc_fact.bounding_box["y1"], 145.5)
        self.assertEqual(inc_ev.bounding_box["x0"], 50.5)

        # Verify OCR confidence
        self.assertAlmostEqual(inc_fact.confidence, 0.965, places=3)
        self.assertAlmostEqual(inc_ev.confidence, 0.965, places=3)

        # Verify extraction method
        self.assertEqual(inc_fact.extraction_method, "OCR_PADDLE")
        self.assertEqual(inc_ev.extraction_method, "OCR_PADDLE")

    # ------------------------------------------------------------
    # C. DETERMINISTIC STATUTORY NORMALIZATION
    # ------------------------------------------------------------
    def test_normalization_formats(self):
        """Test Indian Rupee variations: ₹4,20,000, Rs. 4,20,000, INR 420000, 420000, 4.2 Lakh."""
        from src.normalization.normalizer import normalize_inr

        self.assertEqual(normalize_inr("₹4,20,000"), 420000.0)
        self.assertEqual(normalize_inr("Rs. 4,20,000"), 420000.0)
        self.assertEqual(normalize_inr("INR 420000"), 420000.0)
        self.assertEqual(normalize_inr(420000), 420000.0)
        self.assertEqual(normalize_inr("4.2 Lakh"), 420000.0)
        self.assertEqual(normalize_inr("4.2 lac"), 420000.0)
        self.assertEqual(normalize_inr("₹ 4,20,000 /-"), 420000.0)

    # ------------------------------------------------------------
    # D. ORIGIN SOURCE TYPES
    # ------------------------------------------------------------
    def test_source_type_distinction(self):
        """Verify DOCUMENT facts are strictly distinct from USER_INPUT facts."""
        app_id = "citizen_source_test"

        # Document fact
        doc_fact = ApplicantFact(
            applicant_id=app_id,
            field="age",
            value="19 years",
            normalized_value=19,
            data_type="numeric",
            confidence=0.98,
            source_type=FactSourceType.DOCUMENT,
            source_document="birth_certificate.pdf",
            verification_status=FactVerificationStatus.EXTRACTED,
        )
        self.repo.save_fact(doc_fact)

        # User declared fact
        user_fact = self.context_service.record_user_fact(
            applicant_id=app_id,
            fact_key="age",
            raw_value="19",
            confidence=0.8,
            source_type=FactSourceType.USER_INPUT,
            verification_status=FactVerificationStatus.SELF_REPORTED,
        )

        ctx = self.context_service.get_applicant_context(app_id)
        doc_facts = ctx.get_facts_by_source(FactSourceType.DOCUMENT)
        user_facts = ctx.get_facts_by_source(FactSourceType.USER_INPUT)

        self.assertEqual(len(doc_facts), 1)
        self.assertEqual(doc_facts[0].source_type, FactSourceType.DOCUMENT)
        self.assertEqual(len(user_facts), 1)
        self.assertEqual(user_facts[0].source_type, FactSourceType.USER_INPUT)

    # ------------------------------------------------------------
    # E. DUPLICATE DOCUMENT & IDEMPOTENCY
    # ------------------------------------------------------------
    def test_duplicate_document_idempotency(self):
        """Same file processed twice: SHA-256 identical -> no uncontrolled duplicate facts/evidence."""
        app_id = "applicant_dedup"
        text = "Income Certificate\nAnnual Family Income: Rs. 4,20,000"
        doc = DocumentContent(
            document_id="doc_dedup_01",
            file_path="cert.pdf",
            file_name="cert.pdf",
            mime_type="application/pdf",
            document_type=DocumentType.INCOME_CERTIFICATE,
            pages=[PageContent(page_number=1, text=text)],
            sha256="same_sha256_hash_value_12345",
        )

        # First run: processes and stores
        doc_ctx1, facts1, ev1 = self.context_service.process_and_store_document(doc, applicant_id=app_id)
        self.assertEqual(len(facts1), len(doc_ctx1.extracted_facts))

        initial_facts_count = len(self.repo.get_facts_for_applicant(app_id))
        initial_evidence_count = len(self.repo.get_evidence_for_applicant(app_id))
        self.assertGreater(initial_facts_count, 0)

        # Second run with exact identical SHA-256
        doc_ctx2, facts2, ev2 = self.context_service.process_and_store_document(doc, applicant_id=app_id)

        # Counts must NOT have doubled!
        final_facts_count = len(self.repo.get_facts_for_applicant(app_id))
        final_evidence_count = len(self.repo.get_evidence_for_applicant(app_id))

        self.assertEqual(final_facts_count, initial_facts_count)
        self.assertEqual(final_evidence_count, initial_evidence_count)

    # ------------------------------------------------------------
    # F. CONFLICT DETECTION & RESOLUTION SEPARATION
    # ------------------------------------------------------------
    def test_conflicting_documents_preserved_and_flagged(self):
        """Two documents: income=420000 vs income=610000 -> both preserved, conflict flagged, REVIEW."""
        app_id = "applicant_conflict_test"

        # Document A
        doc_a = DocumentContent(
            document_id="doc_a",
            file_path="cert_a.pdf",
            file_name="cert_a.pdf",
            mime_type="application/pdf",
            document_type=DocumentType.INCOME_CERTIFICATE,
            pages=[PageContent(page_number=1, text="Income Certificate\nAnnual Income: Rs. 4,20,000")],
            sha256="hash_doc_a_420k",
        )
        self.context_service.process_and_store_document(doc_a, applicant_id=app_id)

        # Document B (Discordant value)
        doc_b = DocumentContent(
            document_id="doc_b",
            file_path="cert_b.pdf",
            file_name="cert_b.pdf",
            mime_type="application/pdf",
            document_type=DocumentType.INCOME_CERTIFICATE,
            pages=[PageContent(page_number=1, text="Income Certificate\nAnnual Income: Rs. 6,10,000")],
            sha256="hash_doc_b_610k",
        )
        self.context_service.process_and_store_document(doc_b, applicant_id=app_id)

        # Inspect context
        ctx = self.context_service.get_applicant_context(app_id)

        # 1. Both raw facts and evidence must be preserved
        history = self.context_service.get_fact_history(app_id, "annual_family_income")
        self.assertEqual(len(history), 2)
        history_values = {f.normalized_value for f in history}
        self.assertEqual(history_values, {420000.0, 610000.0})

        # 2. Conflict must be explicitly represented
        self.assertTrue(ctx.has_conflict("annual_family_income"))
        self.assertIn("annual_family_income", ctx.conflicts)

        # 3. get_value must return None for conflicted fields to prevent invalid auto-pass
        self.assertIsNone(ctx.get_value("annual_family_income"))

        # 4. Bridge to RuleEvaluator: profile must flag conflict, evaluating rule to REVIEW (never PASS)
        profile = ctx.to_applicant_profile()
        self.assertIn("annual_family_income", profile._conflicts)

        evaluator = RuleEvaluator()
        income_rule = Rule(
            rule_id="rule_inc_max",
            scheme_id="scheme_test",
            rule_type="eligibility",
            field="annual_family_income",
            operator="<=",
            expected_value=500000,
            value_type="numeric",
        )
        res = evaluator.evaluate_rule(income_rule, profile)
        self.assertEqual(res.status, RuleStatus.REVIEW, "Conflicted facts MUST produce REVIEW")

    # ------------------------------------------------------------
    # G. APPLICANT ISOLATION
    # ------------------------------------------------------------
    def test_strict_applicant_isolation(self):
        """Applicant A cannot access Applicant B's facts, documents, or evidence."""
        app_a = "citizen_alice"
        app_b = "citizen_bob"

        # Alice uploads salary certificate
        doc_a = DocumentContent(
            document_id="doc_alice",
            file_path="alice_cert.pdf",
            file_name="alice_cert.pdf",
            mime_type="application/pdf",
            document_type=DocumentType.INCOME_CERTIFICATE,
            pages=[PageContent(page_number=1, text="Annual Income: Rs. 3,00,000\nState: Maharashtra")],
            sha256="hash_alice_unique",
        )
        self.context_service.process_and_store_document(doc_a, applicant_id=app_a)

        # Bob uploads salary certificate
        doc_b = DocumentContent(
            document_id="doc_bob",
            file_path="bob_cert.pdf",
            file_name="bob_cert.pdf",
            mime_type="application/pdf",
            document_type=DocumentType.INCOME_CERTIFICATE,
            pages=[PageContent(page_number=1, text="Annual Income: Rs. 9,50,000\nState: Gujarat")],
            sha256="hash_bob_unique",
        )
        self.context_service.process_and_store_document(doc_b, applicant_id=app_b)

        # Query Alice
        alice_facts = self.context_service.get_all_facts(app_a)
        alice_fact_keys = {f.field: f.normalized_value for f in alice_facts}
        self.assertEqual(alice_fact_keys.get("annual_family_income"), 300000.0)
        self.assertEqual(alice_fact_keys.get("state"), "Maharashtra")

        # Query Bob
        bob_facts = self.context_service.get_all_facts(app_b)
        bob_fact_keys = {f.field: f.normalized_value for f in bob_facts}
        self.assertEqual(bob_fact_keys.get("annual_family_income"), 950000.0)
        self.assertEqual(bob_fact_keys.get("state"), "Gujarat")

        # Alice MUST NOT see Bob's data
        self.assertNotIn(950000.0, [f.normalized_value for f in alice_facts])
        self.assertNotIn("Gujarat", [f.normalized_value for f in alice_facts])

    # ------------------------------------------------------------
    # H. APPLICANT CONTEXT AGGREGATION
    # ------------------------------------------------------------
    def test_context_building_multi_source(self):
        """Given document facts and user-provided facts, builds unified ApplicantContext with provenance."""
        app_id = "applicant_multi_source"

        # Document fact
        doc = DocumentContent(
            document_id="doc_ms",
            file_path="income.pdf",
            file_name="income.pdf",
            mime_type="application/pdf",
            document_type=DocumentType.INCOME_CERTIFICATE,
            pages=[PageContent(page_number=1, text="Annual Family Income: Rs. 4,20,000")],
            sha256="hash_multi_source_doc",
        )
        self.context_service.process_and_store_document(doc, applicant_id=app_id)

        # User provided facts
        self.context_service.record_user_fact(
            applicant_id=app_id,
            fact_key="age",
            raw_value="19",
            confidence=1.0,
            source_type=FactSourceType.USER_INPUT,
        )
        self.context_service.record_user_fact(
            applicant_id=app_id,
            fact_key="social_category",
            raw_value="OBC",
            confidence=1.0,
            source_type=FactSourceType.USER_INPUT,
        )

        ctx = self.context_service.get_applicant_context(app_id)

        self.assertEqual(ctx.get_value("annual_family_income"), 420000.0)
        self.assertEqual(ctx.get_value("age"), 19)
        self.assertEqual(ctx.get_value("social_category"), "OBC")

        # Check provenance
        inc_ev = ctx.get_evidence("annual_family_income")
        self.assertEqual(len(inc_ev), 1)
        self.assertEqual(inc_ev[0].source_uri, "income.pdf")

        age_ev = ctx.get_evidence("age")
        self.assertEqual(len(age_ev), 1)
        self.assertEqual(age_ev[0].source_type, FactSourceType.USER_INPUT)

    # ------------------------------------------------------------
    # I. PERSISTENCE FAILURE EXPLICIT ERROR HANDLING
    # ------------------------------------------------------------
    def test_persistence_failure_explicitly_fails(self):
        """Force a DB failure -> request does not falsely report complete success."""
        failing_repo = FactPersistenceRepository(db_path=":memory:")
        # Mock save_document_facts_and_evidence to simulate sqlite error
        failing_repo.save_document_facts_and_evidence = MagicMock(
            side_effect=PersistenceError("Simulated disk I/O failure or database corruption")
        )

        failing_service = ApplicantContextService(repository=failing_repo)

        doc = DocumentContent(
            document_id="doc_fail",
            file_path="fail.pdf",
            file_name="fail.pdf",
            mime_type="application/pdf",
            document_type=DocumentType.INCOME_CERTIFICATE,
            pages=[PageContent(page_number=1, text="Income: Rs. 100000")],
            sha256="hash_fail_doc",
        )

        with self.assertRaises(PersistenceError):
            failing_service.process_and_store_document(doc, applicant_id="app_fail")

    # ------------------------------------------------------------
    # J. END-TO-END DOCUMENT PROCESSING & FACT QUERY VIA API
    # ------------------------------------------------------------
    def test_e2e_document_upload_and_fact_query_api(self):
        """
        Complete flow:
        Upload Synthetic Income Certificate -> POST /v1/documents/process
        Query GET /v1/applicants/{id}/context
        Query GET /v1/applicants/{id}/facts/annual_family_income
        Verify:
          value = 420000.0
          raw = 'Rs. 4,20,000'
          provenance attached
        """
        applicant_id = "citizen_e2e_test"
        doc_text = "Government of Gujarat\nRevenue Department\nAnnual Family Income: Rs. 4,20,000\nCategory: OBC\nState: Gujarat"
        files = [("files", ("synthetic_income_certificate.txt", doc_text.encode("utf-8"), "text/plain"))]
        headers = dict(self.headers)
        headers["X-Applicant-ID"] = applicant_id

        # 1. Upload & Process
        upload_resp = self.client.post("/v1/documents/process", headers=headers, files=files)
        self.assertEqual(upload_resp.status_code, 200)
        upload_data = upload_resp.json()
        self.assertEqual(upload_data["document_count"], 1)
        doc_item = upload_data["documents"][0]
        self.assertEqual(doc_item["status"], "VALID")
        self.assertIn("annual_income", doc_item["extracted_fields"])

        # 2. Query Applicant Context
        ctx_resp = self.client.get(f"/v1/applicants/{applicant_id}/context", headers=headers)
        self.assertEqual(ctx_resp.status_code, 200)
        ctx_data = ctx_resp.json()
        self.assertEqual(ctx_data["status"], "success")
        self.assertIn("annual_family_income", ctx_data["canonical_facts"])
        self.assertFalse(ctx_data["has_conflicts"])

        # 3. Query Specific Fact (annual_family_income)
        fact_resp = self.client.get(
            f"/v1/applicants/{applicant_id}/facts/annual_family_income",
            headers=headers
        )
        self.assertEqual(fact_resp.status_code, 200)
        fact_data = fact_resp.json()
        self.assertEqual(fact_data["status"], "success")
        self.assertEqual(fact_data["fact_key"], "annual_family_income")
        self.assertEqual(fact_data["normalized_value"], 420000.0)
        self.assertIn("4,20,000", str(fact_data["raw_value"]))
        self.assertFalse(fact_data["is_conflicted"])
        self.assertGreater(len(fact_data["evidence"]), 0)

        # 4. Query Evidence
        ev_resp = self.client.get(f"/v1/applicants/{applicant_id}/evidence", headers=headers)
        self.assertEqual(ev_resp.status_code, 200)
        ev_data = ev_resp.json()
        self.assertGreater(ev_data["count"], 0)

    def test_system_metadata_and_profile_authority(self):
        """Verifies metadata fields are never treated as facts and profile supersedes informal input."""
        from src.context.models import ApplicantContext
        from src.extraction.models import ApplicantFact, FactSourceType, FactVerificationStatus

        ctx = ApplicantContext(applicant_id="app_meta_test")

        # 1. System metadata ignored
        meta_fact = ApplicantFact(
            applicant_id="app_meta_test",
            field="updated_at",
            value="2026-10-07T20:36:25.534735+00:00",
            normalized_value="2026-10-07T20:36:25.534735+00:00",
            data_type="string",
            confidence=1.0,
            source_document="authenticated_profile",
            source_type=FactSourceType.PROFILE,
        )
        ctx.add_fact(meta_fact)
        self.assertNotIn("updated_at", ctx.conflicts)
        self.assertNotIn("updated_at", ctx.canonical_facts)

        # 2. Informal user input followed by authoritative profile declaration
        user_fact = ApplicantFact(
            applicant_id="app_meta_test",
            field="annual_family_income",
            value="350000",
            normalized_value=350000.0,
            data_type="number",
            confidence=0.8,
            source_document="chat_input",
            source_type=FactSourceType.USER_INPUT,
            verification_status=FactVerificationStatus.SELF_REPORTED,
        )
        ctx.add_fact(user_fact)

        prof_fact = ApplicantFact(
            applicant_id="app_meta_test",
            field="annual_family_income",
            value="200000",
            normalized_value=200000.0,
            data_type="number",
            confidence=1.0,
            source_document="authenticated_profile",
            source_type=FactSourceType.PROFILE,
            verification_status=FactVerificationStatus.SELF_REPORTED,
        )
        ctx.add_fact(prof_fact)

        self.assertNotIn("annual_family_income", ctx.conflicts)
        self.assertEqual(ctx.canonical_facts["annual_family_income"].normalized_value, 200000.0)

        # 3. Numeric string vs int matching tolerance
        self.assertTrue(ctx._values_match(200000, "200000"))
        self.assertTrue(ctx._values_match(200000.0, "2,00,000"))


if __name__ == "__main__":
    unittest.main()

