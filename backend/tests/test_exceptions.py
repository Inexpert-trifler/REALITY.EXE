import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import (
    AppException,
    NotFoundException,
    app_exception_handler,
    unhandled_exception_handler,
)
from app.middleware.request_id import RequestIDMiddleware


@pytest.mark.asyncio
async def test_custom_app_exception():
    """Test custom AppException produces structured error response."""
    test_app = FastAPI()
    test_app.add_middleware(RequestIDMiddleware)
    test_app.add_exception_handler(AppException, app_exception_handler)

    @test_app.get("/test-not-found")
    async def trigger_not_found():
        raise NotFoundException("User profile not found", details={"user_id": "123"})

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/test-not-found")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
        assert data["error"]["message"] == "User profile not found"
        assert data["error"]["details"]["user_id"] == "123"
        assert "request_id" in data["error"]


@pytest.mark.asyncio
async def test_unhandled_exception():
    """Test unhandled exception produces structured 500 error response without crashing."""
    test_app = FastAPI()
    test_app.add_middleware(RequestIDMiddleware)
    test_app.add_exception_handler(Exception, unhandled_exception_handler)

    @test_app.get("/test-crash")
    async def trigger_crash():
        raise RuntimeError("Unexpected internal crash")

    transport = ASGITransport(app=test_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/test-crash")
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert data["error"]["message"] == "An unexpected server error occurred"
