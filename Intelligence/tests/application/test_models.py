"""
Unit tests for Application Case Domain Models.
Phase 10: Validates models, document references, fact snapshots, and serialization.
"""

import unittest
from src.application.status import ApplicationStatus, ReadinessStatus, StatutoryDecision
from src.application.case import (
    ApplicationCase,
    DocumentReference,
    FactSnapshot,
    SchemeEvaluation,
    generate_application_id,
)
from src.application.exceptions import DocumentNotFoundError


class TestApplicationModels(unittest.TestCase):
    """Tests for core application case domain models."""

    def test_application_id_generation(self):
        """Application ID must be a unique non-empty string starting with 'app_'."""
        app_id_1 = generate_application_id()
        app_id_2 = generate_application_id()
        self.assertTrue(app_id_1.startswith("app_"))
        self.assertTrue(app_id_2.startswith("app_"))
        self.assertNotEqual(app_id_1, app_id_2)

    def test_document_reference_no_raw_bytes(self):
        """DocumentReference must store metadata and hash, never raw file bytes."""
        doc = DocumentReference(
            document_id="doc_12345",
            filename="income_cert.pdf",
            document_type="INCOME_CERTIFICATE",
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            processing_status="PROCESSED",
            provenance_refs=[{"page": 1, "field": "annual_family_income"}],
            facts_extracted=["annual_family_income"],
        )
        data = doc.to_dict()
        self.assertNotIn("bytes", data)
        self.assertNotIn("content", data)
        self.assertEqual(data["document_id"], "doc_12345")
        self.assertEqual(data["sha256_hash"], "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

        # Roundtrip
        doc_recon = DocumentReference.from_dict(data)
        self.assertEqual(doc_recon.document_id, doc.document_id)
        self.assertEqual(doc_recon.filename, doc.filename)

    def test_fact_snapshot_reproducibility(self):
        """FactSnapshot accurately captures state of applicant facts and conflicts."""
        snapshot = FactSnapshot(
            facts={"age": 22, "state": "Gujarat", "social_category": "SC"},
            verification_status={"state": "ISSUER_VERIFIED", "social_category": "EXTRACTED"},
            evidence_references={"state": ["doc_domicile_1"]},
            conflicted_fields=[],
            missing_fields=["annual_family_income"],
        )
        d = snapshot.to_dict()
        self.assertEqual(d["facts"]["age"], 22)
        self.assertEqual(d["missing_fields"], ["annual_family_income"])

        recon = FactSnapshot.from_dict(d)
        self.assertEqual(recon.facts, snapshot.facts)
        self.assertEqual(recon.conflicted_fields, snapshot.conflicted_fields)

    def test_scheme_evaluation_separation_of_relevance_and_eligibility(self):
        """
        SchemeEvaluation must separate retrieval relevance score from statutory decision.
        High relevance score does not imply eligibility PASS.
        """
        eval_result = SchemeEvaluation(
            scheme_id="scheme_post_matric_sc",
            scheme_name="Post Matric Scholarship for SC",
            retrieval_relevance_score=0.95,
            retrieval_rank=1,
            decision_status=StatutoryDecision.FAIL,
            is_eligible=False,
            failed_rules=[{"rule_id": "r_income", "field": "annual_family_income", "reason": "Exceeds limit"}],
            policy_snapshot_version="snapshot_20260921_193823",
            rule_version="1.0.0",
        )
        # Relevance is 0.95, but statutory decision is FAIL
        self.assertEqual(eval_result.retrieval_relevance_score, 0.95)
        self.assertEqual(eval_result.decision_status, StatutoryDecision.FAIL)
        self.assertFalse(eval_result.is_eligible)

        d = eval_result.to_dict()
        self.assertEqual(d["decision_status"], "FAIL")
        recon = SchemeEvaluation.from_dict(d)
        self.assertEqual(recon.decision_status, StatutoryDecision.FAIL)
        self.assertEqual(recon.policy_snapshot_version, "snapshot_20260921_193823")

    def test_application_case_roundtrip_and_methods(self):
        """Tests ApplicationCase document attachment, scheme selection, and serialization."""
        case = ApplicationCase(citizen_reference="cit_001")
        self.assertEqual(case.current_status, ApplicationStatus.DRAFT)
        self.assertEqual(case.readiness, ReadinessStatus.NOT_READY)

        doc = DocumentReference(
            document_id="doc_abc",
            filename="caste_cert.pdf",
            document_type="CASTE_CERTIFICATE",
        )
        case.attach_document(doc)
        self.assertIn("doc_abc", case.documents)
        self.assertEqual(case.get_document("doc_abc").filename, "caste_cert.pdf")

        with self.assertRaises(DocumentNotFoundError):
            case.get_document("doc_nonexistent")

        # Select scheme
        case.select_scheme("sc_scholarship")
        self.assertEqual(case.selected_scheme_id, "sc_scholarship")

        # Roundtrip
        serialized = case.to_dict()
        recon = ApplicationCase.from_dict(serialized)
        self.assertEqual(recon.application_id, case.application_id)
        self.assertEqual(recon.citizen_reference, "cit_001")
        self.assertIn("doc_abc", recon.documents)
        self.assertEqual(recon.selected_scheme_id, "sc_scholarship")


if __name__ == "__main__":
    unittest.main()
