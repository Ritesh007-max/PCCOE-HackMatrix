"""
Unit tests for FIN Applicant Facts and Schemas.
Verifies fact creation, verbatim span preservation, verification states, and JSON schema validation.
"""

import unittest
import sys
from pathlib import Path

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.extraction.models import (
    ApplicantFact,
    CanonicalApplicantProfile,
    FactVerificationStatus,
    ExtractionMethod,
    CANONICAL_PROFILE_FIELDS,
)
from src.extraction.schema import (
    validate_applicant_fact_dict,
    validate_evidence_collection_dict,
    validate_applicant_profile_dict,
)
import jsonschema


class TestApplicantFacts(unittest.TestCase):
    """Tests ApplicantFact construction, verbatim text preservation, and states."""

    def test_fact_creation_and_attributes(self):
        """Tests that all 10 required fact fields are supported and preserved."""
        fact = ApplicantFact(
            field="annual_family_income",
            value="Rs. 4.2 Lakh",
            normalized_value=420000.0,
            data_type="numeric",
            confidence=0.95,
            source_document="income_certificate_2024.pdf",
            page_number=1,
            text_span="certified annual income is Rs. 4.2 Lakh",
            extraction_method=ExtractionMethod.REGEX.value,
            verification_status=FactVerificationStatus.EXTRACTED,
            metadata={"issuer": "Revenue Dept"}
        )

        self.assertEqual(fact.field, "annual_family_income")
        self.assertEqual(fact.value, "Rs. 4.2 Lakh")
        self.assertEqual(fact.normalized_value, 420000.0)
        self.assertEqual(fact.data_type, "numeric")
        self.assertEqual(fact.confidence, 0.95)
        self.assertEqual(fact.source_document, "income_certificate_2024.pdf")
        self.assertEqual(fact.page_number, 1)
        self.assertEqual(fact.text_span, "certified annual income is Rs. 4.2 Lakh")
        self.assertEqual(fact.extraction_method, "REGEX")
        self.assertEqual(fact.verification_status, FactVerificationStatus.EXTRACTED)
        self.assertEqual(fact.metadata["issuer"], "Revenue Dept")

    def test_verbatim_text_span_preservation(self):
        """Requirement 9: Preserve the original extracted text exactly."""
        raw_text = "   Applicant resides at Plot 12, Guwahati, Assam - 781001   "
        fact = ApplicantFact(
            field="state",
            value=raw_text,
            normalized_value="Assam",
            data_type="string",
            confidence=1.0,
            source_document="domicile.pdf",
            text_span=raw_text,
        )
        self.assertEqual(fact.value, raw_text)
        self.assertEqual(fact.text_span, raw_text)

    def test_verification_states(self):
        """Requirement 3: Support all 6 canonical verification states."""
        statuses = [
            FactVerificationStatus.SELF_REPORTED,
            FactVerificationStatus.EXTRACTED,
            FactVerificationStatus.USER_CONFIRMED,
            FactVerificationStatus.ISSUER_VERIFIED,
            FactVerificationStatus.CONFLICTED,
            FactVerificationStatus.UNKNOWN,
        ]
        for s in statuses:
            fact = ApplicantFact(
                field="age",
                value=25,
                normalized_value=25,
                data_type="numeric",
                confidence=1.0,
                source_document="aadhaar.pdf",
                verification_status=s,
            )
            self.assertEqual(fact.verification_status, s)

    def test_canonical_profile_fields_dictionary(self):
        """Requirement 1: Authoritative dictionary of canonical profile fields."""
        self.assertIn("age", CANONICAL_PROFILE_FIELDS)
        self.assertIn("annual_family_income", CANONICAL_PROFILE_FIELDS)
        self.assertIn("state", CANONICAL_PROFILE_FIELDS)
        self.assertIn("social_category", CANONICAL_PROFILE_FIELDS)
        self.assertIn("is_permanent_resident", CANONICAL_PROFILE_FIELDS)
        self.assertEqual(CANONICAL_PROFILE_FIELDS["age"]["data_type"], "numeric")
        self.assertEqual(CANONICAL_PROFILE_FIELDS["gender"]["data_type"], "string")

    def test_json_schema_validation_fact(self):
        """Requirement 10: JSON schema validation for ApplicantFact."""
        valid_fact = {
            "field": "age",
            "value": "28 years",
            "normalized_value": 28,
            "data_type": "numeric",
            "confidence": 1.0,
            "source_document": "aadhaar.pdf",
            "page_number": 1,
            "text_span": "DOB: 12/04/1996, Age: 28 years",
            "extraction_method": "REGEX",
            "verification_status": "EXTRACTED",
        }
        # Should validate without error
        validate_applicant_fact_dict(valid_fact)

        # Missing required field 'source_document'
        invalid_fact = {
            "field": "age",
            "data_type": "numeric",
            "verification_status": "EXTRACTED"
        }
        with self.assertRaises(jsonschema.ValidationError):
            validate_applicant_fact_dict(invalid_fact)

    def test_json_schema_validation_profile(self):
        """Requirement 10: JSON schema validation for ApplicantProfile."""
        valid_profile = {
            "age": 35,
            "gender": "Female",
            "state": "Assam",
            "annual_family_income": 120000.0,
            "social_category": "OBC",
            "is_permanent_resident": True,
            "_conflicts": []
        }
        validate_applicant_profile_dict(valid_profile)

        # Invalid gender
        invalid_profile = {
            "gender": "OtherAlien"
        }
        with self.assertRaises(jsonschema.ValidationError):
            validate_applicant_profile_dict(invalid_profile)

    def test_json_schema_validation_evidence(self):
        """Requirement 10: JSON schema validation for EvidenceCollection."""
        valid_evidence = {
            "applicant_id": "app_001",
            "facts": [
                {
                    "field": "age",
                    "value": 25,
                    "normalized_value": 25,
                    "data_type": "numeric",
                    "confidence": 1.0,
                    "source_document": "aadhaar.pdf",
                    "verification_status": "EXTRACTED"
                }
            ],
            "conflicts": [],
            "source_documents": ["aadhaar.pdf"]
        }
        validate_evidence_collection_dict(valid_evidence)


if __name__ == "__main__":
    unittest.main()
