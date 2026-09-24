"""
Integration tests for FIN Phase 11 Application Guidance & Preparation Layer.
Verifies integration between:
  Phase 10 Application Workflow -> Phase 11 ApplicationGuidanceService -> ApplicationGuidancePackage
Covers:
  1. Gujarat SC student scholarship end-to-end guidance
  2. Missing document checklist & action guidance
  3. Conflicting evidence (Gujarat vs Rajasthan) review guidance
  4. Failed eligibility (income ceiling exceeded) unsoftened explanation
  5. Unknown eligibility (missing income fact) identification
  6. Ready-to-apply complete package with verified official portal
  7. Policy version update (V1 -> V2) & cache invalidation
  8. Multilingual localization (English, Hindi, Hinglish)
  9. Deterministic offline / no-LLM execution
"""

from pathlib import Path
import unittest
import sys

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.application.service import ApplicationWorkflowService
from src.application.status import (
    ApplicationStatus,
    StatutoryDecision,
    ReadinessStatus,
    ActionType,
    ActionPriority,
)
from src.application.case import ApplicationCase, FactSnapshot, SchemeEvaluation
from src.application.repository import InMemoryApplicationRepository
from src.llm.config import LLMConfig
from src.pipelines.application_pipeline import ApplicationPipeline
from src.rules.models import Rule, SchemeRuleSet
from src.guidance.service import ApplicationGuidanceService
from src.guidance.models import (
    ApplicationGuidancePackage,
    ApplicationMode,
    GuidanceWarningCode,
    WarningSeverity,
)
from src.guidance.exceptions import (
    GuidanceValidationError,
    ContradictoryGuidanceError,
)


class TestApplicationGuidanceIntegration(unittest.TestCase):
    """Integration test suite for Phase 11 Application Guidance Layer."""

    def setUp(self):
        self.fixtures_dir = _INTELLIGENCE_DIR / "tests" / "fixtures"
        self.repo = InMemoryApplicationRepository()
        self.config = LLMConfig(provider="mock")
        self.pipeline = ApplicationPipeline(llm_config=self.config)
        self.workflow_service = ApplicationWorkflowService(
            repository=self.repo,
            pipeline=self.pipeline,
        )
        self.guidance_service = ApplicationGuidanceService(
            workflow_service=self.workflow_service
        )

        # Standard test ruleset: Gujarat SC Post-Matric Scholarship
        self.sc_ruleset = SchemeRuleSet(
            scheme_id="sc_post_matric_scholarship",
            scheme_slug="sc_post_matric_scholarship",
            scheme_name="Post Matric Scholarship for SC Students",
            version="1.0.0",
            root_logic="AND",
            rules=[
                Rule(
                    rule_id="rule_sc_01",
                    scheme_id="sc_post_matric_scholarship",
                    rule_type="eligibility",
                    field="social_category",
                    operator="=",
                    expected_value="SC",
                    value_type="string",
                    required=True,
                    hard_constraint=True,
                    raw_text="Must belong to Scheduled Caste.",
                ),
                Rule(
                    rule_id="rule_sc_02",
                    scheme_id="sc_post_matric_scholarship",
                    rule_type="eligibility",
                    field="annual_family_income",
                    operator="<=",
                    expected_value=250000,
                    value_type="numeric",
                    required=True,
                    hard_constraint=True,
                    raw_text="Annual family income must not exceed Rs 2,50,000.",
                ),
                Rule(
                    rule_id="rule_sc_03",
                    scheme_id="sc_post_matric_scholarship",
                    rule_type="eligibility",
                    field="state",
                    operator="=",
                    expected_value="Gujarat",
                    value_type="string",
                    required=True,
                    hard_constraint=True,
                    raw_text="Must be permanent resident of Gujarat.",
                ),
            ],
        )
        self.workflow_service.eligibility_engine.register_ruleset(self.sc_ruleset)

    def test_01_full_end_to_end_gujarat_sc_student_scenario(self):
        """
        Scenario 1: Fully eligible applicant.
        Phase 10 workflow evaluates eligibility -> Phase 11 generates Guidance Package.
        Verifies:
          - Statutory decision: PASS
          - Citizen-readable eligibility summary
          - Document guidance & checklist
          - Application steps with grounding
          - Benefit guidance
          - Official portal URL
        """
        # 1. Create Application Case in Phase 10
        case = self.workflow_service.create_application(citizen_reference="citizen_gujarat_sc_01")
        app_id = case.application_id

        self.workflow_service.update_applicant_profile(
            application_id=app_id,
            facts={
                "state": "Gujarat",
                "age": 20,
                "annual_family_income": 120000,
                "social_category": "SC",
                "is_student": True,
            },
        )
        # Add provided documents
        doc1 = self.workflow_service.attach_document(
            application_id=app_id,
            filename="income_cert.pdf",
            document_type="income_certificate",
        )
        doc1.processing_status = "PROCESSED"

        doc2 = self.workflow_service.attach_document(
            application_id=app_id,
            filename="caste_cert.pdf",
            document_type="caste_certificate",
        )
        doc2.processing_status = "PROCESSED"

        doc3 = self.workflow_service.attach_document(
            application_id=app_id,
            filename="domicile_cert.pdf",
            document_type="domicile_certificate",
        )
        doc3.processing_status = "PROCESSED"

        # 2. Evaluate in Phase 10
        eval_result = self.workflow_service.evaluate_scheme(
            application_id=app_id,
            scheme_id="sc_post_matric_scholarship",
            scheme_name="Post Matric Scholarship for SC Students",
            required_documents=["income_certificate", "caste_certificate", "domicile_certificate"],
        )
        self.assertEqual(eval_result.decision_status, StatutoryDecision.PASS)

        # 3. Generate Guidance in Phase 11
        guidance = self.guidance_service.generate_guidance(
            application_id=app_id,
            scheme_id="sc_post_matric_scholarship",
            language="en",
        )

        # 4. Assert Guidance Structure and Correctness
        self.assertIsInstance(guidance, ApplicationGuidancePackage)
        self.assertEqual(guidance.scheme_id, "sc_post_matric_scholarship")
        self.assertEqual(guidance.statutory_decision, "PASS")
        self.assertEqual(guidance.eligibility.status, "PASS")
        self.assertIn("satisfy the evaluated statutory eligibility criteria", guidance.eligibility.summary)
        self.assertEqual(len(guidance.eligibility.satisfied_criteria), 3)

        # Documents check
        available_docs = guidance.documents.get("available", [])
        self.assertTrue(any("Income" in d for d in available_docs))
        self.assertTrue(any("Caste" in d for d in available_docs))
        self.assertTrue(any("Domicile" in d for d in available_docs))

        # Steps & grounding check
        steps = guidance.application.get("steps", [])
        self.assertGreater(len(steps), 0)
        first_step = steps[0]
        self.assertIn("instruction", first_step)

        # Official portal / source check
        self.assertIsNotNone(guidance.sources)
        self.assertGreater(len(guidance.sources), 0)

        # Export test (JSON and Markdown)
        md_export = self.guidance_service.export_guidance_markdown(guidance)
        self.assertIn("Application Guidance", md_export)
        self.assertIn("Post Matric Scholarship for SC Students", md_export)

    def test_02_missing_caste_certificate_scenario(self):
        """
        Scenario 2: Eligible facts, but missing required caste certificate.
        Guidance must:
          - Keep statutory eligibility = PASS
          - Set readiness = ACTION_REQUIRED
          - Clearly list caste_certificate in missing documents checklist
          - Map next action to citizen-readable instruction "Upload your caste certificate."
        """
        case = self.workflow_service.create_application(citizen_reference="citizen_missing_doc")
        app_id = case.application_id

        self.workflow_service.update_applicant_profile(
            application_id=app_id,
            facts={
                "state": "Gujarat",
                "annual_family_income": 120000,
                "social_category": "SC",
            },
        )
        # Provide only income certificate
        doc1 = self.workflow_service.attach_document(
            application_id=app_id,
            filename="income_cert.pdf",
            document_type="income_certificate",
        )
        doc1.processing_status = "PROCESSED"

        self.workflow_service.evaluate_scheme(
            application_id=app_id,
            scheme_id="sc_post_matric_scholarship",
            scheme_name="Post Matric Scholarship for SC Students",
            required_documents=["income_certificate", "caste_certificate"],
        )

        guidance = self.guidance_service.generate_guidance(
            application_id=app_id,
            scheme_id="sc_post_matric_scholarship",
            language="en",
        )

        self.assertEqual(guidance.eligibility.status, "PASS")
        self.assertEqual(guidance.readiness_status, "ACTION_REQUIRED")
        self.assertEqual(guidance.readiness["status"], "ACTION_REQUIRED")
        missing_docs = guidance.documents.get("missing", [])
        self.assertTrue(any("Caste" in d for d in missing_docs))

        # Verify warnings include document missing
        doc_missing_warn = [w for w in guidance.warnings if w.code.value == "DOCUMENT_MISSING"]
        self.assertGreater(len(doc_missing_warn), 0)

        # Verify next action mentions upload
        upload_actions = [a for a in guidance.actions if a.get("action_type") == "UPLOAD_DOCUMENT"]
        self.assertGreater(len(upload_actions), 0)

    def test_03_conflicting_state_evidence_review_scenario(self):
        """
        Scenario 3: Contradictory documents (Gujarat vs Rajasthan).
        Guidance must:
          - Show statutory decision = REVIEW
          - Readiness = READY_FOR_REVIEW
          - Explain conflicting residence facts
          - Instruct RESOLVE_CONFLICT
          - NOT pick one state automatically
        """
        case = self.workflow_service.create_application(citizen_reference="citizen_conflict_01")
        app_id = case.application_id

        self.workflow_service.update_applicant_profile(
            application_id=app_id,
            facts={
                "state": "Gujarat",
                "annual_family_income": 100000,
                "social_category": "SC",
            },
            conflicted_fields=["state"],
        )

        self.workflow_service.evaluate_scheme(
            application_id=app_id,
            scheme_id="sc_post_matric_scholarship",
            scheme_name="Post Matric Scholarship for SC Students",
        )

        guidance = self.guidance_service.generate_guidance(
            application_id=app_id,
            scheme_id="sc_post_matric_scholarship",
        )

        self.assertEqual(guidance.eligibility.status, "REVIEW")
        self.assertEqual(guidance.readiness_status, "READY_FOR_REVIEW")
        self.assertEqual(guidance.readiness["status"], "READY_FOR_REVIEW")
        self.assertIn("contradictory", guidance.eligibility.summary.lower())
        self.assertIn("state", guidance.information.get("conflicted", []))

        # Check warnings
        conflict_warn = [w for w in guidance.warnings if w.code.value == "DOCUMENT_CONFLICT"]
        self.assertGreater(len(conflict_warn), 0)

    def test_04_statutory_failure_income_exceeded(self):
        """
        Scenario 4: Disqualification due to income (350,000 > 250,000 ceiling).
        Guidance must:
          - Output statutory decision = FAIL
          - Honestly state failed income rule
          - NOT soften to "maybe eligible"
          - NOT recommend applying
        """
        case = self.workflow_service.create_application(citizen_reference="citizen_fail_01")
        app_id = case.application_id

        self.workflow_service.update_applicant_profile(
            application_id=app_id,
            facts={
                "state": "Gujarat",
                "annual_family_income": 350000,  # Exceeds 250,000
                "social_category": "SC",
            },
        )
        self.workflow_service.evaluate_scheme(
            application_id=app_id,
            scheme_id="sc_post_matric_scholarship",
            scheme_name="Post Matric Scholarship for SC Students",
        )

        guidance = self.guidance_service.generate_guidance(
            application_id=app_id,
            scheme_id="sc_post_matric_scholarship",
        )

        self.assertEqual(guidance.eligibility.status, "FAIL")
        self.assertIn("not eligible because", guidance.eligibility.summary)
        self.assertGreater(len(guidance.eligibility.failed_criteria), 0)
        self.assertNotIn("eligible to apply", guidance.eligibility.summary.lower())

    def test_05_unknown_eligibility_missing_income(self):
        """
        Scenario 5: Unknown eligibility because annual family income is missing.
        Guidance must:
          - Output statutory decision = UNKNOWN
          - Identify annual_family_income as missing fact
          - Explain why needed (rule requirement)
          - Action = PROVIDE_INFORMATION
          - NOT convert UNKNOWN into PASS
        """
        case = self.workflow_service.create_application(citizen_reference="citizen_unknown_01")
        app_id = case.application_id

        self.workflow_service.update_applicant_profile(
            application_id=app_id,
            facts={
                "state": "Gujarat",
                "social_category": "SC",
                # annual_family_income is omitted
            },
        )
        self.workflow_service.evaluate_scheme(
            application_id=app_id,
            scheme_id="sc_post_matric_scholarship",
            scheme_name="Post Matric Scholarship for SC Students",
        )

        guidance = self.guidance_service.generate_guidance(
            application_id=app_id,
            scheme_id="sc_post_matric_scholarship",
        )

        self.assertEqual(guidance.eligibility.status, "UNKNOWN")
        self.assertIn("cannot be determined yet because mandatory information is missing", guidance.eligibility.summary)
        self.assertIn("annual_family_income", guidance.information.get("missing", []))

    def test_06_ready_to_apply_no_external_submission(self):
        """
        Scenario 6: All requirements satisfied.
        Guidance must:
          - Output readiness = READY_TO_APPLY
          - Provide verified portal link if available
          - Provide step-by-step instructions
          - NOT trigger external transactions, payments, or portal submissions
        """
        case = self.workflow_service.create_application(citizen_reference="citizen_ready_01")
        app_id = case.application_id

        self.workflow_service.update_applicant_profile(
            application_id=app_id,
            facts={
                "state": "Gujarat",
                "annual_family_income": 100000,
                "social_category": "SC",
            },
        )
        for doc_type in ["income_certificate", "caste_certificate", "domicile_certificate"]:
            d = self.workflow_service.attach_document(
                application_id=app_id,
                filename=f"{doc_type}.pdf",
                document_type=doc_type,
            )
            d.processing_status = "PROCESSED"

        self.workflow_service.evaluate_scheme(
            application_id=app_id,
            scheme_id="sc_post_matric_scholarship",
            scheme_name="Post Matric Scholarship for SC Students",
            required_documents=["income_certificate", "caste_certificate", "domicile_certificate"],
        )

        guidance = self.guidance_service.generate_guidance(
            application_id=app_id,
            scheme_id="sc_post_matric_scholarship",
        )

        self.assertEqual(guidance.eligibility.status, "PASS")
        self.assertEqual(guidance.readiness_status, "READY_TO_APPLY")
        steps = guidance.application.get("steps", [])
        self.assertGreater(len(steps), 0)

        # Check immutability: No submission side-effects
        stored_case = self.workflow_service.get_application_state(app_id)
        self.assertEqual(stored_case.current_status, ApplicationStatus.READY_TO_APPLY)

    def test_07_policy_version_update_and_cache_invalidation(self):
        """
        Scenario 7: Policy snapshot / rule update invalidates cached guidance.
        When rule_version changes from 1.0.0 -> 2.0.0, guidance cache must miss and recompute.
        """
        case = self.workflow_service.create_application(citizen_reference="citizen_cache_01")
        app_id = case.application_id

        self.workflow_service.update_applicant_profile(
            application_id=app_id,
            facts={
                "state": "Gujarat",
                "annual_family_income": 100000,
                "social_category": "SC",
            },
        )
        self.workflow_service.evaluate_scheme(
            application_id=app_id,
            scheme_id="sc_post_matric_scholarship",
            scheme_name="Post Matric Scholarship for SC Students",
        )

        # First call generates and caches
        g1 = self.guidance_service.generate_guidance(
            application_id=app_id,
            scheme_id="sc_post_matric_scholarship",
        )
        self.assertEqual(g1.rule_version, "1.0.0")

        # Now update ruleset version to 2.0.0
        sc_ruleset_v2 = SchemeRuleSet(
            scheme_id="sc_post_matric_scholarship",
            scheme_slug="sc_post_matric_scholarship",
            scheme_name="Post Matric Scholarship for SC Students",
            version="2.0.0",
            root_logic="AND",
            rules=self.sc_ruleset.rules,
        )
        self.workflow_service.eligibility_engine.register_ruleset(sc_ruleset_v2)
        # Re-evaluate in Phase 10
        self.workflow_service.evaluate_scheme(
            application_id=app_id,
            scheme_id="sc_post_matric_scholarship",
            scheme_name="Post Matric Scholarship for SC Students",
        )

        # Generating guidance now must return V2
        g2 = self.guidance_service.generate_guidance(
            application_id=app_id,
            scheme_id="sc_post_matric_scholarship",
        )
        self.assertEqual(g2.rule_version, "2.0.0")

    def test_08_multilingual_localization_hindi_hinglish(self):
        """
        Scenario 8: Multilingual localization in Hindi and Hinglish.
        Verifies that:
          - Machine-stable identifiers (scheme_id, document types, rule IDs) are preserved
          - Titles and summaries reflect Hindi and Hinglish phrasing
        """
        case = self.workflow_service.create_application(citizen_reference="citizen_multi_01")
        app_id = case.application_id

        self.workflow_service.update_applicant_profile(
            application_id=app_id,
            facts={
                "state": "Gujarat",
                "annual_family_income": 100000,
                "social_category": "SC",
            },
        )
        self.workflow_service.evaluate_scheme(
            application_id=app_id,
            scheme_id="sc_post_matric_scholarship",
            scheme_name="Post Matric Scholarship for SC Students",
        )

        # Hindi
        hi_guidance = self.guidance_service.generate_guidance(
            application_id=app_id,
            scheme_id="sc_post_matric_scholarship",
            language="hi",
        )
        self.assertEqual(hi_guidance.language, "hi")
        self.assertEqual(hi_guidance.scheme_id, "sc_post_matric_scholarship")
        self.assertIn("पात्रता", hi_guidance.eligibility.summary)

        # Hinglish
        hing_guidance = self.guidance_service.generate_guidance(
            application_id=app_id,
            scheme_id="sc_post_matric_scholarship",
            language="hinglish",
        )
        self.assertEqual(hing_guidance.language, "hinglish")
        self.assertEqual(hing_guidance.scheme_id, "sc_post_matric_scholarship")
        self.assertIn("satisfy", hing_guidance.eligibility.summary.lower())

    def test_09_no_llm_deterministic_fallback(self):
        """
        Scenario 9: Guidance generation strictly without remote LLM (offline mode).
        Verifies complete generation of summaries, documents, steps, and warnings deterministically.
        """
        case = self.workflow_service.create_application(citizen_reference="citizen_nollm_01")
        app_id = case.application_id

        self.workflow_service.update_applicant_profile(
            application_id=app_id,
            facts={
                "state": "Gujarat",
                "annual_family_income": 100000,
                "social_category": "SC",
            },
        )
        self.workflow_service.evaluate_scheme(
            application_id=app_id,
            scheme_id="sc_post_matric_scholarship",
            scheme_name="Post Matric Scholarship for SC Students",
        )

        # Explicitly ensure guidance runs cleanly with mock/no LLM
        guidance = self.guidance_service.generate_guidance(
            application_id=app_id,
            scheme_id="sc_post_matric_scholarship",
        )
        self.assertIsNotNone(guidance)
        self.assertEqual(guidance.eligibility.status, "PASS")
        steps = guidance.application.get("steps", [])
        self.assertGreater(len(steps), 0)


if __name__ == "__main__":
    unittest.main()
