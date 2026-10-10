"""Comprehensive authentication tests.

Covers:
  - successful registration
  - duplicate email
  - duplicate username
  - invalid password (weak)
  - successful login
  - wrong password
  - invalid token
  - expired token
  - authenticated /me
  - unauthenticated request
"""

from datetime import timedelta

import pytest
from httpx import AsyncClient

from app.utils.jwt import create_access_token_with_expiry

# ---------------------------------------------------------------------------
# Shared test data helpers
# ---------------------------------------------------------------------------

BASE_URL = "/api/v1/auth"


def _reg_payload(**overrides) -> dict:
    """Return a valid registration payload, with optional field overrides."""
    base = {
        "username": "testplayer",
        "email": "player@example.com",
        "password": "Secure1234",
        "display_name": "Test Player",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRegister:
    async def test_successful_registration(self, async_client: AsyncClient):
        """Happy-path: register returns 201, a user object, and a bearer token."""
        resp = await async_client.post(f"{BASE_URL}/register", json=_reg_payload())
        assert resp.status_code == 201, resp.text

        body = resp.json()
        user = body["user"]
        token = body["token"]

        # User fields
        assert user["username"] == "testplayer"
        assert user["email"] == "player@example.com"
        assert "id" in user
        assert "password" not in user
        assert "password_hash" not in user

        # Profile initialised with game defaults
        profile = user["profile"]
        assert profile["display_name"] == "Test Player"
        assert profile["level"] == 1
        assert profile["total_xp"] == 0

        # Token shape
        assert token["token_type"] == "bearer"
        assert len(token["access_token"]) > 0
        assert token["expires_in"] > 0

    async def test_email_is_normalised_to_lowercase(self, async_client: AsyncClient):
        """Emails with mixed case should be stored and returned lowercase."""
        resp = await async_client.post(
            f"{BASE_URL}/register",
            json=_reg_payload(email="UPPER@Example.COM", username="caseuser"),
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["user"]["email"] == "upper@example.com"

    async def test_duplicate_email_returns_409(self, async_client: AsyncClient):
        """Registering with an already-used email must return 409."""
        payload = _reg_payload(username="firstuser")
        await async_client.post(f"{BASE_URL}/register", json=payload)

        # Second registration, different username but same email
        dupe = _reg_payload(username="seconduser")
        resp = await async_client.post(f"{BASE_URL}/register", json=dupe)
        assert resp.status_code == 409, resp.text
        body = resp.json()
        assert body["error"]["code"] == "CONFLICT"
        assert "email" in body["error"]["message"].lower()

    async def test_duplicate_username_returns_409(self, async_client: AsyncClient):
        """Registering with an already-used username must return 409."""
        await async_client.post(
            f"{BASE_URL}/register",
            json=_reg_payload(email="first@example.com", username="sharedname"),
        )

        resp = await async_client.post(
            f"{BASE_URL}/register",
            json=_reg_payload(email="second@example.com", username="sharedname"),
        )
        assert resp.status_code == 409, resp.text
        body = resp.json()
        assert body["error"]["code"] == "CONFLICT"
        assert "username" in body["error"]["message"].lower()

    async def test_password_without_digit_is_rejected(self, async_client: AsyncClient):
        """Password with no digit should fail validation (422)."""
        resp = await async_client.post(
            f"{BASE_URL}/register",
            json=_reg_payload(password="NoDigitsHere!", username="u1", email="u1@x.com"),
        )
        assert resp.status_code == 422, resp.text

    async def test_password_without_letter_is_rejected(self, async_client: AsyncClient):
        """Password with no letter should fail validation (422)."""
        resp = await async_client.post(
            f"{BASE_URL}/register",
            json=_reg_payload(password="12345678", username="u2", email="u2@x.com"),
        )
        assert resp.status_code == 422, resp.text

    async def test_password_too_short_is_rejected(self, async_client: AsyncClient):
        """Passwords under 8 characters should fail (422)."""
        resp = await async_client.post(
            f"{BASE_URL}/register",
            json=_reg_payload(password="Ab1", username="u3", email="u3@x.com"),
        )
        assert resp.status_code == 422, resp.text

    async def test_invalid_email_format_returns_422(self, async_client: AsyncClient):
        """Malformed email address should fail validation (422)."""
        resp = await async_client.post(
            f"{BASE_URL}/register",
            json=_reg_payload(email="not-an-email", username="u4"),
        )
        assert resp.status_code == 422, resp.text

    async def test_username_with_spaces_is_rejected(self, async_client: AsyncClient):
        """Usernames containing spaces should fail (422)."""
        resp = await async_client.post(
            f"{BASE_URL}/register",
            json=_reg_payload(username="bad user", email="u5@x.com"),
        )
        assert resp.status_code == 422, resp.text

    async def test_empty_display_name_is_rejected(self, async_client: AsyncClient):
        """Blank display_name should fail validation (422)."""
        resp = await async_client.post(
            f"{BASE_URL}/register",
            json=_reg_payload(display_name="   ", username="u6", email="u6@x.com"),
        )
        assert resp.status_code == 422, resp.text

    async def test_missing_required_fields_returns_422(self, async_client: AsyncClient):
        """Omitting required fields should return 422."""
        resp = await async_client.post(f"{BASE_URL}/register", json={"email": "x@x.com"})
        assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class TestLogin:
    @pytest.fixture(autouse=True)
    async def _create_user(self, async_client: AsyncClient):
        """Ensure a known user exists before every login test."""
        await async_client.post(
            f"{BASE_URL}/register",
            json=_reg_payload(username="loginuser", email="login@example.com"),
        )

    async def test_successful_login(self, async_client: AsyncClient):
        """Valid credentials return 200 with a token."""
        resp = await async_client.post(
            f"{BASE_URL}/login",
            json={"email": "login@example.com", "password": "Secure1234"},
        )
        assert resp.status_code == 200, resp.text

        body = resp.json()
        assert body["token"]["token_type"] == "bearer"
        assert len(body["token"]["access_token"]) > 0
        assert body["user"]["username"] == "loginuser"

    async def test_wrong_password_returns_401(self, async_client: AsyncClient):
        """Incorrect password returns 401."""
        resp = await async_client.post(
            f"{BASE_URL}/login",
            json={"email": "login@example.com", "password": "WrongPass99"},
        )
        assert resp.status_code == 401, resp.text
        assert resp.json()["error"]["code"] == "UNAUTHORIZED"

    async def test_unknown_email_returns_401(self, async_client: AsyncClient):
        """Unknown email address returns 401 (no user enumeration via 404)."""
        resp = await async_client.post(
            f"{BASE_URL}/login",
            json={"email": "ghost@example.com", "password": "Secure1234"},
        )
        assert resp.status_code == 401, resp.text

    async def test_email_normalised_on_login(self, async_client: AsyncClient):
        """Login with mixed-case email should succeed (normalisation applied)."""
        resp = await async_client.post(
            f"{BASE_URL}/login",
            json={"email": "LOGIN@EXAMPLE.COM", "password": "Secure1234"},
        )
        assert resp.status_code == 200, resp.text

    async def test_missing_password_returns_422(self, async_client: AsyncClient):
        """Missing password field should return 422."""
        resp = await async_client.post(f"{BASE_URL}/login", json={"email": "login@example.com"})
        assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


class TestLogout:
    async def test_logout_with_valid_token(self, async_client: AsyncClient):
        """Authenticated logout returns 200."""
        reg = await async_client.post(
            f"{BASE_URL}/register",
            json=_reg_payload(username="logoutuser", email="logout@example.com"),
        )
        token = reg.json()["token"]["access_token"]

        resp = await async_client.post(
            f"{BASE_URL}/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert "logged out" in resp.json()["message"].lower()

    async def test_logout_without_token_returns_401(self, async_client: AsyncClient):
        """Calling /logout without a token must return 401."""
        resp = await async_client.post(f"{BASE_URL}/logout")
        assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# /me  — authenticated endpoint
# ---------------------------------------------------------------------------


class TestMe:
    async def test_me_returns_user_with_valid_token(self, async_client: AsyncClient):
        """GET /me with a valid token returns the authenticated user."""
        reg = await async_client.post(
            f"{BASE_URL}/register",
            json=_reg_payload(username="meuser", email="me@example.com"),
        )
        assert reg.status_code == 201
        token = reg.json()["token"]["access_token"]

        resp = await async_client.get(
            f"{BASE_URL}/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text

        body = resp.json()
        assert body["username"] == "meuser"
        assert body["email"] == "me@example.com"
        assert body["profile"]["level"] == 1
        assert body["profile"]["total_xp"] == 0
        assert "password" not in body
        assert "password_hash" not in body

    async def test_me_without_token_returns_401(self, async_client: AsyncClient):
        """GET /me with no Authorization header returns 401."""
        resp = await async_client.get(f"{BASE_URL}/me")
        assert resp.status_code == 401, resp.text
        assert resp.json()["error"]["code"] == "UNAUTHORIZED"

    async def test_me_with_invalid_token_returns_401(self, async_client: AsyncClient):
        """GET /me with a garbage token returns 401."""
        resp = await async_client.get(
            f"{BASE_URL}/me",
            headers={"Authorization": "Bearer this.is.not.a.valid.jwt"},
        )
        assert resp.status_code == 401, resp.text
        assert resp.json()["error"]["code"] == "UNAUTHORIZED"

    async def test_me_with_expired_token_returns_401(self, async_client: AsyncClient):
        """GET /me with an expired token returns 401."""
        # Register to get a valid user id, then craft an already-expired token
        reg = await async_client.post(
            f"{BASE_URL}/register",
            json=_reg_payload(username="expireduser", email="expired@example.com"),
        )
        user_id = reg.json()["user"]["id"]

        expired_token = create_access_token_with_expiry(
            subject=user_id,
            expires_delta=timedelta(seconds=-1),  # expired immediately
        )

        resp = await async_client.get(
            f"{BASE_URL}/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401, resp.text
        body = resp.json()
        assert body["error"]["code"] == "UNAUTHORIZED"
        assert "expired" in body["error"]["message"].lower()

    async def test_me_with_malformed_bearer_scheme(self, async_client: AsyncClient):
        """Non-bearer schemes should return 401."""
        resp = await async_client.get(
            f"{BASE_URL}/me",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert resp.status_code == 401, resp.text

    async def test_me_token_from_login_works(self, async_client: AsyncClient):
        """Token obtained via /login should authenticate /me correctly."""
        await async_client.post(
            f"{BASE_URL}/register",
            json=_reg_payload(username="loginmeuser", email="loginme@example.com"),
        )
        login_resp = await async_client.post(
            f"{BASE_URL}/login",
            json={"email": "loginme@example.com", "password": "Secure1234"},
        )
        token = login_resp.json()["token"]["access_token"]

        me_resp = await async_client.get(
            f"{BASE_URL}/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_resp.status_code == 200, me_resp.text
        assert me_resp.json()["username"] == "loginmeuser"
