"""Tests for RecruitingStore CRUD, fuzzy matching, and atomic persistence."""

import json
from pathlib import Path

import pytest

from bot.storage.models import PlayerEntry
from bot.storage.recruiting_store import RecruitingStore, get_sport_from_channel


class TestAddPlayer:
    """RecruitingStore.add_player adds a PlayerEntry to the correct sport list."""

    def test_add_player_returns_entry(self, tmp_path: Path) -> None:
        store = RecruitingStore(filepath=tmp_path / "recruits.json")
        result = store.add_player("football", "John Smith", "QB", "Texas", 4)
        assert result is not None
        assert isinstance(result, PlayerEntry)
        assert result.name == "John Smith"
        assert result.position == "QB"
        assert result.school == "Texas"
        assert result.stars == 4

    def test_add_player_appears_in_list(self, tmp_path: Path) -> None:
        store = RecruitingStore(filepath=tmp_path / "recruits.json")
        store.add_player("football", "John Smith", "QB", "Texas", 4)
        players = store.list_players("football")
        assert len(players) == 1
        assert players[0].name == "John Smith"

    def test_add_player_correct_sport_list(self, tmp_path: Path) -> None:
        store = RecruitingStore(filepath=tmp_path / "recruits.json")
        store.add_player("football", "John Smith", "QB", "Texas", 4)
        store.add_player("basketball", "Jane Doe", "PG", "Duke", 5)
        assert len(store.list_players("football")) == 1
        assert len(store.list_players("basketball")) == 1

    def test_add_duplicate_name_case_insensitive_returns_none(self, tmp_path: Path) -> None:
        store = RecruitingStore(filepath=tmp_path / "recruits.json")
        store.add_player("football", "John Smith", "QB", "Texas", 4)
        result = store.add_player("football", "john smith", "WR", "Oklahoma", 3)
        assert result is None

    def test_add_same_name_different_sport_allowed(self, tmp_path: Path) -> None:
        store = RecruitingStore(filepath=tmp_path / "recruits.json")
        store.add_player("football", "John Smith", "QB", "Texas", 4)
        result = store.add_player("basketball", "John Smith", "PG", "Duke", 5)
        assert result is not None


class TestRemovePlayer:
    """RecruitingStore.remove_player with exact and fuzzy matching."""

    def test_remove_exact_match_case_insensitive(self, tmp_path: Path) -> None:
        store = RecruitingStore(filepath=tmp_path / "recruits.json")
        store.add_player("football", "John Smith", "QB", "Texas", 4)
        removed, suggestions = store.remove_player("football", "john smith")
        assert removed is not None
        assert removed.name == "John Smith"
        assert suggestions == []

    def test_remove_no_match_returns_none_empty(self, tmp_path: Path) -> None:
        store = RecruitingStore(filepath=tmp_path / "recruits.json")
        removed, suggestions = store.remove_player("football", "Nobody Here")
        assert removed is None
        assert suggestions == []

    def test_remove_close_match_returns_suggestions(self, tmp_path: Path) -> None:
        store = RecruitingStore(filepath=tmp_path / "recruits.json")
        store.add_player("football", "John Smith", "QB", "Texas", 4)
        store.add_player("football", "John Smyth", "WR", "Oklahoma", 3)
        removed, suggestions = store.remove_player("football", "John Smithe")
        assert removed is None
        assert len(suggestions) > 0
        assert "John Smith" in suggestions or "John Smyth" in suggestions

    def test_remove_player_actually_removes(self, tmp_path: Path) -> None:
        store = RecruitingStore(filepath=tmp_path / "recruits.json")
        store.add_player("football", "John Smith", "QB", "Texas", 4)
        store.remove_player("football", "John Smith")
        assert len(store.list_players("football")) == 0


class TestListPlayers:
    """RecruitingStore.list_players returns sorted players."""

    def test_list_sorted_by_position(self, tmp_path: Path) -> None:
        store = RecruitingStore(filepath=tmp_path / "recruits.json")
        store.add_player("football", "Player A", "WR", "Texas", 4)
        store.add_player("football", "Player B", "CB", "Oklahoma", 3)
        store.add_player("football", "Player C", "QB", "Alabama", 5)
        players = store.list_players("football")
        positions = [p.position for p in players]
        assert positions == sorted(positions)

    def test_list_empty_sport(self, tmp_path: Path) -> None:
        store = RecruitingStore(filepath=tmp_path / "recruits.json")
        players = store.list_players("football")
        assert players == []


class TestPersistence:
    """RecruitingStore save/load roundtrip and missing file handling."""

    def test_save_load_roundtrip(self, tmp_path: Path) -> None:
        filepath = tmp_path / "recruits.json"
        store1 = RecruitingStore(filepath=filepath)
        store1.add_player("football", "John Smith", "QB", "Texas", 4)
        added_at = store1.list_players("football")[0].added_at

        store2 = RecruitingStore(filepath=filepath)
        store2.load()
        players = store2.list_players("football")
        assert len(players) == 1
        assert players[0].name == "John Smith"
        assert players[0].added_at == added_at

    def test_load_missing_file_returns_empty(self, tmp_path: Path) -> None:
        filepath = tmp_path / "nonexistent.json"
        store = RecruitingStore(filepath=filepath)
        store.load()
        assert store.list_players("football") == []
        assert store.list_players("basketball") == []

    def test_atomic_write_creates_valid_json(self, tmp_path: Path) -> None:
        filepath = tmp_path / "recruits.json"
        store = RecruitingStore(filepath=filepath)
        store.add_player("football", "John Smith", "QB", "Texas", 4)
        # Verify the file contains valid JSON
        data = json.loads(filepath.read_text())
        assert "football" in data
        assert len(data["football"]) == 1


class TestGetSportFromChannel:
    """get_sport_from_channel resolves channel IDs to sport strings."""

    def test_football_channel(self) -> None:
        settings = _MockSettings(football=[111, 222], basketball=[333])
        assert get_sport_from_channel(111, settings) == "football"

    def test_basketball_channel(self) -> None:
        settings = _MockSettings(football=[111], basketball=[333, 444])
        assert get_sport_from_channel(333, settings) == "basketball"

    def test_unmapped_channel_returns_none(self) -> None:
        settings = _MockSettings(football=[111], basketball=[333])
        assert get_sport_from_channel(999, settings) is None


class _MockSettings:
    """Minimal mock for Settings with channel ID lists."""

    def __init__(self, football: list[int], basketball: list[int]) -> None:
        self.football_channel_ids = football
        self.basketball_channel_ids = basketball
