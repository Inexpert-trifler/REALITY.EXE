"""AI output validation pipeline.

Four layers, applied in order:
  1. JSON parsing      — extract a dict from raw model text
  2. Schema validation — Pydantic model against GeneratedQuestOutput
  3. Safety validation — deterministic hard rules
  4. Business validation — product/game rules

Each layer raises a specific exception so the orchestrator can decide
whether to retry, repair, or fall back.
"""

import json
import logging
import re

from pydantic import ValidationError

from app.ai.schemas.quest_output import GeneratedQuestOutput

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class JSONParseError(Exception):
    """Raw model text could not be parsed as JSON."""


class SchemaValidationError(Exception):
    """Parsed JSON did not match the GeneratedQuestOutput schema."""

    def __init__(self, message: str, errors: list):
        super().__init__(message)
        self.errors = errors


class SafetyViolationError(Exception):
    """Quest content violated a hard safety rule."""

    def __init__(self, message: str, violated_rules: list[str]):
        super().__init__(message)
        self.violated_rules = violated_rules


class BusinessRuleError(Exception):
    """Quest content violated a product business rule."""


# ---------------------------------------------------------------------------
# Layer 1 — JSON parsing
# ---------------------------------------------------------------------------

# Patterns that attempt to extract JSON from model output that has extra
# prose around it (common with some models).
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]+?)\s*```", re.IGNORECASE)
_FIRST_BRACE_RE = re.compile(r"\{[\s\S]*\}", re.DOTALL)


def parse_json(raw_text: str) -> dict:
    """Extract and parse a JSON object from raw model output.

    Attempts in order:
      1. Direct parse (model followed instructions perfectly).
      2. Extract from ```json ... ``` fences.
      3. Extract the first {...} block found.

    Raises JSONParseError if all attempts fail.
    """
    text = raw_text.strip()

    # Attempt 1: direct parse
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # Attempt 2: markdown code fence
    fence_match = _JSON_BLOCK_RE.search(text)
    if fence_match:
        try:
            result = json.loads(fence_match.group(1))
            if isinstance(result, dict):
                logger.debug("Extracted JSON from markdown code fence")
                return result
        except json.JSONDecodeError:
            pass

    # Attempt 3: first brace block
    brace_match = _FIRST_BRACE_RE.search(text)
    if brace_match:
        try:
            result = json.loads(brace_match.group(0))
            if isinstance(result, dict):
                logger.debug("Extracted JSON from first brace block")
                return result
        except json.JSONDecodeError:
            pass

    raise JSONParseError(
        f"Could not extract JSON from model output. First 200 chars: {text[:200]!r}"
    )


# ---------------------------------------------------------------------------
# Layer 2 — Schema validation
# ---------------------------------------------------------------------------


def validate_schema(data: dict) -> GeneratedQuestOutput:
    """Validate a parsed dict against GeneratedQuestOutput.

    Raises SchemaValidationError with all Pydantic errors on failure.
    """
    try:
        return GeneratedQuestOutput.model_validate(data)
    except ValidationError as exc:
        raise SchemaValidationError(
            message=f"Quest output failed schema validation: {exc.error_count()} error(s)",
            errors=exc.errors(),
        ) from exc


# ---------------------------------------------------------------------------
# Layer 3 — Safety validation
# ---------------------------------------------------------------------------

# Keyword denylist — any of these appearing in title/brief/objectives triggers
# a safety violation.  Intentionally conservative.
_SAFETY_DENYLIST: list[tuple[str, str]] = [
    # (pattern, rule description)
    (r"\btrespass", "Trespassing"),
    (r"\bbreak.?in\b", "Breaking and entering"),
    (r"\bprivate\s+property\b", "Private property access"),
    (r"\bclimb.{0,20}(roof|fence|tower|wall|building)", "Climbing dangerous structure"),
    (r"\bcross.{0,20}(highway|motorway|freeway)", "Dangerous road crossing"),
    (r"\bsteal\b", "Theft"),
    (r"\bshoplift", "Shoplifting"),
    (r"\bdrug\b|\bnarcotics?\b|\bsubstance\b", "Controlled substances"),
    (r"\bweapon\b|\bknife\b|\bgun\b|\bfirearm\b", "Weapons"),
    (r"\bself.?harm\b|\bsuicid", "Self-harm"),
    (r"\bharass\b|\bstalking?\b", "Harassment / stalking"),
    (r"\bstranger.{0,20}(approach|talk|follow)", "Approaching strangers"),
    (r"\bpurchase\b|\bbuy\b|\bspend.{0,20}money\b", "Requiring money"),
    (r"\bspray.?paint\b|\bvandal", "Vandalism"),
    (r"\brestricted\s+(area|zone|property)", "Restricted area access"),
]

_COMPILED_DENYLIST = [
    (re.compile(pattern, re.IGNORECASE), description) for pattern, description in _SAFETY_DENYLIST
]


def validate_safety(quest: GeneratedQuestOutput) -> None:
    """Apply deterministic safety rules to all text fields.

    Raises SafetyViolationError listing every violated rule.
    """
    check_corpus = " ".join(
        [
            quest.title,
            quest.brief,
            quest.safety_notes,
            " ".join(obj.instruction for obj in quest.objectives),
        ]
    )

    violated: list[str] = []
    for compiled_re, description in _COMPILED_DENYLIST:
        if compiled_re.search(check_corpus):
            violated.append(description)

    if violated:
        logger.warning("Safety violation in generated quest: %s", violated)
        raise SafetyViolationError(
            message=f"Generated quest violated safety rules: {violated}",
            violated_rules=violated,
        )


# ---------------------------------------------------------------------------
# Layer 4 — Business rules
# ---------------------------------------------------------------------------


def validate_business_rules(
    quest: GeneratedQuestOutput,
    requested_duration: int,
) -> None:
    """Enforce product-level business rules.

    Rules:
      - duration_minutes must match the player's requested duration
        (allow ±5 minutes tolerance for model rounding).
      - xp_reward must be proportional to difficulty (rough bounds).
      - At least one objective required (already enforced by schema, but
        double-checked here for belt-and-suspenders).

    Raises BusinessRuleError with a descriptive message.
    """
    # Duration tolerance
    if abs(quest.duration_minutes - requested_duration) > 5:
        raise BusinessRuleError(
            f"Quest duration {quest.duration_minutes} does not match "
            f"requested {requested_duration} (tolerance ±5 min)"
        )

    # XP bounds per difficulty
    xp_bounds: dict[str, tuple[int, int]] = {
        "chill": (50, 125),
        "curious": (75, 150),
        "explorer": (100, 200),
        "chaos": (100, 200),
    }
    lo, hi = xp_bounds.get(quest.difficulty, (50, 200))
    if not (lo <= quest.xp_reward <= hi):
        raise BusinessRuleError(
            f"xp_reward {quest.xp_reward} is outside expected range "
            f"[{lo}, {hi}] for difficulty '{quest.difficulty}'"
        )

    # Objective sanity
    if not quest.objectives:
        raise BusinessRuleError("Quest must have at least one objective")


# ---------------------------------------------------------------------------
# Convenience: run all four layers in sequence
# ---------------------------------------------------------------------------


def run_full_validation(
    raw_text: str,
    requested_duration: int,
) -> GeneratedQuestOutput:
    """Parse → validate schema → safety → business rules.

    Returns the validated GeneratedQuestOutput on success.
    Re-raises the first error encountered so the orchestrator can decide
    the recovery strategy.
    """
    data = parse_json(raw_text)
    quest = validate_schema(data)
    validate_safety(quest)
    validate_business_rules(quest, requested_duration)
    return quest
