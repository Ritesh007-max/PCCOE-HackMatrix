# Phase 10: Persistence Layer Abstraction

## 1. Local Persistence Boundary

Phase 10 implements an abstract repository pattern to decouple workflow business logic from underlying storage mechanisms:

```python
class ApplicationRepository(ABC):
    @abstractmethod
    def save(self, case: ApplicationCase) -> None: ...
    @abstractmethod
    def get(self, application_id: str) -> Optional[ApplicationCase]: ...
    @abstractmethod
    def update(self, case: ApplicationCase) -> None: ...
    @abstractmethod
    def append_history(self, event: HistoryEvent) -> None: ...
    @abstractmethod
    def get_history(self, application_id: str) -> List[HistoryEvent]: ...
    @abstractmethod
    def save_decision_snapshot(self, snapshot: DecisionSnapshot) -> None: ...
    @abstractmethod
    def get_decision_snapshot(self, snapshot_id: str) -> Optional[DecisionSnapshot]: ...
    @abstractmethod
    def list_decision_snapshots(self, application_id: str) -> List[DecisionSnapshot]: ...
    @abstractmethod
    def save_review_case(self, review: ReviewCase) -> None: ...
    @abstractmethod
    def get_review_case(self, review_id: str) -> Optional[ReviewCase]: ...
    @abstractmethod
    def list_review_cases(self, application_id: str) -> List[ReviewCase]: ...
```

---

## 2. In-Memory Implementation for Phase 10

For Phase 10, `InMemoryApplicationRepository` provides a thread-safe, zero-dependency in-memory implementation:
- Protected by `threading.RLock()` to support concurrent requests.
- Validates that cases exist on update (raising `ApplicationNotFoundError`).
- Enforces snapshot immutability by refusing duplicate `snapshot_id` writes (raising `ImmutableSnapshotError`).
- Provides chronological indexing for snapshots and audit history.

> [!NOTE]
> The AI microservice layer owns workflow state required during active processing. The future **Backend** subsystem will implement persistent database storage (PostgreSQL / Redis) for durable citizen accounts and multi-tenant persistence.
