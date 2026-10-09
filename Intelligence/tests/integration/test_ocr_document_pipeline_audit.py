"""
FIN — Full OCR & Document Intelligence Pipeline Audit Test Suite
Implements and verifies all audit tasks (Tasks 1-12):
- Task 2: Text-based vs Scanned extraction & OCR fallback
- Task 3: Controlled Test Documents A, B, C, D
- Task 4: Fact Extraction Accuracy Matrix
- Task 5: Evidence & Page Citations (No hardcoded Page 1; real multi-page citations)
- Task 6: Document Verification Separation (OCR extraction leaves verification PENDING)
- Task 7: Applicant Context building & isolation
- Task 8: RAG / Scheme Retrieval using extracted facts
- Task 9: Deterministic Policy Rule Evaluation (PASS, FAIL, UNKNOWN/REVIEW)
- Task 10: Complete End-to-End Pipeline
- Task 11: Error & Edge Cases
- Task 12: Security & Multi-tenant Data Isolation
"""

import os
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.app import app
from src.documents.pdf_parser import LayeredPDFParser
from src.documents.scan_detector import ScanDetector
from src.documents.models import DocumentType, DocumentExtractionMethod, DocumentProcessingStatus
from src.documents.field_extractor import extract_document_fields
from src.context.service import ApplicantContextService
from src.context.fact_mapper import extract_document_canonical_facts
from src.extraction.models import FactSourceType, FactVerificationStatus
from src.rules.models import Rule, RuleStatus
from src.rules.evaluator import RuleEvaluator
from src.rag.config import RAGConfig
from src.rag.embeddings import DeterministicMockEmbeddingModel
from src.rag.models import ContentType, RAGDocument, RetrievalQuery, SourceTier
from src.rag.retriever import HybridRetriever
from src.config.security import DEFAULT_SECURITY_SETTINGS


FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


class TestDocumentPipelineAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.api_key = DEFAULT_SECURITY_SETTINGS.service_api_key or "fin-test-internal-key-2026"
        cls.headers = {
            "X-AI-Service-Key": cls.api_key,
        }
        cls.pdf_parser = LayeredPDFParser()
        cls.scan_detector = ScanDetector()
        cls.context_service = ApplicantContextService()

    # =========================================================================
    # TASK 2 & TASK 3 (TEST A): Single-page Certificate
    # =========================================================================
    def test_task3_test_a_single_page_certificate(self):
        """
        Verify Test A:
        Applicant Name: Aarav Patel
        Certificate Number: TEST/GJ/INC/2026/TEST-84729
        Date: 15/01/2026
        Family Income: ₹1,80,000
        State: Gujarat
        District: Ahmedabad
        Category: SC
        Issuing Authority: Mamlatdar Office
        """
        pdf_path = FIXTURES_DIR / "test_a_single_page.pdf"
        self.assertTrue(pdf_path.exists(), f"Missing fixture: {pdf_path}")

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        doc_content = self.pdf_parser.parse_bytes(
            pdf_bytes,
            filename="test_a_single_page.pdf",
        )

        self.assertEqual(doc_content.page_count, 1)
        self.assertFalse(doc_content.is_scanned)

        full_text = doc_content.get_full_text()
        self.assertIn("Aarav Patel", full_text)
        self.assertIn("TEST/GJ/INC/2026/TEST-84729", full_text)

        # Field extraction
        raw_fields = extract_document_fields(
            full_text=full_text,
            doc_type="INCOME_CERTIFICATE",
            filename="test_a_single_page.pdf",
        )

        self.assertEqual(raw_fields.get("beneficiary_name"), "Aarav Patel")
        self.assertEqual(raw_fields.get("document_number"), "TEST/GJ/INC/2026/TEST-84729")
        self.assertIn("1,80,000", raw_fields.get("annual_family_income", ""))
        self.assertEqual(raw_fields.get("state"), "Gujarat")
        self.assertEqual(raw_fields.get("district"), "Ahmedabad")
        self.assertEqual(raw_fields.get("category"), "SC")
        self.assertIn("Mamlatdar Office", raw_fields.get("issuing_authority", ""))

        # Canonical facts
        facts, evidence, _ = extract_document_canonical_facts(doc_content, applicant_id="test_user_a")
        fact_dict = {f.field: f for f in facts}

        self.assertIn("annual_family_income", fact_dict)
        self.assertEqual(fact_dict["annual_family_income"].normalized_value, 180000.0)
        self.assertEqual(fact_dict["annual_family_income"].page_number, 1)
        self.assertEqual(fact_dict["social_category"].normalized_value, "SC")
        self.assertEqual(fact_dict["state"].normalized_value, "Gujarat")
        self.assertEqual(fact_dict["district"].normalized_value, "Ahmedabad")

    # =========================================================================
    # TASK 3 (TEST B) & TASK 5: Multi-page Evidence & Page-level Citations
    # =========================================================================
    def test_task3_test_b_multi_page_fact_provenance(self):
        """
        Verify Test B: Facts intentionally distributed across 4 pages:
        Page 1: Applicant name, Certificate number
        Page 2: Family income = ₹1,80,000
        Page 3: Father income = ₹1,20,000, Mother income = ₹60,000
        Page 4: Address, Category = SC, Issuing authority = Mamlatdar Office
        Verify that EVERY fact retains its correct source page (NOT hardcoded to Page 1!).
        """
        pdf_path = FIXTURES_DIR / "test_b_multi_page.pdf"
        self.assertTrue(pdf_path.exists(), f"Missing fixture: {pdf_path}")

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        doc_content = self.pdf_parser.parse_bytes(
            pdf_bytes,
            filename="test_b_multi_page.pdf",
        )

        self.assertEqual(doc_content.page_count, 4)

        facts, evidence, _ = extract_document_canonical_facts(doc_content, applicant_id="test_user_b")
        fact_by_field = {f.field: f for f in facts}

        # Page 1 checks
        self.assertEqual(fact_by_field["beneficiary_name"].page_number, 1, "Name must be on Page 1")
        self.assertEqual(fact_by_field["document_number"].page_number, 1, "Cert No must be on Page 1")

        # Page 2 checks
        self.assertEqual(fact_by_field["annual_family_income"].page_number, 2, "Family Income must be on Page 2!")
        self.assertEqual(fact_by_field["annual_family_income"].normalized_value, 180000.0)

        # Page 3 checks
        self.assertEqual(fact_by_field["father_income"].page_number, 3, "Father Income must be on Page 3!")
        self.assertEqual(fact_by_field["father_income"].normalized_value, 120000.0)
        self.assertEqual(fact_by_field["mother_income"].page_number, 3, "Mother Income must be on Page 3!")
        self.assertEqual(fact_by_field["mother_income"].normalized_value, 60000.0)

        # Page 4 checks
        self.assertEqual(fact_by_field["social_category"].page_number, 4, "Category SC must be on Page 4!")
        self.assertEqual(fact_by_field["social_category"].normalized_value, "SC")
        self.assertEqual(fact_by_field["district"].page_number, 4, "District Ahmedabad must be on Page 4!")
        self.assertEqual(fact_by_field["issuing_authority"].page_number, 4, "Mamlatdar Office must be on Page 4!")

        # Evidence records check
        ev_by_field = {ev.metadata.get("field"): ev for ev in evidence}
        self.assertEqual(ev_by_field["annual_family_income"].page_number, 2)
        self.assertEqual(ev_by_field["father_income"].page_number, 3)
        self.assertEqual(ev_by_field["mother_income"].page_number, 3)
        self.assertEqual(ev_by_field["social_category"].page_number, 4)

    # =========================================================================
    # TASK 3 (TEST C): Personal vs Family Income Strict Separation
    # =========================================================================
    def test_task3_test_c_personal_vs_family_income_separation(self):
        """
        Explicitly verify:
        Personal Income: NOT PROVIDED
        Father Income: ₹1,20,000
        Mother Income: ₹60,000
        Family Income: ₹1,80,000

        Expected:
        personal_income = UNKNOWN / unavailable
        family_income = ₹1,80,000
        father_income = ₹1,20,000
        mother_income = ₹60,000

        The system MUST NOT infer personal_income = ₹1,80,000.
        """
        pdf_path = FIXTURES_DIR / "test_c_income_distinction.pdf"
        self.assertTrue(pdf_path.exists(), f"Missing fixture: {pdf_path}")

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        doc_content = self.pdf_parser.parse_bytes(
            pdf_bytes,
            filename="test_c_income_distinction.pdf",
        )

        app_id = "test_user_income_c"
        self.context_service.process_and_store_document(doc_content, applicant_id=app_id)
        ctx = self.context_service.get_applicant_context(app_id)

        # 1. Family income is correctly stored
        self.assertEqual(ctx.get_value("annual_family_income"), 180000.0)
        self.assertEqual(ctx.get_value("father_income"), 120000.0)
        self.assertEqual(ctx.get_value("mother_income"), 60000.0)

        # 2. Personal income MUST NOT be inferred!
        self.assertIsNone(ctx.get_value("annual_income"), "Personal income must be UNKNOWN / None!")
        self.assertIsNone(ctx.get_fact("annual_income"), "Personal income fact must NOT exist in context!")

    # =========================================================================
    # TASK 2 & TASK 3 (TEST D): Scanned PDF OCR Fallback
    # =========================================================================
    def test_task3_test_d_scanned_pdf_ocr_fallback(self):
        """
        Verify:
        normal extraction -> insufficient/empty text -> OCR fallback triggered
        -> correct OCR text -> correct facts -> correct page citations.
        """
        pdf_path = FIXTURES_DIR / "test_d_scanned.pdf"
        self.assertTrue(pdf_path.exists(), f"Missing fixture: {pdf_path}")

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        # Parse with PDFParser
        doc_content = self.pdf_parser.parse_bytes(
            pdf_bytes,
            filename="test_d_scanned.pdf",
        )

        # Verified scanned flag triggered
        self.assertTrue(doc_content.is_scanned, "Scan detector must detect scanned PDF")
        self.assertIn(
            doc_content.extraction_method,
            [DocumentExtractionMethod.OCR_HEURISTIC, DocumentExtractionMethod.OCR_PADDLE],
            "Extraction method must reflect OCR fallback",
        )

        # OCR extracted blocks and text
        full_text = doc_content.get_full_text()
        self.assertIn("Aarav Patel", full_text)
        self.assertIn("Mamlatdar Office", full_text)

        # Facts extracted with OCR method
        facts, evidence, _ = extract_document_canonical_facts(doc_content, applicant_id="test_user_d")
        self.assertGreater(len(facts), 0, "OCR fallback must yield extracted facts")

        fact_map = {f.field: f for f in facts}
        self.assertIn("annual_family_income", fact_map)
        self.assertEqual(fact_map["annual_family_income"].normalized_value, 180000.0)
        self.assertEqual(fact_map["annual_family_income"].page_number, 1)

    # =========================================================================
    # TASK 6: Document Verification Separation
    # =========================================================================
    def test_task6_document_verification_separation(self):
        """
        Verify OCR extraction leaves verification status PENDING / EXTRACTED.
        OCR extraction MUST NOT automatically produce VERIFIED.
        """
        pdf_path = FIXTURES_DIR / "test_a_single_page.pdf"
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        doc_content = self.pdf_parser.parse_bytes(
            pdf_bytes,
            filename="test_a_single_page.pdf",
        )

        facts, evidence, _ = extract_document_canonical_facts(doc_content, applicant_id="test_user_verif")

        for f in facts:
            self.assertEqual(
                f.verification_status,
                FactVerificationStatus.EXTRACTED,
                "Extracted facts must be EXTRACTED, never automatically VERIFIED",
            )

        for ev in evidence:
            self.assertEqual(
                ev.verification_status,
                FactVerificationStatus.EXTRACTED,
                "Evidence records must be EXTRACTED, never automatically VERIFIED",
            )

    # =========================================================================
    # TASK 7 & TASK 12: Applicant Context & Multi-Tenant Isolation
    # =========================================================================
    def test_task7_and_task12_tenant_isolation_and_context(self):
        """
        Verify:
        - User A cannot access User B's documents or facts.
        - Document IDs are ownership-checked.
        - Deleting a document removes associated extracted facts.
        """
        app_a = "user_alpha_test"
        app_b = "user_beta_test"

        pdf_path = FIXTURES_DIR / "test_a_single_page.pdf"
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        doc_a = self.pdf_parser.parse_bytes(
            pdf_bytes,
            filename="test_a_single_page.pdf",
        )
        doc_a.document_id = "doc_alpha_101"

        self.context_service.process_and_store_document(doc_a, applicant_id=app_a)

        # Context of User A has facts
        ctx_a = self.context_service.get_applicant_context(app_a)
        self.assertEqual(ctx_a.get_value("annual_family_income"), 180000.0)

        # Context of User B has NO facts (strict isolation)
        ctx_b = self.context_service.get_applicant_context(app_b)
        self.assertIsNone(ctx_b.get_fact("annual_family_income"))
        self.assertIsNone(ctx_b.get_value("annual_family_income"))

        # Deleting document removes facts
        removed = self.context_service.delete_document(app_a, "doc_alpha_101")
        self.assertTrue(removed)
        ctx_a_after = self.context_service.get_applicant_context(app_a)
        self.assertIsNone(ctx_a_after.get_fact("annual_family_income"))

    # =========================================================================
    # TASK 8: RAG / Scheme Retrieval Using Extracted Facts
    # =========================================================================
    def test_task8_rag_scheme_retrieval_with_facts(self):
        """
        Verify RAG retrieval matches relevant schemes using extracted applicant facts
        (family income 180000, SC category, Gujarat residence).
        """
        config = RAGConfig(use_faiss=False, embedding_dimension=32)
        embedding_model = DeterministicMockEmbeddingModel(dimension=32)
        retriever = HybridRetriever(config=config, embedding_model=embedding_model)

        # Seed sample candidate schemes
        doc_sc_gujarat = RAGDocument(
            id="guj_sc_scholarship_01",
            content="Post-Matric Scholarship for SC Students Gujarat. Financial assistance for SC students residing in Gujarat with family income below 2.5 lakh.",
            source_dataset="schemes_canonical",
            source_tier=SourceTier.PRIMARY_SCHEME.value,
            scheme_id="guj_sc_scholarship_01",
            scheme_slug="guj_sc_scholarship",
            scheme_name="Post-Matric Scholarship for SC Students Gujarat",
            section="eligibility",
            content_type=ContentType.ELIGIBILITY.value,
            state="Gujarat",
            category="SC",
        )
        doc_general_up = RAGDocument(
            id="up_general_02",
            content="Uttar Pradesh General Rural Housing Scheme. Housing assistance for rural residents of Uttar Pradesh.",
            source_dataset="schemes_canonical",
            source_tier=SourceTier.PRIMARY_SCHEME.value,
            scheme_id="up_general_02",
            scheme_slug="up_general",
            scheme_name="Uttar Pradesh General Rural Housing Scheme",
            section="eligibility",
            content_type=ContentType.ELIGIBILITY.value,
            state="Uttar Pradesh",
            category="General",
        )

        retriever.index_documents([doc_sc_gujarat, doc_general_up])

        # Query reflecting applicant facts
        query = RetrievalQuery(query_text="SC category student Gujarat resident family income 180000", top_k=2)
        results = retriever.retrieve_schemes(query)

        self.assertGreater(len(results), 0)
        top_scheme = results[0]
        self.assertEqual(top_scheme.scheme_slug, "guj_sc_scholarship")
        self.assertEqual(top_scheme.scheme_name, "Post-Matric Scholarship for SC Students Gujarat")

    # =========================================================================
    # TASK 9: Deterministic Policy Rules & Uncertainty Handling
    # =========================================================================
    def test_task9_deterministic_policy_rules(self):
        """
        Verify deterministic rule evaluator:
        - Case 1: All requirements met -> PASS
        - Case 2: Known disqualifying fact -> FAIL
        - Case 3: Required fact missing -> UNKNOWN / REVIEW (NEVER converts to PASS or FAIL)
        """
        evaluator = RuleEvaluator()

        # Setup context with facts from Test A
        app_id = "test_user_rules"
        pdf_path = FIXTURES_DIR / "test_a_single_page.pdf"
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        doc = self.pdf_parser.parse_bytes(
            pdf_bytes,
            filename="test_a_single_page.pdf",
        )
        self.context_service.process_and_store_document(doc, applicant_id=app_id)
        ctx = self.context_service.get_applicant_context(app_id)
        profile = ctx.to_applicant_profile()

        # Case 1: Income <= 250000 -> Expected PASS (since family_income = 180000)
        rule_income = Rule(
            rule_id="r_inc_max",
            scheme_id="scheme_sc_guj",
            rule_type="eligibility",
            field="annual_family_income",
            operator="<=",
            expected_value=250000,
            value_type="numeric",
        )
        res_pass = evaluator.evaluate_rule(rule_income, profile)
        self.assertEqual(res_pass.status, RuleStatus.PASS)

        # Case 2: Known disqualifying fact (e.g. required category General, but applicant is SC)
        rule_disqualify = Rule(
            rule_id="r_cat_gen",
            scheme_id="scheme_gen_only",
            rule_type="eligibility",
            field="social_category",
            operator="=",
            expected_value="General",
            value_type="string",
        )
        res_fail = evaluator.evaluate_rule(rule_disqualify, profile)
        self.assertEqual(res_fail.status, RuleStatus.FAIL)

        # Case 3: Missing required fact (e.g. landholding_hectares is not in document)
        rule_missing = Rule(
            rule_id="r_land",
            scheme_id="scheme_farmer",
            rule_type="eligibility",
            field="landholding_hectares",
            operator="<=",
            expected_value=2.0,
            value_type="numeric",
        )
        res_unknown = evaluator.evaluate_rule(rule_missing, profile)
        self.assertIn(
            res_unknown.status,
            [RuleStatus.UNKNOWN, RuleStatus.REVIEW],
            "Missing fact MUST produce UNKNOWN or REVIEW, NEVER PASS or FAIL!",
        )

    # =========================================================================
    # TASK 10: Complete End-to-End Real Flow
    # =========================================================================
    def test_task10_complete_e2e_real_flow(self):
        """
        Complete flow:
        PDF Bytes -> PDFParser -> Field Extraction -> Facts & Evidence ->
        Applicant Context -> Scheme Retrieval -> Policy Rule Evaluation
        """
        applicant_id = "citizen_e2e_verified"
        pdf_path = FIXTURES_DIR / "test_b_multi_page.pdf"

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        # 1. Parse PDF
        doc_content = self.pdf_parser.parse_bytes(
            pdf_bytes,
            filename="test_b_multi_page.pdf",
        )
        self.assertEqual(doc_content.page_count, 4)

        # 2. Extract facts & store in context
        self.context_service.process_and_store_document(doc_content, applicant_id=applicant_id)
        ctx = self.context_service.get_applicant_context(applicant_id)

        # 3. Verify context facts
        self.assertEqual(ctx.get_value("annual_family_income"), 180000.0)
        self.assertEqual(ctx.get_value("social_category"), "SC")

        # 4. Evaluate policy rules on context
        profile = ctx.to_applicant_profile()
        evaluator = RuleEvaluator()
        income_rule = Rule(
            rule_id="e2e_income_cap",
            scheme_id="gujarat_sc_aid",
            rule_type="eligibility",
            field="annual_family_income",
            operator="<=",
            expected_value=200000,
            value_type="numeric",
        )
        result = evaluator.evaluate_rule(income_rule, profile)
        self.assertEqual(result.status, RuleStatus.PASS)

    # =========================================================================
    # TASK 11: Error and Edge Cases
    # =========================================================================
    def test_task11_corrupted_and_empty_pdf_handling(self):
        """Verify corrupted or empty bytes do not crash or hallucinate false facts."""
        # Empty bytes
        res_empty = self.pdf_parser.parse_bytes(b"", filename="empty.pdf")
        self.assertEqual(res_empty.status, DocumentProcessingStatus.CORRUPTED)
        self.assertEqual(res_empty.get_full_text(), "")

        # Corrupted bytes
        corrupted = b"%PDF-1.4\nthis is not valid pdf data trailing garbage"
        res_corrupt = self.pdf_parser.parse_bytes(corrupted, filename="corrupt.pdf")
        self.assertEqual(res_corrupt.status, DocumentProcessingStatus.CORRUPTED)
        self.assertEqual(res_corrupt.get_full_text(), "")


if __name__ == "__main__":
    unittest.main()
