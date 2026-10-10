"""Health check route handler."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.health import HealthResponse
from app.services.health_service import HealthService
from app.api.dependencies import CurrentUser, get_text_provider, get_storage_provider

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service health check",
    responses={
        200: {"description": "Service is healthy or degraded"},
    },
)
async def get_health(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """Return the current health status of the API and its dependencies."""
    return await HealthService.get_health_status(db=db)


@router.get(
    "/api/v1/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service health check (v1)",
)
async def get_health_v1(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    return await HealthService.get_health_status(db=db)


@router.get(
    "/api/v1/db/health",
    status_code=status.HTTP_200_OK,
    summary="Database health check",
)
async def get_db_health(db: AsyncSession = Depends(get_db)) -> dict:
    health = await HealthService.get_health_status(db=db)
    if health.database == "error":
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="Database degraded")
    return {"status": health.database}


@router.get(
    "/api/v1/ai/health",
    status_code=status.HTTP_200_OK,
    summary="AI health check",
)
async def get_ai_health(
    user: CurrentUser,
    provider=Depends(get_text_provider)
) -> dict:
    provider_name = type(provider).__name__.replace("TextProvider", "").lower()
    
    if hasattr(provider, "check_health"):
        res = await provider.check_health()
        return {
            "provider": provider_name,
            "reachable": res.reachable,
            "configured_model": getattr(res, "model", "unknown"),
            "latency_ms": getattr(res, "latency_ms", None) if res.reachable else None,
            "server_version": getattr(res, "server_version", None),
            "error": getattr(res, "error", None),
        }
    return {
        "provider": provider_name,
        "reachable": True,
        "configured_model": getattr(provider, "model_name", "unknown"),
        "latency_ms": 0,
        "server_version": "N/A",
        "error": None,
    }


@router.get(
    "/api/v1/storage/health",
    status_code=status.HTTP_200_OK,
    summary="Storage health check",
)
async def get_storage_health(
    user: CurrentUser,
    provider=Depends(get_storage_provider)
) -> dict:
    # Lightweight check
    return {"status": "configured", "provider": type(provider).__name__}
