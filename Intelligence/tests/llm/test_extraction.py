"""
Unit tests for applicant fact extraction and Phase 4 integration.
Enforces:
1. Candidate holds ONLY raw_value.
2. User statements map strictly to SELF_REPORTED.
3. Normalization is owned 100% by Phase 4.
"""

import unittest
import sys
from pathlib import Path

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.llm.client import LLMClient
from src.llm.config import LLMConfig
from src.llm.extraction import ApplicantFactExtractor
from src.extraction.models import FactVerificationStatus, ExtractionMethod
from src.documents.evidence import EvidenceRegistry


class TestApplicantFactExtraction(unittest.TestCase):

    def setUp(self):
        self.config = LLMConfig(provider="mock")
        self.client = LLMClient(config=self.config)
        self.extractor = ApplicantFactExtractor(llm_client=self.client)

    def test_english_fact_extraction(self):
        text = "My family income is 4.2 lakh and my age is 24."
        result = self.extractor.extract_candidates(text)
        
        # Verify candidates
        fields = {f.field: f for f in result.facts}
        self.assertIn("annual_family_income", fields)
        self.assertIn("age", fields)
        
        income_cand = fields["annual_family_income"]
        self.assertEqual(income_cand.raw_value, "4.2 lakh")
        self.assertEqual(income_cand.suggested_verification_status, FactVerificationStatus.SELF_REPORTED)

    def test_explicit_income_and_age_fact_extraction(self):
        """
        Explicit verification required by Phase 6 validation:
        'My family income is 4.2 lakh and I am 23 years old.'
        - raw_value for income = '4.2 lakh'
        - raw_value for age = '23 years'
        - Phase 4 performs normalization: 420000.0 and 23.
        """
        text = "My family income is 4.2 lakh and I am 23 years old."
        candidates = self.extractor.extract_candidates(text)
        
        fields = {f.field: f for f in candidates.facts}
        self.assertIn("annual_family_income", fields)
        self.assertIn("age", fields)
        
        self.assertEqual(fields["annual_family_income"].raw_value, "4.2 lakh")
        self.assertEqual(fields["age"].raw_value, "23 years")
        
        # Phase 4 normalization
        registry, registered_facts, warnings = self.extractor.register_facts_to_phase4(candidates)
        fact_map = {f.field: f for f in registered_facts}
        self.assertEqual(fact_map["annual_family_income"].normalized_value, 420000.0)
        self.assertEqual(fact_map["age"].normalized_value, 23)

    def test_hindi_fact_extraction(self):
        text = "मेरी उम्र 23 साल है और मेरी पारिवारिक आय 4.2 लाख रुपये है।"
        result = self.extractor.extract_candidates(text)
        
        fields = {f.field: f for f in result.facts}
        self.assertIn("annual_family_income", fields)
        self.assertIn("age", fields)
        self.assertEqual(fields["age"].raw_value, "23")

    def test_hinglish_fact_extraction(self):
        text = "meri age 35 hai aur main Gujarat mein rehta hoon"
        result = self.extractor.extract_candidates(text)
        
        fields = {f.field: f for f in result.facts}
        self.assertIn("age", fields)
        self.assertIn("state", fields)
        self.assertEqual(fields["state"].raw_value, "Gujarat")

    def test_phase4_normalization_ownership(self):
        text = "My family income is 4.2 lakh, age is 24, and I own 2 acres of land."
        candidates = self.extractor.extract_candidates(text)
        
        registry, registered_facts, warnings = self.extractor.register_facts_to_phase4(candidates)
        
        # Invariant: Phase 4 produces the normalized_values, NOT the LLM!
        fact_map = {f.field: f for f in registered_facts}
        
        self.assertIn("annual_family_income", fact_map)
        # Phase 4 normalizes 4.2 lakh to 420000.0
        self.assertEqual(fact_map["annual_family_income"].normalized_value, 420000.0)
        self.assertEqual(fact_map["annual_family_income"].verification_status, FactVerificationStatus.SELF_REPORTED)
        
        self.assertIn("age", fact_map)
        self.assertEqual(fact_map["age"].normalized_value, 24)
        
        self.assertIn("landholding_hectares", fact_map)
        # 2 acres ~ 0.809371 hectares
        self.assertAlmostEqual(fact_map["landholding_hectares"].normalized_value, 0.809371, places=3)

        # Build canonical profile directly consumable by Phase 3
        profile = registry.to_applicant_profile()
        self.assertEqual(profile.get_value("annual_family_income"), 420000.0)
        self.assertEqual(profile.get_value("age"), 24)


if __name__ == "__main__":
    unittest.main()
