"""
FIN Conversation Store.
Thread-safe, tenant-isolated store for multi-turn conversation states.
Ensures Applicant A's state can never be accessed or leaked to Applicant B.
"""

from datetime import datetime, timezone
import logging
import threading
from typing import Dict, List, Optional, Tuple

from .models import ConversationState

logger = logging.getLogger("fin.conversation.store")


class ConversationStore:
    """
    In-memory conversation store enforcing strict applicant isolation.
    Keys are strictly (applicant_id, conversation_id).
    """

    def __init__(self, max_conversations_per_applicant: int = 50):
        self._lock = threading.Lock()
        # Key: (applicant_id, conversation_id) -> ConversationState
        self._states: Dict[Tuple[str, str], ConversationState] = {}
        self._max_per_app = max_conversations_per_applicant

    def get_or_create(
        self,
        applicant_id: str,
        conversation_id: str,
        language: str = "en",
    ) -> ConversationState:
        """
        Retrieves existing conversation state for the specific applicant,
        or creates a new state if none exists.
        Prevents cross-applicant access by requiring matching applicant_id.
        """
        if not applicant_id:
            raise ValueError("applicant_id is required to access conversation state.")
        if not conversation_id:
            raise ValueError("conversation_id is required.")

        key = (str(applicant_id).strip(), str(conversation_id).strip())

        with self._lock:
            if key in self._states:
                state = self._states[key]
                if language and state.language != language:
                    state.language = language
                    state.updated_at = datetime.now(timezone.utc).isoformat()
                return state

            new_state = ConversationState(
                conversation_id=conversation_id,
                applicant_id=applicant_id,
                language=language or "en",
            )
            self._states[key] = new_state
            logger.info("Created conversation %s for applicant %s", conversation_id, applicant_id)
            return new_state

    def get(self, applicant_id: str, conversation_id: str) -> Optional[ConversationState]:
        """Gets conversation state if matching applicant_id owns it, else returns None."""
        if not applicant_id or not conversation_id:
            return None
        key = (str(applicant_id).strip(), str(conversation_id).strip())
        with self._lock:
            return self._states.get(key)

    def save(self, state: ConversationState) -> None:
        """Saves conversation state."""
        key = (str(state.applicant_id).strip(), str(state.conversation_id).strip())
        with self._lock:
            state.updated_at = datetime.now(timezone.utc).isoformat()
            self._states[key] = state

    def clear(self, applicant_id: str, conversation_id: Optional[str] = None) -> None:
        """Clears specific conversation or all conversations for an applicant."""
        with self._lock:
            if conversation_id:
                key = (str(applicant_id).strip(), str(conversation_id).strip())
                self._states.pop(key, None)
            else:
                to_delete = [k for k in self._states if k[0] == str(applicant_id).strip()]
                for k in to_delete:
                    self._states.pop(k, None)

    def list_for_applicant(self, applicant_id: str) -> List[ConversationState]:
        """Lists all conversation states belonging to an applicant."""
        app_key = str(applicant_id).strip()
        with self._lock:
            return [state for k, state in self._states.items() if k[0] == app_key]
