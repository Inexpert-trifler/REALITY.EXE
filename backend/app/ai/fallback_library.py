"""Curated deterministic fallback quest library.

These quests are hand-crafted, safety-reviewed, and serve as the last
resort when the AI pipeline fails.  They must never appear as the
primary response when AI generation is healthy.

Selection is deterministic given the same inputs so tests are stable.
"""

from dataclasses import dataclass


@dataclass
class FallbackQuest:
    """A pre-written quest that needs no AI validation."""

    title: str
    brief: str
    duration_minutes: int
    difficulty: str
    play_style: str
    environment: str
    objectives: list[dict]
    xp_reward: int
    evidence_required: bool
    safety_notes: str
    model_name: str = "fallback"
    prompt_version: str = "fallback_v1"


# ---------------------------------------------------------------------------
# Library — one entry per (environment, difficulty, play_style) is ideal;
# at minimum cover every difficulty level.
# ---------------------------------------------------------------------------

_LIBRARY: list[FallbackQuest] = [
    FallbackQuest(
        title="The Colour Hunt",
        brief=(
            "Your mission, should you choose to accept it: find five distinct "
            "colours in nature before time runs out. No two may be the same shade."
        ),
        duration_minutes=20,
        difficulty="chill",
        play_style="observer",
        environment="any",
        objectives=[
            {
                "id": "obj-1",
                "instruction": "Find and photograph five distinct natural colours",
                "optional": False,
            },
            {"id": "obj-2", "instruction": "Note where each colour appeared", "optional": True},
        ],
        xp_reward=75,
        evidence_required=True,
        safety_notes="Stay on public paths and be aware of your surroundings.",
    ),
    FallbackQuest(
        title="Bench Cartographer",
        brief=(
            "Every park hides benches in unexpected places. Your quest is to find "
            "three benches and note something interesting visible from each one."
        ),
        duration_minutes=20,
        difficulty="chill",
        play_style="explorer",
        environment="park",
        objectives=[
            {"id": "obj-1", "instruction": "Locate three benches in the area", "optional": False},
            {
                "id": "obj-2",
                "instruction": "Photograph the most interesting view from any bench",
                "optional": True,
            },
        ],
        xp_reward=75,
        evidence_required=True,
        safety_notes="Stay in well-lit, public areas.",
    ),
    FallbackQuest(
        title="Shadow Detective",
        brief=(
            "Shadows tell stories. Hunt for three shadows that form an unexpected "
            "shape — look for animals, letters, or faces hiding in the light."
        ),
        duration_minutes=15,
        difficulty="curious",
        play_style="detective",
        environment="any",
        objectives=[
            {
                "id": "obj-1",
                "instruction": "Find three shadows that form recognisable shapes",
                "optional": False,
            },
            {
                "id": "obj-2",
                "instruction": "Photograph the most striking shadow you find",
                "optional": True,
            },
        ],
        xp_reward=100,
        evidence_required=True,
        safety_notes="Watch where you're walking while looking at shadows.",
    ),
    FallbackQuest(
        title="Sound Map",
        brief=(
            "Stand still for 60 seconds. Count every distinct sound you can hear. "
            "Then walk to find the source of the most interesting one."
        ),
        duration_minutes=10,
        difficulty="chill",
        play_style="observer",
        environment="any",
        objectives=[
            {
                "id": "obj-1",
                "instruction": "Stand still and count distinct sounds for 60 seconds",
                "optional": False,
            },
            {
                "id": "obj-2",
                "instruction": "Walk toward the source of the most interesting sound",
                "optional": False,
            },
        ],
        xp_reward=50,
        evidence_required=False,
        safety_notes="Stay aware of traffic and other pedestrians.",
    ),
    FallbackQuest(
        title="The Texture Trail",
        brief=(
            "Your senses are your tools. Find and photograph four dramatically "
            "different textures within walking distance — rough, smooth, soft, and sharp."
        ),
        duration_minutes=20,
        difficulty="curious",
        play_style="observer",
        environment="any",
        objectives=[
            {"id": "obj-1", "instruction": "Photograph a rough texture", "optional": False},
            {"id": "obj-2", "instruction": "Photograph a smooth texture", "optional": False},
            {"id": "obj-3", "instruction": "Photograph a soft texture", "optional": False},
            {
                "id": "obj-4",
                "instruction": "Photograph a visually sharp or jagged texture",
                "optional": True,
            },
        ],
        xp_reward=100,
        evidence_required=True,
        safety_notes="Only touch surfaces that are safe to touch.",
    ),
    FallbackQuest(
        title="Urban Nature Scout",
        brief=(
            "Cities are full of hidden nature. Find evidence of five living things "
            "— plants, insects, birds, or fungi — that most people walk past without noticing."
        ),
        duration_minutes=30,
        difficulty="explorer",
        play_style="explorer",
        environment="city",
        objectives=[
            {
                "id": "obj-1",
                "instruction": "Find five living organisms in an urban setting",
                "optional": False,
            },
            {
                "id": "obj-2",
                "instruction": "Photograph the smallest living thing you find",
                "optional": True,
            },
        ],
        xp_reward=150,
        evidence_required=True,
        safety_notes="Stay on pavements and public paths.",
    ),
    FallbackQuest(
        title="The Stillness Test",
        brief=(
            "Pick a spot, stand completely still for two full minutes, and observe "
            "everything that moves around you. The world is busier than you think."
        ),
        duration_minutes=10,
        difficulty="chill",
        play_style="mindfulness",
        environment="any",
        objectives=[
            {
                "id": "obj-1",
                "instruction": "Stand still for two uninterrupted minutes",
                "optional": False,
            },
            {
                "id": "obj-2",
                "instruction": "Count every distinct moving thing you observe",
                "optional": False,
            },
        ],
        xp_reward=50,
        evidence_required=False,
        safety_notes="Choose a spot away from traffic.",
    ),
    FallbackQuest(
        title="Neighbourhood Archaeologist",
        brief=(
            "Every street holds artifacts of the past. Find three things that look "
            "older than ten years — worn signs, faded paint, weathered stone. "
            "Each one is a clue to what this place used to be."
        ),
        duration_minutes=25,
        difficulty="explorer",
        play_style="detective",
        environment="neighborhood",
        objectives=[
            {
                "id": "obj-1",
                "instruction": "Find three objects or surfaces that show signs of age",
                "optional": False,
            },
            {
                "id": "obj-2",
                "instruction": "Photograph the oldest-looking thing you find",
                "optional": False,
            },
        ],
        xp_reward=150,
        evidence_required=True,
        safety_notes="Stay on public pavements. Do not enter private property.",
    ),
]


def get_fallback_quest(
    duration_minutes: int,
    environment: str,
    difficulty: str,
    play_style: str,
) -> FallbackQuest:
    """Return the best-matching fallback quest deterministically.

    Matching priority:
      1. Exact environment + difficulty + play_style match.
      2. Difficulty + play_style match.
      3. Difficulty match.
      4. Closest duration match from full library.

    Always returns a quest — never raises.
    """

    def _score(q: FallbackQuest) -> int:
        score = 0
        if q.difficulty == difficulty:
            score += 4
        if q.play_style == play_style:
            score += 2
        if q.environment in (environment, "any"):
            score += 1
        # Penalise large duration mismatches
        score -= abs(q.duration_minutes - duration_minutes) // 10
        return score

    best = max(_LIBRARY, key=_score)
    return best
