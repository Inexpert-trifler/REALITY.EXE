"""Sync metadata fields for offline-first support.

These fields are mixed into key responses so a future offline client can
safely determine ordering, detect conflicts, and avoid duplicate processing.

Contract:
  server_timestamp  — authoritative UTC time the server processed the request
  resource_version  — opaque monotonic string (UUID of the resource)
  idempotency_key   — echoed back so the client can match response to request

A client that queued actions offline should:
  1. Attach a stable X-Idempotency-Key to each request.
  2. On reconnect, replay queued requests in order.
  3. Use server_timestamp to resolve ordering conflicts.
  4. On 409 / duplicate response, discard the local copy and use the server's.
"""

from datetime import datetime

from pydantic import BaseModel


class SyncMetadata(BaseModel):
    """Sync-friendly metadata appended to key resource responses."""

    server_timestamp: datetime
    resource_version: str  # UUID of the resource (stable, unique)
    idempotency_key: str | None = None  # echoed if client provided one
