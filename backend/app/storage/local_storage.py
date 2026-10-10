"""LocalStorageProvider — filesystem-backed storage for development.

Files are stored under a configurable base directory.
Filesystem paths are NEVER returned to callers — only opaque storage keys.

This provider must not be used in production.  Switch STORAGE_BACKEND to
"s3" (or any future backend) via environment configuration.
"""

import asyncio
import logging
from pathlib import Path

import aiofiles
import aiofiles.os

from app.core.config import get_settings
from app.storage.base import StorageError, StorageProvider, UploadResult

logger = logging.getLogger(__name__)


class LocalStorageProvider(StorageProvider):
    """Development-only storage provider that writes files to the local disk.

    Args:
        base_dir: Root directory for stored files.  Defaults to
                  Settings.EVIDENCE_UPLOAD_DIR.
    """

    def __init__(self, base_dir: str | None = None) -> None:
        settings = get_settings()
        self._base_dir = Path(base_dir or settings.EVIDENCE_UPLOAD_DIR)

    def _key_to_path(self, key: str) -> Path:
        """Resolve a storage key to an absolute filesystem path.

        The key is stripped of any leading slashes / traversal sequences to
        prevent path traversal attacks.
        """
        # Normalise: remove leading slashes, collapse ".." segments
        safe_key = Path(key.lstrip("/")).resolve().relative_to(Path("/").resolve())
        return self._base_dir / safe_key

    async def _ensure_dir(self, path: Path) -> None:
        """Create parent directories if they don't exist."""
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)

    async def upload(
        self,
        data: bytes,
        key: str,
        content_type: str,
    ) -> UploadResult:
        """Write *data* to disk under the resolved key path."""
        dest = self._key_to_path(key)
        try:
            await self._ensure_dir(dest)
            async with aiofiles.open(dest, "wb") as f:
                await f.write(data)
            logger.debug("LocalStorage: stored %d bytes → key=%s", len(data), key)
            return UploadResult(storage_key=key, size_bytes=len(data))
        except OSError as exc:
            raise StorageError(f"LocalStorage write failed for key={key}: {exc}") from exc

    async def delete(self, key: str) -> None:
        """Delete the file for *key*.  Silent if the file does not exist."""
        path = self._key_to_path(key)
        try:
            await aiofiles.os.remove(path)
            logger.debug("LocalStorage: deleted key=%s", key)
        except FileNotFoundError:
            pass  # idempotent
        except OSError as exc:
            raise StorageError(f"LocalStorage delete failed for key={key}: {exc}") from exc

    async def get_url(self, key: str, expires_seconds: int = 3600) -> str:
        """Return a safe, opaque reference string — not a real URL.

        LocalStorage has no HTTP server, so we return a non-guessable
        reference token rather than a filesystem path.
        """
        # In production this would be a signed S3 URL; here we return
        # a token that the app's own evidence-serving endpoint could use.
        return f"/api/v1/evidence/serve/{key}"
