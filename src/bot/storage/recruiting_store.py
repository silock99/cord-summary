"""Recruiting list persistence with atomic JSON writes and fuzzy matching."""

from __future__ import annotations

import difflib
import json
import logging
import os
import tempfile
from pathlib import Path

from bot.storage.models import PlayerEntry

logger = logging.getLogger(__name__)


class RecruitingStore:
    """In-memory recruiting list backed by atomic JSON file persistence."""

    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath
        self._data: dict[str, list[PlayerEntry]] = {"football": [], "basketball": []}
        self.load()

    def load(self) -> None:
        """Load player data from JSON file. Use empty defaults if missing/corrupt."""
        if not self.filepath.exists():
            return
        try:
            raw = json.loads(self.filepath.read_text(encoding="utf-8"))
            for sport in ("football", "basketball"):
                self._data[sport] = [
                    PlayerEntry.from_dict(entry) for entry in raw.get(sport, [])
                ]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning("Corrupt recruits file %s: %s — using defaults", self.filepath, exc)
            self._data = {"football": [], "basketball": []}

    def save(self) -> None:
        """Atomic write: tempfile + os.replace to prevent corruption."""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        serialized = {
            sport: [p.to_dict() for p in players]
            for sport, players in self._data.items()
        }
        fd, tmp_path = tempfile.mkstemp(dir=self.filepath.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(serialized, f, indent=2)
            os.replace(tmp_path, self.filepath)
        except BaseException:
            # Clean up temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def add_player(
        self, sport: str, name: str, position: str, school: str, stars: int
    ) -> PlayerEntry | None:
        """Add a player to a sport list. Returns None if duplicate name (case-insensitive)."""
        players = self._data.get(sport, [])
        # Check for case-insensitive duplicate
        if any(p.name.lower() == name.lower() for p in players):
            return None
        entry = PlayerEntry(name=name, position=position, school=school, stars=stars)
        players.append(entry)
        self._data[sport] = players
        self.save()
        return entry

    def remove_player(self, sport: str, name: str) -> tuple[PlayerEntry | None, list[str]]:
        """Remove player by exact name (case-insensitive).

        Returns (removed_player, []) on match, or (None, suggestions) on no match.
        """
        players = self._data.get(sport, [])

        # Exact case-insensitive match
        for i, p in enumerate(players):
            if p.name.lower() == name.lower():
                removed = players.pop(i)
                self.save()
                return (removed, [])

        # No exact match — provide fuzzy suggestions
        if not players:
            return (None, [])
        suggestions = difflib.get_close_matches(
            name, [p.name for p in players], n=3, cutoff=0.6
        )
        return (None, suggestions)

    def list_players(self, sport: str) -> list[PlayerEntry]:
        """Return players for a sport, sorted by position."""
        players = self._data.get(sport, [])
        return sorted(players, key=lambda p: p.position)


def get_sport_from_channel(channel_id: int, settings: object) -> str | None:
    """Resolve a channel ID to a sport string using settings config.

    Returns 'football', 'basketball', or None if unmapped.
    """
    if channel_id in getattr(settings, "football_channel_ids", []):
        return "football"
    if channel_id in getattr(settings, "basketball_channel_ids", []):
        return "basketball"
    return None
