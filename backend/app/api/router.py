from fastapi import APIRouter

from app.api.routes.achievements import router as achievements_router
from app.api.routes.ai import router as ai_router
from app.api.routes.auth import router as auth_router
from app.api.routes.completion import router as completion_router
from app.api.routes.evidence import router as evidence_router
from app.api.routes.health import router as health_router
from app.api.routes.history import router as history_router
from app.api.routes.player import router as player_router
from app.api.routes.quests import router as quests_router
from app.api.routes.reflections import router as reflections_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(player_router)
api_router.include_router(quests_router)
api_router.include_router(ai_router)
api_router.include_router(evidence_router)
api_router.include_router(completion_router)
api_router.include_router(reflections_router)
api_router.include_router(achievements_router)
api_router.include_router(history_router)
