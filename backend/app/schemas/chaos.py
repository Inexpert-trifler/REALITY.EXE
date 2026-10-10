"""Chaos Mode schemas."""


from pydantic import BaseModel, Field

from app.schemas.quest import QuestResponse


class ChaosNextRequest(BaseModel):
    """Body for POST /quests/{attempt_id}/chaos-next."""

    discovery_context: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description=(
            "What the player discovered during this quest — used as context "
            "for generating the next continuation quest."
        ),
    )
    duration_minutes: int = Field(
        default=20,
        ge=5,
        le=120,
        description="Requested duration for the continuation quest",
    )


class ChaosSessionResponse(BaseModel):
    """State of the current Chaos chain session."""

    session_id: str
    chain_depth: int
    max_chain_depth: int
    can_continue: bool
    status: str


class ChaosNextResponse(BaseModel):
    """Response from POST /quests/{attempt_id}/chaos-next."""

    session: ChaosSessionResponse
    next_quest: QuestResponse
    message: str
