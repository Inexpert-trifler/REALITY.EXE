import logging
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        code: str = "INTERNAL_SERVER_ERROR",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}


class NotFoundException(AppException):
    """Resource not found exception (404)."""

    def __init__(self, message: str = "Resource not found", details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            details=details,
        )


class BadRequestException(AppException):
    """Bad request exception (400)."""

    def __init__(self, message: str = "Bad request", details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            code="BAD_REQUEST",
            details=details,
        )


class UnauthorizedException(AppException):
    """Authentication required exception (401)."""

    def __init__(
        self, message: str = "Authentication required", details: dict[str, Any] | None = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            details=details,
        )


class ForbiddenException(AppException):
    """Permission denied exception (403)."""

    def __init__(self, message: str = "Permission denied", details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            details=details,
        )


class ConflictException(AppException):
    """Resource conflict exception (409)."""

    def __init__(self, message: str = "Resource conflict", details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            code="CONFLICT",
            details=details,
        )


class InternalServerErrorException(AppException):
    """Internal server error exception (500)."""

    def __init__(
        self, message: str = "Internal server error", details: dict[str, Any] | None = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="INTERNAL_SERVER_ERROR",
            details=details,
        )


def _format_error_payload(
    code: str, message: str, details: dict[str, Any], request_id: str | None = None
) -> dict[str, Any]:
    payload = {
        "error": {
            "code": code,
            "message": message,
            "details": details,
        }
    }
    if request_id:
        payload["error"]["request_id"] = request_id
    return payload


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.warning(f"AppException: [{exc.code}] {exc.message} (Request ID: {request_id})")
    return JSONResponse(
        status_code=exc.status_code,
        content=_format_error_payload(exc.code, exc.message, exc.details, request_id),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.warning(f"HTTPException: [{exc.status_code}] {exc.detail} (Request ID: {request_id})")
    code = "HTTP_ERROR"
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        code = "NOT_FOUND"
    elif exc.status_code == status.HTTP_401_UNAUTHORIZED:
        code = "UNAUTHORIZED"
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        code = "FORBIDDEN"
    elif exc.status_code == status.HTTP_400_BAD_REQUEST:
        code = "BAD_REQUEST"

    message = str(exc.detail) if isinstance(exc.detail, str) else "HTTP Error"
    details = exc.detail if isinstance(exc.detail, dict) else {}

    return JSONResponse(
        status_code=exc.status_code,
        content=_format_error_payload(code, message, details, request_id),
    )


def _sanitize_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Pydantic v2 error dicts to JSON-serializable form.

    Pydantic v2 stores the original ValueError instance inside ``ctx["error"]``.
    The ``input`` field can contain the raw request body bytes on body-size violations.
    Standard ``json.dumps`` cannot serialise either, so we stringify them here.
    """
    _JSON_SAFE = (str, int, float, bool, type(None), list, dict)

    def _safe(v: Any) -> Any:
        if isinstance(v, _JSON_SAFE):
            return v
        if isinstance(v, bytes):
            return f"<bytes: {len(v)} bytes>"
        return str(v)

    sanitized = []
    for error in errors:
        entry: dict[str, Any] = {}
        for k, v in error.items():
            if k == "ctx":
                entry["ctx"] = {ck: _safe(cv) for ck, cv in v.items()}
            elif k == "input":
                entry["input"] = _safe(v)
            else:
                entry[k] = v
        sanitized.append(entry)
    return sanitized


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.warning(f"Validation error for request {request_id}: {exc.errors()}")
    safe_errors = _sanitize_validation_errors(exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=_format_error_payload(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details={"errors": safe_errors},
            request_id=request_id,
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.exception(
        f"Unhandled exception during request processing (Request ID: {request_id}): {exc}"
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_format_error_payload(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred",
            details={},
            request_id=request_id,
        ),
    )
