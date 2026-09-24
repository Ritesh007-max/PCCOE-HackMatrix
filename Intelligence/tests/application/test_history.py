"""
Unit tests for Application Case Audit History.
Phase 10: Ensures immutable append-only event recording.
"""

import unittest
from src.application.status import EventType
from src.application.history import ApplicationHistoryManager, HistoryEvent


class TestApplicationHistory(unittest.TestCase):
    """Tests for history recording and query capabilities."""

    def test_record_and_retrieve_events(self):
        """Events are appended and retrieved in order."""
        history = ApplicationHistoryManager()
        app_id = "app_audit_01"

        history.record_event(
            application_id=app_id,
            event_type=EventType.APPLICATION_CREATED,
            actor="CITIZEN",
            new_state="DRAFT",
        )
        history.record_event(
            application_id=app_id,
            event_type=EventType.DOCUMENT_ADDED,
            actor="SYSTEM",
            metadata={"filename": "income.pdf"},
        )
        history.record_event(
            application_id=app_id,
            event_type=EventType.ELIGIBILITY_EVALUATED,
            old_state="PROCESSING",
            new_state="ELIGIBILITY_EVALUATED",
            metadata={"decision": "PASS"},
        )

        events = history.get_history(app_id)
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].event_type, EventType.APPLICATION_CREATED)
        self.assertEqual(events[1].event_type, EventType.DOCUMENT_ADDED)
        self.assertEqual(events[2].event_type, EventType.ELIGIBILITY_EVALUATED)

    def test_get_transitions(self):
        """get_transitions filters events that transitioned lifecycle states."""
        history = ApplicationHistoryManager()
        app_id = "app_transitions_01"

        history.record_event(
            application_id=app_id,
            event_type=EventType.APPLICATION_CREATED,
            new_state="DRAFT",
        )
        history.record_event(
            application_id=app_id,
            event_type=EventType.FACTS_UPDATED,
            metadata={"updated": ["age"]},  # No state change
        )
        history.record_event(
            application_id=app_id,
            event_type=EventType.READY_TO_APPLY,
            old_state="ELIGIBILITY_EVALUATED",
            new_state="READY_TO_APPLY",
        )

        transitions = history.get_transitions(app_id)
        self.assertEqual(len(transitions), 2)
        self.assertEqual(transitions[0].new_state, "DRAFT")
        self.assertEqual(transitions[1].new_state, "READY_TO_APPLY")

    def test_event_immutability(self):
        """HistoryEvent dataclass is frozen and cannot be modified."""
        event = HistoryEvent(
            event_id="evt_01",
            application_id="app_01",
            event_type=EventType.APPLICATION_CREATED,
            timestamp="2026-09-23T00:00:00Z",
        )
        with self.assertRaises(Exception):
            event.actor = "HACKER"  # type: ignore


if __name__ == "__main__":
    unittest.main()
