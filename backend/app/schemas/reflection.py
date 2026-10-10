"""Reflection HTTP schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.sync import SyncMetadata


class ReflectionCreateRequest(BaseModel):
    """Payload for POST /api/v1/reflections."""

    attempt_id: str = Field(..., description="UUID of the QuestAttempt to reflect on")


class ReflectionResponse(BaseModel):
    """A single reflection returned by the API."""

    id: str
    attempt_id: str
    text: str  # Main reflection body
    gm_message: str | None  # Optional in-character GM note
    next_quest_suggestion: str | None  # Optional next-quest teaser
    model_name: str
    is_fallback: bool  # True when AI was unavailable
    created_at: datetime
    sync: SyncMetadata | None = None  # Populated on POST, None in list items

    model_config = {"from_attributes": True}


class ReflectionListResponse(BaseModel):
    """Paginated list of reflections for the authenticated user."""

    reflections: list[ReflectionResponse]
    total: int
