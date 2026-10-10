import logging
import time
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)

START_TIME = time.time()


class HealthService:
    """Service layer for health checks and system status diagnostics."""

    @staticmethod
    async def get_health_status(db: AsyncSession | None = None) -> HealthResponse:
        """Check status of application and optional database connection."""
        settings = get_settings()
        db_status = "not_checked"

        if db is not None:
            try:
                # Execute simple ping query
                result = await db.execute(text("SELECT 1"))
                if result.scalar() == 1:
                    db_status = "connected"
                else:
                    db_status = "error"
            except Exception as e:
                logger.warning(f"Database health check failed: {e}")
                db_status = "disconnected"

        uptime = round(time.time() - START_TIME, 2)
        overall_status = "healthy" if db_status in ("connected", "not_checked") else "degraded"

        # In production, omit fingerprinting data (version, environment, uptime)
        # to reduce information leakage to unauthenticated callers.
        hide_details = settings.ENVIRONMENT == "production"

        return HealthResponse(
            status=overall_status,
            service=settings.PROJECT_NAME,
            version="" if hide_details else settings.VERSION,
            environment="" if hide_details else settings.ENVIRONMENT,
            timestamp=datetime.now(UTC),
            database=db_status,
            uptime_seconds=None if hide_details else uptime,
        )
