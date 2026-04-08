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


class TestPlayerEntryType:
    """PlayerEntry type field with backward compatibility."""

    def test_player_entry_type_default(self) -> None:
        entry = PlayerEntry(name="X", position="QB", school="Bama", stars=4)
        assert entry.type == "target"

    def test_player_entry_type_explicit(self) -> None:
        entry = PlayerEntry(name="X", position="QB", school="Bama", stars=4, type="outgoing")
        assert entry.type == "outgoing"

    def test_player_entry_backward_compat_from_dict(self) -> None:
        data = {
            "name": "X",
            "position": "QB",
            "school": "Bama",
            "stars": 4,
            "added_at": "2026-01-01T00:00:00+00:00",
        }
        entry = PlayerEntry.from_dict(data)
        assert entry.type == "target"

    def test_player_entry_to_dict_includes_type(self) -> None:
        entry = PlayerEntry(name="X", position="QB", school="Bama", stars=4)
        d = entry.to_dict()
        assert "type" in d
        assert d["type"] == "target"

    def test_player_entry_roundtrip_type(self) -> None:
        entry = PlayerEntry(name="X", position="QB", school="Bama", stars=4, type="outgoing")
        restored = PlayerEntry.from_dict(entry.to_dict())
        assert restored.type == "outgoing"


class TestAddPlayerType:
    """RecruitingStore.add_player with player_type parameter."""

    def test_add_player_with_type_outgoing(self, tmp_path: Path) -> None:
        store = RecruitingStore(filepath=tmp_path / "recruits.json")
        result = store.add_player("football", "John", "QB", "Bama", 4, player_type="outgoing")
        assert result is not None
        assert result.type == "outgoing"

    def test_add_player_default_type_target(self, tmp_path: Path) -> None:
        store = RecruitingStore(filepath=tmp_path / "recruits.json")
        result = store.add_player("football", "Jane", "WR", "Ohio St", 3)
        assert result is not None
        assert result.type == "target"

    def test_add_player_duplicate_with_different_type(self, tmp_path: Path) -> None:
        store = RecruitingStore(filepath=tmp_path / "recruits.json")
        store.add_player("football", "John", "QB", "Bama", 4, player_type="target")
        result = store.add_player("football", "John", "QB", "Bama", 4, player_type="outgoing")
        assert result is None


class TestListPlayersPositionFilter:
    """RecruitingStore.list_players with position filtering."""

    def test_list_players_position_filter(self, tmp_path: Path) -> None:
        store = RecruitingStore(filepath=tmp_path / "recruits.json")
        store.add_player("football", "Player A", "QB", "Texas", 4)
        store.add_player("football", "Player B", "WR", "Oklahoma", 3)
        players = store.list_players("football", position="QB")
        assert len(players) == 1
        assert players[0].name == "Player A"

    def test_list_players_position_filter_case_insensitive(self, tmp_path: Path) -> None:
        store = RecruitingStore(filepath=tmp_path / "recruits.json")
        store.add_player("football", "Player A", "QB", "Texas", 4)
        players = store.list_players("football", position="qb")
        assert len(players) == 1
        assert players[0].name == "Player A"

    def test_list_players_position_filter_no_match(self, tmp_path: Path) -> None:
        store = RecruitingStore(filepath=tmp_path / "recruits.json")
        store.add_player("football", "Player A", "QB", "Texas", 4)
        players = store.list_players("football", position="RB")
        assert len(players) == 0

    def test_list_players_no_position_returns_all(self, tmp_path: Path) -> None:
        store = RecruitingStore(filepath=tmp_path / "recruits.json")
        store.add_player("football", "Player A", "QB", "Texas", 4)
        store.add_player("football", "Player B", "WR", "Oklahoma", 3)
        players = store.list_players("football")
        assert len(players) == 2


class _MockSettings:
    """Minimal mock for Settings with channel ID lists."""

    def __init__(self, football: list[int], basketball: list[int]) -> None:
        self.football_channel_ids = football
        self.basketball_channel_ids = basketball
