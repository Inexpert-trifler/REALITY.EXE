"""Quest history and extended stats schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class EvidenceStatusSummary(BaseModel):
    """Summary of evidence submitted for one attempt."""

    evidence_count: int
    latest_ai_outcome: str | None  # e.g. "SUCCESS", "INCOMPLETE", or None if no analysis
    latest_confidence: float | None


class AttemptHistoryItem(BaseModel):
    """One entry in the player's quest history."""

    attempt_id: str
    quest_id: str
    quest_title: str
    quest_difficulty: str
    quest_play_style: str
    quest_duration_minutes: int
    status: str
    earned_xp: int
    started_at: datetime
    completed_at: datetime | None
    used_pocket_mode: bool  # True if pocket_started_at IS NOT NULL
    evidence: EvidenceStatusSummary


class QuestHistoryResponse(BaseModel):
    """Paginated quest history list."""

    attempts: list[AttemptHistoryItem]
    total: int
    skip: int
    limit: int


class ExtendedPlayerStatsResponse(BaseModel):
    """Full player stats including history aggregations."""

    user_id: str
    level: int
    total_xp: int
    total_quests: int
    completed_quests: int
    abandoned_quests: int
    completion_rate: float = Field(..., description="0.0 – 1.0")
    achievements_count: int
    favorite_play_style: str | None
    avg_quest_duration_minutes: float | None
    level_progress: object  # LevelProgressResponse from player schemas
