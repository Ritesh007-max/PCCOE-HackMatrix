"""
PolicySetu API Middlewares.
Handles request ID correlation tracing, structured telemetry logging,
and dev-friendly in-memory rate limiting without leaking secrets.
"""

import collections
import logging
import time
import uuid
from typing import Callable, Deque, Dict, Optional, Tuple
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .config import DEFAULT_SERVICE_CONFIG, ServiceConfig
from .errors import RateLimitExceededError

logger = logging.getLogger("policysetu.api.access")


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """
    Propagates or generates correlation X-Request-ID across the request lifecycle.
    Attaches the ID to request.state and adds it to the outgoing HTTP headers.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        incoming_id = request.headers.get("X-Request-ID", "").strip()
        request_id = incoming_id if incoming_id else f"req_{uuid.uuid4().hex[:16]}"
        request.state.request_id = request_id

        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Records structured audit log for each incoming HTTP transaction.
    Measures total latency and ensures no sensitive headers or secrets are logged.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        req_id = getattr(request.state, "request_id", "unknown")
        method = request.method
        path = request.url.path

        response: Response = await call_next(request)
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        # Structured access log entry
        logger.info(
            "HTTP %s %s status=%d latency=%.2fms req_id=%s",
            method, path, response.status_code, latency_ms, req_id
        )
        return response


class InMemoryRateLimiter:
    """
    Dev-friendly sliding-window rate limiter.
    Disabled by default in development; configurable through environment variables.
    """
    def __init__(self, config: ServiceConfig):
        self.enabled = config.rate_limit_enabled
        self.limit = config.rate_limit_per_minute
        self.window_seconds = 60.0
        self._history: Dict[str, Deque[float]] = collections.defaultdict(collections.deque)

    def check(self, client_key: str) -> None:
        """Checks rate limit for client key. Raises RateLimitExceededError if over limit."""
        if not self.enabled or self.limit <= 0:
            return

        now = time.monotonic()
        timestamps = self._history[client_key]

        # Evict timestamps older than 60s
        while timestamps and (now - timestamps[0]) > self.window_seconds:
            timestamps.popleft()

        if len(timestamps) >= self.limit:
            logger.warning("Rate limit exceeded for client %s (%d requests in 60s)", client_key, len(timestamps))
            raise RateLimitExceededError(
                f"Rate limit exceeded ({self.limit} req/min). Please try again shortly."
            )

        timestamps.append(now)

    def check_rate_limit(self, client_key: str, config: Optional[ServiceConfig] = None) -> Tuple[bool, int]:
        """Checks rate limit for client key. Returns (allowed: bool, retry_after: int)."""
        cfg_enabled = config.rate_limit_enabled if config else self.enabled
        cfg_limit = config.rate_limit_per_minute if config else self.limit
        if not cfg_enabled or cfg_limit <= 0:
            return True, 0

        now = time.monotonic()
        timestamps = self._history[client_key]
        while timestamps and (now - timestamps[0]) > self.window_seconds:
            timestamps.popleft()

        if len(timestamps) >= cfg_limit:
            retry_after = int(self.window_seconds - (now - timestamps[0])) + 1
            return False, max(1, retry_after)

        timestamps.append(now)
        return True, 0

    def reset(self) -> None:
        """Clears all in-memory rate limiting history."""
        self._history.clear()


# Default limiter instance
DEFAULT_RATE_LIMITER = InMemoryRateLimiter(DEFAULT_SERVICE_CONFIG)


def register_middlewares(app: FastAPI, config: Optional[ServiceConfig] = None) -> None:
    """Registers standard middlewares in order on the FastAPI application."""
    # Note: Middlewares run in reverse order of addition
    app.add_middleware(StructuredLoggingMiddleware)
    app.add_middleware(RequestCorrelationMiddleware)
