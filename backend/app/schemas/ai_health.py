"""Schemas for the AI provider health endpoint."""

from pydantic import BaseModel


class AIHealthResponse(BaseModel):
    """Response for GET /api/v1/ai/health."""

    provider: str = "ollama"
    reachable: bool
    configured_model: str
    latency_ms: float | None
    server_version: str | None
    error: str | None
