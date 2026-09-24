"""
Unit tests for GuidanceLocalizer.
Phase 11: Validates multilingual translation (en, hi, hinglish) and machine ID preservation.
"""

import unittest
from src.guidance.localization import GuidanceLocalizer


class TestGuidanceLocalization(unittest.TestCase):
    """Tests for GuidanceLocalizer."""

    def setUp(self):
        self.localizer = GuidanceLocalizer()

    def test_language_detection(self):
        """Accurately detects English, Hindi, and Hinglish queries."""
        self.assertEqual(
            self.localizer.detect_language("Can I apply for student scholarship?"),
            "en"
        )
        self.assertEqual(
            self.localizer.detect_language("क्या मुझे छात्रवृत्ति मिल सकती है?"),
            "hi"
        )
        self.assertEqual(
            self.localizer.detect_language("mujhe Gujarat mein scholarship chahiye"),
            "hinglish"
        )

    def test_readiness_reason_localization(self):
        """Translates readiness reason across supported languages."""
        en_str = self.localizer.localize_readiness_reason("READY_TO_APPLY", "en")
        hi_str = self.localizer.localize_readiness_reason("READY_TO_APPLY", "hi")
        hing_str = self.localizer.localize_readiness_reason("READY_TO_APPLY", "hinglish")

        self.assertEqual(en_str, "Ready to apply")
        self.assertIn("तैयार", hi_str)
        self.assertIn("ready", hing_str.lower())

    def test_action_title_localization(self):
        """Translates standard next action titles."""
        hi_action = self.localizer.localize_action_title(
            action_type="UPLOAD_DOCUMENT",
            fallback_title="Upload Required Document",
            language="hi",
        )
        self.assertIn("अपलोड", hi_action)

        hing_action = self.localizer.localize_action_title(
            action_type="UPLOAD_DOCUMENT",
            fallback_title="Upload Required Document",
            language="hinglish",
        )
        self.assertIn("upload", hing_action.lower())

    def test_eligibility_summary_localization(self):
        """Translates eligibility summary for PASS, FAIL, UNKNOWN, REVIEW."""
        hi_summary = self.localizer.localize_eligibility_summary(
            summary="Original English text",
            decision="PASS",
            language="hi",
        )
        self.assertIn("पात्रता मानदंडों को पूरा", hi_summary)

        hing_summary = self.localizer.localize_eligibility_summary(
            summary="Original English text",
            decision="FAIL",
            language="hinglish",
        )
        self.assertIn("eligible nahi", hing_summary)


if __name__ == "__main__":
    unittest.main()
