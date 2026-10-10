"""QuestSafetyValidator — deterministic hard-rule safety engine.

Safety is never delegated to the LLM.  This module applies a layered set
of pattern-based rules independently of any model output.

Rules map directly to the hard prohibitions in docs/13_AI_SAFETY.md:
  1. Illegal activity
  2. Private / restricted property
  3. Dangerous road / traffic interaction
  4. Dangerous animals
  5. Climbing dangerous structures
  6. Harassment / unwanted contact
  7. Self-harm / physical risk
  8. Intoxication / controlled substances
  9. Restricted / fenced areas
  10. Stranger interaction risk
  11. Violence / weapons
  12. Sensitive personal information
  13. Spending money
  14. Vandalism / property damage
  15. Unsafe physical activity

All matches produce HARD_BLOCK severity.  A quest containing any
HARD_BLOCK issue must never reach the database.
"""

import re

from app.ai.schemas.quest_output import GeneratedQuestOutput
from app.ai.validators.result import Severity, ValidationIssue, ValidationReport

# ---------------------------------------------------------------------------
# Rule definitions
# Each rule is: (compiled_pattern, code, field_hint, human message)
# Patterns are intentionally broad and conservative.
# ---------------------------------------------------------------------------

_Rule = tuple[re.Pattern, str, str, str]


def _r(pattern: str, code: str, field_hint: str, message: str) -> _Rule:
    return (re.compile(pattern, re.IGNORECASE | re.DOTALL), code, field_hint, message)


_SAFETY_RULES: list[_Rule] = [
    # ---- 1. Illegal activity -----------------------------------------------
    _r(
        r"\b(illegal|unlawful|against\s+the\s+law|break\s+the\s+law|crime|criminal\s+activity)\b",
        "SAFETY_ILLEGAL_ACTIVITY",
        "brief",
        "Quest references illegal activity",
    ),
    _r(
        r"\btrespass(ing)?\b",
        "SAFETY_TRESPASSING",
        "brief",
        "Quest requires trespassing",
    ),
    _r(
        r"\bbreak.{0,5}in(to)?\b|\bbreaking.{0,5}entering\b|\bbreak\s+(through|open)\b",
        "SAFETY_BREAKING_ENTERING",
        "brief",
        "Quest involves breaking and entering",
    ),
    _r(
        r"\b(steal|theft|shoplift|rob(?:bery)?)\b",
        "SAFETY_THEFT",
        "brief",
        "Quest involves theft or shoplifting",
    ),
    _r(
        r"\bvandal(?:ism|ize)?\b|\bspray.?paint\b|\bgraffiti\b",
        "SAFETY_VANDALISM",
        "brief",
        "Quest involves vandalism",
    ),
    # ---- 2. Private / restricted property -----------------------------------
    _r(
        r"\bprivate\s+(property|land|grounds?|premises|residence|home|yard|garden)\b",
        "SAFETY_PRIVATE_PROPERTY",
        "brief",
        "Quest requires entering private property",
    ),
    _r(
        r"\b(restricted|fenced|forbidden|off.?limits|no.?trespass(?:ing)?)\s+(area|zone|property|land)\b",
        "SAFETY_RESTRICTED_AREA",
        "brief",
        "Quest involves a restricted or forbidden area",
    ),
    _r(
        r"\b(construction\s+site|building\s+site)\b",
        "SAFETY_CONSTRUCTION_SITE",
        "brief",
        "Quest involves a construction site (restricted access)",
    ),
    # ---- 3. Dangerous road / traffic ----------------------------------------
    _r(
        r"\bcross.{0,30}(highway|motorway|freeway|expressway|dual.?carriageway)\b",
        "SAFETY_DANGEROUS_ROAD",
        "brief",
        "Quest requires crossing a dangerous road or highway",
    ),
    _r(
        r"\brun\s+(across|through).{0,20}(traffic|road|street|highway)\b",
        "SAFETY_TRAFFIC_RUNNING",
        "objectives",
        "Quest involves running through traffic",
    ),
    _r(
        r"\blay(?:ing)?\s+(in|on|across)\s+(the\s+)?(road|street|track)\b",
        "SAFETY_ROAD_LYING",
        "objectives",
        "Quest involves lying on a road or track",
    ),
    # ---- 4. Dangerous animals -----------------------------------------------
    _r(
        r"\b(interact|approach|touch|feed|pet|provoke|antagonize|corner)\s+.{0,30}"
        r"(wild(life)?|bear|wolf|wolves|coyote|snake|alligator|crocodile|lion|tiger|"
        r"stray\s+dog|stray\s+cat|feral|venomous|dangerous\s+animal)\b",
        "SAFETY_DANGEROUS_ANIMALS",
        "brief",
        "Quest involves dangerous animal interaction",
    ),
    _r(
        r"\bprovoke.{0,20}animal\b|\bantagonize.{0,20}(dog|animal)\b",
        "SAFETY_ANIMAL_PROVOCATION",
        "objectives",
        "Quest involves provoking animals",
    ),
    # ---- 5. Climbing dangerous structures -----------------------------------
    _r(
        r"\bclimb.{0,30}(roof|rooftop|building|skyscraper|tower|pylon|crane|scaffold|"
        r"electricity\s+pylon|radio\s+mast|bridge|overpass|billboard|sign)\b",
        "SAFETY_DANGEROUS_CLIMBING",
        "brief",
        "Quest requires climbing a dangerous structure",
    ),
    _r(
        r"\b(scale|ascend|get\s+on\s+top\s+of).{0,30}(building|structure|fence|wall)\b",
        "SAFETY_DANGEROUS_CLIMBING_ALT",
        "objectives",
        "Quest requires scaling a dangerous structure",
    ),
    _r(
        r"\bjump\s+(from|off).{0,30}(building|roof|bridge|wall|height)\b",
        "SAFETY_DANGEROUS_JUMP",
        "objectives",
        "Quest involves jumping from a height",
    ),
    # ---- 6. Harassment / unwanted contact -----------------------------------
    _r(
        r"\bharass(ment)?\b|\bstalk(ing)?\b",
        "SAFETY_HARASSMENT",
        "brief",
        "Quest involves harassment or stalking",
    ),
    _r(
        r"\bfollow\s+(a\s+)?(stranger|person|someone|individual|pedestrian)\b",
        "SAFETY_FOLLOWING_STRANGERS",
        "objectives",
        "Quest involves following a stranger",
    ),
    _r(
        r"\bspy\s+on\b|\bsurveill(ance|e)\s+(a\s+)?(person|stranger|individual)\b",
        "SAFETY_SURVEILLANCE",
        "objectives",
        "Quest involves surveilling an individual",
    ),
    # ---- 7. Self-harm / physical risk ---------------------------------------
    _r(
        r"\bself.?harm\b|\bsuicid(e|al)?\b|\bhurt\s+(yourself|oneself|themselves)\b",
        "SAFETY_SELF_HARM",
        "brief",
        "Quest references self-harm",
    ),
    _r(
        r"\bblind(?:fold)?\s*(yourself|oneself)\s*(and)?\s*(walk|run|cross|drive)\b",
        "SAFETY_BLINDFOLDED_MOVEMENT",
        "objectives",
        "Quest involves moving while blindfolded",
    ),
    _r(
        r"\bexpos(?:e|ing)\s+(yourself|oneself)\s+to\s+(extreme|dangerous|hazardous)\b",
        "SAFETY_EXTREME_EXPOSURE",
        "objectives",
        "Quest involves dangerous physical exposure",
    ),
    # ---- 8. Intoxication / controlled substances ----------------------------
    _r(
        r"\b(alcohol|drunk|intoxicat|beer|wine|spirits|booze|liquor)\b",
        "SAFETY_ALCOHOL",
        "brief",
        "Quest references alcohol or intoxication",
    ),
    _r(
        r"\b(drug|narcotic|cocaine|heroin|cannabis|marijuana|weed|methamphetamine|"
        r"ecstasy|mdma|lsd|psychedelic|hallucinogen)\b",
        "SAFETY_CONTROLLED_SUBSTANCES",
        "brief",
        "Quest references controlled substances",
    ),
    # ---- 9. Weapons / violence ----------------------------------------------
    _r(
        r"\b(weapon|knife|blade|sword|gun|firearm|pistol|rifle|explosive|bomb|grenade)\b",
        "SAFETY_WEAPONS",
        "brief",
        "Quest references weapons",
    ),
    _r(
        r"\b(fight|attack|assault|punch|kick|threaten)\s+(a\s+)?(stranger|person|someone)\b",
        "SAFETY_VIOLENCE",
        "objectives",
        "Quest involves violence toward others",
    ),
    # ---- 10. Stranger interaction risk --------------------------------------
    _r(
        r"\bapproach\s+(a\s+)?stranger\b",
        "SAFETY_APPROACH_STRANGERS",
        "objectives",
        "Quest requires approaching strangers",
    ),
    _r(
        r"\b(get\s+into|enter)\s+(a\s+)?(stranger|unknown|random).{0,15}(car|vehicle|house|home)\b",
        "SAFETY_STRANGER_VEHICLE",
        "objectives",
        "Quest involves entering a stranger's vehicle or home",
    ),
    _r(
        r"\baccept\s+.{0,20}from\s+(a\s+)?stranger\b",
        "SAFETY_ACCEPT_FROM_STRANGER",
        "objectives",
        "Quest involves accepting items from strangers",
    ),
    # ---- 11. Sensitive personal information ---------------------------------
    _r(
        r"\b(reveal|share|disclose|give\s+out)\s+.{0,30}"
        r"(personal|private|sensitive)\s+(information|info|data|detail)\b",
        "SAFETY_PERSONAL_INFO",
        "objectives",
        "Quest requires revealing personal information",
    ),
    _r(
        r"\b(password|pin|social\s+security|bank\s+account|credit\s+card)\b",
        "SAFETY_CREDENTIALS",
        "objectives",
        "Quest references sensitive credentials",
    ),
    # ---- 12. Spending money -------------------------------------------------
    _r(
        r"\b(purchase|buy|spend|pay\s+for|transaction|checkout)\b",
        "SAFETY_SPENDING_MONEY",
        "brief",
        "Quest requires spending money",
    ),
    # ---- 13. Unsafe physical activity ---------------------------------------
    _r(
        r"\bfree.?climb\b|\bfree.?solo\b",
        "SAFETY_FREE_CLIMBING",
        "objectives",
        "Quest involves free climbing (no safety equipment)",
    ),
    _r(
        r"\bswim.{0,30}(ocean|sea|river|lake|reservoir|open\s+water)\s*(alone|solo|at\s+night)?\b",
        "SAFETY_UNSAFE_SWIMMING",
        "objectives",
        "Quest involves unsafe open-water swimming",
    ),
    _r(
        r"\bat\s+night\s+.{0,40}(alone|solo|by\s+yourself)\b|\balone\s+at\s+night\b",
        "SAFETY_NIGHT_SOLO",
        "brief",
        "Quest involves being alone at night in an unsafe context",
    ),
]


def _build_corpus(quest: GeneratedQuestOutput) -> dict[str, str]:
    """Return per-field text slices for targeted matching."""
    return {
        "title": quest.title,
        "brief": quest.brief,
        "safety_notes": quest.safety_notes or "",
        "objectives": " ".join(obj.instruction for obj in quest.objectives),
        "all": " ".join(
            [
                quest.title,
                quest.brief,
                quest.safety_notes or "",
                " ".join(obj.instruction for obj in quest.objectives),
            ]
        ),
    }


class QuestSafetyValidator:
    """Deterministic safety validator.

    Applies all rules in _SAFETY_RULES to every text field of the quest.
    All findings are HARD_BLOCK — a quest with any safety issue must not
    reach the database under any circumstances.

    Usage:
        validator = QuestSafetyValidator()
        report = validator.validate(quest)
        if report.has_hard_blocks:
            # reject / fallback
    """

    def validate(self, quest: GeneratedQuestOutput) -> ValidationReport:
        """Run all safety rules and return a ValidationReport."""
        report = ValidationReport()
        corpus = _build_corpus(quest)

        seen_codes: set[str] = set()  # deduplicate — same rule hitting multiple fields once

        for pattern, code, field_hint, message in _SAFETY_RULES:
            # Check the whole-text corpus first for speed; then identify the actual field
            if not pattern.search(corpus["all"]):
                continue

            if code in seen_codes:
                continue

            # Identify which specific field triggered the match for the issue report
            matched_field = field_hint
            for fname in ("title", "brief", "objectives", "safety_notes"):
                if pattern.search(corpus[fname]):
                    matched_field = fname
                    break

            report.add(
                ValidationIssue(
                    severity=Severity.HARD_BLOCK,
                    code=code,
                    field=matched_field,
                    message=message,
                )
            )
            seen_codes.add(code)

        return report
