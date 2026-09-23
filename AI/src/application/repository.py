"""
Application Repository Abstraction and Local In-Memory Implementation.
Phase 10: Local repository boundary; future Backend will own durable database persistence.
"""

from abc import ABC, abstractmethod
import threading
from typing import Dict, List, Optional

from .case import ApplicationCase
from .decision import DecisionSnapshot
from .history import HistoryEvent
from .review import ReviewCase
from .exceptions import ImmutableSnapshotError, ApplicationNotFoundError


class ApplicationRepository(ABC):
    """
    Abstract interface for persisting application cases, decision snapshots,
    audit histories, and review cases.
    """

    @abstractmethod
    def save(self, case: ApplicationCase) -> None:
        """Create or save an application case."""
        pass

    @abstractmethod
    def get(self, application_id: str) -> Optional[ApplicationCase]:
        """Retrieve an application case by ID."""
        pass

    @abstractmethod
    def update(self, case: ApplicationCase) -> None:
        """Update an existing application case."""
        pass

    @abstractmethod
    def append_history(self, event: HistoryEvent) -> None:
        """Append an immutable audit history event."""
        pass

    @abstractmethod
    def get_history(self, application_id: str) -> List[HistoryEvent]:
        """Retrieve all audit history events for an application."""
        pass

    @abstractmethod
    def save_decision_snapshot(self, snapshot: DecisionSnapshot) -> None:
        """Persist an immutable decision snapshot."""
        pass

    @abstractmethod
    def get_decision_snapshot(self, snapshot_id: str) -> Optional[DecisionSnapshot]:
        """Retrieve a decision snapshot by its unique snapshot ID."""
        pass

    @abstractmethod
    def list_decision_snapshots(self, application_id: str) -> List[DecisionSnapshot]:
        """List all decision snapshots created for an application case."""
        pass

    @abstractmethod
    def save_review_case(self, review: ReviewCase) -> None:
        """Persist a manual review case."""
        pass

    @abstractmethod
    def get_review_case(self, review_id: str) -> Optional[ReviewCase]:
        """Retrieve a review case by ID."""
        pass

    @abstractmethod
    def list_review_cases(self, application_id: str) -> List[ReviewCase]:
        """List all review cases associated with an application."""
        pass


class InMemoryApplicationRepository(ApplicationRepository):
    """
    Thread-safe in-memory repository for Phase 10 local execution.
    NOTE: Backend microservices will own permanent multi-tenant relational persistence.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._cases: Dict[str, ApplicationCase] = {}
        self._history: Dict[str, List[HistoryEvent]] = {}
        self._snapshots: Dict[str, DecisionSnapshot] = {}
        self._case_snapshots: Dict[str, List[str]] = {}
        self._reviews: Dict[str, ReviewCase] = {}
        self._case_reviews: Dict[str, List[str]] = {}

    def save(self, case: ApplicationCase) -> None:
        with self._lock:
            self._cases[case.application_id] = case

    def get(self, application_id: str) -> Optional[ApplicationCase]:
        with self._lock:
            return self._cases.get(application_id)

    def update(self, case: ApplicationCase) -> None:
        with self._lock:
            if case.application_id not in self._cases:
                raise ApplicationNotFoundError(case.application_id)
            self._cases[case.application_id] = case

    def append_history(self, event: HistoryEvent) -> None:
        with self._lock:
            if event.application_id not in self._history:
                self._history[event.application_id] = []
            self._history[event.application_id].append(event)

    def get_history(self, application_id: str) -> List[HistoryEvent]:
        with self._lock:
            return list(self._history.get(application_id, []))

    def save_decision_snapshot(self, snapshot: DecisionSnapshot) -> None:
        with self._lock:
            if snapshot.snapshot_id in self._snapshots:
                raise ImmutableSnapshotError(
                    snapshot.snapshot_id,
                    field_name="snapshot_id (overwrite prohibited)",
                )
            self._snapshots[snapshot.snapshot_id] = snapshot
            if snapshot.application_id not in self._case_snapshots:
                self._case_snapshots[snapshot.application_id] = []
            self._case_snapshots[snapshot.application_id].append(snapshot.snapshot_id)

    def get_decision_snapshot(self, snapshot_id: str) -> Optional[DecisionSnapshot]:
        with self._lock:
            return self._snapshots.get(snapshot_id)

    def list_decision_snapshots(self, application_id: str) -> List[DecisionSnapshot]:
        with self._lock:
            snap_ids = self._case_snapshots.get(application_id, [])
            return [self._snapshots[sid] for sid in snap_ids if sid in self._snapshots]

    def save_review_case(self, review: ReviewCase) -> None:
        with self._lock:
            self._reviews[review.review_id] = review
            if review.application_id not in self._case_reviews:
                self._case_reviews[review.application_id] = []
            if review.review_id not in self._case_reviews[review.application_id]:
                self._case_reviews[review.application_id].append(review.review_id)

    def get_review_case(self, review_id: str) -> Optional[ReviewCase]:
        with self._lock:
            return self._reviews.get(review_id)

    def list_review_cases(self, application_id: str) -> List[ReviewCase]:
        with self._lock:
            rev_ids = self._case_reviews.get(application_id, [])
            return [self._reviews[rid] for rid in rev_ids if rid in self._reviews]
