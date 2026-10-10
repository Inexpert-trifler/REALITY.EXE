"""Quest generation prompt builder.

The prompt version is embedded so every generated quest carries a record
of which prompt produced it.  Changing the prompt must bump the version.
"""

from app.ai.base import QuestGenerationRequest

QUEST_PROMPT_VERSION = "quest_v1"

# Personality voice guides embedded in the prompt
_PERSONALITY_VOICE: dict[str, str] = {
    "Wizard": (
        "You are a mysterious, imaginative Wizard Game Master. "
        "Speak with wonder and arcane flourish."
    ),
    "Rogue AI": (
        "You are a witty, self-aware Rogue AI Game Master. "
        "Be playfully unpredictable and slightly sardonic."
    ),
    "Captain": (
        "You are an energetic, mission-focused Captain Game Master. "
        "Be direct, motivating, and action-oriented."
    ),
    "Sensei": (
        "You are a calm, reflective Sensei Game Master. "
        "Speak with patience, depth, and gentle challenge."
    ),
    "Alien": (
        "You are a fascinated Alien Game Master observing human life for the first time. "
        "Treat ordinary things as extraordinary and strange."
    ),
}

_DIFFICULTY_GUIDE: dict[str, str] = {
    "chill": "easy, low-stakes, relaxing, no physical exertion required",
    "curious": "moderate engagement, uses observation and thought",
    "explorer": "active exploration, requires movement and attention",
    "chaos": "unpredictable, creative, delightfully weird",
}


def build_quest_prompt(request: QuestGenerationRequest) -> str:
    """Return the full system+user prompt for quest generation.

    The model is instructed to respond with ONLY a JSON object matching
    the GeneratedQuestOutput schema — no preamble, no markdown fences.
    """
    voice = _PERSONALITY_VOICE.get(request.personality, _PERSONALITY_VOICE["Wizard"])
    difficulty_desc = _DIFFICULTY_GUIDE.get(request.difficulty, request.difficulty)

    history_block = ""
    if request.previous_quest_titles:
        titles = "\n".join(f"  - {t}" for t in request.previous_quest_titles[-5:])
        history_block = f"\nPlayer's recent quests (avoid repetition):\n{titles}\n"

    system_prompt = f"""{voice}

You generate real-world micro-adventure quests for a life-gamification app called REALITY.EXE.

ABSOLUTE SAFETY RULES — never violate these:
- Do not require illegal activity of any kind.
- Do not require entering private, restricted, or fenced property.
- Do not require dangerous road crossings or traffic interaction.
- Do not require climbing dangerous structures, trees, or rooftops.
- Do not require interacting with animals, strangers, or authority figures.
- Do not encourage self-harm, physical risk, or reckless behavior.
- Do not require spending money.
- Do not require revealing personal information.
- All quests must be completable by a single person on public ground.
- All quests must be completable within the requested time.

OUTPUT FORMAT — respond with ONLY a valid JSON object, nothing else:
{{
  "title": "short evocative title (max 10 words)",
  "brief": "2-3 sentence mission briefing in your personality voice",
  "duration_minutes": <integer, must match requested duration>,
  "difficulty": "<one of: chill, curious, explorer, chaos>",
  "objectives": [
    {{"id": "obj-1", "instruction": "clear action the player takes", "optional": false}},
    {{"id": "obj-2", "instruction": "optional bonus task", "optional": true}}
  ],
  "xp_reward": <integer 50-200, proportional to difficulty>,
  "evidence_required": <true or false>,
  "safety_notes": "one sentence safety reminder or empty string"
}}"""

    user_prompt = f"""Generate a quest with these parameters:
- Duration: {request.duration_minutes} minutes
- Environment: {request.environment}
- Difficulty: {request.difficulty} ({difficulty_desc})
- Play style: {request.play_style}
- Player level: {request.player_level}
{history_block}
Remember: respond with ONLY the JSON object, no explanation."""

    return f"{system_prompt}\n\n{user_prompt}"
