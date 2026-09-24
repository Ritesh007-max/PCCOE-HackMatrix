"""
Unit tests for ambiguity detection.
Tests approximate amounts, missing units, entity confusion, and residence vs domicile.
"""

import unittest
import sys
from pathlib import Path

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.nlp.ambiguity import AmbiguityDetector
from src.llm.models import AmbiguityType


class TestAmbiguityDetector(unittest.TestCase):

    def setUp(self):
        self.detector = AmbiguityDetector()

    def test_approximate_value_detection(self):
        texts = [
            "My income is around 4 lakh per year",
            "lagbhag 2 acre zameen hai",
            "मेरी आय लगभग 3 लाख है",
            "I have approximately 50000 annual income",
        ]
        for t in texts:
            ambiguities = self.detector.detect_ambiguities(t)
            types = [a.ambiguity_type for a in ambiguities]
            self.assertIn(AmbiguityType.APPROXIMATE_VALUE, types, f"Failed for: {t}")

    def test_missing_land_unit_detection(self):
        texts = [
            "I own land in my village",
            "mere paas zameen hai",
            "मेरे पास ज़मीन है",
        ]
        for t in texts:
            ambiguities = self.detector.detect_ambiguities(t)
            types = [a.ambiguity_type for a in ambiguities]
            self.assertIn(AmbiguityType.MISSING_UNIT, types, f"Failed for: {t}")

    def test_land_with_explicit_units_not_flagged_as_missing_unit(self):
        text = "I own 2 acres of land"
        ambiguities = self.detector.detect_ambiguities(text)
        types = [a.ambiguity_type for a in ambiguities]
        self.assertNotIn(AmbiguityType.MISSING_UNIT, types)

    def test_entity_confusion_family_member(self):
        texts = [
            "My father is a farmer in Uttar Pradesh",
            "mere pitaji kisan hain",
            "मेरे पिता किसान हैं",
        ]
        for t in texts:
            ambiguities = self.detector.detect_ambiguities(t)
            types = [a.ambiguity_type for a in ambiguities]
            self.assertIn(AmbiguityType.ENTITY_CONFUSION, types, f"Failed for: {t}")

    def test_temporary_residence_detection(self):
        texts = [
            "I live in Gujarat currently",
            "main abhi Pune mein rehta hoon",
            "currently staying in Mumbai",
        ]
        for t in texts:
            ambiguities = self.detector.detect_ambiguities(t)
            types = [a.ambiguity_type for a in ambiguities]
            self.assertIn(AmbiguityType.TEMPORARY_RESIDENCE, types, f"Failed for: {t}")


if __name__ == "__main__":
    unittest.main()
