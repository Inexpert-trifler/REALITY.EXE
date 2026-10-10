"""Schemas for the quest completion pipeline.

Covers evidence analysis results, completion outcomes, level-up info,
and the full completion response returned to the client.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class VerificationOutcome(StrEnum):
    """Classification of an evidence analysis result.

    SUCCESS    – evidence clearly supports completion; XP should be awarded.
    INCOMPLETE – evidence insufficient; player may retry.
    UNCERTAIN  – model not confident enough; allow retry without penalty.
    UNSAFE     – evidence contains safety concerns; block completion.
    """

    SUCCESS = "SUCCESS"
    INCOMPLETE = "INCOMPLETE"
    UNCERTAIN = "UNCERTAIN"
    UNSAFE = "UNSAFE"


# ---------------------------------------------------------------------------
# Evidence analysis
# ---------------------------------------------------------------------------


class AnalysisResultResponse(BaseModel):
    """Response from POST /evidence/{evidence_id}/analyze."""

    analysis_id: str
    evidence_id: str
    outcome: VerificationOutcome
    confidence: float = Field(..., ge=0.0, le=1.0)
    visible_content: str
    safety_concerns: list[str]
    completion_recommendation: bool
    can_complete: bool  # True only for SUCCESS
    can_retry: bool  # True for INCOMPLETE / UNCERTAIN
    message: str  # Human-readable status for the player
    model_name: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Completion outcome
# ---------------------------------------------------------------------------


class LevelUpInfo(BaseModel):
    """Emitted when the player crosses a level threshold."""

    leveled_up: bool
    old_level: int
    new_level: int


class NewAchievement(BaseModel):
    """An achievement unlocked as part of this completion."""

    key: str
    unlocked_at: datetime


class CompletionResponse(BaseModel):
    """Full response from POST /quests/{quest_id}/complete.

    Contains all side-effects of the completion in one payload so the
    client can render a rich end screen without extra round-trips.
    """

    attempt_id: str
    quest_id: str
    status: str  # "COMPLETED"
    earned_xp: int
    total_xp: int
    level: int
    level_up: LevelUpInfo
    new_achievements: list[NewAchievement]
    reflection: str | None  # AI-generated reflection text
    idempotent: bool = False  # True if this was a duplicate call
