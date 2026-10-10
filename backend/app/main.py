from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import setup_logging
from app.middleware.logging import LoggingMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

_DEFAULT_AUTH_SECRET = "super-secret-key-change-in-production-min-32-chars-length"

# ---------------------------------------------------------------------------
# OpenAPI tag definitions (controls sidebar order and descriptions in /docs)
# ---------------------------------------------------------------------------
_OPENAPI_TAGS = [
    {
        "name": "Authentication",
        "description": "Register, log in, log out, and inspect the current user.",
    },
    {
        "name": "Player",
        "description": "Player profile, preferences, and aggregated statistics.",
    },
    {
        "name": "Quests",
        "description": (
            "Quest catalogue, AI quest generation, and the full quest-attempt "
            "state machine (start → pocket → return → evidence → complete)."
        ),
    },
    {
        "name": "Evidence",
        "description": "Secure multipart image upload for quest completion evidence.",
    },
    {
        "name": "AI",
        "description": "AI vision analysis and provider health checks.",
    },
    {
        "name": "Reflections",
        "description": "AI-generated post-quest Game Master reflections.",
    },
    {
        "name": "Achievements",
        "description": "Achievement catalogue with unlock state and timestamps.",
    },
    {
        "name": "History",
        "description": "Paginated, filterable quest attempt history.",
    },
    {
        "name": "Health",
        "description": "Service and database health check (unauthenticated).",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    setup_logging(log_level=settings.LOG_LEVEL, environment=settings.ENVIRONMENT)

    if settings.ENVIRONMENT == "production":
        if settings.AUTH_SECRET == _DEFAULT_AUTH_SECRET:
            raise RuntimeError(
                "AUTH_SECRET must be changed from the default value before "
                "running in production.  Set the AUTH_SECRET environment variable."
            )
        if settings.DEBUG:
            raise RuntimeError(
                "DEBUG must be False in production. Set DEBUG=False in the environment."
            )
    yield


def create_app() -> FastAPI:
    """FastAPI Application Factory."""
    settings = get_settings()
    is_prod = settings.ENVIRONMENT == "production"

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=(
            "**REALITY.EXE** — Real-World Quest Generator and Life Gamification Engine.\n\n"
            "All protected endpoints require a `Bearer` token in the `Authorization` header.\n"
            "Tokens are obtained via `POST /auth/register` or `POST /auth/login`.\n\n"
            "### Error format\n"
            "Every error response follows a consistent envelope:\n"
            "```json\n"
            '{"error": {"code": "NOT_FOUND", "message": "Quest not found.", '
            '"request_id": "..."}}\n'
            "```\n"
        ),
        openapi_tags=_OPENAPI_TAGS,
        # Hide interactive docs and raw schema in production
        openapi_url=None if is_prod else f"{settings.API_V1_STR}/openapi.json",
        docs_url=None if is_prod else f"{settings.API_V1_STR}/docs",
        redoc_url=None if is_prod else f"{settings.API_V1_STR}/redoc",
        lifespan=lifespan,
    )

    # Attach rate limiter state
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Configure CORS
    if settings.ALLOWED_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.ALLOWED_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Middleware (bottom to top for request processing)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # Exception handlers
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    @app.api_route("/", methods=["GET", "HEAD"], tags=["Root"], include_in_schema=False)
    async def root():
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "status": "online",
            "message": "REALITY.EXE API is running. Visit /health for system status."
        }

    # Root health route (unauthenticated)
    app.include_router(health_router, prefix="")

    # API v1 routes
    app.include_router(api_router, prefix=settings.API_V1_STR)

    # ── Inject Bearer security scheme into generated OpenAPI spec ───────────
    def _custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            tags=_OPENAPI_TAGS,
            routes=app.routes,
        )
        # Define the BearerAuth security scheme
        schema.setdefault("components", {}).setdefault("securitySchemes", {})["BearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "JWT access token.  Obtain one via `POST /auth/register` or "
                "`POST /auth/login`.  Include as `Authorization: Bearer <token>`."
            ),
        }
        # Apply to all operations by default
        for path_item in schema.get("paths", {}).values():
            for operation in path_item.values():
                if isinstance(operation, dict):
                    operation.setdefault("security", [{"BearerAuth": []}])
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = _custom_openapi  # type: ignore[method-assign]

    return app


app = create_app()
