"""EvidenceVerificationService — vision analysis and outcome classification.

Pipeline:
  1. Load evidence record + associated quest attempt + quest.
  2. Fetch image bytes from storage.
  3. Call vision provider (VisionModelProvider.analyze_evidence).
  4. Classify result into VerificationOutcome.
  5. Persist AIAnalysis record.
  6. Return structured AnalysisResultResponse.

Classification rules (deterministic, applied after AI call):
  - Any safety_concerns → UNSAFE (regardless of confidence or recommendation)
  - confidence < UNCERTAIN_THRESHOLD → UNCERTAIN (allow retry, no completion)
  - completion_recommendation=True AND confidence ≥ SUCCESS_THRESHOLD → SUCCESS
  - otherwise → INCOMPLETE (allow retry)

The vision provider may be unavailable (Ollama offline).  In that case
we fall back to UNCERTAIN so the player can retry later.
"""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import EvidenceAnalysisRequest, VisionModelProvider
from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.ai_analysis import AIAnalysis
from app.models.quest import Quest
from app.models.quest_attempt import QuestAttempt
from app.repositories.evidence_repository import AIAnalysisRepository, EvidenceRepository
from app.schemas.completion import AnalysisResultResponse, VerificationOutcome

logger = logging.getLogger(__name__)

_evidence_repo = EvidenceRepository()
_analysis_repo = AIAnalysisRepository()

# ---------------------------------------------------------------------------
# Classification thresholds
# ---------------------------------------------------------------------------
SUCCESS_THRESHOLD: float = 0.70  # Confidence required to award completion
UNCERTAIN_THRESHOLD: float = 0.40  # Below this → UNCERTAIN regardless of recommendation

# Human-readable messages per outcome
_OUTCOME_MESSAGES: dict[VerificationOutcome, str] = {
    VerificationOutcome.SUCCESS: ("Great work! Your evidence confirms mission success."),
    VerificationOutcome.INCOMPLETE: (
        "The evidence doesn't clearly show the mission objective. Try uploading a clearer photo."
    ),
    VerificationOutcome.UNCERTAIN: (
        "The AI couldn't confidently evaluate your evidence this time. You can retry the analysis."
    ),
    VerificationOutcome.UNSAFE: (
        "The evidence contains safety concerns and cannot be accepted. "
        "Please stay safe and try a different approach."
    ),
}


def classify_result(
    is_relevant: bool,
    completion_recommendation: bool,
    confidence: float,
    safety_concerns: list[str],
) -> VerificationOutcome:
    """Classify vision analysis output into a VerificationOutcome.

    Rules applied in priority order:
    1. Any safety concern → UNSAFE
    2. Confidence below uncertain threshold → UNCERTAIN
    3. Recommended + sufficient confidence → SUCCESS
    4. Everything else → INCOMPLETE
    """
    if safety_concerns:
        return VerificationOutcome.UNSAFE
    if confidence < UNCERTAIN_THRESHOLD:
        return VerificationOutcome.UNCERTAIN
    if completion_recommendation and confidence >= SUCCESS_THRESHOLD:
        return VerificationOutcome.SUCCESS
    return VerificationOutcome.INCOMPLETE


async def analyze_evidence(
    db: AsyncSession,
    *,
    evidence_id: UUID,
    user_id: UUID,
    vision_provider: VisionModelProvider,
    image_bytes: bytes | None = None,
) -> AnalysisResultResponse:
    """Run vision analysis on a piece of evidence and persist the result.

    Args:
        db:              Active async DB session.
        evidence_id:     Evidence to analyse.
        user_id:         Authenticated user (must own the attempt).
        vision_provider: Configured VisionModelProvider.
        image_bytes:     Pre-loaded image bytes (used in tests to avoid
                         storage I/O; if None the bytes are loaded from
                         the storage key — not implemented yet, tests
                         must pass bytes directly).

    Returns:
        AnalysisResultResponse with outcome, confidence, and flags.
    """
    # Load evidence
    evidence = await _evidence_repo.get_by_id(db, evidence_id)
    if evidence is None:
        raise NotFoundException(message="Evidence not found")

    # Load attempt and verify ownership
    result = await db.execute(select(QuestAttempt).where(QuestAttempt.id == evidence.attempt_id))
    attempt = result.scalar_one_or_none()
    if attempt is None:
        raise NotFoundException(message="Quest attempt not found")
    if attempt.user_id != user_id:
        raise ForbiddenException(message="You do not own this evidence")

    # Load quest for context
    quest_result = await db.execute(select(Quest).where(Quest.id == attempt.quest_id))
    quest = quest_result.scalar_one_or_none()
    objectives = quest.objectives_json if quest else []
    brief = quest.brief if quest else ""

    # Run vision analysis — fall back to UNCERTAIN if provider is unavailable
    try:

        if image_bytes is None:
            # In production: load from storage.  For now require caller to pass bytes.
            raise NotFoundException(
                message="Image bytes must be provided for analysis (storage loading not yet implemented)"
            )

        analysis_result = await vision_provider.analyze_evidence(
            EvidenceAnalysisRequest(
                image_bytes=image_bytes,
                mime_type=evidence.mime_type,
                quest_brief=brief,
                quest_objectives=objectives if isinstance(objectives, list) else [objectives],
            )
        )
        visible_content = analysis_result.visible_content
        is_relevant = analysis_result.is_relevant
        confidence = float(analysis_result.confidence)
        safety_concerns = list(analysis_result.safety_concerns)
        model_rec = analysis_result.completion_recommendation
        model_name = analysis_result.model_name
        model_version = analysis_result.model_version

    except Exception as exc:  # noqa: BLE001

        if isinstance(exc, NotFoundException):
            raise
        logger.error("Vision provider error during analysis: %s", exc, exc_info=True)
        # Unavailable provider → UNCERTAIN, player can retry
        visible_content = ""
        is_relevant = False
        confidence = 0.0
        safety_concerns = []
        model_rec = False
        model_name = "unavailable"
        model_version = "unknown"

    outcome = classify_result(is_relevant, model_rec, confidence, safety_concerns)

    # Persist AIAnalysis record
    analysis = AIAnalysis(
        evidence_id=evidence_id,
        model_name=model_name,
        model_version=model_version,
        confidence=confidence,
        findings_json={
            "visible_content": visible_content,
            "is_relevant": is_relevant,
            "safety_concerns": safety_concerns,
        },
        completion_recommendation=outcome.value,
    )
    created_analysis = await _analysis_repo.create(db, analysis)

    logger.info(
        "Evidence analysis: evidence=%s outcome=%s confidence=%.2f model=%s",
        evidence_id,
        outcome.value,
        confidence,
        model_name,
    )

    if outcome == VerificationOutcome.SUCCESS:
        from app.domain.quest_states import AttemptStatus

        if attempt.status == AttemptStatus.EVIDENCE_PENDING.value:
            from app.services import quest_service

            await quest_service.start_verification(db, user_id, attempt.quest_id)

    return AnalysisResultResponse(
        analysis_id=str(created_analysis.id),
        evidence_id=str(evidence_id),
        outcome=outcome,
        confidence=confidence,
        visible_content=visible_content,
        safety_concerns=safety_concerns,
        completion_recommendation=model_rec,
        can_complete=(outcome == VerificationOutcome.SUCCESS),
        can_retry=(outcome in (VerificationOutcome.INCOMPLETE, VerificationOutcome.UNCERTAIN)),
        message=_OUTCOME_MESSAGES[outcome],
        model_name=model_name,
        created_at=created_analysis.created_at,
    )
