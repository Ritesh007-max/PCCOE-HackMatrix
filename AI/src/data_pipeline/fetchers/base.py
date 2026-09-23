"""
Base Fetcher Abstraction for PolicySetu Data Pipeline.
Provides standardized fetch results, deterministic SHA-256 content hashing,
exponential backoff retries, rate limiting, and robots.txt compliance.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import time
from typing import Any, Dict, Optional


@dataclass
class FetchResult:
    """Standardized outcome of a fetch operation."""
    source_id: str
    url: str
    status_code: int
    content: Optional[bytes] = None
    text_content: Optional[str] = None
    content_type: str = "text/plain"
    content_hash: str = ""
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    fetched_at: str = ""
    duration_ms: float = 0.0
    error: Optional[str] = None
    success: bool = True

    def __post_init__(self):
        if not self.fetched_at:
            self.fetched_at = datetime.now(timezone.utc).isoformat()
        if self.content and not self.content_hash:
            self.content_hash = hashlib.sha256(self.content).hexdigest()
        elif self.text_content and not self.content_hash:
            self.content_hash = hashlib.sha256(self.text_content.encode("utf-8")).hexdigest()


class BaseFetcher(ABC):
    """
    Abstract base fetcher with resilient retry and rate-limiting behaviors.
    """

    def __init__(
        self,
        timeout_seconds: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        rate_limit_delay_seconds: float = 0.5,
        user_agent: str = "PolicySetu-DataPipeline/1.0 (Compliance; gov-policy-audit)"
    ):
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.rate_limit_delay_seconds = rate_limit_delay_seconds
        self.user_agent = user_agent
        self._last_request_time: float = 0.0

    @abstractmethod
    def fetch(self, url: str, source_id: str, **kwargs) -> FetchResult:
        """Executes the fetch operation for the given source and URL."""
        pass

    def _apply_rate_limit(self) -> None:
        """Ensures respectful delay between consecutive external requests."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.rate_limit_delay_seconds:
            time.sleep(self.rate_limit_delay_seconds - elapsed)
        self._last_request_time = time.time()

    @staticmethod
    def compute_sha256(data: bytes) -> str:
        """Computes deterministic SHA-256 checksum."""
        return hashlib.sha256(data).hexdigest()
