"""
Unit tests for PolicySetu Normalization and Validation Layer.
Verifies parsing of INR currency, denominations, demographics, booleans, and domain bounds.
"""

import unittest
import sys
from pathlib import Path

_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from src.normalization.normalizer import (
    normalize_inr,
    normalize_age,
    normalize_gender,
    normalize_state,
    normalize_social_category,
    normalize_boolean,
    normalize_percentage,
    normalize_landholding,
    normalize_occupation,
    normalize_field_value,
)
from src.normalization.validators import (
    ValidationError,
    validate_age,
    validate_income,
    validate_percentage,
    validate_landholding,
    validate_residency_years,
    validate_pension,
    validate_field_value,
)


class TestNormalizer(unittest.TestCase):
    """Tests normalizer functions across all supported domains."""

    def test_inr_normalization_basic(self):
        """Tests standard currency formats and delimiters."""
        self.assertEqual(normalize_inr("420000"), 420000.0)
        self.assertEqual(normalize_inr("4,20,000"), 420000.0)
        self.assertEqual(normalize_inr("₹4,20,000"), 420000.0)
        self.assertEqual(normalize_inr("Rs. 250000"), 250000.0)
        self.assertEqual(normalize_inr("INR 65,000"), 65000.0)
        self.assertEqual(normalize_inr("Rs 1,50,000/-"), 150000.0)
        self.assertEqual(normalize_inr(350000), 350000.0)

    def test_lakh_crore_conversions(self):
        """Tests Indian numerical multipliers (lakh, lac, crore, k)."""
        # Lakh / Lac (100,000)
        self.assertEqual(normalize_inr("2.5 lakh"), 250000.0)
        self.assertEqual(normalize_inr("2.50 lac"), 250000.0)
        self.assertEqual(normalize_inr("1.5 Lakhs"), 150000.0)
        self.assertEqual(normalize_inr("Rs. 4.2 Lakh"), 420000.0)

        # Crore (10,000,000)
        self.assertEqual(normalize_inr("1 crore"), 10000000.0)
        self.assertEqual(normalize_inr("0.5 Cr"), 5000000.0)
        self.assertEqual(normalize_inr("2 Cr."), 20000000.0)
        self.assertEqual(normalize_inr("₹ 1.2 Crores"), 12000000.0)

        # Thousand / K (1,000)
        self.assertEqual(normalize_inr("50 thousand"), 50000.0)
        self.assertEqual(normalize_inr("50k"), 50000.0)

    def test_age_normalization(self):
        """Tests chronological age parsing from numbers and natural text."""
        self.assertEqual(normalize_age("25"), 25)
        self.assertEqual(normalize_age("25 years"), 25)
        self.assertEqual(normalize_age("25 yrs"), 25)
        self.assertEqual(normalize_age("age: 34"), 34)
        self.assertEqual(normalize_age("34 years old"), 34)
        self.assertEqual(normalize_age(40), 40)
        self.assertEqual(normalize_age(40.2), 40)
        self.assertIsNone(normalize_age(None))
        self.assertIsNone(normalize_age(""))

    def test_gender_normalization(self):
        """Tests gender canonicalization."""
        self.assertEqual(normalize_gender("Male"), "Male")
        self.assertEqual(normalize_gender("M"), "Male")
        self.assertEqual(normalize_gender("man"), "Male")
        self.assertEqual(normalize_gender("Female"), "Female")
        self.assertEqual(normalize_gender("f"), "Female")
        self.assertEqual(normalize_gender("woman"), "Female")
        self.assertEqual(normalize_gender("Transgender"), "Transgender")
        self.assertEqual(normalize_gender("trans"), "Transgender")
        self.assertEqual(normalize_gender("TG"), "Transgender")
        self.assertIsNone(normalize_gender(None))
        self.assertIsNone(normalize_gender("unknown_entity"))

    def test_state_normalization(self):
        """Tests normalization of 36 standard states/UTs and historical aliases."""
        self.assertEqual(normalize_state("Assam"), "Assam")
        self.assertEqual(normalize_state("Maharashtra"), "Maharashtra")
        self.assertEqual(normalize_state("Tamil Nadu"), "Tamil Nadu")
        # Aliases
        self.assertEqual(normalize_state("Orissa"), "Odisha")
        self.assertEqual(normalize_state("Uttaranchal"), "Uttarakhand")
        self.assertEqual(normalize_state("Pondicherry"), "Puducherry")
        self.assertEqual(normalize_state("NCT of Delhi"), "Delhi")
        self.assertEqual(normalize_state("New Delhi"), "Delhi")
        self.assertEqual(normalize_state("J&K"), "Jammu and Kashmir")
        self.assertEqual(normalize_state("State of Gujarat"), "Gujarat")
        self.assertIsNone(normalize_state("Atlantis"))

    def test_social_category_normalization(self):
        """Tests canonical constitutional social categories."""
        self.assertEqual(normalize_social_category("General"), "General")
        self.assertEqual(normalize_social_category("GEN"), "General")
        self.assertEqual(normalize_social_category("Open"), "General")
        self.assertEqual(normalize_social_category("OBC"), "OBC")
        self.assertEqual(normalize_social_category("Other Backward Class"), "OBC")
        self.assertEqual(normalize_social_category("SC"), "SC")
        self.assertEqual(normalize_social_category("Scheduled Caste"), "SC")
        self.assertEqual(normalize_social_category("ST"), "ST")
        self.assertEqual(normalize_social_category("Scheduled Tribe"), "ST")
        self.assertEqual(normalize_social_category("EWS"), "EWS")
        self.assertIsNone(normalize_social_category("InvalidCategory"))

    def test_boolean_normalization(self):
        """Tests boolean token parsing."""
        self.assertTrue(normalize_boolean("yes"))
        self.assertTrue(normalize_boolean("True"))
        self.assertTrue(normalize_boolean("1"))
        self.assertTrue(normalize_boolean("applicable"))
        self.assertTrue(normalize_boolean(True))

        self.assertFalse(normalize_boolean("no"))
        self.assertFalse(normalize_boolean("false"))
        self.assertFalse(normalize_boolean("0"))
        self.assertFalse(normalize_boolean("ineligible"))
        self.assertFalse(normalize_boolean(False))

        self.assertIsNone(normalize_boolean(None))
        self.assertIsNone(normalize_boolean(""))
        self.assertIsNone(normalize_boolean("maybe"))

    def test_percentage_normalization(self):
        """Tests percentage parsing on 0.0 - 100.0 scale."""
        self.assertEqual(normalize_percentage("45%"), 45.0)
        self.assertEqual(normalize_percentage("45.5 %"), 45.5)
        self.assertEqual(normalize_percentage("45.5"), 45.5)
        self.assertEqual(normalize_percentage("0.45"), 45.0)
        self.assertEqual(normalize_percentage(0.75), 75.0)
        self.assertEqual(normalize_percentage(80), 80.0)

    def test_landholding_normalization(self):
        """Tests landholding normalization to hectares."""
        self.assertEqual(normalize_landholding("2.5 hectares"), 2.5)
        self.assertEqual(normalize_landholding("2.5 ha"), 2.5)
        # 5 acres * 0.404686 = 2.02343 -> 2.0234
        self.assertEqual(normalize_landholding("5 acres"), 2.0234)
        self.assertEqual(normalize_landholding(3.5), 3.5)

    def test_occupation_normalization(self):
        """Tests occupation title standardization."""
        self.assertEqual(normalize_occupation("farmer"), "Farmer")
        self.assertEqual(normalize_occupation("kisan"), "Farmer")
        self.assertEqual(normalize_occupation("small farmer"), "Small and Marginal Farmer")
        self.assertEqual(normalize_occupation("street vendor"), "Street Vendor")
        self.assertEqual(normalize_occupation("hawker"), "Street Vendor")
        self.assertEqual(normalize_occupation("weaver"), "Weaver")


class TestValidators(unittest.TestCase):
    """Tests domain boundary validation and rejection of impossible values."""

    def test_age_bounds(self):
        """Validates age constraints [0, 120]."""
        self.assertEqual(validate_age(0), 0)
        self.assertEqual(validate_age(120), 120)
        self.assertEqual(validate_age(25), 25)

        with self.assertRaises(ValidationError) as ctx:
            validate_age(-1)
        self.assertIn("cannot be negative", str(ctx.exception))

        with self.assertRaises(ValidationError) as ctx:
            validate_age(121)
        self.assertIn("cannot exceed 120", str(ctx.exception))

    def test_income_bounds(self):
        """Validates that annual family income cannot be negative."""
        self.assertEqual(validate_income(0.0), 0.0)
        self.assertEqual(validate_income(500000.0), 500000.0)

        with self.assertRaises(ValidationError) as ctx:
            validate_income(-500.0)
        self.assertIn("cannot be negative", str(ctx.exception))

    def test_percentage_bounds(self):
        """Validates percentage constraints [0.0, 100.0]."""
        self.assertEqual(validate_percentage(0.0), 0.0)
        self.assertEqual(validate_percentage(100.0), 100.0)
        self.assertEqual(validate_percentage(40.0), 40.0)

        with self.assertRaises(ValidationError) as ctx:
            validate_percentage(-0.1)
        self.assertIn("must be between 0.0 and 100.0", str(ctx.exception))

        with self.assertRaises(ValidationError) as ctx:
            validate_percentage(100.1)
        self.assertIn("must be between 0.0 and 100.0", str(ctx.exception))

    def test_landholding_bounds(self):
        """Validates that landholding cannot be negative."""
        self.assertEqual(validate_landholding(0.0), 0.0)
        self.assertEqual(validate_landholding(2.5), 2.5)

        with self.assertRaises(ValidationError) as ctx:
            validate_landholding(-1.0)
        self.assertIn("cannot be negative", str(ctx.exception))

    def test_normalize_field_value_with_validation(self):
        """Tests end-to-end normalization with automatic validation."""
        # Valid cases
        self.assertEqual(normalize_field_value("age", "30 years"), 30)
        self.assertEqual(normalize_field_value("annual_family_income", "₹3.5 Lakh"), 350000.0)
        self.assertEqual(normalize_field_value("state", "Assam"), "Assam")

        # Invalid cases raise ValidationError
        with self.assertRaises(ValidationError):
            normalize_field_value("age", "-10 years")

        with self.assertRaises(ValidationError):
            normalize_field_value("annual_family_income", "-50000")

        with self.assertRaises(ValidationError):
            normalize_field_value("disability_percentage", "150%")


if __name__ == "__main__":
    unittest.main()
