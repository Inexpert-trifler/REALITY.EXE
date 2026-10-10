"""ChaosService — continuation quest generation for Chaos Mode.

Flow:
  completed attempt
  → player provides discovery context
  → load chaos session (or create one for the first continuation)
  → check chain depth limit
  → build enriched prompt using prior quest + discovery
  → call text provider (QuestOrchestrator)
  → safety validation (same pipeline, no risk escalation)
  → start new attempt on continuation quest
  → update chaos session

Constraints:
  - Maximum chain depth is configurable via Settings.CHAOS_MAX_CHAIN_DEPTH
  - Every continuation passes the full safety + quality + business validators
  - AI cannot escalate risk (enforced by the existing SafetyValidator)
  - Player can exit at any time
  - Duplicate calls (same attempt_id after chain is active) return the
    existing next quest without regenerating
"""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import TextModelProvider
from app.ai.orchestrator import QuestOrchestrator
from app.ai.schemas.quest_output import QuestGenerateRequest
from app.core.config import get_settings
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.domain.quest_states import AttemptStatus
from app.models.chaos_session import ChaosSession
from app.models.quest import Quest
from app.models.quest_attempt import QuestAttempt
from app.repositories.base import BaseRepository
from app.schemas.chaos import ChaosNextResponse, ChaosSessionResponse
from app.schemas.quest import QuestResponse
from app.services import quest_service

logger = logging.getLogger(__name__)


class ChaosSessionRepository(BaseRepository[ChaosSession]):
    def __init__(self) -> None:
        super().__init__(ChaosSession)

    async def get_by_root_attempt(
        self, db: AsyncSession, root_attempt_id: UUID
    ) -> ChaosSession | None:
        result = await db.execute(
            select(ChaosSession).where(ChaosSession.root_attempt_id == root_attempt_id)
        )
        return result.scalar_one_or_none()

    async def get_active_for_user(self, db: AsyncSession, user_id: UUID) -> ChaosSession | None:
        result = await db.execute(
            select(ChaosSession).where(
                ChaosSession.user_id == user_id,
                ChaosSession.status == "ACTIVE",
            )
        )
        return result.scalar_one_or_none()


_session_repo = ChaosSessionRepository()

_DIFFICULTY_CHAOS = "chaos"


def _quest_to_response(quest: Quest) -> QuestResponse:
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


async def generate_chaos_next(
    db: AsyncSession,
    *,
    user_id: UUID,
    completed_attempt_id: UUID,
    discovery_context: str,
    duration_minutes: int = 20,
    text_provider: TextModelProvider,
) -> ChaosNextResponse:
    """Generate the next quest in a Chaos chain.

    Args:
        db:                    Active async DB session.
        user_id:               Authenticated player.
        completed_attempt_id:  The just-completed attempt that seeds the chain.
        discovery_context:     What the player found — used as AI context.
        duration_minutes:      Requested duration for the next quest.
        text_provider:         Text provider for quest generation.

    Returns:
        ChaosNextResponse with session state + next quest + new attempt started.

    Raises:
        NotFoundException:   Attempt not found.
        ForbiddenException:  Attempt belongs to another user.
        BadRequestException: Attempt not COMPLETED, chain at max depth,
                             or duplicate continuation request.
    """
    settings = get_settings()

    # Load and validate the seed attempt
    result = await db.execute(select(QuestAttempt).where(QuestAttempt.id == completed_attempt_id))
    attempt = result.scalar_one_or_none()
    if attempt is None:
        raise NotFoundException(message="Quest attempt not found")
    if attempt.user_id != user_id:
        raise ForbiddenException(message="You do not own this quest attempt")
    if AttemptStatus(attempt.status) != AttemptStatus.COMPLETED:
        raise BadRequestException(
            message="Chaos continuation is only available for COMPLETED quest attempts",
            details={"current_status": attempt.status},
        )

    # Load the parent quest for context
    quest_result = await db.execute(select(Quest).where(Quest.id == attempt.quest_id))
    parent_quest = quest_result.scalar_one_or_none()

    # Check for an existing chaos session (idempotency)
    session = await _session_repo.get_by_root_attempt(db, completed_attempt_id)
    if session is not None and session.status == "ACTIVE":
        # Already have a session — check for duplicate: if current_attempt is still ACTIVE,
        # the player hasn't started the next quest yet.  Return what we have.
        if session.current_attempt_id and session.current_attempt_id != completed_attempt_id:
            cur_result = await db.execute(
                select(QuestAttempt).where(QuestAttempt.id == session.current_attempt_id)
            )
            current_attempt = cur_result.scalar_one_or_none()
            if current_attempt and AttemptStatus(current_attempt.status) not in (
                AttemptStatus.COMPLETED,
                AttemptStatus.ABANDONED,
                AttemptStatus.FAILED,
            ):
                # Fetch the quest for the current attempt
                next_quest_result = await db.execute(
                    select(Quest).where(Quest.id == current_attempt.quest_id)
                )
                next_quest = next_quest_result.scalar_one_or_none()
                if next_quest:
                    logger.info(
                        "Chaos idempotent: returning existing continuation attempt=%s",
                        current_attempt.id,
                    )
                    return ChaosNextResponse(
                        session=ChaosSessionResponse(
                            session_id=str(session.id),
                            chain_depth=session.chain_depth,
                            max_chain_depth=session.max_chain_depth,
                            can_continue=session.chain_depth < session.max_chain_depth,
                            status=session.status,
                        ),
                        next_quest=_quest_to_response(next_quest),
                        message="Returning existing continuation quest.",
                    )

    # Determine chain depth and max
    max_depth = getattr(settings, "CHAOS_MAX_CHAIN_DEPTH", 5)
    if session is None:
        # First continuation from this completed attempt
        chain_depth = 2  # root was depth 1
        session = ChaosSession(
            user_id=user_id,
            root_attempt_id=completed_attempt_id,
            current_attempt_id=completed_attempt_id,
            chain_depth=chain_depth,
            max_chain_depth=max_depth,
            status="ACTIVE",
            discovery_context=discovery_context,
        )
        session = await _session_repo.create(db, session)
    else:
        chain_depth = session.chain_depth + 1
        if chain_depth > session.max_chain_depth:
            raise BadRequestException(
                message=(
                    f"Chaos chain has reached the maximum depth "
                    f"({session.max_chain_depth}). Exit or complete the current quest."
                ),
                details={
                    "chain_depth": session.chain_depth,
                    "max_chain_depth": session.max_chain_depth,
                },
            )

    # Build enriched generation request
    personality = parent_quest.personality if parent_quest else "Wizard"
    environment = parent_quest.environment if parent_quest else "any"
    prior_title = parent_quest.title if parent_quest else "a prior quest"

    enriched_brief = (
        f"[Chaos chain depth {chain_depth}/{max_depth}] "
        f"The player just completed: '{prior_title}'. "
        f"They discovered: {discovery_context}. "
        f"Generate a direct continuation quest that builds on this discovery."
    )

    gen_request = QuestGenerateRequest(
        duration_minutes=duration_minutes,
        environment=environment,
        difficulty=_DIFFICULTY_CHAOS,
        play_style="chaos",
        personality=personality,
    )

    # Generate via orchestrator (full safety pipeline)
    orchestrator = QuestOrchestrator(provider=text_provider)

    # Override previous_quest_titles to avoid repetition
    next_quest_response = await orchestrator.generate(
        db,
        request=gen_request,
        player_level=1,
        previous_quest_titles=[prior_title] if parent_quest else [],
    )

    # Start an attempt on the new quest so the player can begin immediately
    new_attempt_response = await quest_service.start_attempt(
        db, user_id, UUID(next_quest_response.id)
    )

    # Update the chaos session
    await _session_repo.update(
        db,
        session.id,
        {
            "chain_depth": chain_depth,
            "current_attempt_id": UUID(new_attempt_response.id),
            "discovery_context": discovery_context,
        },
    )

    logger.info(
        "Chaos next generated: session=%s depth=%d/%d next_attempt=%s",
        session.id,
        chain_depth,
        max_depth,
        new_attempt_response.id,
    )

    return ChaosNextResponse(
        session=ChaosSessionResponse(
            session_id=str(session.id),
            chain_depth=chain_depth,
            max_chain_depth=max_depth,
            can_continue=chain_depth < max_depth,
            status="ACTIVE",
        ),
        next_quest=next_quest_response,
        message=(
            f"Continuation quest generated (chain {chain_depth}/{max_depth}). "
            "Your new quest awaits."
        ),
    )
