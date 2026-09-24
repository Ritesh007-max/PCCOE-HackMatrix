"""
Unit tests for ApplicationStepBuilder.
Phase 11: Validates grounded application steps, ordering, and source attribution.
"""

import unittest
from src.guidance.models import StepSourceType, ApplicationMode
from src.guidance.steps import ApplicationStepBuilder


class TestApplicationSteps(unittest.TestCase):
    """Tests for ApplicationStepBuilder."""

    def test_online_steps_with_portal_url(self):
        """Builds ordered online steps including verified portal link."""
        steps = ApplicationStepBuilder.build_steps(
            scheme_id="pm_kisan",
            scheme_name="PM Kisan",
            application_mode=ApplicationMode.ONLINE,
            official_portal_url="https://pmkisan.gov.in",
            missing_documents=["Land Records"],
        )

        self.assertTrue(len(steps) >= 4)
        # Step 1: Preparation
        self.assertEqual(steps[0].step_number, 1)
        self.assertEqual(steps[0].source_type, StepSourceType.GENERAL_PREPARATION)
        self.assertIn("Land Records", steps[0].notes)

        # Step 2: Portal access with exact link
        self.assertEqual(steps[1].step_number, 2)
        self.assertIn("https://pmkisan.gov.in", steps[1].instruction)
        self.assertEqual(steps[1].source_type, StepSourceType.POLICY_SOURCED)

    def test_offline_steps(self):
        """Offline application mode instructs visiting designated department office."""
        steps = ApplicationStepBuilder.build_steps(
            scheme_id="scheme_offline_1",
            scheme_name="Rural Welfare Grant",
            application_mode=ApplicationMode.OFFLINE,
        )

        step_texts = " ".join(s.instruction for s in steps)
        self.assertIn("department office", step_texts.lower())

    def test_policy_sourced_process_text(self):
        """Decomposes raw policy process text into discrete grounded steps."""
        process_text = (
            "1. Register on the portal. "
            "2. Upload verification certificate issued by Tehsildar. "
            "3. Submit physical copy to the District Social Welfare Office."
        )
        steps = ApplicationStepBuilder.build_steps(
            scheme_id="sc_scholarship",
            scheme_name="SC Scholarship",
            application_process_text=process_text,
            application_mode=ApplicationMode.ONLINE,
        )

        policy_steps = [s for s in steps if s.source_type == StepSourceType.POLICY_SOURCED]
        self.assertTrue(len(policy_steps) >= 2)
        self.assertTrue(any("Tehsildar" in s.instruction for s in policy_steps))


if __name__ == "__main__":
    unittest.main()
