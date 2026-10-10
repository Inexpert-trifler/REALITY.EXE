import pytest
from httpx import AsyncClient
from app.main import app
from app.core.config import get_settings

settings = get_settings()

@pytest.fixture(autouse=True)
def disable_db(monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_MODE", "disabled")

@pytest.mark.asyncio
async def test_health_endpoint_when_db_disabled():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "disabled"

@pytest.mark.asyncio
async def test_endpoint_returns_503_when_db_disabled():
    # Attempting to access an endpoint that requires the DB, for example /api/v1/auth/login or /api/v1/player/profile
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/v1/auth/login", data={"username": "test", "password": "password"})
    assert response.status_code == 503
    assert response.json() == {"detail": "Database persistence is disabled in this environment."}
