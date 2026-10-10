"""Authentication request and response schemas."""

import re

from pydantic import BaseModel, EmailStr, Field, field_validator

# Password policy constants
_MIN_PASSWORD_LENGTH = 8
_MAX_PASSWORD_LENGTH = 128
_USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


class RegisterRequest(BaseModel):
    """Payload for new user registration."""

    username: str = Field(
        ...,
        min_length=3,
        max_length=30,
        description="Unique username (letters, numbers, underscores, hyphens only)",
    )
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(
        ...,
        min_length=_MIN_PASSWORD_LENGTH,
        max_length=_MAX_PASSWORD_LENGTH,
        description="Password (min 8 chars, must contain letter and digit)",
    )
    display_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Player display name shown in the game",
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if not _USERNAME_PATTERN.match(v):
            raise ValueError("Username may only contain letters, numbers, underscores, and hyphens")
        return v.lower()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Lowercase and strip whitespace for consistent storage."""
        return v.strip().lower()

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Display name must not be blank")
        return v

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Enforce strong password: at least one letter and one digit."""
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    """Payload for user login."""

    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., min_length=1, description="Account password")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class TokenResponse(BaseModel):
    """JWT access token issued after successful auth."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token lifetime in seconds")


class PlayerProfileResponse(BaseModel):
    """Embedded player profile data within the user response."""

    display_name: str
    level: int
    total_xp: int
    preferred_personality: str | None
    preferred_play_style: str | None

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    """Public-safe user data returned after registration or from /me."""

    id: str
    username: str
    email: str
    profile: PlayerProfileResponse | None

    model_config = {"from_attributes": True}


class RegisterResponse(BaseModel):
    """Response returned after successful registration."""

    user: UserResponse
    token: TokenResponse


class LoginResponse(BaseModel):
    """Response returned after successful login."""

    user: UserResponse
    token: TokenResponse


class LogoutResponse(BaseModel):
    """Response returned after logout."""

    message: str = "Successfully logged out"
