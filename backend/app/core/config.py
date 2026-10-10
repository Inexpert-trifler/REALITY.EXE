from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_AUTH_SECRET = "super-secret-key-change-in-production-min-32-chars-length"


class Settings(BaseSettings):
    """Application Settings managed via Pydantic v2 settings."""

    PROJECT_NAME: str = "REALITY.EXE API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = (
        "API for REALITY.EXE - Real-World Quest Generator and Life Gamification Engine"
    )
    # Default to development; production deployments must set ENVIRONMENT=production
    ENVIRONMENT: str = "development"
    # Default DEBUG off — set DEBUG=true in .env for local development
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/reality_exe"
    SYNC_DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/reality_exe"

    # Security
    AUTH_SECRET: str = _DEFAULT_AUTH_SECRET
    ALGORITHM: str = "HS256"
    # Reduced from 7 days to 1 hour for better security.
    # Clients that need longer sessions should implement refresh tokens.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Progression — XP required to reach each level (index = level - 1)
    # Level 1 starts at 0 XP; extend this list to add more levels.
    XP_CURVE: list[int] = [0, 100, 250, 500, 850, 1300]

    # AI generation settings
    AI_MAX_RETRIES: int = 2  # model call attempts before fallback
    AI_REQUEST_TIMEOUT_SECONDS: float = 120.0
    AI_GENERATION_TEMPERATURE: float = 0.85

    # Chaos Mode
    CHAOS_MAX_CHAIN_DEPTH: int = 5  # maximum continuation chain length

    # CORS
    ALLOWED_ORIGINS: list[str] | str = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # External services & models
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    TEXT_MODEL: str = "llama3"
    VISION_MODEL: str = "llava"

    STORAGE_ENDPOINT: str = ""
    STORAGE_BUCKET: str = ""
    STORAGE_ACCESS_KEY: str = ""
    STORAGE_SECRET_KEY: str = ""

    # Evidence upload settings
    STORAGE_BACKEND: str = "local"  # "local" | "s3"
    EVIDENCE_UPLOAD_DIR: str = "/tmp/reality_exe_evidence"  # local dev only
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

    MAPS_API_KEY: str = ""
    WEATHER_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("AUTH_SECRET")
    @classmethod
    def validate_auth_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("AUTH_SECRET must be at least 32 characters")
        return v

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json

                return json.loads(v)
            return [i.strip() for i in v.split(",")]
        return v


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
