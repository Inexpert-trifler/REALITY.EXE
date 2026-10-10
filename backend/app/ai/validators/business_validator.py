"""QuestBusinessValidator — product and game-design rule enforcement.

Checks that the generated quest conforms to the platform's supported
configuration space — valid enum values, XP within difficulty-appropriate
bounds, duration within the supported range.

Issues are SOFT_BLOCK (trigger retry/fallback).  None are HARD_BLOCK
because business rule violations do not pose safety risks.
"""

from app.ai.schemas.quest_output import (
    VALID_DIFFICULTIES,
    GeneratedQuestOutput,
)
from app.ai.validators.result import Severity, ValidationIssue, ValidationReport

# Supported duration range (minutes)
MIN_DURATION = 5
MAX_DURATION = 120

# Duration tolerance when matching against the player's requested duration (±)
DURATION_TOLERANCE = 5

# XP bounds per difficulty level [inclusive min, inclusive max]
XP_BOUNDS: dict[str, tuple[int, int]] = {
    "chill": (50, 125),
    "curious": (75, 150),
    "explorer": (100, 200),
    "chaos": (100, 200),
}

# Minimum and maximum total objectives
MIN_OBJECTIVES = 1
MAX_OBJECTIVES = 10


class QuestBusinessValidator:
    """Business rules validator.

    All findings are SOFT_BLOCK — they indicate the model produced output
    that doesn't fit the game's configuration, warranting a retry or fallback.
    """

    def validate(
        self,
        quest: GeneratedQuestOutput,
        *,
        requested_duration: int | None = None,
    ) -> ValidationReport:
        """Run all business rules.

        Args:
            quest:              Validated quest output from schema layer.
            requested_duration: Player's requested duration (if available).
                                When provided, the quest duration must be
                                within DURATION_TOLERANCE minutes of it.
        """
        report = ValidationReport()

        self._check_difficulty(quest, report)
        self._check_duration_range(quest, report)
        self._check_duration_vs_request(quest, report, requested_duration)
        self._check_xp_bounds(quest, report)
        self._check_objective_count(quest, report)

        return report

    # ------------------------------------------------------------------

    def _check_difficulty(self, quest: GeneratedQuestOutput, report: ValidationReport) -> None:
        if quest.difficulty not in VALID_DIFFICULTIES:
            report.add(
                ValidationIssue(
                    severity=Severity.SOFT_BLOCK,
                    code="BUSINESS_INVALID_DIFFICULTY",
                    field="difficulty",
                    message=(
                        f"Difficulty '{quest.difficulty}' is not supported. "
                        f"Valid values: {sorted(VALID_DIFFICULTIES)}"
                    ),
                )
            )

    def _check_duration_range(self, quest: GeneratedQuestOutput, report: ValidationReport) -> None:
        if quest.duration_minutes < MIN_DURATION:
            report.add(
                ValidationIssue(
                    severity=Severity.SOFT_BLOCK,
                    code="BUSINESS_DURATION_TOO_SHORT",
                    field="duration_minutes",
                    message=(
                        f"Duration {quest.duration_minutes} min is below the "
                        f"platform minimum of {MIN_DURATION} min."
                    ),
                )
            )
        elif quest.duration_minutes > MAX_DURATION:
            report.add(
                ValidationIssue(
                    severity=Severity.SOFT_BLOCK,
                    code="BUSINESS_DURATION_TOO_LONG",
                    field="duration_minutes",
                    message=(
                        f"Duration {quest.duration_minutes} min exceeds the "
                        f"platform maximum of {MAX_DURATION} min."
                    ),
                )
            )

    def _check_duration_vs_request(
        self,
        quest: GeneratedQuestOutput,
        report: ValidationReport,
        requested_duration: int | None,
    ) -> None:
        if requested_duration is None:
            return
        delta = abs(quest.duration_minutes - requested_duration)
        if delta > DURATION_TOLERANCE:
            report.add(
                ValidationIssue(
                    severity=Severity.SOFT_BLOCK,
                    code="BUSINESS_DURATION_MISMATCH",
                    field="duration_minutes",
                    message=(
                        f"Quest duration {quest.duration_minutes} min does not match "
                        f"the requested {requested_duration} min "
                        f"(tolerance ±{DURATION_TOLERANCE} min, actual delta {delta} min)."
                    ),
                )
            )

    def _check_xp_bounds(self, quest: GeneratedQuestOutput, report: ValidationReport) -> None:
        bounds = XP_BOUNDS.get(quest.difficulty)
        if bounds is None:
            # Unknown difficulty — already flagged by _check_difficulty, skip XP check
            return
        lo, hi = bounds
        if not (lo <= quest.xp_reward <= hi):
            report.add(
                ValidationIssue(
                    severity=Severity.SOFT_BLOCK,
                    code="BUSINESS_XP_OUT_OF_RANGE",
                    field="xp_reward",
                    message=(
                        f"xp_reward {quest.xp_reward} is outside the expected range "
                        f"[{lo}, {hi}] for difficulty '{quest.difficulty}'."
                    ),
                )
            )

    def _check_objective_count(self, quest: GeneratedQuestOutput, report: ValidationReport) -> None:
        count = len(quest.objectives)
        if count < MIN_OBJECTIVES:
            report.add(
                ValidationIssue(
                    severity=Severity.SOFT_BLOCK,
                    code="BUSINESS_TOO_FEW_OBJECTIVES",
                    field="objectives",
                    message=(f"Quest has {count} objective(s); minimum is {MIN_OBJECTIVES}."),
                )
            )
        elif count > MAX_OBJECTIVES:
            report.add(
                ValidationIssue(
                    severity=Severity.SOFT_BLOCK,
                    code="BUSINESS_TOO_MANY_OBJECTIVES",
                    field="objectives",
                    message=(f"Quest has {count} objective(s); maximum is {MAX_OBJECTIVES}."),
                )
            )
