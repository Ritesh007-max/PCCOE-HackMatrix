"""
FIN API Centralized Error Handling.
Translates internal domain exceptions into consistent, safe HTTP responses
without leaking internal stack traces, API keys, or infrastructure secrets.
All error payloads pass through the zero-trust secret redactor.
"""

import logging
import re
from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .schemas import ApiErrorDetail, ApiErrorResponse
from src.utils.secret_redactor import redact_secrets

logger = logging.getLogger("fin.api.errors")

# Pattern to detect filesystem paths in error strings
PATH_LEAK_PATTERN = re.compile(r"(?:[a-zA-Z]:\\|\/Users\/|\/home\/|\/var\/)[^:\s\"']+")


class APIError(Exception):
    """Base class for explicit API errors."""
    def __init__(
        self,
        message: str = "Bad request",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: str = "BAD_REQUEST",
        details: Optional[Any] = None,
        error_code: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = error_code or code
        self.details = details


class RateLimitExceededError(APIError):
    """Raised when client exceeds rate limit threshold."""
    def __init__(self, message: str = "Rate limit exceeded. Please retry later.", retry_after: int = 60):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="RATE_LIMIT_EXCEEDED"
        )
        self.retry_after = retry_after


class PayloadTooLargeError(APIError):
    """Raised when upload or request payload exceeds maximum byte allowance."""
    def __init__(self, message: str = "Request payload exceeds size limit."):
        super().__init__(
            message=message,
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            code="PAYLOAD_TOO_LARGE"
        )


class UnsupportedMediaTypeError(APIError):
    """Raised when uploaded file has an unsupported format or MIME type."""
    def __init__(self, message: str = "Unsupported document format."):
        super().__init__(
            message=message,
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            code="UNSUPPORTED_MEDIA_TYPE"
        )


def _get_request_id(request: Request) -> Optional[str]:
    """Retrieves correlation request_id stored in request state."""
    return getattr(request.state, "request_id", None)


def _sanitize_error_text(text: str) -> str:
    """Removes sensitive secrets and filesystem paths from error messages."""
    if not text:
        return ""
    # 1. Redact API keys and PII
    cleaned = redact_secrets(text)
    # 2. Mask absolute filesystem paths
    cleaned = PATH_LEAK_PATTERN.sub("[PATH_REDACTED]", cleaned)
    return cleaned


def build_error_response(
    status_code: int,
    code: str,
    message: str,
    request_id: Optional[str] = None,
    details: Optional[Any] = None,
) -> JSONResponse:
    """Creates a consistent, secret-redacted ApiErrorResponse JSON payload."""
    safe_message = _sanitize_error_text(message)

    safe_details = details
    if isinstance(details, str):
        safe_details = _sanitize_error_text(details)
    elif isinstance(details, list):
        safe_details = [
            {k: _sanitize_error_text(str(v)) if isinstance(v, str) else v for k, v in item.items()}
            if isinstance(item, dict) else _sanitize_error_text(str(item))
            for item in details
        ]
    elif isinstance(details, dict):
        safe_details = {k: _sanitize_error_text(str(v)) if isinstance(v, str) else v for k, v in details.items()}

    payload = ApiErrorResponse(
        error=ApiErrorDetail(
            code=code,
            message=safe_message,
            request_id=request_id,
            details=safe_details,
        )
    ).model_dump()
    return JSONResponse(status_code=status_code, content=payload)


def register_exception_handlers(app: FastAPI) -> None:
    """Registers centralized exception handlers on the FastAPI application."""

    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
        req_id = _get_request_id(request)
        logger.warning(
            "API error: code=%s status=%d req_id=%s msg=%s",
            exc.code, exc.status_code, req_id, exc.message
        )
        return build_error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            request_id=req_id,
            details=exc.details,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        req_id = _get_request_id(request)
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            413: "PAYLOAD_TOO_LARGE",
            415: "UNSUPPORTED_MEDIA_TYPE",
            429: "TOO_MANY_REQUESTS",
            500: "INTERNAL_SERVER_ERROR",
            503: "SERVICE_UNAVAILABLE",
        }
        code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
        raw_detail = exc.detail
        detail_msg = raw_detail if isinstance(raw_detail, str) else str(raw_detail)
        return build_error_response(
            status_code=exc.status_code,
            code=code,
            message=detail_msg,
            request_id=req_id,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        req_id = _get_request_id(request)
        errors = []
        for err in exc.errors():
            loc = ".".join(str(x) for x in err.get("loc", []))
            msg = err.get("msg", "Invalid value")
            errors.append({"field": loc, "issue": _sanitize_error_text(msg)})

        return build_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message="Request input validation failed.",
            request_id=req_id,
            details=errors,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        req_id = _get_request_id(request)
        # Log internal detail on server side for developers (filtered by SecretRedactingLoggingFilter)
        logger.error(
            "Unhandled exception on %s %s [req_id=%s]: %s",
            request.method, request.url.path, req_id, exc,
            exc_info=True
        )
        # Strictly return generic, safe error message to external client
        return build_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred while processing the request.",
            request_id=req_id,
        )
