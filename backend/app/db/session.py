import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

from fastapi import HTTPException
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE

logger = logging.getLogger(__name__)

settings = get_settings()

if settings.DATABASE_MODE == "disabled":
    engine = None
    AsyncSessionLocal = None
else:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        future=True,
        pool_pre_ping=True,
    )

    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing asynchronous SQLAlchemy sessions."""
    if settings.DATABASE_MODE == "disabled":
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database persistence is disabled in this environment."
        )
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_optional() -> AsyncGenerator[AsyncSession | None, None]:
    """Optional dependency for providing sessions, returning None if disabled."""
    if settings.DATABASE_MODE == "disabled":
        yield None
        return
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
