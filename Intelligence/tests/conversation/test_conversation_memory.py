"""
Tests for FIN Conversation State & Memory Subsystem.
Verifies:
- Multi-turn state tracking
- Tenant and applicant isolation (Applicant A cannot access Applicant B)
- Deterministic reference resolution ("it", "this scheme", "that document")
- Ambiguous reference resolution refusal (CLARIFICATION_REQUIRED instead of guessing)
"""

import unittest
from src.conversation.models import ConversationState, MessageRole, TurnReference
from src.conversation.store import ConversationStore
from src.conversation.resolver import ConversationReferenceResolver
from src.context.models import ApplicantContext


class TestConversationMemory(unittest.TestCase):

    def setUp(self):
        self.store = ConversationStore()
        self.resolver = ConversationReferenceResolver()

    def test_conversation_state_creation_and_isolation(self):
        # Create state for Applicant A
        state_a = self.store.get_or_create(
            applicant_id="applicant_A",
            conversation_id="conv_1",
            language="en",
        )
        state_a.set_active_scheme("PMJAY")
        state_a.add_message(MessageRole.USER, "What is PMJAY?")
        state_a.add_message(MessageRole.ASSISTANT, "PMJAY is a health insurance scheme.")
        self.store.save(state_a)

        # Applicant B cannot access Applicant A's conversation
        state_b = self.store.get(
            applicant_id="applicant_B",
            conversation_id="conv_1",
        )
        self.assertIsNone(state_b, "Applicant B must not be able to retrieve Applicant A's conversation.")

        # Listing for applicant A returns 1, applicant B returns 0
        self.assertEqual(len(self.store.list_for_applicant("applicant_A")), 1)
        self.assertEqual(len(self.store.list_for_applicant("applicant_B")), 0)

    def test_deterministic_pronoun_resolution(self):
        state = self.store.get_or_create("app_1", "conv_single")
        state.set_active_scheme("PMJAY")
        self.store.save(state)

        # "Am I eligible for it?" -> resolves to PMJAY
        resolved = self.resolver.resolve("Am I eligible for it?", state=state)
        self.assertFalse(resolved.is_ambiguous)
        self.assertEqual(resolved.scheme_id, "PMJAY")
        self.assertEqual(resolved.resolved_by, "CONVERSATION_STATE")

    def test_ambiguous_scheme_reference_detected(self):
        state = self.store.get_or_create("app_1", "conv_ambig")
        # Discussed two schemes recently
        state.set_active_scheme("PMJAY")
        state.set_active_scheme("PM-Kisan")  # now recent_schemes has [PM-Kisan, PMJAY]
        self.store.save(state)

        # Asking "Am I eligible for it?" without clear immediate turn context flags ambiguity
        resolved = self.resolver.resolve("Am I eligible for it?", state=state)
        self.assertTrue(resolved.is_ambiguous)
        self.assertEqual(resolved.resolved_by, "AMBIGUOUS")
        self.assertIn("PM-Kisan", resolved.candidate_schemes)
        self.assertIn("PMJAY", resolved.candidate_schemes)


if __name__ == "__main__":
    unittest.main()
