"""Pydantic schemas for the AI quest generation pipeline.

These are internal schemas used only inside the AI layer.
The public-facing API schemas live in app/schemas/quest.py.
"""

from pydantic import BaseModel, Field, field_validator

VALID_DIFFICULTIES = {"chill", "curious", "explorer", "chaos"}
VALID_ENVIRONMENTS = {"campus", "park", "neighborhood", "trail", "city", "surprise", "any"}
VALID_PLAY_STYLES = {"explorer", "detective", "observer", "adventurer", "chaos"}
VALID_PERSONALITIES = {"Wizard", "Rogue AI", "Captain", "Sensei", "Alien"}


class GeneratedObjective(BaseModel):
    """A single quest objective from the AI output."""

    id: str = Field(..., min_length=1, max_length=100)
    instruction: str = Field(..., min_length=5, max_length=500)
    optional: bool = False


class GeneratedQuestOutput(BaseModel):
    """Strict schema the model output must conform to.

    Every field is required.  If the model omits or mis-types any field
    the validator layer will catch it before persistence.
    """

    title: str = Field(..., min_length=3, max_length=200)
    brief: str = Field(..., min_length=20, max_length=2000)
    duration_minutes: int = Field(..., ge=5, le=120)
    difficulty: str
    objectives: list[GeneratedObjective] = Field(..., min_length=1, max_length=10)
    xp_reward: int = Field(..., ge=0, le=500)
    evidence_required: bool = True
    safety_notes: str = Field(default="", max_length=1000)

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in VALID_DIFFICULTIES:
            raise ValueError(f"difficulty must be one of {sorted(VALID_DIFFICULTIES)}")
        return v

    @field_validator("objectives")
    @classmethod
    def validate_objectives(cls, v: list[GeneratedObjective]) -> list[GeneratedObjective]:
        required = [o for o in v if not o.optional]
        if not required:
            raise ValueError("At least one non-optional objective is required")
        return v


class QuestGenerateRequest(BaseModel):
    """HTTP request body for POST /api/v1/quests/generate."""

    duration_minutes: int = Field(
        ..., ge=5, le=120, description="Requested quest duration in minutes"
    )
    environment: str = Field(..., description=f"One of: {sorted(VALID_ENVIRONMENTS)}")
    difficulty: str = Field(..., description=f"One of: {sorted(VALID_DIFFICULTIES)}")
    play_style: str = Field(..., description=f"One of: {sorted(VALID_PLAY_STYLES)}")
    personality: str = Field(..., description=f"One of: {sorted(VALID_PERSONALITIES)}")

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in VALID_ENVIRONMENTS:
            raise ValueError(f"environment must be one of {sorted(VALID_ENVIRONMENTS)}")
        return v

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in VALID_DIFFICULTIES:
            raise ValueError(f"difficulty must be one of {sorted(VALID_DIFFICULTIES)}")
        return v

    @field_validator("play_style")
    @classmethod
    def validate_play_style(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in VALID_PLAY_STYLES:
            raise ValueError(f"play_style must be one of {sorted(VALID_PLAY_STYLES)}")
        return v

    @field_validator("personality")
    @classmethod
    def validate_personality(cls, v: str) -> str:
        # Allow any capitalisation — normalise to title case
        mapping = {p.lower(): p for p in VALID_PERSONALITIES}
        normalised = mapping.get(v.lower().strip())
        if normalised is None:
            raise ValueError(f"personality must be one of {sorted(VALID_PERSONALITIES)}")
        return normalised
