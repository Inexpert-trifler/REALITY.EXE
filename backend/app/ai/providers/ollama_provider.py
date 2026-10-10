"""Ollama text and vision model providers.

Implements TextModelProvider and VisionModelProvider against the Ollama
local inference server HTTP API.

Design principles:
  - Every config value comes from Settings or constructor args — no hardcoded model names.
  - Structured JSON output is requested via Ollama's `format` parameter so the
    model is constrained to emit valid JSON before our validator even runs.
  - All network calls are wrapped in a retry loop with configurable attempts.
  - Latency, model name, prompt version, success/failure are always logged.
  - Connection errors and timeouts degrade gracefully to ProviderUnavailableError
    so callers can fall back without crashing.
  - Passwords, tokens, and secrets are never logged here.

Ollama API reference: https://github.com/ollama/ollama/blob/main/docs/api.md

Key endpoints used:
  POST /api/generate  — text generation and vision (with `images`)
  GET  /api/version   — lightweight reachability probe
  GET  /api/tags      — list locally available models (used by health check)
"""

import logging
import time
from typing import Any

import httpx

from app.ai.base import (
    EvidenceAnalysisRequest,
    EvidenceAnalysisResult,
    ProviderOutputError,
    ProviderUnavailableError,
    QuestGenerationRequest,
    RawModelOutput,
    ReflectionRequest,
    TextModelProvider,
    VisionModelProvider,
)
from app.ai.prompts.quest_prompt import QUEST_PROMPT_VERSION, build_quest_prompt
from app.ai.prompts.reflection_prompt import REFLECTION_PROMPT_VERSION, build_reflection_prompt
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# JSON schema for structured quest output — passed to Ollama's `format` field
# so the model is *constrained* to emit valid JSON matching this shape.
_QUEST_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "brief": {"type": "string"},
        "duration_minutes": {"type": "integer"},
        "difficulty": {"type": "string"},
        "objectives": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "instruction": {"type": "string"},
                    "optional": {"type": "boolean"},
                },
                "required": ["id", "instruction", "optional"],
            },
        },
        "xp_reward": {"type": "integer"},
        "evidence_required": {"type": "boolean"},
        "safety_notes": {"type": "string"},
    },
    "required": [
        "title",
        "brief",
        "duration_minutes",
        "difficulty",
        "objectives",
        "xp_reward",
        "evidence_required",
        "safety_notes",
    ],
}


class OllamaTextProvider(TextModelProvider):
    """TextModelProvider backed by a locally running Ollama server.

    Configuration (all optional, fall back to Settings):
        base_url    – Ollama server base URL, e.g. "http://localhost:11434"
        model       – model name, e.g. "llama3" or "gemma3:4b"
        timeout     – per-request timeout in seconds
        temperature – sampling temperature (0.0 – 1.0)
        max_tokens  – max tokens for generation (Ollama: num_predict)
        max_retries – how many times to retry on transient errors before giving up
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        temperature: float | None = None,
        max_tokens: int = 1024,
        max_retries: int = 2,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self._model = model or settings.TEXT_MODEL
        self._timeout = timeout or settings.AI_REQUEST_TIMEOUT_SECONDS
        self._temperature = (
            temperature if temperature is not None else settings.AI_GENERATION_TEMPERATURE
        )
        self._max_tokens = max_tokens
        self._max_retries = max_retries

    @property
    def model_name(self) -> str:
        return self._model

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    async def _post_generate(
        self,
        prompt: str,
        *,
        use_json_format: bool = True,
        temperature: float | None = None,
        system: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """POST /api/generate and return (response_text, full_response_dict).

        Retries up to self._max_retries times on transient errors.
        Raises ProviderUnavailableError on connection/timeout problems.
        Raises ProviderOutputError on empty responses.
        """
        url = f"{self._base_url}/api/generate"
        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature or self._temperature,
                "num_predict": self._max_tokens,
            },
        }
        if use_json_format:
            payload["format"] = _QUEST_JSON_SCHEMA
        if system:
            payload["system"] = system

        last_exc: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            t_start = time.monotonic()
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()

                latency_ms = round((time.monotonic() - t_start) * 1000, 1)
                data: dict[str, Any] = resp.json()
                text: str = data.get("response", "")

                # Log provenance — never log the prompt itself (may contain player data)
                logger.info(
                    "Ollama generate: model=%s attempt=%d/%d latency_ms=%s "
                    "prompt_tokens=%s completion_tokens=%s done=%s",
                    self._model,
                    attempt,
                    self._max_retries,
                    latency_ms,
                    data.get("prompt_eval_count", "?"),
                    data.get("eval_count", "?"),
                    data.get("done", "?"),
                )

                if not text.strip():
                    raise ProviderOutputError(
                        f"Ollama returned empty response (model={self._model})"
                    )

                return text, data

            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                latency_ms = round((time.monotonic() - t_start) * 1000, 1)
                logger.warning(
                    "Ollama unreachable: attempt=%d/%d latency_ms=%s error=%s",
                    attempt,
                    self._max_retries,
                    latency_ms,
                    exc,
                )
                last_exc = exc
                # Connection failures are not retried — Ollama is just down
                raise ProviderUnavailableError(
                    f"Cannot connect to Ollama at {self._base_url}: {exc}"
                ) from exc

            except httpx.TimeoutException as exc:
                latency_ms = round((time.monotonic() - t_start) * 1000, 1)
                logger.warning(
                    "Ollama timeout: attempt=%d/%d latency_ms=%s timeout=%ss",
                    attempt,
                    self._max_retries,
                    latency_ms,
                    self._timeout,
                )
                last_exc = exc
                if attempt == self._max_retries:
                    raise ProviderUnavailableError(
                        f"Ollama timed out after {self._timeout}s ({self._max_retries} attempt(s))"
                    ) from exc
                # else: retry

            except httpx.HTTPStatusError as exc:
                latency_ms = round((time.monotonic() - t_start) * 1000, 1)
                status = exc.response.status_code
                logger.warning(
                    "Ollama HTTP error: attempt=%d/%d status=%d latency_ms=%s",
                    attempt,
                    self._max_retries,
                    status,
                    latency_ms,
                )
                last_exc = exc
                # 5xx → retry; 4xx → permanent failure
                if status < 500 or attempt == self._max_retries:
                    raise ProviderUnavailableError(
                        f"Ollama HTTP {status} (model={self._model})"
                    ) from exc

            except ProviderOutputError:
                raise

        # Should only be reached after exhausting retries on timeouts
        raise ProviderUnavailableError(
            f"Ollama unavailable after {self._max_retries} attempt(s)"
        ) from last_exc

    # ------------------------------------------------------------------
    # TextModelProvider interface
    # ------------------------------------------------------------------

    async def generate_quest(self, request: QuestGenerationRequest) -> RawModelOutput:
        """Generate a quest using structured JSON output mode."""
        prompt = build_quest_prompt(request)

        logger.info(
            "Quest generation starting: model=%s prompt_version=%s "
            "env=%s difficulty=%s play_style=%s player_level=%d",
            self._model,
            QUEST_PROMPT_VERSION,
            request.environment,
            request.difficulty,
            request.play_style,
            request.player_level,
        )

        try:
            text, raw_data = await self._post_generate(
                prompt,
                use_json_format=True,
                temperature=self._temperature,
            )
            logger.info(
                "Quest generation succeeded: model=%s prompt_version=%s",
                self._model,
                QUEST_PROMPT_VERSION,
            )
            return RawModelOutput(
                text=text,
                model_name=self._model,
                prompt_version=QUEST_PROMPT_VERSION,
                prompt_tokens=raw_data.get("prompt_eval_count", 0),
                completion_tokens=raw_data.get("eval_count", 0),
            )
        except (ProviderUnavailableError, ProviderOutputError) as exc:
            logger.error(
                "Quest generation failed: model=%s prompt_version=%s error=%s",
                self._model,
                QUEST_PROMPT_VERSION,
                exc,
            )
            raise

    async def generate_reflection(self, request: ReflectionRequest) -> RawModelOutput:
        """Generate a post-quest reflection (plain text, no JSON schema)."""
        prompt = build_reflection_prompt(request)

        logger.info(
            "Reflection generation starting: model=%s prompt_version=%s outcome=%s",
            self._model,
            REFLECTION_PROMPT_VERSION,
            request.outcome,
        )

        try:
            text, raw_data = await self._post_generate(
                prompt,
                use_json_format=False,  # reflections are plain text
                temperature=0.7,  # slightly lower for coherence
            )
            logger.info(
                "Reflection generation succeeded: model=%s prompt_version=%s",
                self._model,
                REFLECTION_PROMPT_VERSION,
            )
            return RawModelOutput(
                text=text,
                model_name=self._model,
                prompt_version=REFLECTION_PROMPT_VERSION,
                prompt_tokens=raw_data.get("prompt_eval_count", 0),
                completion_tokens=raw_data.get("eval_count", 0),
            )
        except (ProviderUnavailableError, ProviderOutputError) as exc:
            logger.error(
                "Reflection generation failed: model=%s error=%s",
                self._model,
                exc,
            )
            raise

    # ------------------------------------------------------------------
    # Health check (used by /api/v1/ai/health)
    # ------------------------------------------------------------------

    async def check_health(self) -> "OllamaHealthResult":
        """Probe the Ollama server and return structured health information.

        Uses GET /api/version (lightweight, no model load required).
        Never raises — returns a result with reachable=False on any error.
        """
        url = f"{self._base_url}/api/version"
        t_start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
            latency_ms = round((time.monotonic() - t_start) * 1000, 1)
            version = resp.json().get("version", "unknown")
            logger.debug("Ollama health OK: version=%s latency_ms=%s", version, latency_ms)
            return OllamaHealthResult(
                reachable=True,
                model=self._model,
                latency_ms=latency_ms,
                server_version=version,
                error=None,
            )
        except httpx.ConnectError as exc:
            latency_ms = round((time.monotonic() - t_start) * 1000, 1)
            logger.warning("Ollama health check: cannot connect — %s", exc)
            return OllamaHealthResult(
                reachable=False,
                model=self._model,
                latency_ms=latency_ms,
                server_version=None,
                error=f"Cannot connect to Ollama at {self._base_url}",
            )
        except httpx.TimeoutException:
            latency_ms = round((time.monotonic() - t_start) * 1000, 1)
            logger.warning("Ollama health check timed out after 5s")
            return OllamaHealthResult(
                reachable=False,
                model=self._model,
                latency_ms=latency_ms,
                server_version=None,
                error="Ollama health check timed out",
            )
        except Exception as exc:  # noqa: BLE001
            latency_ms = round((time.monotonic() - t_start) * 1000, 1)
            logger.warning("Ollama health check error: %s", exc)
            return OllamaHealthResult(
                reachable=False,
                model=self._model,
                latency_ms=latency_ms,
                server_version=None,
                error=str(exc),
            )


# ---------------------------------------------------------------------------
# Health result dataclass
# ---------------------------------------------------------------------------

from dataclasses import dataclass  # noqa: E402 — after class body for readability


@dataclass
class OllamaHealthResult:
    """Result of an Ollama server health probe."""

    reachable: bool
    model: str
    latency_ms: float
    server_version: str | None
    error: str | None


# ---------------------------------------------------------------------------
# Vision provider
# ---------------------------------------------------------------------------


class OllamaVisionProvider(VisionModelProvider):
    """VisionModelProvider backed by an Ollama multimodal model (e.g. llava).

    Uses POST /api/generate with base64-encoded images.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        max_tokens: int = 512,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self._model = model or settings.VISION_MODEL
        self._timeout = timeout or settings.AI_REQUEST_TIMEOUT_SECONDS
        self._max_tokens = max_tokens

    @property
    def model_name(self) -> str:
        return self._model

    async def analyze_evidence(self, request: EvidenceAnalysisRequest) -> EvidenceAnalysisResult:
        import base64
        import json

        image_b64 = base64.b64encode(request.image_bytes).decode("utf-8")
        objectives_text = "; ".join(o.get("instruction", "") for o in request.quest_objectives)
        # Prompt is minimal — no quest-specific secrets or personal details
        prompt = (
            f"Quest brief: {request.quest_brief}\n"
            f"Objectives: {objectives_text}\n\n"
            "Analyze this image. Respond with ONLY a JSON object:\n"
            '{"visible_content": "description of what you see", '
            '"is_relevant": true or false, '
            '"confidence": 0.0 to 1.0, '
            '"safety_concerns": [], '
            '"completion_recommendation": true or false}'
        )
        url = f"{self._base_url}/api/generate"
        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
            "format": "json",
            "options": {"num_predict": self._max_tokens},
        }

        t_start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()

            latency_ms = round((time.monotonic() - t_start) * 1000, 1)
            raw_resp = resp.json()
            raw_text = raw_resp.get("response", "{}")

            logger.info(
                "Vision analysis: model=%s latency_ms=%s",
                self._model,
                latency_ms,
            )

            data = json.loads(raw_text)
            return EvidenceAnalysisResult(
                visible_content=data.get("visible_content", ""),
                is_relevant=bool(data.get("is_relevant", False)),
                confidence=float(data.get("confidence", 0.5)),
                safety_concerns=data.get("safety_concerns", []),
                completion_recommendation=bool(data.get("completion_recommendation", False)),
                model_name=self._model,
                model_version=raw_resp.get("model", self._model),
            )
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise ProviderUnavailableError(f"Vision provider unreachable: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailableError(f"Vision provider error: {exc}") from exc
