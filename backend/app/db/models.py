"""Central import of all ORM models.

Import this module anywhere you need all models registered with
``Base.metadata`` — e.g., in the test DB setup fixture, Alembic env.py,
and the app lifespan.  Each import ensures the model class is registered.
"""

# fmt: off
from app.models.achievement import Achievement  # noqa: F401
from app.models.ai_analysis import AIAnalysis  # noqa: F401
from app.models.chaos_session import ChaosSession  # noqa: F401
from app.models.evidence import Evidence  # noqa: F401
from app.models.player_profile import PlayerProfile  # noqa: F401
from app.models.quest import Quest  # noqa: F401
from app.models.quest_attempt import QuestAttempt  # noqa: F401
from app.models.reflection import Reflection  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.xp_transaction import XPTransaction  # noqa: F401
# fmt: on
