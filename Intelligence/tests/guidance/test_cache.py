"""
Unit tests for Guidance Caching and Invalidation.
Phase 11: Validates multi-dimensional cache retention and automatic invalidation.
"""

import unittest
from unittest.mock import MagicMock
from src.application.service import ApplicationWorkflowService
from src.application.status import StatutoryDecision
from src.application.case import SchemeEvaluation
from src.guidance.service import ApplicationGuidanceService


class TestGuidanceCache(unittest.TestCase):
    """Tests for multi-dimensional guidance caching."""

    def test_cache_hit_and_invalidation_on_update(self):
        """Re-requesting returns cached guidance; mutating application state triggers recomputation."""
        workflow_service = ApplicationWorkflowService()
        guidance_service = ApplicationGuidanceService(workflow_service=workflow_service)

        case = workflow_service.create_application()
        case.candidate_schemes["s1"] = SchemeEvaluation(
            scheme_id="s1",
            scheme_name="Scholarship",
            decision_status=StatutoryDecision.PASS,
        )
        case.selected_scheme_id = "s1"
        workflow_service.repository.update(case)

        # Mock generator to track executions
        original_gen = guidance_service.generator.generate
        guidance_service.generator.generate = MagicMock(side_effect=original_gen)  # type: ignore

        # 1. First call -> Cache MISS
        pkg1 = guidance_service.generate_guidance(case.application_id, "s1")
        self.assertEqual(guidance_service.generator.generate.call_count, 1)

        # 2. Second call with same state -> Cache HIT
        pkg2 = guidance_service.generate_guidance(case.application_id, "s1")
        self.assertEqual(guidance_service.generator.generate.call_count, 1)
        self.assertEqual(pkg1.generated_at, pkg2.generated_at)

        # 3. Update application state -> Invalidation
        workflow_service.update_applicant_profile(case.application_id, {"age": 25})

        # 4. Third call -> Cache MISS (re-generated due to updated timestamp)
        pkg3 = guidance_service.generate_guidance(case.application_id, "s1")
        self.assertEqual(guidance_service.generator.generate.call_count, 2)

    def test_explicit_cache_invalidation(self):
        """Explicitly calling invalidate_cache clears the memory cache."""
        workflow_service = ApplicationWorkflowService()
        guidance_service = ApplicationGuidanceService(workflow_service=workflow_service)

        case = workflow_service.create_application()
        case.candidate_schemes["s2"] = SchemeEvaluation(
            scheme_id="s2",
            scheme_name="Grant",
            decision_status=StatutoryDecision.PASS,
        )
        workflow_service.repository.update(case)

        guidance_service.generate_guidance(case.application_id, "s2")
        self.assertTrue(len(guidance_service._cache) >= 1)

        guidance_service.invalidate_cache(case.application_id)
        self.assertEqual(len(guidance_service._cache), 0)


if __name__ == "__main__":
    unittest.main()
