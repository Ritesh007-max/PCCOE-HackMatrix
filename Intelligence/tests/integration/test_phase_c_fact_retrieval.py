"""
FIN Phase C: Runtime Data Integrity, Correct Fact Retrieval & Structured AI Responses Regression Tests.

Covers all 14 mandatory regression cases specified in Phase C:
1. Applicant full name retrieval (returns requested value, not document status).
2. Certificate number retrieval (returns actual certificate number, not document status or 'Token').
3. Personal income absent while family income exists (clearly reports personal income unavailable, shows family income).
4. Father's income not substituted as personal income or total annual family income.
5. Family income returns the correct source-backed total (₹1,80,000 from Page 2, not signup 3,50,000 or father 1,20,000).
6. Conflicting income sources trigger REVIEW with competing values and page provenance.
7. Stale facts do not override active evidence incorrectly.
8. Deleted / inactive documents are excluded.
9. Different query handlers return consistent values.
10. Page 2 citations remain accurate.
11. Cross-applicant data isolation.
12. Structured answers contain no raw Markdown leakage.
13. Missing facts are reported as unavailable.
14. No fixed sample values in production response logic (dynamic extraction across different synthetic records).
"""

import sys
import unittest
from pathlib import Path

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from fastapi.testclient import TestClient

from src.api.app import app
from src.api.config import DEFAULT_SERVICE_CONFIG
from src.documents.field_extractor import extract_document_fields
from src.context.fact_mapper import extract_document_canonical_facts
from src.api.routes.chat import (
    resolve_document_fact_page,
    format_document_citation_page,
    summarize_page_text,
)


class TestPhaseCFactRetrieval(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.headers = {"X-AI-Service-Key": DEFAULT_SERVICE_CONFIG.service_api_key}
        # Multi-page synthetic document representing the test case
        self.doc_multi_page = {
            "id": "doc_test_aarav_001",
            "file_name": "FIN_MultiPage_Income_Certificate_QA.pdf",
            "document_type": "INCOME_CERTIFICATE",
            "verification_status": "VERIFIED",
            "is_active": True,
            "extracted_text": (
                "--- [Page 1] ---\n"
                "SYNTHETIC TEST DOCUMENT — NOT VALID FOR OFFICIAL USE\n"
                "GOVERNMENT OF GUJARAT — REVENUE DEPARTMENT\n"
                "OFFICE OF THE MAMLATDAR & EXECUTIVE MAGISTRATE, AHMEDABAD (CITY)\n"
                "Certificate No: TEST/GJ/INC/2026/TEST-84729\n"
                "Date of Issue: 18 February 2026\n"
                "Aadhaar Reference Token: 8392-4820-1940 (Last 4 Digits: 1940)\n\n"
                "1. Full Name of Applicant: Aarav Patel\n"
                "2. Father's / Guardian's Name: Rajesh Patel\n"
                "3. Mother's Name: Meenaben Patel\n"
                "4. Date of Birth: 12 August 2004 (Age: 22 Years)\n"
                "5. Residential Address: B-402, Shivalik Heights, S.G. Highway, Bodakdev\n"
                "   District: Ahmedabad, Gujarat — 380054\n"
                "6. Social Category: General / EWS\n"
                "7. Purpose of Certificate: Educational Scholarship & Welfare Scheme Eligibility Evaluation\n\n"
                "--- [Page 2] ---\n"
                "SYNTHETIC TEST DOCUMENT — NOT VALID FOR OFFICIAL USE\n"
                "DETAILED INCOME ASSESSMENT & ENQUIRY REPORT\n\n"
                "Income Determination Schedule:\n"
                "1. Father's Employment Income (Pvt. Logistics Executive): Rs. 1,20,000 /-\n"
                "2. Mother's Tailoring & Home Enterprise Income: Rs. 60,000 /-\n"
                "3. Income from Agricultural / Land Holdings: Rs. 0 /-\n"
                "4. Income from Other Household Sources: Rs. 0 /-\n\n"
                "Total Annual Family Income: Rs. 1,80,000 /-\n"
                "(In Words: Rupees One Lakh Eighty Thousand Only)\n\n"
                "It is hereby certified that the total annual family income of Aarav Patel from all combined sources "
                "for the financial assessment year 2025-2026 is determined to be Rs. 1,80,000/-.\n"
            ),
            "extracted_fields": {
                "beneficiary_name": "Aarav Patel",
                "document_number": "TEST/GJ/INC/2026/TEST-84729",
                "annual_family_income": "180000",
                "father_income": "120000",
                "mother_income": "60000",
                "other_income": "0",
                "date_of_birth": "12 August 2004",
                "district": "Ahmedabad",
                "social_category": "EWS",
            }
        }

    def _post_chat(self, query: str, applicant_id: str = "app_test_001", documents=None, applicant_facts=None):
        payload = {
            "query": query,
            "applicant_id": applicant_id,
            "documents": documents if documents is not None else [self.doc_multi_page],
            "applicant_facts": applicant_facts or {}
        }
        res = self.client.post("/v1/chat", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 200, msg=f"Chat API returned {res.status_code}: {res.text}")
        return res.json()

    # 1. Applicant full name retrieval
    def test_1_applicant_full_name_retrieval(self):
        data = self._post_chat("What is my full name?", applicant_facts={"full_name": "Aarav Patel"})
        ans = data.get("answer", "")
        self.assertIn("Aarav Patel", ans)
        self.assertNotIn("Ready for AI Chat", ans)
        self.assertIn("Applicant Full Name", ans)

    # 2. Certificate number retrieval
    def test_2_certificate_number_retrieval(self):
        data = self._post_chat("What is my certificate number?", applicant_facts={"document_number": "TEST/GJ/INC/2026/TEST-84729"})
        ans = data.get("answer", "")
        self.assertIn("TEST/GJ/INC/2026/TEST-84729", ans)
        self.assertNotIn("Token", ans)
        self.assertNotIn("Ready for AI Chat", ans)
        self.assertIn("Certificate Number", ans)

    # 3. Personal income absent while family income exists
    def test_3_personal_income_absent_while_family_income_exists(self):
        data = self._post_chat("What is my personal income?", applicant_facts={"annual_family_income": 180000})
        ans = data.get("answer", "")
        self.assertIn("personal annual income is not available", ans)
        self.assertIn("Annual Family Income on File", ans)
        self.assertIn("1,80,000", ans)
        self.assertNotIn("1,20,000", ans)  # Must NOT call father's income family income

    # 4. Father's income not substituted as personal income
    def test_4_father_income_not_substituted(self):
        data = self._post_chat("What is my father's income?")
        ans = data.get("answer", "")
        self.assertIn("Father's Annual Income", ans)
        self.assertIn("1,20,000", ans)
        self.assertIn("Page 2", ans)

    # 5. Family income returns correct source-backed total (₹1,80,000)
    def test_5_family_income_returns_correct_total(self):
        # Even if applicant_facts has default signup 350000, active doc must govern!
        data = self._post_chat("What is my annual family income?", applicant_facts={"annual_income": "350000"})
        ans = data.get("answer", "")
        self.assertIn("1,80,000", ans)
        self.assertNotIn("3,50,000", ans)
        self.assertIn("Page 2", ans)
        self.assertIn("Father's income: ₹1,20,000", ans)
        self.assertIn("Mother's income: ₹60,000", ans)

    # 6. Conflicting income sources trigger REVIEW
    def test_6_conflicting_income_sources_trigger_review(self):
        doc_conflict = {
            "id": "doc_test_old_002",
            "file_name": "Old_Certificate_2024.pdf",
            "document_type": "INCOME_CERTIFICATE",
            "is_active": True,
            "extracted_fields": {
                "annual_family_income": "240000"
            },
            "extracted_text": "--- [Page 1] ---\nAnnual Family Income: Rs. 2,40,000 /-"
        }
        data = self._post_chat(
            "What is my annual family income according to my documents?",
            documents=[self.doc_multi_page, doc_conflict]
        )
        ans = data.get("answer", "")
        self.assertIn("REVIEW", ans)
        self.assertIn("1,80,000", ans)
        self.assertIn("2,40,000", ans)

    # 7. Stale facts do not override active evidence
    def test_7_stale_facts_do_not_override_active_evidence(self):
        data = self._post_chat(
            "What is my annual family income?",
            applicant_facts={"annual_family_income": 350000, "income": 350000}
        )
        ans = data.get("answer", "")
        self.assertIn("1,80,000", ans)
        self.assertNotIn("3,50,000", ans)

    # 8. Deleted documents are excluded
    def test_8_deleted_documents_excluded(self):
        deleted_doc = {
            "id": "doc_deleted_999",
            "file_name": "Deleted_Doc.pdf",
            "is_active": False,
            "deleted_at": "2026-03-01T00:00:00Z",
            "extracted_fields": {"annual_family_income": "999999"}
        }
        data = self._post_chat(
            "What is my annual family income?",
            documents=[deleted_doc, self.doc_multi_page]
        )
        ans = data.get("answer", "")
        self.assertNotIn("999999", ans)
        self.assertIn("1,80,000", ans)

    # 9. Different query handlers return consistent values
    def test_9_different_query_handlers_return_consistent_values(self):
        data_page = self._post_chat("What information is on page 2?")
        ans_page = data_page.get("answer", "")

        data_fact = self._post_chat("What is my annual family income?")
        ans_fact = data_fact.get("answer", "")

        self.assertIn("1,80,000", ans_page)
        self.assertIn("1,80,000", ans_fact)

    # 10. Page 2 citations remain accurate
    def test_10_page_2_citations_remain_accurate(self):
        p_num = resolve_document_fact_page(self.doc_multi_page, "180000", "annual_family_income")
        self.assertEqual(p_num, 2)
        p_father = resolve_document_fact_page(self.doc_multi_page, "120000", "father_income")
        self.assertEqual(p_father, 2)
        p_name = resolve_document_fact_page(self.doc_multi_page, "Aarav Patel", "beneficiary_name")
        self.assertEqual(p_name, 1)

    # 11. Cross-applicant data isolation
    def test_11_cross_applicant_isolation(self):
        data = self._post_chat(
            "What is my full name?",
            applicant_id="tenant_user_B",
            documents=[],
            applicant_facts={"full_name": "Priya Sharma"}
        )
        ans = data.get("answer", "")
        self.assertIn("Priya Sharma", ans)
        self.assertNotIn("Aarav Patel", ans)

    # 12. Structured answers contain no raw Markdown leakage
    def test_12_structured_answers_no_raw_markdown_leakage(self):
        data = self._post_chat("What is my annual family income?")
        ans = data.get("answer", "")
        self.assertIn("**Annual Family Income**", ans)
        self.assertIn("**Source**", ans)
        self.assertIn("**Evidence status:**", ans)
        self.assertNotIn("--- [Page", ans)
        self.assertNotIn("SYNTHETIC TEST DOCUMENT", ans)

    # 13. Missing facts are reported as unavailable
    def test_13_missing_facts_reported_as_unavailable(self):
        data = self._post_chat("What is my pan card number?")
        ans = data.get("answer", "")
        self.assertTrue(
            "not mentioned or established in the document" in ans or "not available in your uploaded documents" in ans,
            msg=f"Expected unavailable notice, got: {ans}"
        )

    # 14. No fixed sample values in production logic (dynamic test with different applicant and amount)
    def test_14_no_fixed_sample_values(self):
        doc_dynamic = {
            "id": "doc_dyn_099",
            "file_name": "Income_Cert_Vikram.pdf",
            "is_active": True,
            "extracted_text": (
                "--- [Page 1] ---\n"
                "Applicant: Vikram Singh\n"
                "Certificate No: CERT-RAJ-7721\n"
                "--- [Page 2] ---\n"
                "Total Annual Family Income: Rs. 4,20,000 /-\n"
                "Father's Income: Rs. 3,00,000 /-\n"
            ),
            "extracted_fields": {
                "beneficiary_name": "Vikram Singh",
                "document_number": "CERT-RAJ-7721",
                "annual_family_income": "420000",
                "father_income": "300000"
            }
        }
        data_name = self._post_chat("What is my full name?", applicant_id="app_vikram", documents=[doc_dynamic])
        ans_name = data_name.get("answer", "")
        self.assertIn("Vikram Singh", ans_name)
        self.assertNotIn("Aarav", ans_name)

        data_inc = self._post_chat("What is my annual family income?", applicant_id="app_vikram", documents=[doc_dynamic])
        ans_inc = data_inc.get("answer", "")
        self.assertIn("4,20,000", ans_inc)
        self.assertNotIn("1,80,000", ans_inc)
        self.assertIn("Father's income: ₹3,00,000", ans_inc)

    # 15. Explicit Page 2 query mentioning income retrieves Page 2 and is NOT hijacked by ambiguity
    def test_15_explicit_page_2_query_mentioning_income(self):
        query = "Summarize the important information on Page 2 of my uploaded certificate, including the income assessment."
        data = self._post_chat(query, applicant_facts={"annual_income": "350000"})
        ans = data.get("answer", "")
        self.assertNotEqual(data.get("intent"), "CLARIFICATION_REQUIRED")
        self.assertNotIn("Which one would you like to review?", ans)
        self.assertIn("Page 2", ans)
        self.assertIn("1,80,000", ans)
        self.assertTrue(len(data.get("citations", [])) > 0)
        self.assertIn("Page 2", data["citations"][0].get("excerpt", ""))

    # 16. Explicit Page 3 query mentioning income retrieves Page 3 without ambiguity hijack
    def test_16_explicit_page_3_query_mentioning_income(self):
        doc_3_page = {
            "id": "doc_test_3page",
            "file_name": "Three_Page_Certificate.pdf",
            "document_type": "INCOME_CERTIFICATE",
            "is_active": True,
            "extracted_text": (
                "--- [Page 1] ---\nApplicant: Aarav Patel\n"
                "--- [Page 2] ---\nFamily Structure Details\n"
                "--- [Page 3] ---\nIncome Assessment Schedule:\nAnnual Family Income: Rs. 1,80,000 /-\n"
            ),
            "extracted_fields": {"annual_family_income": "180000"}
        }
        query = "What is mentioned on Page 3 regarding the income assessment?"
        data = self._post_chat(query, documents=[doc_3_page], applicant_facts={"annual_income": "350000"})
        ans = data.get("answer", "")
        self.assertNotIn("Which one would you like to review?", ans)
        self.assertIn("Page 3", ans)
        self.assertIn("1,80,000", ans)
        self.assertTrue(len(data.get("citations", [])) > 0)
        self.assertIn("Page 3", data["citations"][0].get("excerpt", ""))

    # 17. Standalone ambiguous income query still asks clarification
    def test_17_standalone_ambiguous_income_query_asks_clarification(self):
        # When user asks "What is my income?" without page or document context,
        # and both personal income (profile) and family income (document) exist with different values,
        # system must ask clarification.
        data = self._post_chat("What is my income?", applicant_facts={"annual_income": "350000"})
        ans = data.get("answer", "")
        self.assertEqual(data.get("intent"), "CLARIFICATION_REQUIRED")
        self.assertIn("Both personal annual income and family annual income are available in your records", ans)
        self.assertIn("Which one would you like to review?", ans)

    # 18. Personal income query remains distinct from family income
    def test_18_personal_income_distinct_from_family_income(self):
        data = self._post_chat("What is my personal income?", applicant_facts={"annual_family_income": 180000})
        ans = data.get("answer", "")
        self.assertIn("personal annual income is not available", ans)
        self.assertIn("Annual Family Income on File", ans)
        self.assertIn("1,80,000", ans)

    # 19. Family income query returns correct evidence-backed total
    def test_19_family_income_returns_evidence_backed_total(self):
        data = self._post_chat("What is my annual family income?", applicant_facts={"annual_income": "350000"})
        ans = data.get("answer", "")
        self.assertIn("1,80,000", ans)
        self.assertNotIn("3,50,000", ans)
        self.assertIn("Page 2", ans)

    # 20. Page-specific answer cites correct page provenance
    def test_20_page_specific_answer_cites_correct_page(self):
        query = "Summarize the important information on Page 2 of my uploaded certificate, including the income assessment."
        data = self._post_chat(query)
        citations = data.get("citations", [])
        self.assertTrue(len(citations) > 0)
        self.assertEqual(citations[0]["chunk_id"], "doc_test_aarav_001_page_2")
        self.assertIn("Page 2", citations[0]["excerpt"])

    # 21. Page-specific query does not return generic ambiguity response
    def test_21_page_query_does_not_return_generic_ambiguity(self):
        query = "Summarize Page 2 including the income assessment"
        data = self._post_chat(query, applicant_facts={"annual_income": "350000"})
        ans = data.get("answer", "")
        self.assertNotIn("Which one would you like to review?", ans)
        self.assertIn("Page 2", ans)

    # 22. Phase C2: Page 2 income summary includes total, distinct components, and assessment period
    def test_22_page_2_income_summary_structure(self):
        query = "Summarize Page 2 of my uploaded certificate, including the income assessment."
        data = self._post_chat(query)
        ans = data.get("answer", "")
        self.assertIn("**Income Breakdown**", ans)
        self.assertIn("Father's income: ₹1,20,000", ans)
        self.assertIn("Mother's income: ₹60,000", ans)
        self.assertIn("Total annual family income: ₹1,80,000", ans)
        self.assertIn("**Assessment Period**", ans)
        self.assertIn("**Source**", ans)
        self.assertIn("Page 2", ans)

    # 23. Phase C2: Table headings do not appear as orphan bullets
    def test_23_table_headings_not_orphan_bullets(self):
        query = "Summarize Page 2 of my uploaded certificate"
        data = self._post_chat(query)
        ans = data.get("answer", "")
        self.assertNotIn("Income Component", ans)
        self.assertNotIn("Contributing Household", ans)
        self.assertNotIn("Nature of Livelihood", ans)
        self.assertNotIn("Annual Amount", ans)

    # 24. Phase C2: Non-income document produces relevant summary and does not force income format
    def test_24_non_income_document_summary(self):
        doc_electricity = {
            "id": "doc_test_elec",
            "file_name": "Electricity_Bill.pdf",
            "document_type": "UTILITY_BILL",
            "is_active": True,
            "extracted_text": (
                "--- [Page 1] ---\n"
                "UTILITY BILL RECEIPT\n"
                "Consumer Name: Aarav Patel\n"
                "Consumer Account No: 10928374\n"
                "Bill Issue Date: 10 January 2026\n"
                "Total Amount: Rs. 1,450 /-\n"
            ),
            "extracted_fields": {
                "beneficiary_name": "Aarav Patel"
            }
        }
        data = self._post_chat("Summarize page 1 of my electricity bill", documents=[doc_electricity])
        ans = data.get("answer", "")
        self.assertIn("**Key Information**", ans)
        self.assertIn("Consumer Name: Aarav Patel", ans)
        self.assertNotIn("**Income Breakdown**", ans)
        self.assertIn("Electricity_Bill.pdf", ans)

    # 25. Phase C2: Provenance isolation ensures Page 1 identity facts are not inserted into Page 2 summary
    def test_25_provenance_isolation_no_cross_page_injection(self):
        query = "Summarize Page 2 of my uploaded certificate"
        data = self._post_chat(query)
        ans = data.get("answer", "")
        # Page 1 contains "Social Category: General / EWS" and "12 August 2004", Page 2 must NOT have them
        self.assertNotIn("Social Category", ans)
        self.assertNotIn("Date of Birth", ans)

    # 26. Phase C2: Conflicting evidence in page summary triggers REVIEW
    def test_26_conflicting_evidence_in_page_summary(self):
        doc_conflict = {
            "id": "doc_test_old_002",
            "file_name": "Old_Certificate_2024.pdf",
            "document_type": "INCOME_CERTIFICATE",
            "is_active": True,
            "extracted_fields": {
                "annual_family_income": "240000"
            },
            "extracted_text": "--- [Page 1] ---\nAnnual Family Income: Rs. 2,40,000 /-"
        }
        data = self._post_chat(
            "Summarize Page 2 of my uploaded certificate",
            documents=[self.doc_multi_page, doc_conflict]
        )
        ans = data.get("answer", "")
        self.assertIn("REVIEW REQUIRED — Conflicting Evidence Detected", ans)
        self.assertIn("1,80,000", ans)
        self.assertIn("2,40,000", ans)

    # 27. Phase C3: Assessment-period verification returns distinct fields and CONSISTENT result for matching dates/FY
    def test_27_assessment_period_verification_consistent(self):
        doc_with_dates = {
            "id": "doc_test_dates_001",
            "file_name": "FIN_Dated_Income_Certificate.pdf",
            "document_type": "INCOME_CERTIFICATE",
            "verification_status": "VERIFIED",
            "is_active": True,
            "extracted_text": (
                "--- [Page 1] ---\n"
                "Applicant: Aarav Patel\n\n"
                "--- [Page 2] ---\n"
                "Assessment Period: 1 April 2025 to 31 March 2026 (Financial Year 2025–2026)\n"
                "Total Annual Family Income: Rs. 1,80,000 /-\n"
            ),
            "extracted_fields": {
                "annual_family_income": "180000"
            }
        }
        query = "Verify the assessment period, exact dates, financial year, and consistency on Page 2 of my uploaded certificate."
        data = self._post_chat(query, documents=[doc_with_dates])
        ans = data.get("answer", "")
        self.assertIn("### Assessment Period Verification", ans)
        self.assertIn("Exact Source Start Date", ans)
        self.assertIn("1 April 2025", ans)
        self.assertIn("Exact Source End Date", ans)
        self.assertIn("31 March 2026", ans)
        self.assertIn("Financial Year as Stated", ans)
        self.assertIn("2025", ans)
        self.assertIn("Consistency Result", ans)
        self.assertIn("CONSISTENT", ans)
        self.assertIn("Page 2", ans)
        self.assertNotIn("**Income Breakdown**", ans)

    # 28. Phase C3: Conflicting date/FY values return REVIEW REQUIRED (CONFLICT)
    def test_28_assessment_period_verification_conflict(self):
        doc_conflict_dates = {
            "id": "doc_test_conflict_dates",
            "file_name": "Conflict_Dates.pdf",
            "document_type": "INCOME_CERTIFICATE",
            "is_active": True,
            "extracted_text": (
                "--- [Page 2] ---\n"
                "Assessment Period: 01 April 2022 to 31 March 2023 (Financial Year 2025–2026)\n"
                "Total Annual Family Income: Rs. 1,80,000 /-\n"
            ),
            "extracted_fields": {
                "annual_family_income": "180000"
            }
        }
        query = "Verify the assessment period, exact dates, financial year, and consistency on Page 2"
        data = self._post_chat(query, documents=[doc_conflict_dates])
        ans = data.get("answer", "")
        self.assertIn("REVIEW REQUIRED (CONFLICT)", ans)
        self.assertIn("01 April 2022", ans)
        self.assertIn("31 March 2023", ans)

    # 29. Phase C3: Missing dates return UNABLE TO VERIFY without inventing facts
    def test_29_assessment_period_verification_missing_dates(self):
        doc_missing_dates = {
            "id": "doc_test_no_dates",
            "file_name": "No_Dates.pdf",
            "document_type": "INCOME_CERTIFICATE",
            "is_active": True,
            "extracted_text": (
                "--- [Page 2] ---\n"
                "Financial Assessment Year: 2025-2026\n"
                "Total Annual Family Income: Rs. 1,80,000 /-\n"
            ),
            "extracted_fields": {
                "annual_family_income": "180000"
            }
        }
        query = "Verify the assessment period, exact dates, financial year, and consistency on Page 2"
        data = self._post_chat(query, documents=[doc_missing_dates])
        ans = data.get("answer", "")
        self.assertIn("Consistency Result", ans)
        self.assertIn("UNABLE TO VERIFY", ans)
        self.assertIn("Not specified in document", ans)

    # 30. Phase C3: Explicit income extraction enumerates individual vs consolidated total
    def test_30_explicit_income_extraction_individual_vs_total(self):
        query = "Enumerate every explicitly stated income amount, identify individual vs total income, and cite the source on Page 2."
        data = self._post_chat(query)
        ans = data.get("answer", "")
        self.assertIn("### Explicit Income Extraction", ans)
        self.assertIn("Father's Employment Income", ans)
        self.assertIn("Individual Contribution", ans)
        self.assertIn("Mother's Self-Employment Income", ans)
        self.assertIn("Total Annual Family Income", ans)
        self.assertIn("Consolidated Total", ans)
        self.assertIn("Page 2", ans)

    # 31. Phase C3: Missing income components are not fabricated as zero
    def test_31_explicit_income_extraction_no_fabricated_zero(self):
        single_earner_doc = {
            "id": "doc_test_single",
            "file_name": "Single_Earner.pdf",
            "document_type": "INCOME_CERTIFICATE",
            "is_active": True,
            "extracted_text": (
                "--- [Page 2] ---\n"
                "Father's Employment Income: Rs. 1,50,000 /-\n"
                "Total Annual Family Income: Rs. 1,50,000 /-\n"
            ),
            "extracted_fields": {
                "father_income": "150000",
                "annual_family_income": "150000"
            }
        }
        query = "Enumerate every explicitly stated income amount, identify individual vs total income, and cite the source on Page 2."
        data = self._post_chat(query, documents=[single_earner_doc])
        ans = data.get("answer", "")
        self.assertIn("Father's Employment Income", ans)
        self.assertIn("₹1,50,000", ans)
        self.assertIn("Total Annual Family Income", ans)
        self.assertNotIn("Mother", ans)
        self.assertNotIn("Other Household Sources", ans)

    # 32. Phase C3: Intent-aware response selection ensures different tasks return distinct contracts
    def test_32_intent_aware_contract_diversity(self):
        data_summary = self._post_chat("Summarize Page 2")
        data_verify = self._post_chat("Verify the assessment period and consistency on Page 2")
        data_enum = self._post_chat("Enumerate every explicitly stated income amount on Page 2")

        ans_summary = data_summary.get("answer", "")
        ans_verify = data_verify.get("answer", "")
        ans_enum = data_enum.get("answer", "")

        self.assertIn("**Page 2 — ", ans_summary)
        self.assertIn("### Assessment Period Verification", ans_verify)
        self.assertIn("### Explicit Income Extraction", ans_enum)

        self.assertNotEqual(ans_summary, ans_verify)
        self.assertNotEqual(ans_verify, ans_enum)

    # 33. Phase C3.2.1: Explicit zero in source remains zero and is identified as stated
    def test_33_explicit_zero_in_source_preserved_and_labeled(self):
        query = "What is other family income according to my document?"
        data = self._post_chat(query)
        ans = data.get("answer", "")
        self.assertIn("**Other Family Income**", ans)
        self.assertIn("₹0", ans)
        self.assertIn("Explicitly stated in document", ans)
        self.assertIn("Page 2", ans)

    # 34. Phase C3.2.1: Missing income component remains unavailable and is not assumed zero
    def test_34_missing_component_not_assumed_zero(self):
        single_doc = {
            "id": "doc_test_single_2",
            "file_name": "Single_Earner.pdf",
            "document_type": "INCOME_CERTIFICATE",
            "is_active": True,
            "extracted_text": (
                "--- [Page 2] ---\n"
                "Father's Employment Income: Rs. 1,50,000 /-\n"
                "Total Annual Family Income: Rs. 1,50,000 /-\n"
            ),
            "extracted_fields": {
                "father_income": "150000",
                "annual_family_income": "150000"
            }
        }
        query = "What is other family income according to my document?"
        data = self._post_chat(query, documents=[single_doc])
        ans = data.get("answer", "")
        self.assertIn("not specified", ans.lower())
        self.assertNotIn("₹0", ans)

    # 35. Phase C3.2.1: Explicit income extraction on document with zero source preserves ₹0 without calculation
    def test_35_explicit_income_extraction_zero_source_no_calculation(self):
        query = "Enumerate every explicitly stated income amount on Page 2"
        data = self._post_chat(query)
        ans = data.get("answer", "")
        self.assertIn("### Explicit Income Extraction", ans)
        self.assertIn("Other Family Income", ans)
        self.assertIn("₹0", ans)
        self.assertIn("Page 2", ans)


if __name__ == "__main__":
    unittest.main()



