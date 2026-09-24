"""
Unit tests for ApplicationGuidanceService.
Phase 11: Validates guidance orchestration, export formatting, and offline execution.
"""

import unittest
from src.application.service import ApplicationWorkflowService
from src.application.status import StatutoryDecision, ReadinessStatus
from src.application.case import DocumentReference, SchemeEvaluation
from src.guidance.service import ApplicationGuidanceService


class TestGuidanceService(unittest.TestCase):
    """Tests for ApplicationGuidanceService."""

    def setUp(self):
        self.workflow_service = ApplicationWorkflowService()
        self.guidance_service = ApplicationGuidanceService(workflow_service=self.workflow_service)

    def test_generate_guidance_for_application(self):
        """Generates complete guidance package for an application case."""
        case = self.workflow_service.create_application(citizen_reference="cit_guidance_01")
        self.workflow_service.update_applicant_profile(
            application_id=case.application_id,
            facts={"age": 22, "annual_family_income": 120000, "state": "Gujarat"},
        )
        self.workflow_service.attach_document(
            application_id=case.application_id,
            filename="income.pdf",
            document_type="income_certificate",
        )

        # Set evaluation
        updated_case = self.workflow_service.get_application_state(case.application_id)
        updated_case.candidate_schemes["pm_kisan"] = SchemeEvaluation(
            scheme_id="pm_kisan",
            scheme_name="PM Kisan",
            decision_status=StatutoryDecision.PASS,
            is_eligible=True,
            benefit_summary={"status": "CALCULATED", "amount": 6000.0, "benefit_type": "DIRECT_BENEFIT_TRANSFER"},
        )
        updated_case.selected_scheme_id = "pm_kisan"
        updated_case.readiness = ReadinessStatus.READY_TO_APPLY
        self.workflow_service.repository.update(updated_case)

        package = self.guidance_service.generate_guidance(
            application_id=case.application_id,
            scheme_id="pm_kisan",
        )

        self.assertEqual(package.application_id, case.application_id)
        self.assertEqual(package.scheme_id, "pm_kisan")
        self.assertEqual(package.statutory_decision, "PASS")
        self.assertEqual(package.readiness_status, "READY_TO_APPLY")
        self.assertEqual(package.benefit.amount, 6000.0)
        self.assertTrue(len(package.application.get("steps", [])) >= 2)

    def test_markdown_and_json_export(self):
        """Exports guidance to clean Markdown and JSON."""
        case = self.workflow_service.create_application()
        updated_case = self.workflow_service.get_application_state(case.application_id)
        updated_case.candidate_schemes["s1"] = SchemeEvaluation(
            scheme_id="s1",
            scheme_name="Demo Scheme",
            decision_status=StatutoryDecision.PASS,
        )
        updated_case.selected_scheme_id = "s1"
        self.workflow_service.repository.update(updated_case)

        package = self.guidance_service.generate_guidance(case.application_id, "s1")

        # JSON export
        json_dict = package.to_dict()
        self.assertEqual(json_dict["application_id"], case.application_id)
        self.assertEqual(json_dict["scheme_id"], "s1")

        # Markdown export
        md_text = ApplicationGuidanceService.export_guidance_markdown(package)
        self.assertIn("# Application Guidance: Demo Scheme", md_text)
        self.assertIn("Statutory Decision:", md_text)
        self.assertIn("Step-by-Step Application Procedure", md_text)


if __name__ == "__main__":
    unittest.main()
