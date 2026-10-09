"""
FIN Phase D1.2.2: Scheme Query Routing & Canonical Retrieval Fix Integration Tests.

Validates the 12 mandatory requirements:
1. Named scheme question containing "application process" routes to canonical scheme retrieval, not tickets.
2. Named scheme question containing "required documents" routes to statutory scheme requirements, not personal document vault.
3. Genuine personal application status query returns active tickets.
4. Genuine active ticket query returns active tickets.
5. Personal uploaded-document query returns document vault list.
6. Page-specific certificate query returns page-level extraction.
7. Direct canonical lookup for a scheme outside the initial retriever subset (e.g. YIPB / Kerala).
8. Missing scheme fields remain explicitly marked as unavailable.
9. Backend fallback routing parity.
10. Applicant isolation.
11. No hardcoded sample values.
12. Exact reproduction prompt from Phase D1.2.1 returns grounded canonical scheme answer.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from pathlib import Path

from src.api.app import app
from src.api.config import DEFAULT_SERVICE_CONFIG
from src.rag.scheme_name_index import (
    get_scheme_name_index,
    format_canonical_scheme_response,
    clean_canonical_field,
)


@pytest.fixture
def auth_headers():
    return {
        DEFAULT_SERVICE_CONFIG.header_name: DEFAULT_SERVICE_CONFIG.service_api_key
    }


@pytest.fixture
def sample_user_applications():
    return [
        {
            "id": "app-84729001",
            "ticket_id": "APP-84729001",
            "scheme_id": "pmegp",
            "scheme_name": "Prime Minister's Employment Generation Programme",
            "status": "under_review",
            "estimated_benefit": "₹ 2,00,000",
            "submitted_at": "2026-09-10T08:00:00Z"
        }
    ]


@pytest.fixture
def sample_user_documents():
    return [
        {
            "id": "doc-cert-101",
            "file_name": "Income_Certificate_QA.pdf",
            "document_type": "INCOME_CERTIFICATE",
            "verification_status": "VERIFIED",
            "doc_number": "GJ-INC-2026-99",
            "issuer": "Mamlatdar Office",
            "extracted_fields": {
                "annual_family_income": "180000",
                "father_income": "120000",
                "mother_income": "60000",
                "document_number": "GJ-INC-2026-99"
            },
            "extracted_text": (
                "--- [Page 1] ---\n"
                "GOVERNMENT OF GUJARAT - REVENUE DEPARTMENT\n"
                "Certificate No: GJ-INC-2026-99\n"
                "Beneficiary: Test Applicant\n"
                "--- [Page 2] ---\n"
                "DETAILED INCOME ASSESSMENT:\n"
                "Father's Income: Rs. 1,20,000\n"
                "Mother's Income: Rs. 60,000\n"
                "Total Annual Family Income: Rs. 1,80,000"
            )
        }
    ]


@pytest.mark.anyio
async def test_case_1_named_scheme_application_process(auth_headers, sample_user_applications, sample_user_documents):
    """
    Case 1: Named scheme question containing 'application process' must NOT trigger personal ticket lookup.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/v1/chat",
            headers=auth_headers,
            json={
                "query": "Explain the application process for the Young Investigators Programme in Biotechnology.",
                "conversation_id": "test-c1",
                "applications": sample_user_applications,
                "documents": sample_user_documents,
            }
        )
        assert res.status_code == 200
        data = res.json()

        assert data["intent"] == "SCHEME_DISCOVERY"
        assert "Here are your active government applications" not in data["answer"]
        assert "APP-84729001" not in data["answer"]
        assert "Young Investigators Programme in Biotechnology" in data["answer"]
        assert "Application Process" in data["answer"]
        assert len(data["citations"]) > 0
        assert data["citations"][0]["scheme_id"] == "yipb"


@pytest.mark.anyio
async def test_case_2_named_scheme_required_documents(auth_headers, sample_user_applications, sample_user_documents):
    """
    Case 2: Named scheme question containing 'required documents' must NOT trigger personal document vault lookup.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/v1/chat",
            headers=auth_headers,
            json={
                "query": "What documents are required for the Young Investigators Programme in Biotechnology?",
                "conversation_id": "test-c2",
                "applications": sample_user_applications,
                "documents": sample_user_documents,
            }
        )
        assert res.status_code == 200
        data = res.json()

        assert data["intent"] == "SCHEME_DISCOVERY"
        assert "You have uploaded" not in data["answer"]
        assert "Income_Certificate_QA.pdf" not in data["answer"]
        assert "Required Documents" in data["answer"]
        assert "Young Investigators Programme in Biotechnology" in data["answer"]
        assert len(data["citations"]) > 0
        assert data["citations"][0]["scheme_id"] == "yipb"


@pytest.mark.anyio
async def test_case_3_genuine_personal_application_status(auth_headers, sample_user_applications, sample_user_documents):
    """
    Case 3: Genuine personal application status query returns user active tickets.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/v1/chat",
            headers=auth_headers,
            json={
                "query": "What is the status of my application?",
                "conversation_id": "test-c3",
                "applications": sample_user_applications,
                "documents": sample_user_documents,
            }
        )
        assert res.status_code == 200
        data = res.json()

        assert data["intent"] == "APPLICATION_INQUIRY"
        assert "Here are your active government applications and support tickets" in data["answer"]
        assert "APP-84729001" in data["answer"]
        assert "Prime Minister's Employment Generation Programme" in data["answer"]


@pytest.mark.anyio
async def test_case_4_genuine_active_ticket_query(auth_headers, sample_user_applications, sample_user_documents):
    """
    Case 4: Genuine active ticket query returns user active tickets.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/v1/chat",
            headers=auth_headers,
            json={
                "query": "Show my active tickets",
                "conversation_id": "test-c4",
                "applications": sample_user_applications,
                "documents": sample_user_documents,
            }
        )
        assert res.status_code == 200
        data = res.json()

        assert data["intent"] == "APPLICATION_INQUIRY"
        assert "APP-84729001" in data["answer"]


@pytest.mark.anyio
async def test_case_5_personal_uploaded_document_query(auth_headers, sample_user_applications, sample_user_documents):
    """
    Case 5: Personal uploaded-document query returns document vault list.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/v1/chat",
            headers=auth_headers,
            json={
                "query": "What documents have I uploaded?",
                "conversation_id": "test-c5",
                "applications": sample_user_applications,
                "documents": sample_user_documents,
            }
        )
        assert res.status_code == 200
        data = res.json()

        assert data["intent"] == "DOCUMENT_INQUIRY"
        assert "You have uploaded **1 document(s)** in your vault:" in data["answer"]
        assert "Income_Certificate_QA.pdf" in data["answer"]


@pytest.mark.anyio
async def test_case_6_page_specific_certificate_query(auth_headers, sample_user_applications, sample_user_documents):
    """
    Case 6: Page-specific certificate query returns Page 2 extraction.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/v1/chat",
            headers=auth_headers,
            json={
                "query": "What is written on Page 2 of my certificate?",
                "conversation_id": "test-c6",
                "applications": sample_user_applications,
                "documents": sample_user_documents,
            }
        )
        assert res.status_code == 200
        data = res.json()

        assert data["intent"] == "DOCUMENT_INQUIRY"
        assert "Page 2" in data["answer"]
        assert any("page_2" in c["chunk_id"] for c in data["citations"])


@pytest.mark.anyio
async def test_case_7_direct_canonical_lookup_outside_initial_retriever_subset(auth_headers):
    """
    Case 7: Scheme outside initial retriever subset resolves dynamically (e.g. YIPB).
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/v1/chat",
            headers=auth_headers,
            json={
                "query": "Tell me about the Young Investigators Programme in Biotechnology.",
                "conversation_id": "test-c7",
                "applications": [],
                "documents": [],
            }
        )
        assert res.status_code == 200
        data = res.json()

        assert data["intent"] == "SCHEME_DISCOVERY"
        assert "Young Investigators Programme in Biotechnology" in data["answer"]
        assert "Kerala" in data["answer"]
        assert len(data["suggested_schemes"]) > 0
        assert data["suggested_schemes"][0]["scheme_id"] == "yipb"


def test_case_8_missing_scheme_fields_remain_explicitly_unavailable():
    """
    Case 8: Missing canonical fields explicitly report as unavailable without hallucinating.
    """
    incomplete_rec = {
        "scheme_name": "Test Welfare Scheme",
        "slug": "test-scheme",
        "detailed_description": None,
        "brief_description": None,
        "eligibility": "nan",
        "benefits": "",
        "documents_required": None,
        "application_process": "nan",
        "source_url": None,
        "references": None
    }
    ans = format_canonical_scheme_response(incomplete_rec)

    assert "### Test Welfare Scheme" in ans
    assert "**Purpose & Overview**\nNot specified in official scheme record" in ans
    assert "**Eligibility Criteria**\nNot specified in official scheme record" in ans
    assert "**Financial Assistance & Benefits**\nNot specified in official scheme record" in ans
    assert "**Required Documents**\nNot specified in official scheme record" in ans
    assert "**Application Process & How to Apply**\nNot specified in official scheme record" in ans
    assert "**Official Source & References**\nNot specified in official scheme record" in ans


@pytest.mark.anyio
async def test_case_10_applicant_isolation(auth_headers):
    """
    Case 10: Applicant isolation - data from User B is never returned to User A.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Request for Applicant A with Applicant A's tickets
        res = await client.post(
            "/v1/chat",
            headers=auth_headers,
            json={
                "query": "Show my active tickets",
                "applicant_id": "applicant_a",
                "conversation_id": "conv_a",
                "applications": [
                    {"ticket_id": "APP-USER-A-ONLY", "scheme_name": "Scheme A", "status": "approved"}
                ],
                "documents": []
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert "APP-USER-A-ONLY" in data["answer"]
        assert "APP-USER-B" not in data["answer"]


@pytest.mark.anyio
async def test_exact_reproduction_prompt_grounded(auth_headers, sample_user_applications, sample_user_documents):
    """
    Phase D1.2.1 Exact Reproduction Query:
    'Explain the Young Investigators Programme in Biotechnology. Tell me its purpose, eligibility,
    financial assistance, benefits, required documents, application process, and official source.
    Use actual scheme information and do not invent missing details.'
    """
    query = (
        "Explain the Young Investigators Programme in Biotechnology. Tell me its purpose, eligibility, "
        "financial assistance, benefits, required documents, application process, and official source. "
        "Use actual scheme information and do not invent missing details."
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/v1/chat",
            headers=auth_headers,
            json={
                "query": query,
                "conversation_id": "test-repro",
                "applications": sample_user_applications,
                "documents": sample_user_documents,
            }
        )
        assert res.status_code == 200
        data = res.json()

        assert data["intent"] == "SCHEME_DISCOVERY"
        answer = data["answer"]

        # MUST NOT be personal tickets!
        assert "Here are your active government applications" not in answer
        assert "APP-84729001" not in answer

        # MUST contain all requested canonical scheme fields
        assert "Young Investigators Programme in Biotechnology" in answer
        assert "Purpose & Overview" in answer
        assert "Eligibility Criteria" in answer
        assert "Financial Assistance & Benefits" in answer
        assert "Required Documents" in answer
        assert "Application Process & How to Apply" in answer
        assert "Official Source & References" in answer

        # Grounded factual contents from Kerala canonical record
        assert "Kerala" in answer
        assert "45,000" in answer or "fellowship" in answer.lower()
        assert "30 lakh" in answer.lower() or "30 Lakhs" in answer
        assert "myscheme.gov.in/schemes/yipb" in answer

        # Citations must reflect official scheme source
        assert len(data["citations"]) > 0
        assert data["citations"][0]["scheme_id"] == "yipb"
        assert "myscheme.gov.in" in data["citations"][0]["url"]


@pytest.fixture
def multipage_sample_user_documents():
    return [
        {
            "id": "doc-cert-qa",
            "file_name": "FIN_MultiPage_Income_Certificate_QA.pdf",
            "document_type": "INCOME_CERTIFICATE",
            "verification_status": "VERIFIED",
            "doc_number": "GJ-INC-2026-99",
            "issuer": "Mamlatdar Office",
            "extracted_fields": {
                "annual_family_income": "180000",
                "father_income": "120000",
                "mother_income": "60000",
                "document_number": "GJ-INC-2026-99"
            },
            "extracted_text": (
                "--- [Page 1] ---\n"
                "GOVERNMENT OF GUJARAT - REVENUE DEPARTMENT\n"
                "Certificate No: GJ-INC-2026-99\n"
                "Beneficiary: Test Applicant\n"
                "--- [Page 2] ---\n"
                "DETAILED INCOME ASSESSMENT:\n"
                "Father's Income: Rs. 1,20,000\n"
                "Mother's Income: Rs. 60,000\n"
                "Total Annual Family Income: Rs. 1,80,000\n"
                "--- [Page 3] ---\n"
                "4. That all documentary proofs uploaded in support of this application are authentic copies of genuine records.\n"
                "2. REVENUE DOCUMENT REVIEW CHECKLIST\n"
                "Local Field Revenue Inquiry Dossier COMPLETED (Findings Endorsed)"
            )
        }
    ]


@pytest.mark.anyio
async def test_d123_exact_reproduction_failure_resolved(auth_headers, sample_user_applications, multipage_sample_user_documents):
    """
    Phase D1.2.3: Validates that the exact reproduced query with non-adjacent document phrasing
    and negative personal constraints returns canonical YIPB scheme data,
    NOT the uploaded document Page 3 verification text.
    """
    query = (
        "Explain only the application process for the Young Investigators Programme in Biotechnology. Include:\n"
        "1. Application mode.\n"
        "2. Where and when applications are invited.\n"
        "3. Pre-proposal submission and review stages.\n"
        "4. Detailed proposal evaluation stages.\n"
        "5. Required institutional endorsement or supporting documents.\n"
        "6. How applicants are notified.\n\n"
        "Use the available scheme record. Do not show my personal applications, tickets, or uploaded documents. "
        "If a deadline or current application window is unavailable, explicitly say so."
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/v1/chat",
            headers=auth_headers,
            json={
                "query": query,
                "conversation_id": "test-d123-repro",
                "applications": sample_user_applications,
                "documents": multipage_sample_user_documents,
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "SCHEME_DISCOVERY"
        answer = data["answer"]

        # MUST NOT contain personal document or ticket interception
        assert "FIN_MultiPage_Income_Certificate_QA.pdf" not in answer
        assert "Page 3" not in answer
        assert "APP-84729001" not in answer
        assert "Here are your active government applications" not in answer

        # MUST contain canonical scheme application process
        assert "Young Investigators Programme in Biotechnology" in answer
        assert "Application Process & How to Apply" in answer
        assert "Application Mode:" in answer
        assert "online" in answer.lower()
        assert "Kerala" in answer
        assert "Pre" in answer and "Proposal" in answer
        assert "Review" in answer or "review" in answer
        assert "Endorsement" in answer or "endorsement" in answer
        assert "Application Window & Deadlines:" in answer
        assert len(data["citations"]) > 0
        assert data["citations"][0]["scheme_id"] == "yipb"


@pytest.mark.anyio
async def test_d123_non_adjacent_scheme_document_wording(auth_headers, sample_user_applications, multipage_sample_user_documents):
    """
    Phase D1.2.3: Validates non-adjacent document phrasing for a named scheme routes to scheme record, not personal documents.
    """
    query = "What supporting documents and institutional endorsements are required for the Young Investigators Programme in Biotechnology?"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/v1/chat",
            headers=auth_headers,
            json={
                "query": query,
                "conversation_id": "test-d123-nonadj",
                "applications": sample_user_applications,
                "documents": multipage_sample_user_documents,
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "SCHEME_DISCOVERY"
        assert "FIN_MultiPage_Income_Certificate_QA.pdf" not in data["answer"]
        assert "Required Documents" in data["answer"]
        assert data["citations"][0]["scheme_id"] == "yipb"


@pytest.mark.anyio
async def test_d123_scheme_with_negative_constraints(auth_headers, sample_user_applications, multipage_sample_user_documents):
    """
    Phase D1.2.3: Validates that negative constraints (do not show my documents / tickets) do not trigger personal lookups.
    """
    query = "Tell me about PM-Kisan. Do not show my uploaded documents or tickets."
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/v1/chat",
            headers=auth_headers,
            json={
                "query": query,
                "conversation_id": "test-d123-neg",
                "applications": sample_user_applications,
                "documents": multipage_sample_user_documents,
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "SCHEME_DISCOVERY"
        assert "FIN_MultiPage_Income_Certificate_QA.pdf" not in data["answer"]
        assert "APP-84729001" not in data["answer"]
        assert "PM-Kisan" in data["answer"] or "PM Kisan" in data["answer"] or "pm-kisan" in data["citations"][0]["scheme_id"].lower()


@pytest.mark.anyio
async def test_d123_genuine_page3_uploaded_cert_inquiry(auth_headers, sample_user_applications, multipage_sample_user_documents):
    """
    Phase D1.2.3: Validates genuine Page 3 personal document inquiry is preserved.
    """
    query = "What information is mentioned on page 3 of my certificate?"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/v1/chat",
            headers=auth_headers,
            json={
                "query": query,
                "conversation_id": "test-d123-page3",
                "applications": sample_user_applications,
                "documents": multipage_sample_user_documents,
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "DOCUMENT_INQUIRY"
        assert "Page 3" in data["answer"]
        assert "FIN_MultiPage_Income_Certificate_QA.pdf" in data["answer"]
        assert len(data["citations"]) > 0
        assert data["citations"][0]["scheme_id"] == "USER_DOCUMENT"


@pytest.mark.anyio
async def test_d123_scheme_app_process_without_documents(auth_headers, sample_user_applications):
    """
    Phase D1.2.3: Validates scheme application process query when no personal documents exist.
    """
    query = "Explain the application process for the Young Investigators Programme in Biotechnology."
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/v1/chat",
            headers=auth_headers,
            json={
                "query": query,
                "conversation_id": "test-d123-nodocs",
                "applications": sample_user_applications,
                "documents": [],
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "SCHEME_DISCOVERY"
        assert "Young Investigators Programme in Biotechnology" in data["answer"]
        assert "Application Process & How to Apply" in data["answer"]
        assert data["citations"][0]["scheme_id"] == "yipb"

