"""
Unit tests for ApplicationWorkflowService.
Phase 10: Service methods orchestration, state handling, and idempotency.
"""

import unittest
from unittest.mock import MagicMock
from src.application.service import ApplicationWorkflowService
from src.application.status import (
    ApplicationStatus,
    StatutoryDecision,
    ReadinessStatus,
    ReviewReason,
    ReviewStatus,
)
from src.application.repository import InMemoryApplicationRepository
from src.application.exceptions import ApplicationNotFoundError
from src.rules.models import RuleStatus


class TestApplicationWorkflowService(unittest.TestCase):
    """Tests for ApplicationWorkflowService orchestration."""

    def setUp(self):
        self.repo = InMemoryApplicationRepository()
        self.service = ApplicationWorkflowService(repository=self.repo)

    def test_create_and_get_application(self):
        """Creates an application and retrieves it from repository."""
        case = self.service.create_application(citizen_reference="user_42", metadata={"channel": "web"})
        self.assertTrue(case.application_id.startswith("app_"))
        self.assertEqual(case.current_status, ApplicationStatus.DRAFT)
        self.assertEqual(case.citizen_reference, "user_42")

        fetched = self.service.get_application_state(case.application_id)
        self.assertEqual(fetched.application_id, case.application_id)

    def test_get_nonexistent_application_raises(self):
        """Querying an unknown application ID raises ApplicationNotFoundError."""
        with self.assertRaises(ApplicationNotFoundError):
            self.service.get_application_state("app_unknown_id")

    def test_attach_document(self):
        """Attaching a document computes hash and updates status to DOCUMENTS_PENDING."""
        case = self.service.create_application()
        doc_bytes = b"%PDF-1.4 test document content for hash verification"

        doc_ref = self.service.attach_document(
            application_id=case.application_id,
            filename="income_cert.pdf",
            document_type="income_certificate",
            content_bytes=doc_bytes,
        )

        self.assertTrue(doc_ref.document_id.startswith("doc_"))
        self.assertEqual(doc_ref.filename, "income_cert.pdf")
        self.assertTrue(len(doc_ref.sha256_hash) > 0)

        updated_case = self.service.get_application_state(case.application_id)
        self.assertEqual(updated_case.current_status, ApplicationStatus.DOCUMENTS_PENDING)
        self.assertIn(doc_ref.document_id, updated_case.documents)

    def test_update_applicant_profile(self):
        """Updates facts and transitions to FACTS_READY."""
        case = self.service.create_application()
        updated = self.service.update_applicant_profile(
            application_id=case.application_id,
            facts={"age": 25, "gender": "Female", "state": "Rajasthan"},
        )
        self.assertEqual(updated.current_status, ApplicationStatus.FACTS_READY)
        self.assertEqual(updated.facts.facts["age"], 25)
        self.assertEqual(updated.facts.facts["state"], "Rajasthan")

    def test_request_manual_review(self):
        """Manually flagging case for review creates ReviewCase and transitions to UNDER_REVIEW."""
        case = self.service.create_application()
        self.service.update_applicant_profile(case.application_id, {"age": 25})

        review = self.service.request_manual_review(
            application_id=case.application_id,
            reason=ReviewReason.DOCUMENT_AMBIGUITY,
            scheme_id="scheme_test",
        )

        self.assertTrue(review.review_id.startswith("rev_"))
        self.assertEqual(review.status, ReviewStatus.OPEN)

        updated_case = self.service.get_application_state(case.application_id)
        self.assertEqual(updated_case.current_status, ApplicationStatus.UNDER_REVIEW)

        # Check repository has the review
        reviews = self.repo.list_review_cases(case.application_id)
        self.assertEqual(len(reviews), 1)

    def test_idempotency_cache(self):
        """Submitting with identical idempotency_key returns cached application without re-running."""
        case = self.service.create_application()
        idemp_key = "idemp_abc_123"

        # Mock the pipeline
        mock_result = MagicMock()
        mock_result.documents_processed = []
        mock_result.applicant_profile = {"age": 22}
        mock_result.conflicts_detected = []
        mock_result.missing_information = {}
        mock_result.retrieved_schemes = []
        mock_result.eligibility_decision = {"scheme_id": "s1", "status": "PASS", "eligible": True}
        mock_result.benefit_calculation = None

        self.service.pipeline.process_application = MagicMock(return_value=mock_result)  # type: ignore

        # First call
        res1 = self.service.process_documents(
            application_id=case.application_id,
            document_inputs=["dummy_doc.pdf"],
            idempotency_key=idemp_key,
        )
        self.assertEqual(self.service.pipeline.process_application.call_count, 1)

        # Second call with same idempotency key
        res2 = self.service.process_documents(
            application_id=case.application_id,
            document_inputs=["dummy_doc.pdf"],
            idempotency_key=idemp_key,
        )
        # Should NOT call pipeline again
        self.assertEqual(self.service.pipeline.process_application.call_count, 1)
        self.assertEqual(res1.application_id, res2.application_id)


if __name__ == "__main__":
    unittest.main()
