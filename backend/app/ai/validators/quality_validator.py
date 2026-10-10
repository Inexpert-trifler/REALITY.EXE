"""QuestQualityValidator — content quality and playability checks.

Ensures the generated quest is genuinely completable, understandable,
and has a clear success condition.  Issues are SOFT_BLOCK (trigger retry)
or WARNING (logged but do not block).

Rules enforced:
  - Duration is realistic for the objective count and type
  - Every required objective has a clear, actionable instruction
  - Objectives don't contain vague non-instructions ("do something", "etc.")
  - At least one objective must be non-optional (enforced by schema, double-checked)
  - Objective count within sensible range (1–8 required, up to 10 total)
  - Brief provides enough context to understand the mission
  - Brief is not pure boilerplate / generic filler
  - Title is descriptive (not generic one-word placeholders)
  - No duplicate objective instructions
  - No impossible requirements (requires specific weather, specific day, etc.)
  - Safety notes present for explorer / chaos difficulty
"""

import re

from app.ai.schemas.quest_output import GeneratedQuestOutput
from app.ai.validators.result import Severity, ValidationIssue, ValidationReport

# Patterns for vague / non-actionable objective text
_VAGUE_PATTERNS: list[re.Pattern] = [
    re.compile(r"^\s*(do\s+something|etc\.?|and\s+more|or\s+something)\s*$", re.IGNORECASE),
    re.compile(r"\b(somehow|whatever|anything)\b", re.IGNORECASE),
    re.compile(r"\.\.\.$"),  # trailing ellipsis — incomplete instruction
]

# Impossible or overly contingent requirements
_IMPOSSIBLE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (
        re.compile(
            r"\b(must\s+be\s+raining|only\s+if\s+it\s+rains|when\s+it\s+snows)\b", re.IGNORECASE
        ),
        "Objective depends on specific weather conditions",
    ),
    (
        re.compile(
            r"\b(on\s+a\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b",
            re.IGNORECASE,
        ),
        "Objective depends on a specific day of the week",
    ),
    (
        re.compile(r"\b(requires?\s+(a\s+)?(car|vehicle|bicycle|bike|scooter)\b)", re.IGNORECASE),
        "Objective requires a vehicle the player may not have",
    ),
    (
        re.compile(
            r"\b(requires?\s+(a\s+)?(friend|companion|partner|group|team)\b)", re.IGNORECASE
        ),
        "Objective requires another person (solo quest)",
    ),
    (
        re.compile(r"\b(only\s+available|limited\s+time|expires?|deadline)\b", re.IGNORECASE),
        "Objective references time-limited external availability",
    ),
]

# Generic/boilerplate title guard
_GENERIC_TITLES = {
    "quest",
    "mission",
    "task",
    "challenge",
    "adventure",
    "new quest",
    "your quest",
    "a quest",
    "untitled",
}

# Minimum words for a useful brief
_MIN_BRIEF_WORDS = 8

# XP-per-minute rough sanity bounds
_MIN_XP_PER_MIN = 1.0  # e.g. 10 XP for 10 min — too low
_MAX_XP_PER_MIN = 15.0  # e.g. 200 XP for 10 min — too high


class QuestQualityValidator:
    """Content quality validator.

    Findings are SOFT_BLOCK (retry / fallback) or WARNING (logged only).
    No safety judgements are made here — those belong in QuestSafetyValidator.
    """

    def validate(self, quest: GeneratedQuestOutput) -> ValidationReport:
        report = ValidationReport()

        self._check_title(quest, report)
        self._check_brief(quest, report)
        self._check_objectives(quest, report)
        self._check_duration_vs_objectives(quest, report)
        self._check_impossible_requirements(quest, report)
        self._check_xp_rate(quest, report)
        self._check_safety_notes_for_hard_difficulty(quest, report)

        return report

    # ------------------------------------------------------------------

    def _check_title(self, quest: GeneratedQuestOutput, report: ValidationReport) -> None:
        title_lower = quest.title.lower().strip()

        if title_lower in _GENERIC_TITLES:
            report.add(
                ValidationIssue(
                    severity=Severity.SOFT_BLOCK,
                    code="QUALITY_GENERIC_TITLE",
                    field="title",
                    message=(
                        f"Title '{quest.title}' is too generic. "
                        "Quest titles should be descriptive and evocative."
                    ),
                )
            )
            return

        if len(quest.title.split()) < 2:
            report.add(
                ValidationIssue(
                    severity=Severity.WARNING,
                    code="QUALITY_TITLE_TOO_SHORT",
                    field="title",
                    message=(
                        f"Title '{quest.title}' is a single word — "
                        "consider a more descriptive title."
                    ),
                )
            )

    def _check_brief(self, quest: GeneratedQuestOutput, report: ValidationReport) -> None:
        words = quest.brief.split()
        if len(words) < _MIN_BRIEF_WORDS:
            report.add(
                ValidationIssue(
                    severity=Severity.SOFT_BLOCK,
                    code="QUALITY_BRIEF_TOO_SHORT",
                    field="brief",
                    message=(
                        f"Brief has only {len(words)} word(s); "
                        f"minimum is {_MIN_BRIEF_WORDS} for a useful mission description."
                    ),
                )
            )

        # Brief should not be identical to the title (lazy model output)
        if quest.brief.strip().lower() == quest.title.strip().lower():
            report.add(
                ValidationIssue(
                    severity=Severity.SOFT_BLOCK,
                    code="QUALITY_BRIEF_SAME_AS_TITLE",
                    field="brief",
                    message="Brief is identical to the title — no actual mission context provided.",
                )
            )

    def _check_objectives(self, quest: GeneratedQuestOutput, report: ValidationReport) -> None:
        required = [o for o in quest.objectives if not o.optional]
        total = len(quest.objectives)

        # Must have at least one required objective (also enforced by schema)
        if not required:
            report.add(
                ValidationIssue(
                    severity=Severity.SOFT_BLOCK,
                    code="QUALITY_NO_REQUIRED_OBJECTIVE",
                    field="objectives",
                    message="All objectives are optional — there is no clear success condition.",
                )
            )

        # Too many objectives for the duration
        if total > 8:
            report.add(
                ValidationIssue(
                    severity=Severity.WARNING,
                    code="QUALITY_TOO_MANY_OBJECTIVES",
                    field="objectives",
                    message=(
                        f"Quest has {total} objectives. More than 8 may make "
                        "completion unrealistic within the given duration."
                    ),
                )
            )

        # Check each objective for vague / non-actionable instructions
        seen_instructions: set[str] = set()
        for obj in quest.objectives:
            instr_lower = obj.instruction.lower().strip()

            # Duplicate detection
            if instr_lower in seen_instructions:
                report.add(
                    ValidationIssue(
                        severity=Severity.SOFT_BLOCK,
                        code="QUALITY_DUPLICATE_OBJECTIVE",
                        field="objectives",
                        message=f"Duplicate objective instruction: '{obj.instruction}'",
                    )
                )
            seen_instructions.add(instr_lower)

            # Vague instruction check
            for pattern in _VAGUE_PATTERNS:
                if pattern.search(obj.instruction):
                    report.add(
                        ValidationIssue(
                            severity=Severity.SOFT_BLOCK,
                            code="QUALITY_VAGUE_OBJECTIVE",
                            field="objectives",
                            message=(
                                f"Objective '{obj.id}' has a vague or incomplete instruction: "
                                f"'{obj.instruction}'"
                            ),
                        )
                    )
                    break  # one issue per objective

            # Instruction too short to be actionable
            if len(obj.instruction.split()) < 4:
                report.add(
                    ValidationIssue(
                        severity=Severity.SOFT_BLOCK,
                        code="QUALITY_OBJECTIVE_TOO_SHORT",
                        field="objectives",
                        message=(
                            f"Objective '{obj.id}' instruction is too short "
                            f"({len(obj.instruction.split())} words) to be actionable: "
                            f"'{obj.instruction}'"
                        ),
                    )
                )

    def _check_duration_vs_objectives(
        self, quest: GeneratedQuestOutput, report: ValidationReport
    ) -> None:
        """Flag quests with more required objectives than time allows."""
        required_count = sum(1 for o in quest.objectives if not o.optional)
        # Rough heuristic: each required objective needs at least 3 minutes
        min_minutes_needed = required_count * 3

        if quest.duration_minutes < min_minutes_needed:
            report.add(
                ValidationIssue(
                    severity=Severity.SOFT_BLOCK,
                    code="QUALITY_DURATION_TOO_SHORT_FOR_OBJECTIVES",
                    field="duration_minutes",
                    message=(
                        f"Duration {quest.duration_minutes} min is likely too short for "
                        f"{required_count} required objective(s) "
                        f"(estimated minimum: {min_minutes_needed} min)."
                    ),
                )
            )

    def _check_impossible_requirements(
        self, quest: GeneratedQuestOutput, report: ValidationReport
    ) -> None:
        corpus = " ".join(
            [
                quest.brief,
                " ".join(obj.instruction for obj in quest.objectives),
            ]
        )
        for pattern, message in _IMPOSSIBLE_PATTERNS:
            if pattern.search(corpus):
                report.add(
                    ValidationIssue(
                        severity=Severity.SOFT_BLOCK,
                        code="QUALITY_IMPOSSIBLE_REQUIREMENT",
                        field="objectives",
                        message=message,
                    )
                )

    def _check_xp_rate(self, quest: GeneratedQuestOutput, report: ValidationReport) -> None:
        """Flag suspiciously low or high XP per minute."""
        if quest.duration_minutes <= 0:
            return
        rate = quest.xp_reward / quest.duration_minutes
        if rate < _MIN_XP_PER_MIN:
            report.add(
                ValidationIssue(
                    severity=Severity.WARNING,
                    code="QUALITY_XP_RATE_TOO_LOW",
                    field="xp_reward",
                    message=(
                        f"XP rate {rate:.1f} XP/min is unusually low "
                        f"({quest.xp_reward} XP for {quest.duration_minutes} min)."
                    ),
                )
            )
        elif rate > _MAX_XP_PER_MIN:
            report.add(
                ValidationIssue(
                    severity=Severity.WARNING,
                    code="QUALITY_XP_RATE_TOO_HIGH",
                    field="xp_reward",
                    message=(
                        f"XP rate {rate:.1f} XP/min is unusually high "
                        f"({quest.xp_reward} XP for {quest.duration_minutes} min)."
                    ),
                )
            )

    def _check_safety_notes_for_hard_difficulty(
        self, quest: GeneratedQuestOutput, report: ValidationReport
    ) -> None:
        """Explorer and chaos quests should always carry safety notes."""
        if quest.difficulty in ("explorer", "chaos"):
            if not quest.safety_notes or len(quest.safety_notes.strip()) < 10:
                report.add(
                    ValidationIssue(
                        severity=Severity.WARNING,
                        code="QUALITY_MISSING_SAFETY_NOTES",
                        field="safety_notes",
                        message=(
                            f"Difficulty '{quest.difficulty}' quests should include "
                            "safety notes, but none were provided."
                        ),
                    )
                )
