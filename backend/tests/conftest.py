from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.db.models  # noqa: F401 — ensures all ORM models are registered with Base.metadata
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app

# Use in-memory SQLite for fast, isolated async testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Create all table schemas in the test database before running tests."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean DB session per test."""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTPX AsyncClient bound to the FastAPI test app with DB dependency override."""
    app = create_app()

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def make_client_with_provider(db_session: AsyncSession):
    """Factory fixture: returns a context-manager async client with a custom AI provider override.

    Usage in tests:
        async with make_client_with_provider(FakeTextProvider()) as client:
            resp = await client.post(...)
    """
    from contextlib import asynccontextmanager

    from app.api.dependencies import get_text_provider

    @asynccontextmanager
    async def _factory(provider):
        app = create_app()

        async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
            yield db_session

        def _override_provider():
            return provider

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_text_provider] = _override_provider

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client

    return _factory
