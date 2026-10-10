from typing import Any

from pydantic import BaseModel, Field


class ErrorDetails(BaseModel):
    """Error detail container."""

    code: str = Field(
        ...,
        description="Machine-readable error code",
        json_schema_extra={"example": "NOT_FOUND"},
    )
    message: str = Field(
        ...,
        description="Human-readable error description",
        json_schema_extra={"example": "Resource not found"},
    )
    details: dict[str, Any] = Field(
        default_factory=dict, description="Additional context or validation errors"
    )
    request_id: str | None = Field(
        None,
        description="Unique request tracing ID",
        json_schema_extra={"example": "req_123456789"},
    )


class ErrorResponse(BaseModel):
    """Global API error response format."""

    error: ErrorDetails
