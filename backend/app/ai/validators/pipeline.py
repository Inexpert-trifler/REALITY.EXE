"""ValidationPipeline — orchestrates all three validators in order.

Pipeline order:
  1. QuestSafetyValidator   → HARD_BLOCK stops the pipeline immediately
  2. QuestQualityValidator  → SOFT_BLOCK / WARNING continue accumulating
  3. QuestBusinessValidator → SOFT_BLOCK / WARNING continue accumulating

If safety produces any HARD_BLOCK issues the pipeline stops and returns
immediately — quality and business validators are not even run, preventing
any DB write by callers that respect the contract.

Usage:
    pipeline = ValidationPipeline()
    report = pipeline.run(quest, requested_duration=20)
    if report.has_hard_blocks:
        # quest must not reach the DB — trigger fallback
    elif report.has_soft_blocks:
        # retry if attempts remain, else fallback
    else:
        # safe to persist
"""

import logging

from app.ai.schemas.quest_output import GeneratedQuestOutput
from app.ai.validators.business_validator import QuestBusinessValidator
from app.ai.validators.quality_validator import QuestQualityValidator
from app.ai.validators.result import ValidationReport
from app.ai.validators.safety_validator import QuestSafetyValidator

logger = logging.getLogger(__name__)


class ValidationPipeline:
    """Three-stage validation pipeline for AI-generated quests.

    Instantiate once and call run() per quest.  All validators are
    stateless so the same instance can be reused across requests.
    """

    def __init__(self) -> None:
        self._safety = QuestSafetyValidator()
        self._quality = QuestQualityValidator()
        self._business = QuestBusinessValidator()

    def run(
        self,
        quest: GeneratedQuestOutput,
        *,
        requested_duration: int | None = None,
    ) -> ValidationReport:
        """Run all validators and return a merged ValidationReport.

        Args:
            quest:              Pydantic-validated quest output.
            requested_duration: Player's originally requested duration,
                                used by the business validator to check
                                the model respected the request.

        Returns:
            ValidationReport containing all findings from all stages.
            Callers MUST check report.has_hard_blocks before persisting.
        """
        # Stage 1 — Safety (hard-block stops here)
        safety_report = self._safety.validate(quest)

        if safety_report.has_hard_blocks:
            logger.warning(
                "Quest failed HARD safety validation: %d issue(s) — "
                "pipeline halted, quest will not be persisted. codes=%s",
                len(safety_report.hard_blocks),
                [i.code for i in safety_report.hard_blocks],
            )
            return safety_report

        # Stage 2 — Quality
        quality_report = self._quality.validate(quest)

        # Stage 3 — Business rules
        business_report = self._business.validate(quest, requested_duration=requested_duration)

        merged = safety_report.merge(quality_report).merge(business_report)

        if merged.is_blocking:
            logger.warning(
                "Quest failed validation: hard=%d soft=%d warn=%d",
                len(merged.hard_blocks),
                len(merged.soft_blocks),
                len(merged.warnings),
            )
        elif merged.warnings:
            logger.info(
                "Quest passed validation with %d warning(s): %s",
                len(merged.warnings),
                [i.code for i in merged.warnings],
            )
        else:
            logger.info("Quest passed all validation stages cleanly.")

        return merged
