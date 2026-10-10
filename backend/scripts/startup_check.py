#!/usr/bin/env python3
"""REALITY.EXE backend startup diagnostic.

Runs once at container start (before the server process) and reports:
  - Database connectivity
  - AI provider (Ollama) configuration
  - Storage configuration

Exits non-zero if a required service is unavailable and the application
cannot function at all (i.e. the database is unreachable).

AI and storage failures are reported as warnings — the application can
start and serve quests from the fallback library even without Ollama.
"""

import asyncio
import os
import sys
import time

# ── Colour helpers ──────────────────────────────────────────────────────────
_USE_COLOUR = sys.stdout.isatty()
_GREEN = "\033[32m" if _USE_COLOUR else ""
_YELLOW = "\033[33m" if _USE_COLOUR else ""
_RED = "\033[31m" if _USE_COLOUR else ""
_BLUE = "\033[34m" if _USE_COLOUR else ""
_RESET = "\033[0m" if _USE_COLOUR else ""
_BOLD = "\033[1m" if _USE_COLOUR else ""


def _ok(label: str, detail: str = "") -> None:
    suffix = f"  ({detail})" if detail else ""
    print(f"  {_GREEN}✓{_RESET}  {label}{suffix}")


def _warn(label: str, detail: str = "") -> None:
    suffix = f"  ({detail})" if detail else ""
    print(f"  {_YELLOW}⚠{_RESET}  {label}{suffix}")


def _fail(label: str, detail: str = "") -> None:
    suffix = f"  ({detail})" if detail else ""
    print(f"  {_RED}✗{_RESET}  {label}{suffix}", file=sys.stderr)


def _header(title: str) -> None:
    print(f"\n{_BOLD}{_BLUE}{title}{_RESET}")


# ── Database check ──────────────────────────────────────────────────────────


async def check_database(database_url: str) -> tuple[bool, str]:
    """Attempt an async DB connection and run SELECT 1."""
    try:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(database_url, pool_pre_ping=True, future=True)
        t0 = time.monotonic()
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
        latency_ms = round((time.monotonic() - t0) * 1000, 1)
        await engine.dispose()
        return True, f"{latency_ms} ms"
    except Exception as exc:
        return False, str(exc)


# ── Ollama check ─────────────────────────────────────────────────────────────


async def check_ollama(base_url: str, text_model: str, vision_model: str) -> dict:
    """Probe the Ollama server and check whether the required models are present."""
    result = {
        "reachable": False,
        "server_version": None,
        "text_model_present": False,
        "vision_model_present": False,
        "latency_ms": None,
        "error": None,
    }
    try:
        import httpx

        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=5.0) as client:
            ver_resp = await client.get(f"{base_url}/api/version")
            ver_resp.raise_for_status()
            result["latency_ms"] = round((time.monotonic() - t0) * 1000, 1)
            result["reachable"] = True
            result["server_version"] = ver_resp.json().get("version", "unknown")

            # Check available models
            tags_resp = await client.get(f"{base_url}/api/tags")
            if tags_resp.status_code == 200:
                models = {m["name"].split(":")[0] for m in tags_resp.json().get("models", [])}
                result["text_model_present"] = (
                    text_model in models or text_model.split(":")[0] in models
                )
                result["vision_model_present"] = (
                    vision_model in models or vision_model.split(":")[0] in models
                )
    except Exception as exc:
        result["error"] = str(exc)
    return result


# ── Storage check ────────────────────────────────────────────────────────────


def check_storage(backend: str, upload_dir: str, endpoint: str, bucket: str) -> tuple[bool, str]:
    """Verify storage is usable."""
    if backend == "local":
        if not upload_dir:
            return False, "EVIDENCE_UPLOAD_DIR is not set"
        if not os.path.isdir(upload_dir):
            try:
                os.makedirs(upload_dir, exist_ok=True)
                return True, f"created {upload_dir}"
            except OSError as exc:
                return False, f"cannot create {upload_dir}: {exc}"
        if not os.access(upload_dir, os.W_OK):
            return False, f"{upload_dir} is not writable"
        return True, f"local → {upload_dir}"
    elif backend == "s3":
        if not endpoint and not bucket:
            return False, "S3 backend selected but STORAGE_ENDPOINT and STORAGE_BUCKET are not set"
        if not bucket:
            return False, "STORAGE_BUCKET is not set"
        return True, f"s3 → {bucket}"
    else:
        return False, f"unknown backend: {backend!r}"


# ── Main ─────────────────────────────────────────────────────────────────────


async def main() -> int:
    # Load settings (respects .env file)
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app.core.config import get_settings

    settings = get_settings()

    print(f"\n{_BOLD}{'=' * 55}{_RESET}")
    print(f"{_BOLD}  REALITY.EXE  startup diagnostic{_RESET}")
    print(f"  environment: {settings.ENVIRONMENT}   version: {settings.VERSION}")
    print(f"{_BOLD}{'=' * 55}{_RESET}")

    exit_code = 0

    # ── 1. Database ──────────────────────────────────────────────────────────
    _header("Database")
    if settings.DATABASE_MODE == "disabled":
        _warn("Database check skipped", "DATABASE_MODE is disabled")
    else:
        db_ok, db_detail = await check_database(settings.DATABASE_URL)
        if db_ok:
            _ok("PostgreSQL", db_detail)
        else:
            _fail("PostgreSQL — cannot connect", db_detail)
            _fail("Database is required. Aborting.")
            exit_code = 1

    if exit_code:
        print()
        return exit_code

    # ── 2. AI provider ───────────────────────────────────────────────────────
    _header("AI provider (Ollama)")
    print(f"  base_url:     {settings.OLLAMA_BASE_URL}")
    print(f"  text_model:   {settings.TEXT_MODEL}")
    print(f"  vision_model: {settings.VISION_MODEL}")

    ollama = await check_ollama(
        settings.OLLAMA_BASE_URL, settings.TEXT_MODEL, settings.VISION_MODEL
    )
    if ollama["reachable"]:
        _ok(f"Ollama server  v{ollama['server_version']}", f"{ollama['latency_ms']} ms")
        if ollama["text_model_present"]:
            _ok(f"Text model  '{settings.TEXT_MODEL}'  ready")
        else:
            _warn(
                f"Text model  '{settings.TEXT_MODEL}'  NOT found",
                "quests will use the deterministic fallback library",
            )
            _warn(f"  Pull it:  docker exec <ollama-container> ollama pull {settings.TEXT_MODEL}")
        if ollama["vision_model_present"]:
            _ok(f"Vision model  '{settings.VISION_MODEL}'  ready")
        else:
            _warn(
                f"Vision model  '{settings.VISION_MODEL}'  NOT found",
                "evidence analysis will return UNCERTAIN",
            )
    else:
        _warn(
            "Ollama server unreachable",
            ollama.get("error", "connection refused"),
        )
        _warn(
            "  Quest generation will use the deterministic fallback library.",
            "AI features are optional.",
        )

    # ── 3. Storage ───────────────────────────────────────────────────────────
    _header("Storage")
    print(f"  backend:      {settings.STORAGE_BACKEND}")
    storage_ok, storage_detail = check_storage(
        settings.STORAGE_BACKEND,
        settings.EVIDENCE_UPLOAD_DIR,
        settings.STORAGE_ENDPOINT,
        settings.STORAGE_BUCKET,
    )
    if storage_ok:
        _ok("Storage", storage_detail)
    else:
        _warn("Storage not configured", storage_detail)
        _warn("  Evidence uploads will fail until storage is configured.")

    # ── 4. Security ──────────────────────────────────────────────────────────
    _header("Security")
    from app.core.config import _DEFAULT_AUTH_SECRET

    if settings.AUTH_SECRET == _DEFAULT_AUTH_SECRET:
        if settings.ENVIRONMENT == "production":
            _fail("AUTH_SECRET is the default value — production is misconfigured")
            exit_code = 1
        else:
            _warn("AUTH_SECRET is the default value — change before going to production")
    else:
        _ok("AUTH_SECRET is set")

    if settings.DEBUG and settings.ENVIRONMENT == "production":
        _fail("DEBUG=true in production — not allowed")
        exit_code = 1
    elif settings.DEBUG:
        _warn("DEBUG=true — SQL queries will be logged")
    else:
        _ok("DEBUG=false")

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{_BOLD}{'=' * 55}{_RESET}")
    if exit_code == 0:
        print(f"  {_GREEN}{_BOLD}Ready to start.{_RESET}")
    else:
        print(f"  {_RED}{_BOLD}Startup aborted — fix errors above.{_RESET}", file=sys.stderr)
    print()

    return exit_code


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
