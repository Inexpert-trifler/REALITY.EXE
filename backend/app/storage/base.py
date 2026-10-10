"""StorageProvider interface.

Product logic must never import a specific storage backend directly.
Swap backends by changing the dependency injection wiring in
app/api/dependencies.py — no service-layer changes required.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class UploadResult:
    """Outcome of a successful store operation."""

    storage_key: str  # Opaque key — never expose filesystem paths
    size_bytes: int


class StorageProvider(ABC):
    """Abstract interface every storage backend must implement."""

    @abstractmethod
    async def upload(
        self,
        data: bytes,
        key: str,
        content_type: str,
    ) -> UploadResult:
        """Persist *data* under *key* and return metadata.

        Args:
            data:         Raw file bytes.
            key:          Pre-generated opaque storage key (e.g. UUID path).
            content_type: MIME type of the data.

        Returns:
            UploadResult with the key and confirmed byte count.

        Raises:
            StorageError on any I/O failure.
        """

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Remove the object identified by *key*.

        Must not raise if the key does not exist (idempotent).
        """

    @abstractmethod
    async def get_url(self, key: str, expires_seconds: int = 3600) -> str:
        """Return a time-limited, opaque access URL for *key*.

        The URL must not reveal internal filesystem paths or bucket names
        beyond what is strictly necessary.
        """


class StorageError(Exception):
    """Raised when a storage backend operation fails."""
