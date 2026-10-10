"""Quest and QuestAttempt schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Quest (read-only from this domain — generation is a later prompt)
# ---------------------------------------------------------------------------


class ObjectiveResponse(BaseModel):
    """A single quest objective."""

    id: str
    instruction: str
    optional: bool = False


class QuestResponse(BaseModel):
    """Public quest data returned by the API."""

    id: str
    title: str
    brief: str
    duration_minutes: int
    environment: str
    difficulty: str
    play_style: str
    personality: str
    objectives: list[Any]  # raw JSON until AI generation is built
    xp_reward: int
    evidence_required: bool
    safety_notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# QuestAttempt
# ---------------------------------------------------------------------------


class AttemptResponse(BaseModel):
    """Serialized QuestAttempt returned after every state transition."""

    id: str
    quest_id: str
    user_id: str
    status: str
    started_at: datetime
    pocket_started_at: datetime | None
    completed_at: datetime | None
    result: str | None
    earned_xp: int

    model_config = {"from_attributes": True}


class QuestListResponse(BaseModel):
    """Paginated list of quests."""

    quests: list[QuestResponse]
    total: int
    skip: int
    limit: int
