"""Player profile and progression schemas."""

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Enums / allowed values (as plain string literals for flexibility)
# ---------------------------------------------------------------------------

VALID_PERSONALITIES = {"Wizard", "Rogue AI", "Captain", "Sensei", "Alien"}
VALID_PLAY_STYLES = {"explorer", "detective", "observer", "adventurer", "chaos"}


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


class ProfileResponse(BaseModel):
    """Full player profile returned by GET /player/profile."""

    id: str
    user_id: str
    display_name: str
    level: int
    total_xp: int
    preferred_personality: str | None
    preferred_play_style: str | None

    model_config = {"from_attributes": True}


class ProfilePatchRequest(BaseModel):
    """Fields that a player is allowed to update on their own profile.

    All fields are optional — only provided fields are updated.
    XP and level are NOT patchable here; they are managed exclusively
    by XPService.
    """

    display_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Player display name shown in the game",
    )
    preferred_personality: str | None = Field(
        default=None,
        description=f"Game-master personality. One of: {sorted(VALID_PERSONALITIES)}",
    )
    preferred_play_style: str | None = Field(
        default=None,
        description=f"Preferred quest style. One of: {sorted(VALID_PLAY_STYLES)}",
    )

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("display_name must not be blank")
        return v

    @field_validator("preferred_personality")
    @classmethod
    def validate_personality(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_PERSONALITIES:
            raise ValueError(f"preferred_personality must be one of: {sorted(VALID_PERSONALITIES)}")
        return v

    @field_validator("preferred_play_style")
    @classmethod
    def validate_play_style(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_PLAY_STYLES:
            raise ValueError(f"preferred_play_style must be one of: {sorted(VALID_PLAY_STYLES)}")
        return v


# ---------------------------------------------------------------------------
# Progression / level progress
# ---------------------------------------------------------------------------


class LevelProgressResponse(BaseModel):
    """How far through the current level the player is."""

    current_level: int
    current_xp: int
    xp_for_current_level: int = Field(
        ..., description="XP threshold at which this level was reached"
    )
    xp_for_next_level: int | None = Field(
        ..., description="XP threshold for the next level, null when max level"
    )
    xp_into_level: int = Field(
        ..., description="XP accumulated since the start of the current level"
    )
    xp_needed_for_next: int | None = Field(
        ..., description="Remaining XP to reach next level, null when max level"
    )
    progress_percent: float = Field(..., description="0–100 completion of the current level band")


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


class PlayerStatsResponse(BaseModel):
    """Aggregated statistics returned by GET /player/stats."""

    user_id: str
    level: int
    total_xp: int
    total_quests: int
    completed_quests: int
    abandoned_quests: int
    completion_rate: float = Field(..., description="0.0 – 1.0")
    achievements_count: int
    favorite_play_style: str | None = None
    avg_quest_duration_minutes: float | None = None
    level_progress: LevelProgressResponse
