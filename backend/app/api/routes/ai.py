"""AI provider management routes."""

import logging

from fastapi import APIRouter, Depends, status

from app.api.dependencies import CurrentUser, get_text_provider
from app.schemas.ai_health import AIHealthResponse
from app.schemas.errors import AUTH_RESPONSES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"])


@router.get(
    "/health",
    response_model=AIHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Check AI provider (Ollama) availability",
    responses={
        200: {
            "description": (
                "AI provider health status. Always HTTP 200 — "
                "check `reachable` field for actual provider status."
            )
        },
        **AUTH_RESPONSES,
    },
)
async def ai_health(
    _current_user: CurrentUser,
    provider=Depends(get_text_provider),
) -> AIHealthResponse:
    """Probe the configured AI provider and return health information.

    This endpoint **always returns HTTP 200** — it never returns `503`
    when the AI is down, because the application can still serve quests
    from the deterministic fallback library.

    Check the `reachable` field to determine whether the AI backend is up:

    | `reachable` | Meaning |
    |---|---|
    | `true` | Ollama is online and responding |
    | `false` | Ollama is offline; `error` field explains why |

    **Requires**: `Authorization: Bearer <token>`
    """
    from app.ai.providers.ollama_provider import OllamaTextProvider

    if isinstance(provider, OllamaTextProvider):
        result = await provider.check_health()
        return AIHealthResponse(
            provider="ollama",
            reachable=result.reachable,
            configured_model=result.model,
            latency_ms=result.latency_ms if result.reachable else None,
            server_version=result.server_version,
            error=result.error,
        )

    return AIHealthResponse(
        provider=type(provider).__name__.lower(),
        reachable=True,
        configured_model=provider.model_name,
        latency_ms=None,
        server_version=None,
        error=None,
    )
