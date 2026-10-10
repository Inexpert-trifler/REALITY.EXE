import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_health_endpoint(async_client: AsyncClient):
    """Test GET /health returns 200 and expected metadata structure."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["service"] == "REALITY.EXE API"
    assert data["version"] in ("0.1.0", "")
    assert data["environment"] in ("development", "testing", "production", "test", "")
    assert "timestamp" in data
    assert data["database"] == "connected"
    assert data["uptime_seconds"] is None or isinstance(data["uptime_seconds"], (int, float))


@pytest.mark.asyncio
async def test_api_v1_health_endpoint(async_client: AsyncClient):
    """Test GET /api/v1/health returns 200 and expected metadata structure."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["service"] == "REALITY.EXE API"
    assert data["version"] in ("0.1.0", "")
    assert data["database"] == "connected"
