"""Pydantic schemas package."""

from app.schemas.error import ErrorDetails, ErrorResponse
from app.schemas.health import HealthResponse

__all__ = ["HealthResponse", "ErrorDetails", "ErrorResponse"]
