"""
Unit tests for Application Readiness and Completeness Engine.
Phase 10: Validates deterministic readiness matrix and checklist generation.
"""

import unittest
from src.application.status import (
    ReadinessStatus,
    StatutoryDecision,
    DocumentRequirementStatus,
)
from src.application.case import (
    ApplicationCase,
    DocumentReference,
    FactSnapshot,
    SchemeEvaluation,
)
from src.application.readiness import ApplicationReadinessEvaluator


class TestApplicationReadiness(unittest.TestCase):
    """Tests for deterministic readiness evaluation."""

    def test_scenario_1_pass_complete_docs_no_conflicts(self):
        """PASS + complete documents + no conflicts -> READY_TO_APPLY."""
        case = ApplicationCase(
            facts=FactSnapshot(facts={"age": 20, "annual_family_income": 100000}),
        )
        case.attach_document(DocumentReference(document_id="d1", filename="income.pdf", document_type="income_certificate"))
        case.attach_document(DocumentReference(document_id="d2", filename="caste.pdf", document_type="caste_certificate"))

        evaluation = SchemeEvaluation(
            scheme_id="scheme_1",
            scheme_name="Scholarship",
            decision_status=StatutoryDecision.PASS,
            is_eligible=True,
            missing_fields=[],
            conflicted_fields=[],
        )

        readiness = ApplicationReadinessEvaluator.evaluate_readiness(
            case=case,
            target_evaluation=evaluation,
            required_documents=["income_certificate", "caste_certificate"],
        )
        self.assertEqual(readiness, ReadinessStatus.READY_TO_APPLY)

    def test_scenario_2_pass_missing_required_document(self):
        """PASS + missing required certificate -> ACTION_REQUIRED."""
        case = ApplicationCase(
            facts=FactSnapshot(facts={"age": 20, "annual_family_income": 100000}),
        )
        # Only income certificate attached; caste certificate missing
        case.attach_document(DocumentReference(document_id="d1", filename="income.pdf", document_type="income_certificate"))

        evaluation = SchemeEvaluation(
            scheme_id="scheme_1",
            scheme_name="Scholarship",
            decision_status=StatutoryDecision.PASS,
            is_eligible=True,
            missing_fields=[],
            conflicted_fields=[],
        )

        readiness = ApplicationReadinessEvaluator.evaluate_readiness(
            case=case,
            target_evaluation=evaluation,
            required_documents=["income_certificate", "caste_certificate"],
        )
        self.assertEqual(readiness, ReadinessStatus.ACTION_REQUIRED)

    def test_scenario_3_unknown_missing_facts(self):
        """UNKNOWN + missing facts -> ACTION_REQUIRED."""
        case = ApplicationCase(
            facts=FactSnapshot(facts={"age": 20}),
        )
        evaluation = SchemeEvaluation(
            scheme_id="scheme_1",
            scheme_name="Scholarship",
            decision_status=StatutoryDecision.UNKNOWN,
            is_eligible=False,
            missing_fields=["annual_family_income"],
        )

        readiness = ApplicationReadinessEvaluator.evaluate_readiness(
            case=case,
            target_evaluation=evaluation,
        )
        self.assertEqual(readiness, ReadinessStatus.ACTION_REQUIRED)

    def test_scenario_4_review_conflicting_evidence(self):
        """REVIEW + conflicting evidence -> READY_FOR_REVIEW."""
        case = ApplicationCase(
            facts=FactSnapshot(
                facts={"age": 20, "state": "Gujarat"},
                conflicted_fields=["state"],
            ),
        )
        evaluation = SchemeEvaluation(
            scheme_id="scheme_1",
            scheme_name="Scholarship",
            decision_status=StatutoryDecision.REVIEW,
            is_eligible=False,
            conflicted_fields=["state"],
        )

        readiness = ApplicationReadinessEvaluator.evaluate_readiness(
            case=case,
            target_evaluation=evaluation,
        )
        self.assertEqual(readiness, ReadinessStatus.READY_FOR_REVIEW)

    def test_scenario_5_fail_statutory_decision(self):
        """FAIL statutory decision -> NOT_READY (statutory decision remains FAIL)."""
        case = ApplicationCase(
            facts=FactSnapshot(facts={"age": 35, "annual_family_income": 800000}),
        )
        evaluation = SchemeEvaluation(
            scheme_id="scheme_1",
            scheme_name="Scholarship",
            decision_status=StatutoryDecision.FAIL,
            is_eligible=False,
            failed_rules=[{"rule_id": "r_income", "field": "annual_family_income"}],
        )

        readiness = ApplicationReadinessEvaluator.evaluate_readiness(
            case=case,
            target_evaluation=evaluation,
        )
        # Readiness is NOT_READY, statutory decision remains FAIL
        self.assertEqual(readiness, ReadinessStatus.NOT_READY)
        self.assertEqual(evaluation.decision_status, StatutoryDecision.FAIL)

    def test_document_completeness_report(self):
        """Audit of required vs attached documents."""
        attached = [
            DocumentReference(document_id="d1", filename="my_income_certificate.pdf", document_type="income_certificate"),
            DocumentReference(document_id="d2", filename="resident_domicile.pdf", document_type="domicile_certificate"),
        ]
        required = ["income_certificate", "domicile_certificate", "caste_certificate"]

        report = ApplicationReadinessEvaluator.evaluate_document_completeness(
            required_document_types=required,
            attached_documents=attached,
        )
        self.assertFalse(report.is_complete)
        self.assertEqual(report.required_documents["income_certificate"], DocumentRequirementStatus.AVAILABLE)
        self.assertEqual(report.required_documents["domicile_certificate"], DocumentRequirementStatus.AVAILABLE)
        self.assertEqual(report.required_documents["caste_certificate"], DocumentRequirementStatus.MISSING)
        self.assertIn("caste_certificate", report.missing_documents)

    def test_checklist_generation(self):
        """Generates structured deterministic checklist."""
        case = ApplicationCase(
            facts=FactSnapshot(
                facts={"age": 20},
                conflicted_fields=["state"],
            ),
        )
        case.attach_document(DocumentReference(document_id="d1", filename="income.pdf", document_type="income_certificate"))

        evaluation = SchemeEvaluation(
            scheme_id="s1",
            scheme_name="Demo Scheme",
            decision_status=StatutoryDecision.REVIEW,
            conflicted_fields=["state"],
            missing_fields=["social_category"],
        )

        checklist = ApplicationReadinessEvaluator.generate_checklist(
            case=case,
            target_evaluation=evaluation,
            required_documents=["income_certificate", "caste_certificate"],
        )
        chk_dict = checklist.to_dict()
        self.assertTrue(len(chk_dict["documents"]) >= 2)
        self.assertTrue(any(i["item"] == "social_category" and i["status"] == "MISSING" for i in chk_dict["information"]))
        self.assertTrue(any("Resolve conflict in 'state'" in r["item"] for r in chk_dict["review"]))
        self.assertTrue(any(s["status"] == "BLOCKED" for s in chk_dict["application_steps"]))


if __name__ == "__main__":
    unittest.main()
