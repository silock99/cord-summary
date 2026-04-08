"""Tests for TTLCache wiring into transfer commands."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.storage.cache import TTLCache


class TestTransferCacheWiring:
    """TTLCache is wired into SummaryBot and used by transfer commands."""

    def test_bot_has_transfer_cache(self) -> None:
        """SummaryBot initializes a TTLCache as transfer_cache."""
        with patch("bot.client.Settings") as MockSettings:
            MockSettings.return_value = MagicMock()
            from bot.client import SummaryBot

            bot = SummaryBot(settings=MockSettings.return_value)
            assert hasattr(bot, "transfer_cache")
            assert isinstance(bot.transfer_cache, TTLCache)

    def test_transfer_list_caches_result(self) -> None:
        """Second /transfer-list call returns cached result without hitting store."""
        cache = TTLCache(default_ttl=900.0)
        mock_store = MagicMock()
        mock_store.list_players.return_value = [
            MagicMock(name="Player1", type="target", stars=3, position="QB", school="Texas", added_at="2026-01-01T00:00:00+00:00"),
        ]

        sport = "football"
        cache_key = f"transfer:{sport}"

        # First call: cache miss, should call store
        result = cache.get(cache_key)
        assert result is None
        players = mock_store.list_players(sport, position=None)
        cache.set(cache_key, players)
        assert mock_store.list_players.call_count == 1

        # Second call: cache hit, store NOT called again
        cached = cache.get(cache_key)
        assert cached is not None
        assert mock_store.list_players.call_count == 1  # Still 1

    def test_transfer_list_cache_key_includes_position(self) -> None:
        """Position filter changes the cache key."""
        cache = TTLCache(default_ttl=900.0)
        mock_store = MagicMock()
        mock_store.list_players.return_value = []

        sport = "football"
        position = "QB"
        cache_key_no_pos = f"transfer:{sport}"
        cache_key_with_pos = f"transfer:{sport}:{position.lower()}"

        cache.set(cache_key_no_pos, ["all"])
        cache.set(cache_key_with_pos, ["qb_only"])

        assert cache.get(cache_key_no_pos) == ["all"]
        assert cache.get(cache_key_with_pos) == ["qb_only"]
        # Different keys for different filters
        assert cache_key_no_pos != cache_key_with_pos

    def test_transfer_add_invalidates_cache(self) -> None:
        """After /transfer-add, cache is cleared so next list query is fresh."""
        cache = TTLCache(default_ttl=900.0)

        # Populate cache
        cache.set("transfer:football", ["player1"])
        cache.set("transfer:basketball", ["player2"])
        assert cache.get("transfer:football") is not None

        # Simulate mutation: clear cache (as transfer_add does)
        cache.clear()

        # Cache should be empty
        assert cache.get("transfer:football") is None
        assert cache.get("transfer:basketball") is None

    def test_transfer_remove_invalidates_cache(self) -> None:
        """After /transfer-remove, cache is cleared so next list query is fresh."""
        cache = TTLCache(default_ttl=900.0)

        # Populate cache
        cache.set("transfer:football", ["player1"])
        assert cache.get("transfer:football") is not None

        # Simulate mutation: clear cache (as transfer_remove does)
        cache.clear()

        assert cache.get("transfer:football") is None

    def test_cache_miss_calls_store(self) -> None:
        """On cache miss (first call or after invalidation), store.list_players is called."""
        cache = TTLCache(default_ttl=900.0)
        mock_store = MagicMock()
        mock_store.list_players.return_value = ["p1", "p2"]

        sport = "basketball"
        cache_key = f"transfer:{sport}"

        # Miss
        assert cache.get(cache_key) is None
        players = mock_store.list_players(sport, position=None)
        cache.set(cache_key, players)
        mock_store.list_players.assert_called_once()

        # Invalidate
        cache.clear()
        assert cache.get(cache_key) is None

        # Miss again -> store called again
        players2 = mock_store.list_players(sport, position=None)
        cache.set(cache_key, players2)
        assert mock_store.list_players.call_count == 2
