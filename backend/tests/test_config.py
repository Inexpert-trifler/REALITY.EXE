from app.core.config import Settings, get_settings


def test_settings_defaults():
    """Test default values of application settings."""
    settings = get_settings()
    assert settings.PROJECT_NAME == "REALITY.EXE API"
    assert settings.VERSION == "0.1.0"
    assert settings.API_V1_STR == "/api/v1"
    assert isinstance(settings.ALLOWED_ORIGINS, list)
    assert len(settings.ALLOWED_ORIGINS) > 0


def test_cors_origins_parsing():
    """Test parsing string list in CORS origins."""
    settings = Settings(ALLOWED_ORIGINS='["http://localhost:3000","http://example.com"]')
    assert settings.ALLOWED_ORIGINS == ["http://localhost:3000", "http://example.com"]
