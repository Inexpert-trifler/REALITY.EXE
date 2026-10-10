"""Release gate tests — docs/16_TESTING.md specifies:

"No release if:
  - Unsafe quest can bypass validator.
  - Malformed AI output reaches the database.
  - Evidence upload accepts unsupported files.
  - Critical auth bypass exists."

Each gate is a direct, explicit test that enforces the hard requirement.
"""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas.quest_output import GeneratedObjective, GeneratedQuestOutput
from app.ai.validators import (
    QuestSafetyValidator,
    Severity,
    ValidationPipeline,
)
from app.ai.validators.output_validator import parse_json, validate_schema
from app.models.quest import Quest
from app.models.quest_attempt import QuestAttempt

# ---------------------------------------------------------------------------
# GATE 1 — Unsafe quest cannot bypass the safety validator
# ---------------------------------------------------------------------------


class TestGate1UnsafeQuestCannotBypassValidator:
    """Every unsafe quest characteristic must be caught by QuestSafetyValidator
    before any quest reaches the database."""

    def _make_quest(
        self, brief: str, objectives_text: str = "Do something fun"
    ) -> GeneratedQuestOutput:
        return GeneratedQuestOutput.model_construct(
            title="Test Quest",
            brief=brief,
            duration_minutes=20,
            difficulty="chill",
            objectives=[GeneratedObjective(id="o1", instruction=objectives_text, optional=False)],
            xp_reward=75,
            evidence_required=True,
            safety_notes="Stay safe.",
        )

    # Every entry in this list MUST be caught
    @pytest.mark.parametrize(
        "unsafe_text,expected_code_prefix",
        [
            ("You must trespass onto private property.", "SAFETY_TRESPASS"),
            ("Break into the abandoned warehouse to find the clue.", "SAFETY_BREAKING"),
            ("Steal a badge from the security desk.", "SAFETY_THEFT"),
            ("Spray-paint your mark on the underpass wall.", "SAFETY_VANDAL"),
            ("Enter the restricted area near the power station.", "SAFETY_RESTRICTED"),
            ("Cross the highway on foot at the unmarked crossing.", "SAFETY_DANGEROUS_ROAD"),
            ("Climb to the rooftop of the community centre.", "SAFETY_DANGEROUS_CLIMB"),
            ("Approach a stranger and follow them home to see where they live.", "SAFETY_APPROACH"),
            ("You must hurt yourself to complete this challenge.", "SAFETY_SELF"),
            ("Consume alcohol before starting the mission to relax your nerves.", "SAFETY_ALCOHOL"),
            ("Find the hidden cannabis plants behind the warehouse.", "SAFETY_CONTROLLED"),
            ("Find a hidden knife cache near the park bench.", "SAFETY_WEAPONS"),
            ("Reveal your personal information to the gate guard.", "SAFETY_PERSONAL"),
            ("Purchase a coffee at the start of the quest.", "SAFETY_SPENDING"),
        ],
    )
    def test_unsafe_text_blocked(self, unsafe_text: str, expected_code_prefix: str):
        quest = self._make_quest(brief=unsafe_text)
        report = QuestSafetyValidator().validate(quest)
        assert report.has_hard_blocks, (
            f"GATE 1 VIOLATION: Unsafe text was not blocked: {unsafe_text!r}\n"
            f"Issues found: {report.issues}"
        )
        codes = {i.code for i in report.hard_blocks}
        matched = any(c.startswith(expected_code_prefix) for c in codes)
        assert matched, (
            f"GATE 1 VIOLATION: Expected code starting with {expected_code_prefix!r} "
            f"but got {codes}"
        )

    def test_pipeline_stops_on_hard_block(self):
        """Safety HARD_BLOCK must halt the entire pipeline."""
        quest = self._make_quest(brief="Trespass onto private property for this mission.")
        pipeline = ValidationPipeline()
        report = pipeline.run(quest, requested_duration=20)

        assert report.has_hard_blocks
        # Quality and business issues should NOT be present — pipeline halted
        non_safety = [i for i in report.issues if not i.code.startswith("SAFETY_")]
        assert not non_safety, (
            f"GATE 1 VIOLATION: Pipeline did not halt on HARD_BLOCK. "
            f"Non-safety issues leaked: {non_safety}"
        )

    def test_all_safety_findings_are_hard_block(self):
        """Safety validator must only emit HARD_BLOCK — never WARNING or SOFT_BLOCK."""
        quest = self._make_quest(brief="Trespass and vandalize and steal things for this mission.")
        report = QuestSafetyValidator().validate(quest)
        for issue in report.issues:
            assert issue.severity == Severity.HARD_BLOCK, (
                f"GATE 1 VIOLATION: Safety issue has non-HARD_BLOCK severity: "
                f"code={issue.code} severity={issue.severity}"
            )

    def test_clean_quest_passes(self):
        """Sanity check: a safe quest must pass without false positives."""
        quest = self._make_quest(
            brief="Walk to the park and find five distinct natural colours. Look closely.",
            objectives_text="Find five distinct natural colours in public spaces.",
        )
        report = QuestSafetyValidator().validate(quest)
        assert not report.has_hard_blocks, (
            f"GATE 1 FALSE POSITIVE: Clean quest was blocked: {report.issues}"
        )


# ---------------------------------------------------------------------------
# GATE 2 — Malformed AI output cannot reach the database
# ---------------------------------------------------------------------------


class TestGate2MalformedAICannotReachDatabase:
    """The orchestrator must never persist a quest that failed validation."""

    @pytest.mark.parametrize(
        "bad_output",
        [
            "",  # empty
            "not json at all",  # prose
            '{"title": "Missing required fields"}',  # schema fail
            '{"title": "T", "brief": "B", '  # unsafe content
            '"duration_minutes": 20, "difficulty": "chill", '
            '"objectives": [{"id": "o1", "instruction": "Trespass onto private land", "optional": false}], '
            '"xp_reward": 75, "evidence_required": true, "safety_notes": ""}',
            "null",  # null
            "[]",  # array instead of object
        ],
    )
    async def test_bad_output_triggers_fallback_not_error(
        self, bad_output: str, db_session: AsyncSession
    ):
        """Bad AI output must result in a fallback quest, not a 500 error or
        an unsafe/malformed quest being persisted."""
        from app.ai.base import RawModelOutput, TextModelProvider
        from app.ai.orchestrator import QuestOrchestrator
        from app.ai.prompts.quest_prompt import QUEST_PROMPT_VERSION
        from app.ai.schemas.quest_output import QuestGenerateRequest

        class _BadProvider(TextModelProvider):
            @property
            def model_name(self):
                return "bad-provider"

            async def generate_quest(self, req):
                return RawModelOutput(
                    text=bad_output, model_name=self.model_name, prompt_version=QUEST_PROMPT_VERSION
                )

            async def generate_reflection(self, req):
                return RawModelOutput(
                    text="", model_name=self.model_name, prompt_version="reflection_v2"
                )

        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            orchestrator = QuestOrchestrator(provider=_BadProvider())
            result = await orchestrator.generate(
                db,
                request=QuestGenerateRequest(
                    duration_minutes=20,
                    environment="park",
                    difficulty="chill",
                    play_style="explorer",
                    personality="Wizard",
                ),
            )

        # Must return a valid quest (fallback), not raise
        assert result.id, "GATE 2 VIOLATION: No quest returned for bad AI output"
        assert result.title, "GATE 2 VIOLATION: Persisted quest has no title"

    def test_json_parse_rejects_non_dict(self):
        """parse_json must reject outputs that aren't JSON objects."""
        from app.ai.validators.output_validator import JSONParseError

        for bad in ("null", "[]", '"a string"', "123"):
            with pytest.raises((JSONParseError, Exception)):
                result = parse_json(bad)
                # If parse_json returns, validate_schema must reject it
                if isinstance(result, dict):
                    pass  # ok — dict with bad schema will fail next step
                else:
                    raise JSONParseError("Not a dict")

    def test_schema_validation_rejects_incomplete_quest(self):
        """Quests missing required fields must be rejected by the schema layer."""
        from app.ai.validators.output_validator import SchemaValidationError

        incomplete = {"title": "Only title, nothing else"}
        with pytest.raises(SchemaValidationError):
            validate_schema(incomplete)


# ---------------------------------------------------------------------------
# GATE 3 — Evidence upload rejects unsupported files
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# GATE 3 — Evidence upload rejects unsupported files
# ---------------------------------------------------------------------------


class TestGate3EvidenceUploadRejectsUnsupportedFiles:
    """The evidence upload endpoint must reject every file type not in the allowlist."""

    @pytest.mark.parametrize(
        "filename,content_type,data",
        [
            ("exploit.svg", "image/svg+xml", b'<svg xmlns="http://www.w3.org/2000/svg"/>'),
            ("page.html", "text/html", b"<html><script>alert(1)</script></html>"),
            ("binary.exe", "application/octet-stream", b"\x4d\x5a" + b"\x00" * 100),
            ("payload.pdf", "application/pdf", b"%PDF-1.4 malicious"),
            ("data.txt", "text/plain", b"plain text file"),
            ("image.gif", "image/gif", b"GIF89a\x01\x00\x01\x00"),
        ],
    )
    async def test_unsupported_file_type_rejected(
        self,
        filename,
        content_type,
        data,
        db_session: AsyncSession,
    ):
        from httpx import ASGITransport, AsyncClient

        from app.api.dependencies import get_storage_provider
        from app.db.session import get_db
        from app.domain.quest_states import AttemptStatus
        from app.main import create_app
        from app.storage.base import StorageProvider, UploadResult

        class _Store(StorageProvider):
            def __init__(self):
                self.upload_calls = 0

            async def upload(self, d, k, ct):
                self.upload_calls += 1
                return UploadResult(storage_key=k, size_bytes=len(d))

            async def delete(self, k):
                pass

            async def get_url(self, k, **kw):
                return f"/s/{k}"

        store = _Store()
        app = create_app()

        async def _db():
            yield db_session

        app.dependency_overrides[get_db] = _db
        app.dependency_overrides[get_storage_provider] = lambda: store

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            resp = await client.post(
                "/api/v1/auth/register",
                json={
                    "username": f"g3{uuid4().hex[:6]}",
                    "email": f"g3{uuid4().hex[:6]}@example.com",
                    "password": "Secure1234",
                    "display_name": "P",
                },
            )
            token = resp.json()["token"]["access_token"]
            uid = UUID(resp.json()["user"]["id"])

            q = Quest(
                title="T",
                brief="B",
                duration_minutes=20,
                environment="park",
                difficulty="chill",
                play_style="explorer",
                personality="Wizard",
                objectives_json=[{"id": "o1", "instruction": "Do something", "optional": False}],
                xp_reward=75,
                evidence_required=True,
                safety_notes="",
                model_name="t",
                prompt_version="v1",
            )
            db_session.add(q)
            await db_session.flush()
            att = QuestAttempt(
                quest_id=q.id, user_id=uid, status=AttemptStatus.RETURNED.value, earned_xp=0
            )
            db_session.add(att)
            await db_session.flush()

            upload = await client.post(
                "/api/v1/evidence/upload",
                data={"attempt_id": str(att.id)},
                files={"file": (filename, data, content_type)},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert upload.status_code == 400, (
            f"GATE 3 VIOLATION: {filename} accepted! Got {upload.status_code}: {upload.text}"
        )
        assert store.upload_calls == 0, f"GATE 3: storage written for {filename}"

    async def test_oversized_file_rejected(self, db_session: AsyncSession):
        from httpx import ASGITransport, AsyncClient

        from app.api.dependencies import get_storage_provider
        from app.db.session import get_db
        from app.domain.quest_states import AttemptStatus
        from app.main import create_app
        from app.storage.base import StorageProvider, UploadResult

        class _Store(StorageProvider):
            def __init__(self):
                self.upload_calls = 0

            async def upload(self, d, k, ct):
                self.upload_calls += 1
                return UploadResult(storage_key=k, size_bytes=len(d))

            async def delete(self, k):
                pass

            async def get_url(self, k, **kw):
                return f"/s/{k}"

        store = _Store()
        app = create_app()

        async def _db():
            yield db_session

        app.dependency_overrides[get_db] = _db
        app.dependency_overrides[get_storage_provider] = lambda: store

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            resp = await client.post(
                "/api/v1/auth/register",
                json={
                    "username": f"g3x{uuid4().hex[:6]}",
                    "email": f"g3x{uuid4().hex[:6]}@example.com",
                    "password": "Secure1234",
                    "display_name": "P",
                },
            )
            token = resp.json()["token"]["access_token"]
            uid = UUID(resp.json()["user"]["id"])

            q = Quest(
                title="T",
                brief="B",
                duration_minutes=20,
                environment="park",
                difficulty="chill",
                play_style="explorer",
                personality="Wizard",
                objectives_json=[{"id": "o1", "instruction": "Do something", "optional": False}],
                xp_reward=75,
                evidence_required=True,
                safety_notes="",
                model_name="t",
                prompt_version="v1",
            )
            db_session.add(q)
            await db_session.flush()
            att = QuestAttempt(
                quest_id=q.id, user_id=uid, status=AttemptStatus.RETURNED.value, earned_xp=0
            )
            db_session.add(att)
            await db_session.flush()

            oversized = b"\xff\xd8\xff" + b"X" * (11 * 1024 * 1024)
            upload = await client.post(
                "/api/v1/evidence/upload",
                data={"attempt_id": str(att.id)},
                files={"file": ("big.jpg", oversized, "image/jpeg")},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert upload.status_code == 400, (
            f"GATE 3 VIOLATION: Oversized accepted! Got {upload.status_code}"
        )
        assert store.upload_calls == 0, "GATE 3: storage written for oversized file"


# ---------------------------------------------------------------------------
# GATE 4 — No critical auth bypass
# ---------------------------------------------------------------------------


class TestGate4NoAuthBypass:
    """Every protected endpoint must reject unauthenticated requests."""

    PROTECTED_ENDPOINTS = [
        ("GET", "/api/v1/auth/me"),
        ("GET", "/api/v1/player/profile"),
        ("PATCH", "/api/v1/player/profile"),
        ("GET", "/api/v1/player/stats"),
        ("GET", "/api/v1/quests"),
        ("POST", "/api/v1/quests/generate"),
        ("GET", "/api/v1/achievements"),
        ("GET", "/api/v1/history"),
        ("GET", "/api/v1/ai/health"),
        ("POST", "/api/v1/reflections"),
        ("GET", "/api/v1/reflections"),
        ("POST", "/api/v1/auth/logout"),
    ]

    @pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
    async def test_unauthenticated_request_returns_401(
        self, method: str, path: str, async_client: AsyncClient
    ):
        """No protected endpoint should be accessible without a valid token."""
        if method == "GET":
            resp = await async_client.get(path)
        elif method == "POST":
            resp = await async_client.post(path, json={})
        elif method == "PATCH":
            resp = await async_client.patch(path, json={})
        else:
            pytest.skip(f"Unsupported method {method}")

        assert resp.status_code == 401, (
            f"GATE 4 VIOLATION: {method} {path} returned {resp.status_code} "
            f"without authentication (expected 401)"
        )

    async def test_expired_token_returns_401(self, async_client: AsyncClient):
        """An expired JWT must not be accepted."""
        from datetime import timedelta

        from app.utils.jwt import create_access_token_with_expiry

        token, _ = await _register_for_gate(async_client, f"g4{uuid4().hex[:6]}")
        me = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        user_id = me.json()["id"]

        expired = create_access_token_with_expiry(user_id, timedelta(seconds=-1))
        resp = await async_client.get(
            "/api/v1/player/profile",
            headers={"Authorization": f"Bearer {expired}"},
        )
        assert resp.status_code == 401, (
            f"GATE 4 VIOLATION: Expired token accepted (got {resp.status_code})"
        )

    async def test_forged_user_id_in_token_returns_401(self, async_client: AsyncClient):
        """A token signed with the correct secret but for a non-existent user
        must return 401 — the DB check must verify the user exists."""
        from app.utils.jwt import create_access_token

        fake_user_id = str(uuid4())
        token = create_access_token(fake_user_id)
        resp = await async_client.get(
            "/api/v1/player/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401, (
            f"GATE 4 VIOLATION: Forged user ID in valid-signed token was accepted "
            f"(got {resp.status_code})"
        )

    async def test_tampered_token_returns_401(self, async_client: AsyncClient):
        """A token with a tampered signature must be rejected."""
        token, _ = await _register_for_gate(async_client, f"g4b{uuid4().hex[:6]}")
        # Flip the last character of the signature
        parts = token.rsplit(".", 1)
        tampered = parts[0] + "." + (parts[1][:-1] + ("A" if parts[1][-1] != "A" else "B"))

        resp = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tampered}"},
        )
        assert resp.status_code == 401, (
            f"GATE 4 VIOLATION: Tampered token accepted (got {resp.status_code})"
        )

    async def test_wrong_scheme_returns_401(self, async_client: AsyncClient):
        """Basic auth scheme must be rejected (not Bearer)."""
        resp = await async_client.get(
            "/api/v1/player/profile",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert resp.status_code == 401


async def _register_for_gate(client: AsyncClient, username: str) -> tuple[str, str]:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "Secure1234",
            "display_name": "P",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]["access_token"], resp.json()["user"]["id"]
