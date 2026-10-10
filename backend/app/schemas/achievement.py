"""Achievement schemas."""

from datetime import datetime

from pydantic import BaseModel


class AchievementResponse(BaseModel):
    """One achievement — includes static metadata + unlock status."""

    id: str  # empty string if not yet unlocked
    key: str
    name: str
    description: str
    icon: str
    unlocked_at: datetime | None  # None if not yet unlocked


class AchievementListResponse(BaseModel):
    """Full achievement catalogue with unlock state for one player."""

    unlocked_count: int
    achievements: list[AchievementResponse]
