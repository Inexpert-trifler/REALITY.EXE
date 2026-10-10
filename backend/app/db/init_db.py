import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def init_db(db: AsyncSession) -> None:
    """Initialize database tables and seed baseline system data if required."""
    logger.info("Verifying database connection...")
    result = await db.execute(text("SELECT 1"))
    if result.scalar() == 1:
        logger.info("Database connection verified successfully.")
    else:
        logger.error("Database connection ping failed.")
