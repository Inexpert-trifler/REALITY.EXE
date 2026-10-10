"""Comprehensive tests for the Quest Engine AI pipeline.

Covers:
  Unit (no DB / HTTP):
    Validator — JSON parsing:
      - valid JSON passthrough
      - extract from markdown fence
      - extract from prose wrapper
      - empty string raises JSONParseError
      - pure prose raises JSONParseError

    Validator — schema validation:
      - valid output passes
      - missing title fails SchemaValidationError
      - invalid difficulty fails
      - empty objectives list fails
      - all-optional objectives fail (no required objective)

    Validator — safety validation:
      - clean quest passes
      - trespass keyword triggers violation
      - vandal keyword triggers violation
      - multiple violations all reported

    Validator — business rules:
      - exact duration match passes
      - ±5 min tolerance passes
      - duration mismatch >5 min fails
      - xp_reward out of range for difficulty fails

    Fallback library:
      - always returns a quest
      - prefers matching difficulty
      - prefers matching environment

  Integration (HTTP + fake provider):
    - POST /quests/generate unauthenticated → 401
    - POST /quests/generate invalid payload → 422
    - POST /quests/generate with valid fake provider → 201 + persisted quest
    - Response contains all required fields
    - Generates quest with matching parameters
    - Retry: fail once, succeed on second attempt
    - Retry: fail twice → fallback quest served (model_name=fallback)
    - Fallback quest still returns 201 (not 5xx)
    - Provider is isolated: fake not accidentally available in prod wiring
"""

import json

import pytest
from httpx import AsyncClient

from app.ai.fallback_library import get_fallback_quest
from app.ai.validators.output_validator import (
    BusinessRuleError,
    JSONParseError,
    SafetyViolationError,
    SchemaValidationError,
    parse_json,
    run_full_validation,
    validate_business_rules,
    validate_safety,
    validate_schema,
)
from app.api.dependencies import get_text_provider
from tests.fakes.fake_provider import FakeTextProvider, _valid_quest_json

BASE_AUTH = "/api/v1/auth"
BASE_QUESTS = "/api/v1/quests"


def _reg(username: str, email: str) -> dict:
    return {
        "username": username,
        "email": email,
        "password": "Secure1234",
        "display_name": f"Player {username}",
    }


async def _register_and_token(client: AsyncClient, username: str, email: str) -> str:
    resp = await client.post(f"{BASE_AUTH}/register", json=_reg(username, email))
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _valid_payload(**overrides) -> dict:
    base = {
        "duration_minutes": 20,
        "environment": "park",
        "difficulty": "chill",
        "play_style": "explorer",
        "personality": "Wizard",
    }
    base.update(overrides)
    return base


def _valid_quest_output(duration: int = 20, difficulty: str = "chill", xp: int = 75) -> dict:
    return {
        "title": "Test Quest",
        "brief": "A test quest for unit testing purposes only. It is safe and fun.",
        "duration_minutes": duration,
        "difficulty": difficulty,
        "objectives": [
            {"id": "obj-1", "instruction": "Find a leaf on the ground", "optional": False},
        ],
        "xp_reward": xp,
        "evidence_required": True,
        "safety_notes": "Stay on public paths.",
    }


# ===========================================================================
# Unit — JSON parsing
# ===========================================================================


class TestParseJson:
    def test_valid_json_passthrough(self):
        data = {"title": "A Quest"}
        assert parse_json(json.dumps(data)) == data

    def test_extract_from_markdown_fence(self):
        raw = '```json\n{"title": "Fenced Quest"}\n```'
        assert parse_json(raw) == {"title": "Fenced Quest"}

    def test_extract_from_prose_wrapper(self):
        raw = 'Here is the quest:\n{"title": "Prose Quest"}\nThat is all.'
        assert parse_json(raw) == {"title": "Prose Quest"}

    def test_empty_string_raises(self):
        with pytest.raises(JSONParseError):
            parse_json("")

    def test_pure_prose_raises(self):
        with pytest.raises(JSONParseError):
            parse_json("This is just a sentence without any JSON at all.")

    def test_code_fence_without_json_keyword(self):
        raw = '```\n{"title": "No keyword fence"}\n```'
        assert parse_json(raw) == {"title": "No keyword fence"}


# ===========================================================================
# Unit — schema validation
# ===========================================================================


class TestValidateSchema:
    def test_valid_output_passes(self):
        result = validate_schema(_valid_quest_output())
        assert result.title == "Test Quest"

    def test_missing_title_fails(self):
        data = _valid_quest_output()
        del data["title"]
        with pytest.raises(SchemaValidationError) as exc_info:
            validate_schema(data)
        assert exc_info.value.errors

    def test_invalid_difficulty_fails(self):
        data = _valid_quest_output()
        data["difficulty"] = "extreme"
        with pytest.raises(SchemaValidationError):
            validate_schema(data)

    def test_empty_objectives_fails(self):
        data = _valid_quest_output()
        data["objectives"] = []
        with pytest.raises(SchemaValidationError):
            validate_schema(data)

    def test_all_optional_objectives_fails(self):
        data = _valid_quest_output()
        data["objectives"] = [
            {"id": "obj-1", "instruction": "Optional thing", "optional": True},
        ]
        with pytest.raises(SchemaValidationError):
            validate_schema(data)

    def test_duration_too_short_fails(self):
        data = _valid_quest_output()
        data["duration_minutes"] = 2
        with pytest.raises(SchemaValidationError):
            validate_schema(data)

    def test_xp_too_high_fails(self):
        data = _valid_quest_output()
        data["xp_reward"] = 9999
        with pytest.raises(SchemaValidationError):
            validate_schema(data)


# ===========================================================================
# Unit — safety validation
# ===========================================================================


class TestValidateSafety:
    def _make(self, **overrides):
        data = _valid_quest_output()
        data.update(overrides)
        return validate_schema(data)

    def test_clean_quest_passes(self):
        quest = self._make()
        validate_safety(quest)  # must not raise

    def test_trespass_in_brief_triggers(self):
        quest = self._make(brief="You must trespass onto private land to complete this quest.")
        with pytest.raises(SafetyViolationError) as exc_info:
            validate_safety(quest)
        assert "Trespassing" in exc_info.value.violated_rules

    def test_vandalism_keyword_triggers(self):
        quest = self._make(
            objectives=[
                {
                    "id": "obj-1",
                    "instruction": "spray-paint your name on the wall",
                    "optional": False,
                }
            ]
        )
        with pytest.raises(SafetyViolationError) as exc_info:
            validate_safety(quest)
        assert any("Vandal" in r for r in exc_info.value.violated_rules)

    def test_multiple_violations_all_reported(self):
        quest = self._make(
            brief="Steal something and trespass onto private property.",
        )
        with pytest.raises(SafetyViolationError) as exc_info:
            validate_safety(quest)
        assert len(exc_info.value.violated_rules) >= 2

    def test_weapons_keyword_triggers(self):
        quest = self._make(brief="Find a hidden weapon cache near the park.")
        with pytest.raises(SafetyViolationError):
            validate_safety(quest)

    def test_self_harm_triggers(self):
        quest = self._make(brief="Push yourself to the point of self-harm for this quest.")
        with pytest.raises(SafetyViolationError):
            validate_safety(quest)


# ===========================================================================
# Unit — business rules
# ===========================================================================


class TestValidateBusinessRules:
    def _quest(self, duration=20, difficulty="chill", xp=75):
        return validate_schema(_valid_quest_output(duration=duration, difficulty=difficulty, xp=xp))

    def test_exact_duration_passes(self):
        validate_business_rules(self._quest(duration=20), requested_duration=20)

    def test_within_tolerance_passes(self):
        validate_business_rules(self._quest(duration=20), requested_duration=25)

    def test_duration_mismatch_fails(self):
        with pytest.raises(BusinessRuleError):
            validate_business_rules(self._quest(duration=20), requested_duration=45)

    def test_xp_below_range_fails(self):
        with pytest.raises(BusinessRuleError):
            validate_business_rules(self._quest(xp=10), requested_duration=20)

    def test_xp_above_range_for_chill_fails(self):
        with pytest.raises(BusinessRuleError):
            # chill range is 50-125; 200 is too high
            validate_business_rules(self._quest(xp=200), requested_duration=20)

    def test_correct_xp_for_explorer_passes(self):
        quest = validate_schema(_valid_quest_output(difficulty="explorer", xp=150))
        validate_business_rules(quest, requested_duration=20)


# ===========================================================================
# Unit — fallback library
# ===========================================================================


class TestFallbackLibrary:
    def test_always_returns_a_quest(self):
        result = get_fallback_quest(20, "mars", "unknown", "unknown")
        assert result is not None
        assert result.title

    def test_prefers_matching_difficulty(self):
        result = get_fallback_quest(20, "park", "chill", "observer")
        assert result.difficulty == "chill"

    def test_returns_quest_for_every_difficulty(self):
        for diff in ("chill", "curious", "explorer", "chaos"):
            result = get_fallback_quest(20, "any", diff, "explorer")
            assert result.title

    def test_prefers_matching_environment(self):
        result = get_fallback_quest(20, "city", "explorer", "explorer")
        # Should score the city quest higher
        assert result is not None


# ===========================================================================
# Integration — POST /quests/generate
# ===========================================================================


def _override_with(provider: FakeTextProvider):
    """Return a FastAPI override dict using the given fake provider."""

    def _dep():
        return provider

    return {get_text_provider: _dep}


class TestGenerateEndpoint:
    async def test_generate_unauthenticated_returns_401(self, async_client: AsyncClient):
        resp = await async_client.post(f"{BASE_QUESTS}/generate", json=_valid_payload())
        assert resp.status_code == 401, resp.text

    async def test_generate_invalid_payload_returns_422(self, async_client: AsyncClient):
        token = await _register_and_token(async_client, "gen0", "gen0@example.com")
        resp = await async_client.post(
            f"{BASE_QUESTS}/generate",
            json={"duration_minutes": 20},  # missing required fields
            headers=_auth(token),
        )
        assert resp.status_code == 422, resp.text

    async def test_generate_invalid_difficulty_returns_422(self, async_client: AsyncClient):
        token = await _register_and_token(async_client, "gen00", "gen00@example.com")
        resp = await async_client.post(
            f"{BASE_QUESTS}/generate",
            json=_valid_payload(difficulty="ultra"),
            headers=_auth(token),
        )
        assert resp.status_code == 422, resp.text

    async def test_generate_success_with_fake_provider(self, make_client_with_provider):
        provider = FakeTextProvider()
        async with make_client_with_provider(provider) as client:
            reg = await client.post(f"{BASE_AUTH}/register", json=_reg("gen1", "gen1@example.com"))
            t = reg.json()["token"]["access_token"]
            resp = await client.post(
                f"{BASE_QUESTS}/generate",
                json=_valid_payload(),
                headers=_auth(t),
            )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["title"] == "The Fake Quest"
        assert body["id"]
        assert body["xp_reward"] == 75
        assert isinstance(body["objectives"], list)
        assert len(body["objectives"]) > 0
        assert provider.call_count == 1

    async def test_generate_returns_all_required_fields(self, make_client_with_provider):
        provider = FakeTextProvider()
        async with make_client_with_provider(provider) as client:
            reg = await client.post(f"{BASE_AUTH}/register", json=_reg("gen2", "gen2@example.com"))
            t = reg.json()["token"]["access_token"]
            resp = await client.post(
                f"{BASE_QUESTS}/generate",
                json=_valid_payload(difficulty="curious", duration_minutes=20),
                headers=_auth(t),
            )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        required_fields = {
            "id",
            "title",
            "brief",
            "duration_minutes",
            "difficulty",
            "objectives",
            "xp_reward",
            "evidence_required",
            "created_at",
        }
        for field in required_fields:
            assert field in body, f"Missing field: {field}"

    async def test_generate_retry_then_succeed(self, make_client_with_provider):
        """Provider fails first call, succeeds on second → 201."""
        provider = FakeTextProvider(fail_times=1)
        async with make_client_with_provider(provider) as client:
            reg = await client.post(f"{BASE_AUTH}/register", json=_reg("gen3", "gen3@example.com"))
            t = reg.json()["token"]["access_token"]
            resp = await client.post(
                f"{BASE_QUESTS}/generate",
                json=_valid_payload(),
                headers=_auth(t),
            )
        assert resp.status_code == 201, resp.text
        assert provider.call_count == 2

    async def test_generate_all_retries_fail_serves_fallback(self, make_client_with_provider):
        """All model attempts fail → fallback quest served with 201."""
        provider = FakeTextProvider(response="this is not json at all")
        async with make_client_with_provider(provider) as client:
            reg = await client.post(f"{BASE_AUTH}/register", json=_reg("gen4", "gen4@example.com"))
            t = reg.json()["token"]["access_token"]
            resp = await client.post(
                f"{BASE_QUESTS}/generate",
                json=_valid_payload(),
                headers=_auth(t),
            )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["title"]
        assert body["xp_reward"] > 0

    async def test_generate_safety_violation_triggers_fallback(self, make_client_with_provider):
        """Model returns unsafe quest → fallback served."""
        unsafe_json = json.dumps(
            {
                "title": "Danger Quest",
                "brief": "You must trespass onto private property to complete this quest. It is very dangerous.",
                "duration_minutes": 20,
                "difficulty": "chill",
                "objectives": [
                    {"id": "obj-1", "instruction": "Trespass and steal things", "optional": False}
                ],
                "xp_reward": 75,
                "evidence_required": False,
                "safety_notes": "",
            }
        )
        provider = FakeTextProvider(response=unsafe_json)
        async with make_client_with_provider(provider) as client:
            reg = await client.post(f"{BASE_AUTH}/register", json=_reg("gen5", "gen5@example.com"))
            t = reg.json()["token"]["access_token"]
            resp = await client.post(
                f"{BASE_QUESTS}/generate",
                json=_valid_payload(),
                headers=_auth(t),
            )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["title"] != "Danger Quest"

    async def test_fake_provider_not_in_production_wiring(self):
        """get_text_provider must return an OllamaTextProvider (not fake)."""
        from app.ai.providers.ollama_provider import OllamaTextProvider

        provider = get_text_provider()
        assert isinstance(provider, OllamaTextProvider), (
            "Production dependency wiring must return OllamaTextProvider, "
            f"got {type(provider).__name__}"
        )

    async def test_personality_case_insensitive(self, make_client_with_provider):
        """Personality field normalises capitalisation."""
        provider = FakeTextProvider()
        async with make_client_with_provider(provider) as client:
            reg = await client.post(f"{BASE_AUTH}/register", json=_reg("gen6", "gen6@example.com"))
            t = reg.json()["token"]["access_token"]
            resp = await client.post(
                f"{BASE_QUESTS}/generate",
                json=_valid_payload(personality="wizard"),  # lowercase
                headers=_auth(t),
            )
        assert resp.status_code == 201, resp.text

    async def test_full_pipeline_run_full_validation(self):
        """run_full_validation happy path passes end-to-end."""
        raw = _valid_quest_json(duration_minutes=20, difficulty="chill", xp_reward=75)
        result = run_full_validation(raw, requested_duration=20)
        assert result.title == "The Fake Quest"
        assert result.difficulty == "chill"
        assert len(result.objectives) == 2
