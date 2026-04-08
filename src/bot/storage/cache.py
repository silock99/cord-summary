"""In-memory TTL cache for API responses."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    """A cached value with its expiration timestamp."""

    value: Any
    expires_at: float


class TTLCache:
    """Simple in-memory cache with per-key time-to-live expiration.

    Uses ``time.monotonic()`` for expiration checks to avoid wall-clock drift.
    """

    def __init__(self, default_ttl: float = 900.0) -> None:
        self.default_ttl = default_ttl
        self._store: dict[str, CacheEntry] = {}

    def get(self, key: str) -> Any | None:
        """Return cached value or ``None`` if missing/expired."""
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() >= entry.expires_at:
            del self._store[key]
            return None
        return entry.value

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Store *value* under *key* with optional per-key TTL (seconds)."""
        if ttl is None:
            ttl = self.default_ttl
        self._store[key] = CacheEntry(
            value=value,
            expires_at=time.monotonic() + ttl,
        )

    def invalidate(self, key: str) -> bool:
        """Remove *key* from cache. Returns ``True`` if key existed."""
        if key in self._store:
            del self._store[key]
            return True
        return False

    def clear(self) -> None:
        """Remove all entries from cache."""
        self._store.clear()
