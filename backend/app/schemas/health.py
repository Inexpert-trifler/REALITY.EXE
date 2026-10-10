from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Health check response schema containing service status and metadata."""

    status: str = Field(
        ...,
        description="Overall health status",
        json_schema_extra={"example": "healthy"},
    )
    service: str = Field(
        ...,
        description="Service identifier",
        json_schema_extra={"example": "REALITY.EXE API"},
    )
    version: str = Field(
        ...,
        description="Application version",
        json_schema_extra={"example": "0.1.0"},
    )
    environment: str = Field(
        ...,
        description="Execution environment",
        json_schema_extra={"example": "development"},
    )
    timestamp: datetime = Field(..., description="UTC timestamp when health check was performed")
    database: str = Field(
        ...,
        description="Database connection status",
        json_schema_extra={"example": "connected"},
    )
    uptime_seconds: float | None = Field(
        None,
        description="Service uptime in seconds",
        json_schema_extra={"example": 120.5},
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "service": "REALITY.EXE API",
                "version": "0.1.0",
                "environment": "development",
                "timestamp": "2026-10-07T00:00:00Z",
                "database": "connected",
                "uptime_seconds": 124.5,
            }
        }
    )
