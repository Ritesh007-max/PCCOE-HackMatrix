"""
FIN API Middlewares.
Handles request ID correlation tracing, structured telemetry logging with secret redaction,
security response headers, request size protection, and multi-tier rate limiting.
"""

import collections
from enum import Enum
import logging
import re
import time
from typing import Any, Callable, Deque, Dict, Optional, Tuple
import uuid
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config import DEFAULT_SERVICE_CONFIG, ServiceConfig
from .errors import RateLimitExceededError
from src.utils.secret_redactor import SecretRedactingLoggingFilter

logger = logging.getLogger("fin.api.access")
# Attach zero-trust secret and PII redactor to access logger
logger.addFilter(SecretRedactingLoggingFilter())

REQUEST_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")


class RateLimitTier(str, Enum):
    """Operational rate limiting tiers based on endpoint computational expense."""
    PUBLIC = "public"
    PROTECTED = "protected"
    EXPENSIVE = "expensive"


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """
    Propagates or generates correlation X-Request-ID across the request lifecycle.
    Validates formatting and length to prevent header injection or spoofing.
    Attaches the ID to request.state and adds it to the outgoing HTTP headers.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        incoming_id = request.headers.get("X-Request-ID", "").strip()
        if incoming_id and REQUEST_ID_REGEX.match(incoming_id):
            request_id = incoming_id
        else:
            request_id = f"req_{uuid.uuid4().hex[:16]}"

        request.state.request_id = request_id

        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Applies production-grade HTTP security response headers.
    Defends against MIME type sniffing, clickjacking, and XSS.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        response.headers["X-XSS-Protection"] = "0"
        return response


class RequestBodyLimitMiddleware(BaseHTTPMiddleware):
    """
    Guards against oversized HTTP payload attacks by inspecting Content-Length early.
    """
    def __init__(self, app: Any, max_bytes: int = 30 * 1024 * 1024):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length = request.headers.get("Content-Length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_bytes:
                    req_id = getattr(request.state, "request_id", None)
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": {
                                "code": "PAYLOAD_TOO_LARGE",
                                "message": f"Request body size {length} bytes exceeds maximum limit of {self.max_bytes} bytes.",
                                "request_id": req_id,
                            }
                        },
                    )
            except ValueError:
                pass
        return await call_next(request)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Records structured audit log for each incoming HTTP transaction.
    Measures total latency and ensures no sensitive headers, PII, or secrets are logged.
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
    Multi-tier sliding-window rate limiter.
    Separates PUBLIC (60 req/min), PROTECTED (120 req/min), and EXPENSIVE (20 req/min) operations.
    """
    def __init__(self, config: ServiceConfig):
        self.enabled = config.rate_limit_enabled
        self.limit = config.rate_limit_per_minute
        self.limit_public = getattr(config, "rate_limit_public", 60)
        self.limit_protected = getattr(config, "rate_limit_protected", 120)
        self.limit_expensive = getattr(config, "rate_limit_expensive", 20)
        self.window_seconds = 60.0
        self._history: Dict[Tuple[str, str], Deque[float]] = collections.defaultdict(collections.deque)

    def get_tier_for_path(self, path: str) -> RateLimitTier:
        """Determines rate limit tier for a given endpoint path."""
        p = path.lower()
        if p.startswith("/v1/documents") or p.startswith("/v1/applications") or p.startswith("/v1/chat") or p.startswith("/v1/policy/sync") or p.startswith("/v1/policy/rollback"):
            return RateLimitTier.EXPENSIVE
        elif p.startswith("/health/live"):
            return RateLimitTier.PUBLIC
        return RateLimitTier.PROTECTED

    def get_limit(self, tier: RateLimitTier) -> int:
        if tier == RateLimitTier.EXPENSIVE:
            return self.limit_expensive
        elif tier == RateLimitTier.PUBLIC:
            return self.limit_public
        return self.limit_protected

    def check(self, client_key: str, tier: RateLimitTier = RateLimitTier.PROTECTED) -> None:
        """Checks rate limit for client key in a specific tier. Raises RateLimitExceededError if over limit."""
        if not self.enabled:
            return

        tier_limit = self.get_limit(tier)
        if tier_limit <= 0:
            return

        now = time.monotonic()
        bucket_key = (client_key, tier.value)
        timestamps = self._history[bucket_key]

        # Evict timestamps older than 60s
        while timestamps and (now - timestamps[0]) > self.window_seconds:
            timestamps.popleft()

        if len(timestamps) >= tier_limit:
            logger.warning(
                "Rate limit exceeded for client %s on tier %s (%d requests in 60s)",
                client_key, tier.value, len(timestamps)
            )
            raise RateLimitExceededError(
                f"Rate limit exceeded for {tier.value} tier ({tier_limit} req/min). Please try again shortly."
            )

        timestamps.append(now)

    def check_rate_limit(
        self,
        client_key: str,
        config: Optional[ServiceConfig] = None,
        tier: RateLimitTier = RateLimitTier.PROTECTED
    ) -> Tuple[bool, int]:
        """Checks rate limit for client key. Returns (allowed: bool, retry_after: int)."""
        cfg_enabled = config.rate_limit_enabled if config else self.enabled
        tier_limit = self.get_limit(tier) if not config else config.rate_limit_per_minute

        if not cfg_enabled or tier_limit <= 0:
            return True, 0

        now = time.monotonic()
        bucket_key = (client_key, tier.value)
        timestamps = self._history[bucket_key]
        while timestamps and (now - timestamps[0]) > self.window_seconds:
            timestamps.popleft()

        if len(timestamps) >= tier_limit:
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
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(StructuredLoggingMiddleware)
    app.add_middleware(RequestCorrelationMiddleware)
