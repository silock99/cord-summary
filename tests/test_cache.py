"""Tests for TTLCache in-memory cache with time-to-live expiration."""

import time

from bot.storage.cache import TTLCache


class TestTTLCache:
    """TTLCache stores values with per-key TTL and returns None for expired entries."""

    def test_set_and_get(self) -> None:
        cache = TTLCache()
        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_get_missing_returns_none(self) -> None:
        cache = TTLCache()
        assert cache.get("nonexistent") is None

    def test_expired_entry_returns_none(self) -> None:
        cache = TTLCache()
        cache.set("key", "value", ttl=0.0)
        time.sleep(0.01)
        assert cache.get("key") is None

    def test_invalidate_existing(self) -> None:
        cache = TTLCache()
        cache.set("key", "value")
        assert cache.invalidate("key") is True
        assert cache.get("key") is None

    def test_invalidate_missing(self) -> None:
        cache = TTLCache()
        assert cache.invalidate("missing") is False

    def test_clear(self) -> None:
        cache = TTLCache()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_custom_ttl_overrides_default(self) -> None:
        cache = TTLCache(default_ttl=0.0)
        cache.set("key", "value", ttl=60.0)
        assert cache.get("key") == "value"
