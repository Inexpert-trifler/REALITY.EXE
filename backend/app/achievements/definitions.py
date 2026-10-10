"""Achievement definitions registry.

Every achievement in the game is defined here with its metadata.
No logic lives here — just the catalogue.  AchievementService contains
the evaluation logic.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AchievementDefinition:
    """Static metadata for one achievement."""

    key: str  # machine-readable identifier stored in DB
    name: str  # display name
    description: str  # player-facing description
    icon: str  # icon hint for the client (e.g. emoji or slug)
    threshold: int = 1  # how many times the condition must be met


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ACHIEVEMENTS: dict[str, AchievementDefinition] = {
    "first_contact": AchievementDefinition(
        key="first_contact",
        name="First Contact",
        description="Complete your very first quest.",
        icon="🌟",
        threshold=1,
    ),
    "touch_grass": AchievementDefinition(
        key="touch_grass",
        name="Touch Grass",
        description="Complete three outdoor quests.",
        icon="🌿",
        threshold=3,
    ),
    "curious_mind": AchievementDefinition(
        key="curious_mind",
        name="Curious Mind",
        description="Complete five Observer quests.",
        icon="🔍",
        threshold=5,
    ),
    "chaos_agent": AchievementDefinition(
        key="chaos_agent",
        name="Chaos Agent",
        description="Complete a Chaos quest.",
        icon="🌀",
        threshold=1,
    ),
    "pocket_player": AchievementDefinition(
        key="pocket_player",
        name="Pocket Player",
        description="Complete five quests using Pocket Mode.",
        icon="📱",
        threshold=5,
    ),
}


def get_definition(key: str) -> AchievementDefinition | None:
    """Return the definition for *key*, or None if unknown."""
    return ACHIEVEMENTS.get(key)
