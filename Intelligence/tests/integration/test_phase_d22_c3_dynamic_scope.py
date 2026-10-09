"""
Integration tests for FIN D2.2-C3:
Dynamic Response Scope Refinement.

Validates the 9 mandatory requirements:
1. YIPB application-only query excludes detailed evaluation rubric paragraph descriptions and unrelated sections.
2. YIPB selection-criteria query includes source-backed detailed scoring rubric.
3. YIPB complete overview returns comprehensive information.
4. Documents-only query returns strictly document categories.
5. Financial-assistance-only query returns strictly benefits and financial assistance.
6. Another canonical scheme with different application structure (PM-Kisan) works dynamically.
7. No loss of mandatory application conditions or substantive thresholds.
8. No invented deadlines, requirements, or URLs.
9. Existing routing, fallback, security, and UNKNOWN eligibility remain passing.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from src.api.app import app
from src.api.config import DEFAULT_SERVICE_CONFIG
from src.rag.scheme_name_index import (
    get_scheme_name_index,
    format_canonical_scheme_response,
    detect_scheme_query_scope,
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


@pytest.fixture
def pm_kisan_record():
    idx = get_scheme_name_index()
    match = idx.resolve_canonical_scheme("PM-Kisan")
    assert match is not None, "PM-Kisan must resolve in canonical index"
    _, rec = match
    return rec


def test_1_yipb_application_only_query(yipb_record):
    """
    Requirement 1: YIPB application-only query includes application mode, window,
    submission stages, institutional requirements, essential conditions, and official references;
    omits lengthy reviewer scoring descriptions and unrelated sections.
    """
    query = "Tell me only about the application process of Young Investigators Programme in Biotechnology"
    ans = format_canonical_scheme_response(yipb_record, query=query)

    # Must include
    assert "**Application Mode:** Online" in ans
    assert "Application Window & Deadlines:" in ans
    assert "Stage 1: Submission and Evaluation of Pre" in ans
    assert "Stage 2: Submission and Evaluation of Detailed Proposal" in ans
    assert "Official Source & References" in ans
    assert "https://www.myscheme.gov.in/schemes/yipb" in ans

    # Must preserve substantive thresholds
    assert "Only 50% of the proposals that secure higher than 60% score points" in ans

    # Must NOT include reviewer score-level definitions or scales
    assert "Reviewer Scoring Scale" not in ans
    assert "Score 0:" not in ans
    assert "Score 5:" not in ans

    # Must condense reviewer counts, evaluation-matrix descriptions, and referee logistics
    assert "3 subject experts" not in ans
    assert "Evaluation Matrix containing 7 criteria" not in ans
    assert "sent to five national-level experts" not in ans
    assert "The reviewers will assign suitable scores" not in ans

    # Must retain the fact that proposals undergo expert review and committee consideration
    assert "subject experts for peer review" in ans
    assert "placed in the Programme Advisory Committee" in ans

    # Must preserve PI/Co-I presentation obligation while condensing committee governance
    assert "The PI/Co-Is will be invited to present the proposal before the PAC" in ans
    assert "PAC is a high-level Committee" not in ans

    # Must NOT include lengthy paragraph descriptions
    assert "The criterion is inadequately addressed and there are serious inherent weaknesses" not in ans
    assert "Broadly addresses the criterion, but there are serious inherent weaknesses" not in ans
    assert "The proposal addresses the criterion well, no shortcomings as such are found" not in ans

    # Must NOT include unrelated sections
    assert "**Eligibility Criteria**" not in ans
    assert "**Financial Assistance & Benefits**" not in ans
    assert "**Purpose & Overview**" not in ans
    assert "> **Jurisdiction & Applicability:**" not in ans


def test_2_yipb_selection_criteria_query(yipb_record):
    """
    Requirement 2: When the user explicitly requests evaluation criteria or scoring rubric,
    the full source-backed detailed rubric and reviewer workflow details are returned.
    """
    query = "What are the selection criteria and evaluation rubric for Young Investigators Programme in Biotechnology?"
    scope = detect_scheme_query_scope(query)
    assert scope["wants_scoring"] is True

    ans = format_canonical_scheme_response(yipb_record, query=query)

    # Detailed scoring rubric present
    assert "Reviewer Scoring Rubric (Detailed Criteria):" in ans
    assert "Score 0:" in ans and "Fails to address the criteria" in ans
    assert "Score 1:" in ans and "Poor: The criterion is inadequately addressed" in ans
    assert "Score 2:" in ans and "Fair: Broadly addresses the criterion" in ans
    assert "Score 3:" in ans and "Good: The proposal addresses the criterion well" in ans
    assert "Score 4:" in ans and "Very Good: The proposal addresses the criterion well" in ans
    assert "Score 5:" in ans and "Excellent: The proposal addresses the criterion well" in ans

    # Full reviewer details retained on explicit evaluation query
    assert "3 subject experts" in ans
    assert "Evaluation Matrix containing 7 criteria" in ans
    assert "five national-level experts" in ans

    # Substantive thresholds retained
    assert "Only 50% of the proposals that secure higher than 60% score points" in ans


def test_3_yipb_complete_overview(yipb_record):
    """
    Requirement 3: Complete overview query returns all major sections.
    """
    query = "Give me a complete overview of Young Investigators Programme in Biotechnology"
    scope = detect_scheme_query_scope(query)
    assert scope["is_broad_overview"] is True

    ans = format_canonical_scheme_response(yipb_record, query=query)

    assert "**Purpose & Overview**" in ans
    assert "**Eligibility Criteria**" in ans
    assert "**Financial Assistance & Benefits**" in ans
    assert "**Required Documents**" in ans
    assert "**Application Process & How to Apply**" in ans
    assert "**Official Source & References**" in ans
    assert "**State / Jurisdiction:** Kerala" in ans


def test_4_documents_only_query(yipb_record):
    """
    Requirement 4: Documents-only query returns strictly document categories.
    """
    query = "Tell me only about the required documents for Young Investigators Programme in Biotechnology"
    scope = detect_scheme_query_scope(query)
    assert scope["is_exclusive"] is True
    assert scope["wants_documents"] is True

    ans = format_canonical_scheme_response(yipb_record, query=query)

    assert "**Required Documents**" in ans
    assert "Institutional Endorsement & Research Documents" in ans
    assert "**Official Source & References**" in ans

    assert "**Application Process & How to Apply**" not in ans
    assert "**Eligibility Criteria**" not in ans
    assert "**Financial Assistance & Benefits**" not in ans
    assert "**Purpose & Overview**" not in ans


def test_5_financial_assistance_only_query(yipb_record):
    """
    Requirement 5: Financial-assistance-only query returns strictly benefits and funding.
    """
    query = "Tell me only about the financial assistance and benefits under Young Investigators Programme in Biotechnology"
    scope = detect_scheme_query_scope(query)
    assert scope["is_exclusive"] is True
    assert scope["wants_benefits"] is True

    ans = format_canonical_scheme_response(yipb_record, query=query)

    assert "**Financial Assistance & Benefits**" in ans
    assert "**Official Source & References**" in ans

    assert "**Application Process & How to Apply**" not in ans
    assert "**Eligibility Criteria**" not in ans
    assert "**Required Documents**" not in ans
    assert "**Purpose & Overview**" not in ans


def test_6_another_canonical_scheme_different_structure(pm_kisan_record):
    """
    Requirement 6: Dynamic formatting across a different canonical scheme (PM-Kisan).
    PM-Kisan has 7 sequential VLE/CSC steps without complex reviewer rubrics.
    """
    query = "Tell me only about the application process for PM-Kisan"
    ans = format_canonical_scheme_response(pm_kisan_record, query=query)

    assert "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)" in ans
    assert "Central" in ans
    assert "**Application Mode:**" in ans
    assert "Step 1" in ans
    assert "Step 7" in ans
    assert "https://www.myscheme.gov.in/schemes/pm-kisan" in ans

    # Unrelated sections excluded
    assert "**Financial Assistance & Benefits**" not in ans
    assert "**Eligibility Criteria**" not in ans
    assert "**Purpose & Overview**" not in ans


def test_7_no_loss_of_mandatory_application_conditions(yipb_record):
    """
    Requirement 7: Essential submission conditions and rules are never discarded.
    """
    ans = format_canonical_scheme_response(
        yipb_record,
        query="Tell me only about the application process of Young Investigators Programme in Biotechnology"
    )

    # Note 01: Mandatory online mode condition
    assert "Proposals under this programme shall be submitted online only" in ans
    # PAC presentation stage
    assert "Programme Advisory Committee" in ans or "PAC" in ans
    # Cutoff percentage threshold
    assert "higher than 60% score points" in ans
    # Top 50% selection quota
    assert "Only 50% of the proposals" in ans


def test_8_no_invented_deadlines_or_requirements(yipb_record):
    """
    Requirement 8: All dates, requirements, and URLs strictly derive from canonical record.
    Zero hallucinated URLs or dummy text.
    """
    ans = format_canonical_scheme_response(yipb_record, query="What is the application process for YIPB?")

    # Canonical URLs only
    assert "https://www.myscheme.gov.in/schemes/yipb" in ans
    assert "https://kscste.kerala.gov.in/wp-content/uploads/2019/06/YIPB_guidelines.pdf" in ans
    assert "https://kscste.kerala.gov.in/wp-content/uploads/2019/06/YIPB_endorsement_22.pdf" in ans

    # No dummy domains or placeholders
    assert "example.com" not in ans
    assert "placeholder" not in ans
    assert "dummy" not in ans


@pytest.mark.anyio
async def test_9_existing_routing_fallback_security_and_unknown_eligibility(auth_headers):
    """
    Requirement 9: API endpoint routing, tenant isolation, and UNKNOWN eligibility integrity.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/v1/chat",
            headers=auth_headers,
            json={
                "query": "Tell me only about the application process of Young Investigators Programme in Biotechnology",
                "conversation_id": "test-c3-api",
                "applicant_facts": {"state": "Maharashtra"},
                "applications": [
                    {
                        "id": "app-isolated-001",
                        "ticket_id": "APP-ISOLATED-001",
                        "scheme_name": "Isolated Scheme",
                        "status": "pending",
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
        assert "APP-ISOLATED-001" not in data["answer"]
        assert "Isolated Scheme" not in data["answer"]

        # Statutory eligibility check
        suggested = data.get("suggested_schemes", [])
        assert len(suggested) > 0
        assert suggested[0]["scheme_id"] == "yipb"
        assert suggested[0]["eligibility_status"] == "UNKNOWN"
        assert suggested[0].get("eligibility_score") is None


def test_10_browser_reproduction_application_and_institutional_docs(yipb_record):
    """
    Requirement 8: Reproduces the exact browser test query:
    'Tell me only about the application process and institutional documents for Young Investigators Programme in Biotechnology.'
    """
    query = "Tell me only about the application process and institutional documents for Young Investigators Programme in Biotechnology."
    ans = format_canonical_scheme_response(yipb_record, query=query)

    # Required content
    assert "**Application Mode:** Online" in ans
    assert "Stage 1: Submission and Evaluation of Pre" in ans
    assert "Stage 2: Submission and Evaluation of Detailed Proposal" in ans
    assert "Institutional Endorsement & Research Documents" in ans
    assert "Only 50% of the proposals that secure higher than 60% score points" in ans

    # Must preserve PI/Co-I presentation obligation
    assert "The PI/Co-Is will be invited to present the proposal before the PAC" in ans

    # Must retain expert review and committee placement
    assert "subject experts for peer review" in ans
    assert "placed in the Programme Advisory Committee" in ans

    # Must NOT contain reviewer rubric, scoring scale, or score entries
    assert "Reviewer Scoring Scale" not in ans
    assert "Score 0:" not in ans
    assert "Score 5:" not in ans

    # Must NOT contain reviewer-only counts, referee logistics, or matrix detail
    assert "3 subject experts" not in ans
    assert "Evaluation Matrix containing 7 criteria" not in ans
    assert "sent to five national-level experts" not in ans
    assert "The reviewers will assign suitable scores" not in ans

    # Must NOT contain internal committee boilerplate
    assert "PAC is a high-level Committee" not in ans

    # Institutional documents listed once
    assert ans.count("Institutional Endorsement & Research Documents") == 1

    # Unrelated sections excluded
    assert "**Eligibility Criteria**" not in ans
    assert "**Financial Assistance & Benefits**" not in ans
    assert "**Purpose & Overview**" not in ans


def test_11_another_scheme_preserves_application_requirements():
    """
    Requirement 9: Proves another scheme (e.g. TARE or PM-Kisan) is not accidentally stripped
    of relevant application requirements.
    """
    idx = get_scheme_name_index()
    match = idx.resolve_canonical_scheme("Teachers Associateship for Research Excellence")
    assert match is not None
    _, tare_rec = match

    query = "Tell me only about the application process for TARE"
    ans = format_canonical_scheme_response(tare_rec, query=query)

    assert "Teachers Associateship for Research Excellence (TARE)" in ans
    assert "**Application Mode:** Online" in ans
    assert "**Application Window & Deadlines:**" in ans
    assert "Official Source & References" in ans
    assert "https://www.myscheme.gov.in/schemes/tare" in ans

    # Unrelated sections excluded
    assert "**Financial Assistance & Benefits**" not in ans
    assert "**Eligibility Criteria**" not in ans
    assert "**Purpose & Overview**" not in ans

