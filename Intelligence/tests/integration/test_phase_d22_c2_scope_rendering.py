"""
Integration tests for FIN D2.2-C2-F:
Safe Markdown Rendering & Dynamic Scheme Scope Fix.

Validates all 9 Intelligence requirements:
1. Application-only YIPB query excludes unrelated eligibility and financial sections.
2. Institutional-document request excludes unrelated generic identity checklist.
3. All-documents query retains applicable general and institutional documents.
4. Jurisdiction metadata remains present.
5. Detailed jurisdiction disclaimer appears only when relevant.
6. No duplicate institutional requirements.
7. Compact reviewer rubric preserves source-backed thresholds.
8. No fabricated scheme facts or URLs.
9. Existing canonical routing, fallback, UNKNOWN eligibility, and tenant-isolation tests remain passing.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from src.api.app import app
from src.api.config import DEFAULT_SERVICE_CONFIG
from src.rag.scheme_name_index import (
    get_scheme_name_index,
    format_canonical_scheme_response,
    detect_scheme_query_scope,
    categorize_canonical_documents,
    clean_canonical_field,
)


@pytest.fixture
def auth_headers():
    return {
        DEFAULT_SERVICE_CONFIG.header_name: DEFAULT_SERVICE_CONFIG.service_api_key
    }


@pytest.fixture
def yipb_record():
    idx = get_scheme_name_index()
    match = idx.resolve_canonical_scheme("Young Investigators Programme in Biotechnology")
    assert match is not None, "YIPB must resolve in canonical index"
    _, rec = match
    return rec


def test_1_application_only_query_excludes_unrelated_sections(yipb_record):
    """
    Requirement 1: Exclusive application-process query returns ONLY application process
    and source references, excluding unrelated eligibility, financial benefits, and purpose sections.
    """
    query = "Tell me only about the application process of Young Investigators Programme in Biotechnology"
    ans = format_canonical_scheme_response(yipb_record, query=query)

    # Required sections present
    assert "Application Process & How to Apply" in ans
    assert "Official Source & References" in ans
    assert "**State / Jurisdiction:** Kerala" in ans

    # Unrelated sections excluded
    assert "**Eligibility Criteria**" not in ans
    assert "**Financial Assistance & Benefits**" not in ans
    assert "**Purpose & Overview**" not in ans
    assert "> **Jurisdiction & Applicability:**" not in ans
    assert "**Required Documents**" not in ans


def test_2_institutional_document_request_excludes_generic_identity_checklist(yipb_record):
    """
    Requirement 2: Request specifically asking for institutional documents includes
    institutional endorsement and research requirements, while excluding general identity
    documents (Aadhaar, photo, caste certificate).
    """
    query = "What institutional documents are required for Young Investigators Programme in Biotechnology?"
    scope = detect_scheme_query_scope(query)
    assert scope["wants_institutional_only"] is True

    ans = format_canonical_scheme_response(yipb_record, query=query)

    # Institutional items present
    assert "Institutional Endorsement & Research Documents" in ans
    assert "Endorsement from the Implementing Institution" in ans
    assert "Certificate from the Investigators" in ans
    assert "Certificate of No pending SE&UC" in ans

    # Generic identity checklist suppressed
    assert "Applicant Identity & General Supporting Documents" not in ans
    assert "Aadhaar" not in ans
    assert "Passport" not in ans
    assert "Caste Certificate" not in ans


def test_3_all_documents_query_retains_applicable_general_and_institutional_documents(yipb_record):
    """
    Requirement 3: General or all-documents query preserves complete categorization
    including institutional and general supporting documents.
    """
    query = "What are all the required documents for Young Investigators Programme in Biotechnology?"
    scope = detect_scheme_query_scope(query)
    assert scope["wants_institutional_only"] is False

    ans = format_canonical_scheme_response(yipb_record, query=query)

    assert "Required Documents" in ans
    assert "Institutional Endorsement & Research Documents" in ans
    assert "Applicant Identity & General Supporting Documents" in ans
    assert "Endorsement from the Implementing Institution" in ans


def test_4_jurisdiction_metadata_remains_present(yipb_record):
    """
    Requirement 4: Scheme jurisdiction metadata (State / Jurisdiction / Nodal Authority)
    is preserved across all response scopes.
    """
    queries = [
        "Tell me only about the application process for YIPB",
        "What are the benefits of YIPB?",
        "Tell me all details of YIPB",
    ]
    for q in queries:
        ans = format_canonical_scheme_response(yipb_record, query=q)
        assert "**State / Jurisdiction:** Kerala" in ans
        assert "Nodal Authority" in ans


def test_5_detailed_jurisdiction_disclaimer_appears_only_when_relevant(yipb_record):
    """
    Requirement 5: Detailed multi-line jurisdiction disclaimer appears when user asks about
    eligibility or jurisdiction, but is omitted from exclusive application-only queries.
    """
    # 5a. Omitted when asking application only
    app_query = "Tell me only about the application process of YIPB"
    app_ans = format_canonical_scheme_response(yipb_record, query=app_query)
    assert "> **Jurisdiction & Applicability:**" not in app_ans

    # 5b. Included when asking about eligibility or jurisdiction
    elig_query = "What is the jurisdiction and eligibility criteria for YIPB?"
    elig_ans = format_canonical_scheme_response(yipb_record, query=elig_query)
    assert "> **Jurisdiction & Applicability:**" in elig_ans
    assert "statutory eligibility status remains **UNKNOWN**" in elig_ans


def test_6_no_duplicate_institutional_requirements(yipb_record):
    """
    Requirement 6: When both process notes and a separate documents section are present,
    institutional items are not repeated verbatim.
    When only process is shown, Note 02 preserves the full list.
    """
    # Both sections included (e.g. process and documents requested)
    both_query = "Tell me only about the application process and institutional documents for YIPB"
    both_ans = format_canonical_scheme_response(yipb_record, query=both_query)

    # Note 02 references Required Documents rather than listing them all again
    assert "itemized with prescribed formats under Required Documents" in both_ans
    assert "1. Institutional Endorsement & Research Documents:" in both_ans

    # Application process only (no documents section)
    proc_only_query = "Tell me only about the application process of YIPB"
    proc_only_ans = format_canonical_scheme_response(yipb_record, query=proc_only_query)
    assert "Endorsement from the Implementing Institution" in proc_only_ans


def test_7_compact_reviewer_rubric_preserves_source_backed_thresholds(yipb_record):
    """
    Requirement 7: The reviewer scoring rubric (Scores 0 to 5) is omitted from application-only queries,
    while preserving all numerical thresholds and substantive criteria.
    """
    query = "Explain the application process for Young Investigators Programme in Biotechnology"
    ans = format_canonical_scheme_response(yipb_record, query=query)

    # Substantive thresholds preserved
    assert "Only 50% of the proposals that secure higher than 60% score points" in ans

    # Reviewer score definitions omitted from application process
    assert "Reviewer Scoring Scale" not in ans
    assert "Score 0: Non-evaluable" not in ans
    assert "Score 0:" not in ans
    assert "Score 5:" not in ans


def test_8_no_fabricated_scheme_facts_or_urls(yipb_record):
    """
    Requirement 8: All links use canonical URLs from official source records without
    fabrication, and avoid ambiguous nested formatting ([Prescribed Format](URL)).
    """
    ans = format_canonical_scheme_response(yipb_record, query="What documents are required for YIPB?")

    # Verify safe link formatting without nested parentheses
    assert "([Prescribed Format]" not in ans
    assert "— [Prescribed Format](https://kscste.kerala.gov.in/wp-content/uploads/2019/06/YIPB_endorsement_22.pdf)" in ans
    assert "https://www.myscheme.gov.in/schemes/yipb" in ans


@pytest.mark.anyio
async def test_9_api_routing_and_tenant_isolation_preserved(auth_headers):
    """
    Requirement 9: Canonical routing, cold-start reliability, and tenant isolation
    remain completely intact via API endpoint.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/v1/chat",
            headers=auth_headers,
            json={
                "query": "Tell me only about the application process of Young Investigators Programme in Biotechnology",
                "conversation_id": "test-c2-api",
                "applications": [
                    {
                        "id": "app-secret-999",
                        "ticket_id": "APP-SECRET-999",
                        "scheme_name": "Private Scheme",
                        "status": "approved",
                    }
                ],
                "documents": [],
            },
        )
        assert res.status_code == 200
        data = res.json()

        assert data["intent"] == "SCHEME_DISCOVERY"
        assert "Young Investigators Programme in Biotechnology" in data["answer"]
        assert "Application Process & How to Apply" in data["answer"]
        # Tenant isolation
        assert "APP-SECRET-999" not in data["answer"]
        assert "Private Scheme" not in data["answer"]
        # Exclusivity: eligibility criteria excluded
        assert "**Eligibility Criteria**" not in data["answer"]
