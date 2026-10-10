"""Quest attempt state machine definition.

This module is the single source of truth for all valid statuses and the
allowed transitions between them.  Nothing outside this module is
permitted to define or hard-code status strings.
"""

from enum import StrEnum

from app.core.exceptions import BadRequestException


class AttemptStatus(StrEnum):
    """All possible QuestAttempt statuses.

    Inherits from StrEnum so that ``str(status) == status.value`` and the
    enum value can be used directly wherever a plain string is expected
    (e.g., SQLAlchemy column writes, JSON serialisation).
    """

    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    POCKET_MODE = "POCKET_MODE"
    RETURNED = "RETURNED"
    EVIDENCE_PENDING = "EVIDENCE_PENDING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    PAUSED = "PAUSED"
    ABANDONED = "ABANDONED"
    FAILED = "FAILED"


# ---------------------------------------------------------------------------
# Transition map
#
# Keys are the *current* status; values are the set of statuses that are
# valid next states.  Any transition not listed here is forbidden.
# ---------------------------------------------------------------------------

VALID_TRANSITIONS: dict[AttemptStatus, frozenset[AttemptStatus]] = {
    AttemptStatus.CREATED: frozenset(
        {
            AttemptStatus.ACTIVE,
            AttemptStatus.ABANDONED,
        }
    ),
    AttemptStatus.ACTIVE: frozenset(
        {
            AttemptStatus.POCKET_MODE,
            AttemptStatus.PAUSED,
            AttemptStatus.ABANDONED,
            AttemptStatus.FAILED,
        }
    ),
    AttemptStatus.POCKET_MODE: frozenset(
        {
            AttemptStatus.RETURNED,
            AttemptStatus.ABANDONED,
            AttemptStatus.FAILED,
        }
    ),
    AttemptStatus.RETURNED: frozenset(
        {
            AttemptStatus.EVIDENCE_PENDING,
            AttemptStatus.COMPLETED,  # evidence_required=False shortcut
            AttemptStatus.ABANDONED,
        }
    ),
    AttemptStatus.EVIDENCE_PENDING: frozenset(
        {
            AttemptStatus.VERIFYING,
            AttemptStatus.ABANDONED,
            AttemptStatus.FAILED,
        }
    ),
    AttemptStatus.VERIFYING: frozenset(
        {
            AttemptStatus.COMPLETED,
            AttemptStatus.EVIDENCE_PENDING,  # retry
            AttemptStatus.FAILED,
        }
    ),
    AttemptStatus.PAUSED: frozenset(
        {
            AttemptStatus.ACTIVE,  # resume
            AttemptStatus.ABANDONED,
        }
    ),
    # Terminal states — no outgoing transitions
    AttemptStatus.COMPLETED: frozenset(),
    AttemptStatus.ABANDONED: frozenset(),
    AttemptStatus.FAILED: frozenset(),
}

# Statuses that represent a live (non-terminal) attempt
ACTIVE_STATUSES: frozenset[AttemptStatus] = frozenset(
    {
        AttemptStatus.CREATED,
        AttemptStatus.ACTIVE,
        AttemptStatus.POCKET_MODE,
        AttemptStatus.RETURNED,
        AttemptStatus.EVIDENCE_PENDING,
        AttemptStatus.VERIFYING,
        AttemptStatus.PAUSED,
    }
)

# Terminal statuses
TERMINAL_STATUSES: frozenset[AttemptStatus] = frozenset(
    {
        AttemptStatus.COMPLETED,
        AttemptStatus.ABANDONED,
        AttemptStatus.FAILED,
    }
)


def assert_transition(current: AttemptStatus, target: AttemptStatus) -> None:
    """Validate that *current* → *target* is an allowed transition.

    Raises:
        BadRequestException (400): if the transition is invalid, with a
            message that names both statuses clearly so the client can
            act on it without reading source code.
    """
    allowed = VALID_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        allowed_names = sorted(s.value for s in allowed)
        raise BadRequestException(
            message=(
                f"Cannot transition from {current.value} to {target.value}. "
                f"Allowed next states: {allowed_names or ['none (terminal)']}"
            ),
            details={
                "current_status": current.value,
                "target_status": target.value,
                "allowed_transitions": allowed_names,
            },
        )
