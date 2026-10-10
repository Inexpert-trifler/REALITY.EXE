"""Standardised API error response schemas.

Every error from this API has the shape:

    {
        "error": {
            "code":       "MACHINE_READABLE_CODE",
            "message":    "Human-readable description.",
            "request_id": "uuid-echo"   // present on most errors
        }
    }

These Pydantic models exist so FastAPI generates accurate OpenAPI error
schema definitions in ``responses`` declarations.  They are never
instantiated directly — the exception handlers in ``core/exceptions.py``
build the dicts manually.
"""

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Inner error object."""

    code: str
    message: str
    request_id: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "NOT_FOUND",
                    "message": "Quest not found.",
                    "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                }
            ]
        }
    }


class ErrorResponse(BaseModel):
    """Standard API error envelope."""

    error: ErrorDetail

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Quest not found.",
                        "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    }
                }
            ]
        }
    }


# ---------------------------------------------------------------------------
# Typed error response schemas for specific HTTP status codes.
# Using these in ``responses=`` keeps the generated schema precise.
# ---------------------------------------------------------------------------


class Error400(ErrorResponse):
    """400 Bad Request — invalid input or business rule violation."""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "Evidence cannot be uploaded when the attempt is in 'ACTIVE' state.",
                        "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    }
                }
            ]
        }
    }


class Error401(ErrorResponse):
    """401 Unauthorized — missing or invalid Bearer token."""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "Authentication credentials were not provided.",
                        "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    }
                }
            ]
        }
    }


class Error403(ErrorResponse):
    """403 Forbidden — authenticated but not authorised for this resource."""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": {
                        "code": "FORBIDDEN",
                        "message": "You do not own this quest attempt.",
                        "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    }
                }
            ]
        }
    }


class Error404(ErrorResponse):
    """404 Not Found — requested resource does not exist."""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Quest not found.",
                        "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    }
                }
            ]
        }
    }


class Error409(ErrorResponse):
    """409 Conflict — resource already exists (e.g. duplicate email/username)."""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": {
                        "code": "CONFLICT",
                        "message": "An account with this email address already exists.",
                        "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    }
                }
            ]
        }
    }


class Error422(ErrorResponse):
    """422 Unprocessable Content — request body failed schema validation."""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Request validation failed.",
                        "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    }
                }
            ]
        }
    }


# ---------------------------------------------------------------------------
# Convenience dict blocks — paste into responses= declarations
# ---------------------------------------------------------------------------

AUTH_RESPONSES = {
    401: {"model": Error401, "description": "Missing or invalid Bearer token"},
}

COMMON_RESPONSES = {
    401: {"model": Error401, "description": "Missing or invalid Bearer token"},
    422: {"model": Error422, "description": "Request body validation failed"},
}

RESOURCE_RESPONSES = {
    401: {"model": Error401, "description": "Missing or invalid Bearer token"},
    403: {"model": Error403, "description": "Resource belongs to another user"},
    404: {"model": Error404, "description": "Resource not found"},
    422: {"model": Error422, "description": "Request body validation failed"},
}
