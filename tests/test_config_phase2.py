"""Tests for Phase 2 config extensions and system prompt updates."""

import os
import pytest


# Minimal env vars required by Settings
REQUIRED_ENV = {
    "DISCORD_TOKEN": "x",
    "GUILD_ID": "1",
    "SUMMARY_CHANNEL_ID": "1",
    "OPENAI_API_KEY": "x",
}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Set required env vars and clear optional ones for each test."""
    for k, v in REQUIRED_ENV.items():
        monkeypatch.setenv(k, v)
    # Clear optional vars so defaults are tested
    for k in ("ALLOWED_CHANNEL_IDS", "DEFAULT_SUMMARY_MINUTES", "QUIET_THRESHOLD"):
        monkeypatch.delenv(k, raising=False)


class TestAllowedChannelIds:
    def test_comma_separated_string_parsed(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_CHANNEL_IDS", "123,456")
        from bot.config import Settings
        s = Settings()
        assert s.allowed_channel_ids == [123, 456]

    def test_empty_string_gives_empty_list(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_CHANNEL_IDS", "")
        from bot.config import Settings
        s = Settings()
        assert s.allowed_channel_ids == []

    def test_default_is_empty_list(self):
        from bot.config import Settings
        s = Settings()
        assert s.allowed_channel_ids == []

    def test_spaces_stripped(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_CHANNEL_IDS", " 123 , 456 , 789 ")
        from bot.config import Settings
        s = Settings()
        assert s.allowed_channel_ids == [123, 456, 789]


class TestDefaultSummaryMinutes:
    def test_default_value(self):
        from bot.config import Settings
        s = Settings()
        assert s.default_summary_minutes == 240

    def test_override_from_env(self, monkeypatch):
        monkeypatch.setenv("DEFAULT_SUMMARY_MINUTES", "60")
        from bot.config import Settings
        s = Settings()
        assert s.default_summary_minutes == 60


class TestQuietThreshold:
    def test_default_value(self):
        from bot.config import Settings
        s = Settings()
        assert s.quiet_threshold == 5

    def test_override_from_env(self, monkeypatch):
        monkeypatch.setenv("QUIET_THRESHOLD", "10")
        from bot.config import Settings
        s = Settings()
        assert s.quiet_threshold == 10


class TestSystemPrompts:
    def test_summary_prompt_has_topic_grouped_format(self):
        from bot.summarizer import SUMMARY_SYSTEM_PROMPT
        assert "(**Topic Name**)" in SUMMARY_SYSTEM_PROMPT

    def test_summary_prompt_no_action_items(self):
        from bot.summarizer import SUMMARY_SYSTEM_PROMPT
        assert "Do not extract action items or decisions as separate sections" in SUMMARY_SYSTEM_PROMPT

    def test_merge_prompt_no_action_items(self):
        from bot.summarizer import MERGE_SYSTEM_PROMPT
        assert "Do not extract action items or decisions as separate sections" in MERGE_SYSTEM_PROMPT

    def test_merge_prompt_has_topic_grouped_format(self):
        from bot.summarizer import MERGE_SYSTEM_PROMPT
        assert "(**Topic Name**)" in MERGE_SYSTEM_PROMPT
