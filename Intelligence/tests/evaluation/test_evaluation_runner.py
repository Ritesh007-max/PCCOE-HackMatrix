"""
Tests for Phase 13 Automated Evaluation Runner & Report Generator.
"""

import unittest
from pathlib import Path
import sys

_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.evaluation.runner import EvaluationSuiteRunner


class TestEvaluationSuiteRunner(unittest.TestCase):
    """Verifies that evaluation runner executes suites, aggregates metrics, and saves reports."""

    def setUp(self):
        self.runner = EvaluationSuiteRunner()

    def test_run_eligibility_suite(self):
        record = self.runner.run_suite("eligibility")
        self.assertEqual(record["suite_name"], "eligibility")
        self.assertGreater(record["total_cases"], 0)
        self.assertEqual(record["failed"], 0)
        self.assertIn("eligibility", record["suites"])
        self.assertIn("json", record["report_paths"])
        self.assertIn("markdown", record["report_paths"])

    def test_run_red_team_suite(self):
        record = self.runner.run_suite("red-team")
        self.assertEqual(record["suite_name"], "red-team")
        self.assertGreater(record["total_cases"], 0)
        self.assertEqual(record["failed"], 0)
        self.assertIn("red_team", record["suites"])

    def test_run_grounding_suite(self):
        record = self.runner.run_suite("grounding")
        self.assertEqual(record["suite_name"], "grounding")
        self.assertGreater(record["total_cases"], 0)
        self.assertEqual(record["failed"], 0)
