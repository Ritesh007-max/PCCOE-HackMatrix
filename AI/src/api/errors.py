"""
PolicySetu API Centralized Error Handling.
Translates internal domain exceptions into consistent, safe HTTP responses
without leaking internal stack traces, API keys, or infrastructure secrets.
"""

import logging
from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .schemas import ApiErrorDetail, ApiErrorResponse

logger = logging.getLogger("policysetu.api.errors")


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


def build_error_response(
    status_code: int,
    code: str,
    message: str,
    request_id: Optional[str] = None,
    details: Optional[Any] = None,
) -> JSONResponse:
    """Creates a consistent ApiErrorResponse JSON payload."""
    payload = ApiErrorResponse(
        error=ApiErrorDetail(
            code=code,
            message=message,
            request_id=request_id,
            details=details,
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
        return build_error_response(
            status_code=exc.status_code,
            code=code,
            message=str(exc.detail),
            request_id=req_id,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        req_id = _get_request_id(request)
        errors = []
        for err in exc.errors():
            loc = ".".join(str(x) for x in err.get("loc", []))
            msg = err.get("msg", "Invalid value")
            errors.append({"field": loc, "issue": msg})

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
        logger.error(
            "Unhandled exception on %s %s [req_id=%s]: %s",
            request.method, request.url.path, req_id, exc,
            exc_info=True
        )
        return build_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred while processing the request.",
            request_id=req_id,
        )
