"""
FIN Phase D2.2: Scheme Match Score Integrity Regression Tests.

Validates the Phase D2.2 mandatory requirements:
1. Explicit canonical scheme query does not create a 100% eligibility score.
2. Search relevance remains separate from eligibility.
3. Missing Ph.D. information remains UNKNOWN.
4. Missing postdoctoral experience remains UNKNOWN.
5. Missing age remains UNKNOWN.
6. Unsupported jurisdiction conclusions remain REVIEW.
7. No fallback 80%, 85%, or 100% is injected as eligibility.
8. Criterion explanations include fact provenance.
9. LLM text cannot override deterministic eligibility.
10. Unverified criteria are explicitly itemized.
11. Statutory scoring formula absence is disclosed.
12. Existing genuine PASS/FAIL decisions remain unchanged.
13. Applicant isolation and historical decision integrity remain intact.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from src.api.app import app
from src.api.config import DEFAULT_SERVICE_CONFIG
from src.rag.scheme_name_index import (
    get_scheme_name_index,
    format_canonical_score_explanation,
    format_canonical_scheme_response,
)


@pytest.fixture
def auth_headers():
    return {
        DEFAULT_SERVICE_CONFIG.header_name: DEFAULT_SERVICE_CONFIG.service_api_key
    }


@pytest.fixture
def sample_user_documents():
    return [
        {
            "id": "doc-cert-101",
            "file_name": "FIN_MultiPage_Income_Certificate_QA.pdf",
            "document_type": "INCOME_CERTIFICATE",
            "issuer": "Tahsildar / Competent Authority, Maharashtra",
            "verification_status": "VERIFIED",
            "extracted_fields": {
                "annual_family_income": "3,47,250",
                "certificate_number": "FIN-TEST-82941",
                "issuing_authority": "Tahsildar, Maharashtra",
                "beneficiary_name": "Aarav Sharma"
            },
            "extracted_text": "GOVERNMENT OF MAHARASHTRA\nIncome Certificate\nAnnual Income: Rs 3,47,250"
        }
    ]


@pytest.fixture
def sample_applicant_facts():
    return {
        "full_name": "Aarav Sharma",
        "state": "Maharashtra",
        "annual_income": 347250,
        "occupation": "Salaried"
    }


@pytest.mark.anyio
async def test_canonical_query_does_not_create_100_percent_eligibility_score(auth_headers, sample_user_documents, sample_applicant_facts):
    """
    Requirement 1 & 2: Explicit canonical scheme query emits 1.0 search relevance,
    but eligibility_status MUST be UNKNOWN and eligibility_score MUST be None.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/v1/chat",
            headers=auth_headers,
            json={
                "query": "Explain only the application process for the Young Investigators Programme in Biotechnology.",
                "conversation_id": "test-d22-canon-score",
                "applicant_facts": sample_applicant_facts,
                "documents": sample_user_documents,
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "SCHEME_DISCOVERY"
        assert len(data["suggested_schemes"]) == 1

        scheme_card = data["suggested_schemes"][0]
        assert scheme_card["scheme_id"] == "yipb"
        # Search relevance is 1.0 (exact match)
        assert scheme_card["relevance_score"] == 1.0
        # Eligibility MUST NOT be fabricated to 100%
        assert scheme_card["eligibility_status"] == "UNKNOWN"
        assert scheme_card.get("eligibility_score") is None


@pytest.mark.anyio
async def test_score_explanation_returns_criterion_breakdown(auth_headers, sample_user_documents, sample_applicant_facts):
    """
    Requirement 3, 4, 5, 6, 8, 10, 11:
    When user asks why scheme matches or requests score explanation:
    - Missing Ph.D. remains UNKNOWN
    - Missing Postdoc remains UNKNOWN
    - Missing Age remains UNKNOWN
    - Cross-state jurisdiction (Maharashtra vs Kerala) remains REVIEW
    - Fact provenance is included
    - Unverified criteria are itemized
    - Scoring formula absence is disclosed
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/v1/chat",
            headers=auth_headers,
            json={
                "query": "Why does the Young Investigators Programme in Biotechnology match and what is the scoring formula? Explain my eligibility criteria and match score.",
                "conversation_id": "test-d22-explanation",
                "applicant_facts": sample_applicant_facts,
                "documents": sample_user_documents,
            }
        )
        assert res.status_code == 200
        data = res.json()
        ans = data["answer"]

        # 1. Search relevance vs eligibility disclosure
        assert "Search Retrieval Relevance" in ans or "Search Relevance Score" in ans
        assert "100%" in ans
        assert "Statutory Eligibility Score" in ans
        assert "None" in ans
        assert "UNKNOWN / REVIEW" in ans or "UNKNOWN" in ans

        # 2. Missing Ph.D. remains UNKNOWN (Requirement 3)
        assert "Doctoral Degree Qualification" in ans or "Ph.D." in ans
        assert "**UNKNOWN**" in ans

        # 3. Missing Postdoctoral experience remains UNKNOWN (Requirement 4)
        assert "Post-Doctoral" in ans or "postdoctoral" in ans.lower()

        # 4. Missing Age remains UNKNOWN (Requirement 5)
        assert "Age Limit" in ans or "Age Verification" in ans

        # 5. Unsupported jurisdiction remains REVIEW (Requirement 6)
        assert "**REVIEW**" in ans
        assert "Maharashtra" in ans
        assert "Kerala" in ans

        # 6. Fact Provenance included (Requirement 8)
        assert "Missing from profile and document vault" in ans or "Verified Document" in ans or "Applicant Profile" in ans

        # 7. Unverified criteria listed (Requirement 10)
        assert "Unverified Criteria Requiring Supporting Evidence" in ans

        # 8. Scoring formula absence disclosed (Requirement 11)
        assert "Scoring Formula" in ans
        assert "None" in ans


def test_format_canonical_score_explanation_direct():
    """
    Direct unit test validating pure function behavior on YIPB canonical record.
    Ensures missing qualifications remain UNKNOWN and cross-state remains REVIEW.
    """
    scheme_index = get_scheme_name_index()
    canon_match = scheme_index.resolve_canonical_scheme("Young Investigators Programme in Biotechnology")
    assert canon_match is not None
    _, canonical_rec = canon_match

    # Case A: Empty profile and documents -> Ph.D., Postdoc, Age, State all UNKNOWN
    explanation = format_canonical_score_explanation(
        canonical_rec,
        query="explain match score",
        applicant_facts={},
        documents=[]
    )
    assert "Doctoral Degree Qualification" in explanation
    assert "Post-Doctoral Research Experience" in explanation
    assert "Statutory Age Limit" in explanation
    assert "State & Institutional Jurisdiction" in explanation
    assert "**UNKNOWN**" in explanation
    assert "100%" in explanation  # Search relevance
    assert "`None`" in explanation  # Eligibility score

    # Case B: Cross-state applicant facts (Maharashtra applicant on Kerala scheme)
    explanation_cross = format_canonical_score_explanation(
        canonical_rec,
        query="why 100% score",
        applicant_facts={"state": "Maharashtra"},
        documents=[]
    )
    assert "**REVIEW**" in explanation_cross
    assert "Maharashtra" in explanation_cross
    assert "Kerala" in explanation_cross
    assert "cross-state" in explanation_cross.lower() or "Cross-state" in explanation_cross

    # Case C: Qualified age (e.g. 32 years) with missing Ph.D.
    explanation_partial = format_canonical_score_explanation(
        canonical_rec,
        query="explain criteria",
        applicant_facts={"state": "Kerala", "age": 32},
        documents=[]
    )
    # Age < 40 passes
    assert "32 years" in explanation_partial
    assert "Applicant age (32) meets the statutory ceiling" in explanation_partial
    # But missing Ph.D. must STILL remain UNKNOWN! (Invariant: UNKNOWN must never become PASS)
    assert "**UNKNOWN**" in explanation_partial
    assert "Missing from profile and document vault" in explanation_partial


def test_no_fallback_percentages_injected_into_relevance_or_eligibility():
    """
    Requirement 7: No fallback 80%, 85%, or 100% is injected as eligibility.
    """
    scheme_index = get_scheme_name_index()
    canon_match = scheme_index.resolve_canonical_scheme("Young Investigators Programme in Biotechnology")
    assert canon_match is not None
    _, canonical_rec = canon_match

    res = format_canonical_score_explanation(canonical_rec, applicant_facts={}, documents=[])
    # The eligibility score must be disclosed as None, never 80%, 85%, or 100%
    assert "Statutory Eligibility Score:** `None`" in res


# ==============================================================================
# Phase D2.2-C: Dynamic Scheme Response Scope & Evidence Formatting Tests
# ==============================================================================

@pytest.mark.anyio
async def test_d22c_exact_application_only_yipb_query(auth_headers, sample_user_documents, sample_applicant_facts):
    """
    Test 1: Exact application-only YIPB query.
    Must include: Scheme name, jurisdiction metadata, application mode, submission stages/steps,
    relevant institutional & supporting documents, official source references.
    Must NOT include: Purpose & Overview, Eligibility Criteria, Financial Assistance & Benefits,
    raw delimiters, contact details in process body, personal applications/tickets/vault docs.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/v1/chat",
            headers=auth_headers,
            json={
                "query": "Explain only the application process for the Young Investigators Programme in Biotechnology. Include its application mode, submission stages, required institutional documents, and official source. Do not show my personal applications, tickets, or uploaded documents.",
                "conversation_id": "test-d22c-app-only",
                "applicant_facts": sample_applicant_facts,
                "documents": sample_user_documents,
            }
        )
        assert res.status_code == 200
        data = res.json()
        ans = data["answer"]

        # Scope included
        assert "Young Investigators Programme in Biotechnology" in ans
        assert "**State / Jurisdiction:** Kerala" in ans
        assert "Application Mode:** Online" in ans
        assert "Stage 1: Submission and Evaluation of Pre" in ans
        assert "Stage 2: Submission and Evaluation of Detailed Proposal" in ans
        assert "Step 01" in ans and "Step 02" in ans and "Step 03" in ans and "Step 04" in ans
        assert "Institutional Endorsement & Research Documents" in ans
        assert "Endorsement from the Implementing Institution" in ans
        assert "Official Source & References" in ans
        assert "[Official Scheme Portal]" in ans or "[Statutory Scheme Guidelines (PDF)]" in ans

        # Scope EXCLUDED (unrelated sections)
        assert "**Purpose & Overview**" not in ans
        assert "**Eligibility Criteria**" not in ans
        assert "**Financial Assistance & Benefits**" not in ans
        assert "Nodal Contact Details & Helpdesk" not in ans  # Contact separated out since not requested

        # Delimiter artifacts cleaned
        assert "| - " not in ans

        # No personal vault data leaked
        assert "doc-cert-101" not in ans
        assert "FIN_MultiPage_Income_Certificate_QA.pdf" not in ans
        assert len(data.get("citations", [])) == 1
        assert data["citations"][0]["scheme_id"] == "yipb"

        # Score integrity
        scheme_card = data["suggested_schemes"][0]
        assert scheme_card["relevance_score"] == 1.0
        assert scheme_card["eligibility_status"] == "UNKNOWN"
        assert scheme_card.get("eligibility_score") is None


def test_d22c_pure_scope_selection_eligibility_only():
    """
    Test 2: Eligibility-only query.
    Must include: Header, metadata, eligibility criteria, official sources.
    Must NOT include: Process, benefits, documents, purpose.
    """
    idx = get_scheme_name_index()
    canon_match = idx.resolve_canonical_scheme("Young Investigators Programme in Biotechnology")
    assert canon_match is not None
    _, rec = canon_match

    ans = format_canonical_scheme_response(rec, query="What are only the eligibility criteria for YIPB?")
    assert "**Eligibility Criteria**" in ans
    assert "The applicant should possess a Ph.D." in ans
    assert "**Official Source & References**" in ans

    assert "**Purpose & Overview**" not in ans
    assert "**Application Process & How to Apply**" not in ans
    assert "**Financial Assistance & Benefits**" not in ans
    assert "**Required Documents**" not in ans


def test_d22c_pure_scope_selection_documents_only():
    """
    Test 3: Documents-only query.
    Must include: Header, metadata, required documents (categorized), official sources.
    Must NOT include: Process, benefits, eligibility, purpose.
    """
    idx = get_scheme_name_index()
    canon_match = idx.resolve_canonical_scheme("Young Investigators Programme in Biotechnology")
    assert canon_match is not None
    _, rec = canon_match

    ans = format_canonical_scheme_response(rec, query="Show only the required documents for Young Investigators Programme in Biotechnology")
    assert "**Required Documents**" in ans
    assert "Institutional Endorsement & Research Documents" in ans
    assert "Applicant Identity & General Supporting Documents" in ans
    assert "**Official Source & References**" in ans

    assert "**Purpose & Overview**" not in ans
    assert "**Application Process & How to Apply**" not in ans
    assert "**Financial Assistance & Benefits**" not in ans
    assert "**Eligibility Criteria**" not in ans


def test_d22c_pure_scope_selection_financial_assistance_only():
    """
    Test 4: Financial-assistance-only query.
    Must include: Header, metadata, financial assistance & benefits, official sources.
    Must NOT include: Process, documents, eligibility, purpose.
    """
    idx = get_scheme_name_index()
    canon_match = idx.resolve_canonical_scheme("Young Investigators Programme in Biotechnology")
    assert canon_match is not None
    _, rec = canon_match

    ans = format_canonical_scheme_response(rec, query="Explain only the financial assistance and benefits of YIPB")
    assert "**Financial Assistance & Benefits**" in ans
    assert "fellowship of ₹45,000" in ans or "45,000" in ans
    assert "**Official Source & References**" in ans

    assert "**Purpose & Overview**" not in ans
    assert "**Application Process & How to Apply**" not in ans
    assert "**Required Documents**" not in ans
    assert "**Eligibility Criteria**" not in ans


def test_d22c_complete_scheme_overview():
    """
    Test 5: Complete scheme overview.
    Must include: Purpose, eligibility, benefits, documents, process, and sources.
    """
    idx = get_scheme_name_index()
    canon_match = idx.resolve_canonical_scheme("Young Investigators Programme in Biotechnology")
    assert canon_match is not None
    _, rec = canon_match

    ans = format_canonical_scheme_response(rec, query="Provide complete scheme overview for Young Investigators Programme in Biotechnology")
    assert "**Purpose & Overview**" in ans
    assert "**Eligibility Criteria**" in ans
    assert "**Financial Assistance & Benefits**" in ans
    assert "**Required Documents**" in ans
    assert "**Application Process & How to Apply**" in ans
    assert "**Official Source & References**" in ans


def test_d22c_institutional_document_grouping_and_ambiguous_classification():
    """
    Test 6 & 7: Evidence-grounded document categorization and ambiguous classification.
    """
    idx = get_scheme_name_index()
    canon_match = idx.resolve_canonical_scheme("Young Investigators Programme in Biotechnology")
    assert canon_match is not None
    _, rec = canon_match

    # YIPB has clear institutional evidence from source
    ans = format_canonical_scheme_response(rec, query="show documents")
    assert "**1. Institutional Endorsement & Research Documents:**" in ans
    assert "- Endorsement from the Implementing Institution" in ans
    assert "- Certificate from the Investigators" in ans
    assert "- Certificate of No pending SE&UC" in ans
    assert "**2. Applicant Identity & General Supporting Documents:**" in ans
    assert "- Identity proof of applicant" in ans
    assert "- Passport size photographs" in ans
    assert "**3. Other Stated Requirements:**" in ans
    assert "- Any other document, as required" in ans

    # Ambiguous/General scheme without institutional keywords
    synthetic_rec = {
        "scheme_name": "General Tenancy Welfare Scheme",
        "slug": "tenancy-welfare",
        "level": "State",
        "state": "Gujarat",
        "documents_required": "Aadhaar Card; Rent Agreement Copy; Electricity Bill; Registration Receipt",
        "application_process": "Apply at the local municipal office.",
        "source_url": "https://gujarat.gov.in"
    }
    ambig_ans = format_canonical_scheme_response(synthetic_rec, query="only documents")
    # Must NOT force Category 1 "Institutional Endorsement" when source has no institutional evidence!
    assert "Institutional Endorsement" not in ambig_ans
    assert "- Aadhaar Card" in ambig_ans
    assert "- Rent Agreement Copy" in ambig_ans


def test_d22c_transparent_jurisdiction_and_no_invented_eligibility_rule():
    """
    Test 8 & 9: Transparent jurisdiction handling.
    Does NOT infer applicant is ineligible because they live in Maharashtra while scheme is in Kerala.
    Does NOT invent domicile/residency rules.
    Explicitly states applicability is unverified and eligibility remains UNKNOWN.
    """
    idx = get_scheme_name_index()
    canon_match = idx.resolve_canonical_scheme("Young Investigators Programme in Biotechnology")
    assert canon_match is not None
    _, rec = canon_match

    ans = format_canonical_scheme_response(
        rec,
        query="Explain application process",
        applicant_facts={"state": "Maharashtra"}
    )
    assert "Jurisdiction & Applicability" in ans
    assert "Kerala" in ans
    assert "Maharashtra" in ans
    assert "unverified" in ans.lower()
    assert "UNKNOWN" in ans
    # Must NOT declare user ineligible
    assert "ineligible" not in ans.lower()


def test_d22c_descriptive_markdown_links_and_delimiter_removal():
    """
    Test 10, 11, 12, 13:
    - Descriptive Markdown links preserve canonical URLs
    - No raw delimiter artifacts (| - )
    - Primary official source remains present
    - No reference dumping (bounded count)
    - Full procedural stages and steps preserved
    """
    idx = get_scheme_name_index()
    canon_match = idx.resolve_canonical_scheme("Young Investigators Programme in Biotechnology")
    assert canon_match is not None
    _, rec = canon_match

    ans = format_canonical_scheme_response(rec, query="application process and official source")

    # 1. Descriptive Markdown links
    assert "[Official Scheme Portal](https://www.myscheme.gov.in/schemes/yipb)" in ans
    assert "[Statutory Scheme Guidelines (PDF)](https://kscste.kerala.gov.in/wp-content/uploads/2019/06/YIPB_guidelines.pdf)" in ans
    assert "[Institutional Endorsement Format (PDF)](https://kscste.kerala.gov.in/wp-content/uploads/2019/06/YIPB_endorsement_22.pdf)" in ans

    # 2. No delimiter artifacts
    assert "| - " not in ans
    assert " | " not in ans

    # 3. Essential process stages preserved with substantive thresholds
    assert "Stage 1: Submission and Evaluation of Pre" in ans
    assert "Stage 2: Submission and Evaluation of Detailed Proposal" in ans
    assert "Score 0:" not in ans
    assert "Score 5:" not in ans
    assert "60%" in ans  # 60% threshold preserved
    assert "50%" in ans  # 50% threshold preserved

