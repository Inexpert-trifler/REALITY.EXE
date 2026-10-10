"""Quest generation orchestrator.

Implements the full pipeline:
  request → build context → build prompt → model → parse →
  schema validation → safety validation → quality validation →
  business validation → persist

Recovery strategy:
  1. First model call + full validation pipeline.
  2. One retry on any validation failure (new model call, same prompt).
  3. Fallback to deterministic library quest.

Safety violations (HARD_BLOCK) are never retried — the quest is immediately
rejected and fallback is served.  The fallback library is pre-validated and
safe by construction.

The fake test provider must never be wired here in production — that guard
is enforced by the dependency injection layer.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import QuestGenerationRequest, RawModelOutput, TextModelProvider
from app.ai.fallback_library import FallbackQuest, get_fallback_quest
from app.ai.schemas.quest_output import GeneratedQuestOutput, QuestGenerateRequest
from app.ai.validators import ValidationPipeline
from app.ai.validators.output_validator import (
    JSONParseError,
    SchemaValidationError,
    parse_json,
    validate_schema,
)
from app.ai.validators.result import ValidationReport
from app.models.quest import Quest
from app.repositories.quest_repository import QuestRepository
from app.schemas.quest import QuestResponse

logger = logging.getLogger(__name__)

_quest_repo = QuestRepository()
_pipeline = ValidationPipeline()

# Maximum model attempts before falling back
_MAX_ATTEMPTS = 2


def _to_quest_model(
    validated: GeneratedQuestOutput,
    raw: RawModelOutput,
) -> Quest:
    """Map a validated GeneratedQuestOutput + metadata → Quest ORM model."""
    return Quest(
        title=validated.title,
        brief=validated.brief,
        duration_minutes=validated.duration_minutes,
        environment="unknown",  # not in model output; set from request by caller
        difficulty=validated.difficulty,
        play_style="unknown",  # set from request by caller
        personality="unknown",  # set from request by caller
        objectives_json=validated.model_dump()["objectives"],
        xp_reward=validated.xp_reward,
        evidence_required=validated.evidence_required,
        safety_notes=validated.safety_notes or None,
        model_name=raw.model_name,
        prompt_version=raw.prompt_version,
    )


def _fallback_to_quest_model(fb: FallbackQuest, req: QuestGenerateRequest) -> Quest:
    """Map a fallback library quest → Quest ORM model."""
    return Quest(
        title=fb.title,
        brief=fb.brief,
        duration_minutes=fb.duration_minutes,
        environment=req.environment,
        difficulty=fb.difficulty,
        play_style=req.play_style,
        personality=req.personality,
        objectives_json=fb.objectives,
        xp_reward=fb.xp_reward,
        evidence_required=fb.evidence_required,
        safety_notes=fb.safety_notes or None,
        model_name=fb.model_name,
        prompt_version=fb.prompt_version,
    )


def _quest_to_response(quest: Quest) -> QuestResponse:
    from app.schemas.quest import QuestResponse

    return QuestResponse(
        id=str(quest.id),
        title=quest.title,
        brief=quest.brief,
        duration_minutes=quest.duration_minutes,
        environment=quest.environment,
        difficulty=quest.difficulty,
        play_style=quest.play_style,
        personality=quest.personality,
        objectives=quest.objectives_json
        if isinstance(quest.objectives_json, list)
        else [quest.objectives_json],
        xp_reward=quest.xp_reward,
        evidence_required=quest.evidence_required,
        safety_notes=quest.safety_notes,
        created_at=quest.created_at,
    )


class QuestOrchestrator:
    """Drives the full quest generation pipeline for one request."""

    def __init__(self, provider: TextModelProvider) -> None:
        self._provider = provider

    async def generate(
        self,
        db: AsyncSession,
        request: QuestGenerateRequest,
        player_level: int = 1,
        previous_quest_titles: list[str] | None = None,
    ) -> QuestResponse:
        """Generate, validate, and persist a quest.

        Returns:
            QuestResponse — either AI-generated or from the fallback library.
        """
        gen_request = QuestGenerationRequest(
            duration_minutes=request.duration_minutes,
            environment=request.environment,
            difficulty=request.difficulty,
            play_style=request.play_style,
            personality=request.personality,
            player_level=player_level,
            previous_quest_titles=previous_quest_titles or [],
        )

        import time

        last_report: ValidationReport | None = None
        last_error: Exception | None = None

        for attempt_num in range(1, _MAX_ATTEMPTS + 1):
            start_time = time.time()
            try:
                raw = await self._provider.generate_quest(gen_request)
                latency = round((time.time() - start_time) * 1000, 2)

                logger.info(
                    "AI generation completed",
                    extra={
                        "event": "ai_generation",
                        "model": raw.model_name,
                        "latency": latency,
                        "prompt_tokens": raw.prompt_tokens,
                        "completion_tokens": raw.completion_tokens,
                        "attempt": attempt_num,
                    },
                )

                if not raw.text.strip():
                    raise JSONParseError("Model returned empty response")

                # Layer 1 — JSON parse
                data = parse_json(raw.text)

                # Layer 2 — Schema validation
                validated = validate_schema(data)

                # Layers 3+4+5 — Safety, Quality, Business via pipeline
                report = _pipeline.run(validated, requested_duration=request.duration_minutes)
                last_report = report

                # HARD_BLOCK: safety violation — never retry, go straight to fallback
                if report.has_hard_blocks:
                    logger.warning(
                        "Quest attempt blocked by HARD safety rules",
                        extra={
                            "event": "quest_validation",
                            "attempt": attempt_num,
                            "status": "hard_blocked",
                            "blocks": [i.code for i in report.hard_blocks],
                        },
                    )
                    break  # exit retry loop → fallback

                # SOFT_BLOCK: quality or business failure — retry if attempts remain
                if report.has_soft_blocks:
                    logger.warning(
                        "Quest attempt has soft blocks",
                        extra={
                            "event": "quest_validation",
                            "attempt": attempt_num,
                            "status": "soft_blocked",
                            "blocks": [i.code for i in report.soft_blocks],
                        },
                    )
                    if attempt_num < _MAX_ATTEMPTS:
                        continue  # retry
                    break  # out of attempts → fallback

                # All clear — persist and return
                quest_model = _to_quest_model(validated, raw)
                quest_model.environment = request.environment
                quest_model.play_style = request.play_style
                quest_model.personality = request.personality

                persisted = await _quest_repo.create(db, quest_model)
                logger.info(
                    "Quest generated and persisted",
                    extra={
                        "event": "quest_generation_success",
                        "quest_id": str(persisted.id),
                        "model": raw.model_name,
                        "attempt": attempt_num,
                        "warnings_count": len(report.warnings),
                    },
                )
                return _quest_to_response(persisted)

            except (JSONParseError, SchemaValidationError) as exc:
                latency = round((time.time() - start_time) * 1000, 2)
                last_error = exc
                logger.warning(
                    "Attempt %d/%d — parse/schema error",
                    attempt_num,
                    _MAX_ATTEMPTS,
                    extra={
                        "event": "ai_failure",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "attempt": attempt_num,
                        "latency": latency,
                    },
                )
            except Exception as exc:
                latency = round((time.time() - start_time) * 1000, 2)
                last_error = exc
                logger.error(
                    "Attempt %d/%d — unexpected error",
                    attempt_num,
                    _MAX_ATTEMPTS,
                    exc_info=True,
                    extra={
                        "event": "ai_failure",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "attempt": attempt_num,
                        "latency": latency,
                    },
                )

        # All model attempts failed or were blocked — use deterministic fallback
        reason = (
            f"safety hard-block: {[i.code for i in last_report.hard_blocks]}"
            if last_report and last_report.has_hard_blocks
            else str(last_error)
        )
        logger.warning(
            "All %d AI attempt(s) failed (reason: %s). "
            "Serving fallback quest for env=%s difficulty=%s.",
            _MAX_ATTEMPTS,
            reason,
            request.environment,
            request.difficulty,
        )
        fallback = get_fallback_quest(
            duration_minutes=request.duration_minutes,
            environment=request.environment,
            difficulty=request.difficulty,
            play_style=request.play_style,
        )
        quest_model = _fallback_to_quest_model(fallback, request)
        persisted = await _quest_repo.create(db, quest_model)
        logger.info("Fallback quest persisted: id=%s", persisted.id)
        return _quest_to_response(persisted)
