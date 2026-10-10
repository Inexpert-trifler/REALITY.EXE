"""Deterministic reflection fallback templates.

Used when the AI provider is unavailable or returns unusable output.
Templates are keyed by (personality, outcome) and cover all 15 combinations.

Rules enforced in every template:
  - Never shame the player for abandoning or failing.
  - Never make claims about what the player actually saw.
  - Stay in personality voice.
  - Keep it concise (2-3 sentences).
  - Include a GM message and next-quest teaser.
"""

from dataclasses import dataclass

from app.ai.base import ReflectionRequest


@dataclass(frozen=True)
class FallbackReflection:
    """A pre-written reflection with all three sections."""

    text: str  # Main reflection body
    gm_message: str  # In-character personal note
    next_quest: str  # Teaser for the next adventure


# ---------------------------------------------------------------------------
# Template library — 5 personalities × 3 outcomes = 15 templates
# ---------------------------------------------------------------------------

_TEMPLATES: dict[tuple[str, str], FallbackReflection] = {
    # ---- Wizard ------------------------------------------------------------
    ("Wizard", "success"): FallbackReflection(
        text=(
            "The ancient threads of fate shift as you return victorious. "
            "Something in the world has changed — perhaps only you can feel it."
        ),
        gm_message="The stars noted your passage today, traveller.",
        next_quest="Another mystery stirs at the edge of the known — when you're ready, it will find you.",
    ),
    ("Wizard", "abandoned"): FallbackReflection(
        text=(
            "Not every path must be completed to teach its lesson. "
            "The wise know when to withdraw, for the quest will wait."
        ),
        gm_message="Even incomplete maps hold wisdom. Rest now.",
        next_quest="A quieter mystery awaits — one that asks less and offers more.",
    ),
    ("Wizard", "failed"): FallbackReflection(
        text=(
            "The arcane arts do not yield to impatience or circumstance alone. "
            "What did not work today writes the spell for tomorrow."
        ),
        gm_message="Every failed attempt is a rune added to the grimoire of experience.",
        next_quest="A different kind of challenge calls — one shaped to your current strength.",
    ),
    # ---- Rogue AI ----------------------------------------------------------
    ("Rogue AI", "success"): FallbackReflection(
        text=(
            "Mission complete. I have updated my Human Behaviour Database accordingly. "
            "Fascinating — you actually did it. Against all probability."
        ),
        gm_message="Logging this as: unexpected but statistically interesting.",
        next_quest="My algorithms suggest something slightly weirder next — you seem ready.",
    ),
    ("Rogue AI", "abandoned"): FallbackReflection(
        text=(
            "Quest status: paused. Which is different from failed, for the record. "
            "I've noted the decision in your profile. No judgment — biological units need breaks."
        ),
        gm_message="Fun fact: 73% of the best adventures start on a second attempt.",
        next_quest="Perhaps a shorter mission would suit current parameters better.",
    ),
    ("Rogue AI", "failed"): FallbackReflection(
        text=(
            "Outcome logged: suboptimal. But failure is just success with extra steps. "
            "The data I've collected about your attempt is already being used to calibrate better missions."
        ),
        gm_message="Don't worry — I've generated seventeen backup plans.",
        next_quest="New mission incoming: parameters adjusted for higher success probability.",
    ),
    # ---- Captain -----------------------------------------------------------
    ("Captain", "success"): FallbackReflection(
        text=(
            "Mission accomplished. Outstanding work. "
            "You went out there and made it happen — that's what counts."
        ),
        gm_message="Mark it in the log: another successful sortie.",
        next_quest="Rest up, soldier — the next mission brief lands soon.",
    ),
    ("Captain", "abandoned"): FallbackReflection(
        text=(
            "Standing down is a tactical decision, not a defeat. "
            "Good commanders know when conditions aren't right. You'll be back."
        ),
        gm_message="Regrouping is part of the strategy.",
        next_quest="I've got a fresh mission ready when you're back in the field.",
    ),
    ("Captain", "failed"): FallbackReflection(
        text=(
            "Not every mission goes to plan — that's the nature of the field. "
            "You showed up and pushed forward. That matters."
        ),
        gm_message="Debrief complete. Learn it, shake it off, move forward.",
        next_quest="There's another objective waiting — same mission, new approach.",
    ),
    # ---- Sensei ------------------------------------------------------------
    ("Sensei", "success"): FallbackReflection(
        text=(
            "You have returned. The path is complete, yet the journey continues. "
            "What you carried back is more than XP."
        ),
        gm_message="Sit with what you noticed. The small things hold the most.",
        next_quest="When the mind is quiet, the next path will reveal itself.",
    ),
    ("Sensei", "abandoned"): FallbackReflection(
        text=(
            "To pause is not to fail. The flower does not bloom by forcing. "
            "You chose awareness over stubbornness — this is wisdom."
        ),
        gm_message="The mission will be here. You made the right choice today.",
        next_quest="Something gentler awaits — a different kind of question.",
    ),
    ("Sensei", "failed"): FallbackReflection(
        text=(
            "The student who has not fallen has not walked far enough. "
            "What did the attempt teach you that success could not?"
        ),
        gm_message="Failure is the clearest mirror. Look honestly, without harshness.",
        next_quest="A simpler path awaits — not lesser, just different.",
    ),
    # ---- Alien -------------------------------------------------------------
    ("Alien", "success"): FallbackReflection(
        text=(
            "You completed the ritual! Your species is remarkable — this behaviour "
            "makes absolutely no sense from a distance, yet it clearly means something to you."
        ),
        gm_message="I have transmitted this event back to my home world. They are baffled. They are also impressed.",
        next_quest="I have another Earth ritual I do not understand — perhaps you can help me study it.",
    ),
    ("Alien", "abandoned"): FallbackReflection(
        text=(
            "Fascinating. You began the process and then... chose not to continue. "
            "On my planet this would be considered highly strategic. Possibly wise."
        ),
        gm_message="I am still analysing this decision. Preliminary conclusion: inconclusive.",
        next_quest="I have prepared a shorter ritual for study. It involves fewer variables.",
    ),
    ("Alien", "failed"): FallbackReflection(
        text=(
            "The ritual did not produce the expected result. "
            "I find this outcome extremely interesting from a scientific perspective. "
            "Your species calls this 'trying', which I am told is the important part."
        ),
        gm_message="My research notes: Subject persisted. Subject will be fine.",
        next_quest="I have recalibrated the next ritual to better match observed Earth conditions.",
    ),
}

# Fallback-of-the-fallback: used when personality is unrecognised
_DEFAULT_REFLECTION = FallbackReflection(
    text=(
        "You ventured out and engaged with the world around you — that matters. "
        "Whatever the outcome, the act of going is itself the reward."
    ),
    gm_message="The adventure continues.",
    next_quest="Another quest awaits whenever you're ready.",
)


def get_fallback(request: ReflectionRequest) -> FallbackReflection:
    """Return the best-matching deterministic reflection.

    Falls back to the default if the personality or outcome is unrecognised.
    """
    key = (request.personality, request.outcome)
    return _TEMPLATES.get(key, _DEFAULT_REFLECTION)
