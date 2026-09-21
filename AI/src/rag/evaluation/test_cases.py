"""
PolicySetu Evaluation Test Cases.
Curated ground-truth test queries mapped to authoritative scheme slugs.
Covers English, Hindi, Hinglish, state-filtered, and FAQ-derived retrieval targets.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class RetrievalTestCase:
    """Represents a single offline benchmark query with expected ground truth."""
    query_id: str
    query_text: str
    expected_scheme_slug: str
    query_type: str  # "exact_name", "faq_derived", "hindi", "hinglish", "benefit", "state_filtered"
    language: str = "en"
    state_filter: Optional[str] = None
    description: str = ""


# Ground-truth evaluation test set using real scheme slugs present in canonical schemes
EVALUATION_TEST_CASES: List[RetrievalTestCase] = [
    # 1. Exact Scheme Name Queries
    RetrievalTestCase(
        query_id="EN_EXACT_01",
        query_text="Atal Pension Yojana",
        expected_scheme_slug="apy",
        query_type="exact_name",
        description="Exact search for national pension scheme"
    ),
    RetrievalTestCase(
        query_id="EN_EXACT_02",
        query_text="Pradhan Mantri Matru Vandana Yojana",
        expected_scheme_slug="pmmvy",
        query_type="exact_name",
        description="Exact search for maternity benefit scheme"
    ),
    RetrievalTestCase(
        query_id="EN_EXACT_03",
        query_text="PM Street Vendor AtmaNirbhar Nidhi",
        expected_scheme_slug="pm-svanidhi",
        query_type="exact_name",
        description="Exact search for urban street vendor loan scheme"
    ),

    # 2. FAQ-Derived Questions
    RetrievalTestCase(
        query_id="FAQ_01",
        query_text="What is the monthly pension amount under Atal Pension Yojana?",
        expected_scheme_slug="apy",
        query_type="faq_derived",
        description="FAQ regarding APY pension amounts"
    ),
    RetrievalTestCase(
        query_id="FAQ_02",
        query_text="Who is eligible for maternity financial assistance of 5000 rupees?",
        expected_scheme_slug="pmmvy",
        query_type="faq_derived",
        description="FAQ regarding PMMVY maternity benefits"
    ),
    RetrievalTestCase(
        query_id="FAQ_03",
        query_text="How much working capital loan can a street vendor get without collateral?",
        expected_scheme_slug="pm-svanidhi",
        query_type="faq_derived",
        description="FAQ regarding SVANidhi microcredit"
    ),

    # 3. Hindi Queries
    RetrievalTestCase(
        query_id="HI_01",
        query_text="अटल पेंशन योजना के तहत न्यूनतम पेंशन क्या है?",
        expected_scheme_slug="apy",
        query_type="hindi",
        language="hi",
        description="Hindi query on APY pension"
    ),
    RetrievalTestCase(
        query_id="HI_02",
        query_text="गर्भवती महिलाओं के लिए सरकारी आर्थिक सहायता योजना",
        expected_scheme_slug="pmmvy",
        query_type="hindi",
        language="hi",
        description="Hindi query on pregnancy financial support"
    ),
    RetrievalTestCase(
        query_id="HI_03",
        query_text="स्ट्रीट वेंडर के लिए बिना गारंटी लोन",
        expected_scheme_slug="pm-svanidhi",
        query_type="hindi",
        language="hi",
        description="Hindi query on collateral-free vendor credit"
    ),

    # 4. Hinglish / Code-Mixed Queries
    RetrievalTestCase(
        query_id="HINGLISH_01",
        query_text="mujhe old age pension ke liye atal pension yojana me apply karna hai",
        expected_scheme_slug="apy",
        query_type="hinglish",
        language="hi-en",
        description="Hinglish inquiry for elderly pension"
    ),
    RetrievalTestCase(
        query_id="HINGLISH_02",
        query_text="pregnant mahilaon ke liye 5000 rs maternity benefit scheme",
        expected_scheme_slug="pmmvy",
        query_type="hinglish",
        language="hi-en",
        description="Hinglish inquiry for maternity scheme"
    ),
    RetrievalTestCase(
        query_id="HINGLISH_03",
        query_text="thela lagane wale street vendors ke liye 10000 loan scheme",
        expected_scheme_slug="pm-svanidhi",
        query_type="hinglish",
        language="hi-en",
        description="Hinglish inquiry for vendor loan"
    ),

    # 5. State-Filtered Queries
    RetrievalTestCase(
        query_id="STATE_01",
        query_text="housing subsidy for permanent residents of Assam",
        expected_scheme_slug="aag",
        query_type="state_filtered",
        state_filter="Assam",
        description="Assam Aponar Apon Ghar housing subsidy"
    ),
    RetrievalTestCase(
        query_id="STATE_02",
        query_text="financial assistance for pregnant women in Karnataka",
        expected_scheme_slug="mj-fapm",
        query_type="state_filtered",
        state_filter="Karnataka",
        description="Karnataka Matru Jyothi scheme"
    ),
]
