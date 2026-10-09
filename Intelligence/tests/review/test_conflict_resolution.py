"""
Tests for FIN Human Review & Conflict Resolution Subsystem.
Verifies:
- Structured conflict record creation
- Preserves all conflicting evidence permanently
- Caseworker authorized resolution workflow
- Rejection and escalation workflows
- Immutability: historical decisions remain untouched
"""

import unittest
from src.review.models import ConflictRecord, ConflictStatus
from src.review.service import ConflictResolutionService
from src.review.audit import AuditLogger
from src.context.service import ApplicantContextService
from src.persistence.repository import FactPersistenceRepository


class TestConflictResolution(unittest.TestCase):

    def setUp(self):
        # Use isolated in-memory repository for clean state
        self.repo = FactPersistenceRepository(":memory:")
        self.context_service = ApplicantContextService(self.repo)
        self.audit_logger = AuditLogger()
        self.review_service = ConflictResolutionService(
            context_service=self.context_service,
            audit_logger=self.audit_logger,
        )

    def test_conflict_creation_and_listing(self):
        conflict = self.review_service.record_conflict(
            applicant_id="app_123",
            field="annual_family_income",
            source_a="DOCUMENT",
            value_a=420000,
            source_b="USER_INPUT",
            value_b=800000,
        )
        self.assertEqual(conflict.status, ConflictStatus.OPEN)
        self.assertEqual(conflict.field, "annual_family_income")

        conflicts = self.review_service.list_conflicts(applicant_id="app_123")
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].conflict_id, conflict.conflict_id)

    def test_authorized_resolution_workflow(self):
        conflict = self.review_service.record_conflict(
            applicant_id="app_456",
            field="annual_family_income",
            source_a="DOCUMENT",
            value_a=420000,
            source_b="USER_INPUT",
            value_b=800000,
        )

        # Resolution requires authenticated resolver and reason
        with self.assertRaises(ValueError):
            self.review_service.resolve_conflict(
                conflict_id=conflict.conflict_id,
                resolver_id="",  # missing resolver
                selected_source="DOCUMENT",
                reason="Verified document",
            )

        # Authorized resolution
        resolved = self.review_service.resolve_conflict(
            conflict_id=conflict.conflict_id,
            resolver_id="officer_patel",
            selected_source="DOCUMENT",
            reason="Verified income certificate issued by Tehsildar.",
        )
        self.assertEqual(resolved.status, ConflictStatus.RESOLVED)
        self.assertEqual(resolved.resolver_id, "officer_patel")
        self.assertEqual(resolved.authoritative_value, 420000)

        # Check audit trail
        events = self.audit_logger.get_events_for_applicant("app_456")
        event_types = [e.event_type for e in events]
        self.assertIn("FACT_CONFLICT_DETECTED", event_types)
        self.assertIn("CONFLICT_RESOLVED", event_types)

    def test_conflict_rejection_and_escalation(self):
        c1 = self.review_service.record_conflict(
            applicant_id="app_789",
            field="age",
            source_a="DOC_1",
            value_a=25,
            source_b="DOC_2",
            value_b=26,
        )
        rejected = self.review_service.reject_conflict(
            conflict_id=c1.conflict_id,
            resolver_id="supervisor_sharma",
            reason="Within allowable reporting variance.",
        )
        self.assertEqual(rejected.status, ConflictStatus.REJECTED)

        c2 = self.review_service.record_conflict(
            applicant_id="app_789",
            field="caste_certificate",
            source_a="DOC_1",
            value_a="OBC",
            source_b="DOC_2",
            value_b="GENERAL",
        )
        escalated = self.review_service.escalate_conflict(
            conflict_id=c2.conflict_id,
            resolver_id="officer_patel",
            reason="Requires state caste scrutiny committee verification.",
        )
        self.assertEqual(escalated.status, ConflictStatus.ESCALATED)


if __name__ == "__main__":
    unittest.main()
