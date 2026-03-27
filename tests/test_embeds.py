"""Tests for embed formatting and topic-boundary splitting."""

import discord
import pytest

from bot.formatting.embeds import build_summary_embeds, _split_into_topics, EMBED_DESC_LIMIT, EMBED_COLOR


class TestSingleShortSummary:
    def test_returns_one_embed(self):
        embeds = build_summary_embeds("Short summary text", "general", "Last 4 hours")
        assert len(embeds) == 1

    def test_correct_title(self):
        embeds = build_summary_embeds("Short summary text", "general", "Last 4 hours")
        assert embeds[0].title == "Summary: #general"

    def test_correct_color(self):
        embeds = build_summary_embeds("Short summary text", "general", "Last 4 hours")
        assert embeds[0].color.value == EMBED_COLOR

    def test_correct_footer(self):
        embeds = build_summary_embeds("Short summary text", "general", "Last 4 hours")
        assert embeds[0].footer.text == "Period: Last 4 hours"

    def test_description_matches_text(self):
        embeds = build_summary_embeds("Short summary text", "general", "Last 4 hours")
        assert embeds[0].description == "Short summary text"


class TestEmptySummary:
    def test_returns_one_embed(self):
        embeds = build_summary_embeds("", "general", "Last 4 hours")
        assert len(embeds) == 1

    def test_contains_no_content_message(self):
        embeds = build_summary_embeds("", "general", "Last 4 hours")
        assert embeds[0].description == "No summary content generated."

    def test_whitespace_only(self):
        embeds = build_summary_embeds("   \n  ", "general", "Last 4 hours")
        assert embeds[0].description == "No summary content generated."


class TestMultiTopicSplit:
    def _make_long_text(self):
        """Create text with 3 topics that together exceed EMBED_DESC_LIMIT."""
        topic1 = "**Server Infrastructure**\n" + "- " + "x" * 1800 + "\n"
        topic2 = "**Development Updates**\n" + "- " + "y" * 1800 + "\n"
        topic3 = "**Community Events**\n" + "- " + "z" * 1800 + "\n"
        return topic1 + "\n" + topic2 + "\n" + topic3

    def test_produces_multiple_embeds(self):
        text = self._make_long_text()
        assert len(text) > EMBED_DESC_LIMIT
        embeds = build_summary_embeds(text, "general", "Last 4 hours")
        assert len(embeds) >= 2

    def test_second_embed_has_continued_title(self):
        text = self._make_long_text()
        embeds = build_summary_embeds(text, "general", "Last 4 hours")
        assert "(continued)" in embeds[1].title

    def test_first_embed_no_continued(self):
        text = self._make_long_text()
        embeds = build_summary_embeds(text, "general", "Last 4 hours")
        assert "(continued)" not in embeds[0].title

    def test_all_embeds_under_limit(self):
        text = self._make_long_text()
        embeds = build_summary_embeds(text, "general", "Last 4 hours")
        for embed in embeds:
            assert len(embed.description) <= EMBED_DESC_LIMIT


class TestSingleOversizedSection:
    def test_truncation_with_marker(self):
        huge_section = "**Big Topic**\n" + "x" * 5000
        embeds = build_summary_embeds(huge_section, "general", "Last 4 hours")
        assert len(embeds) == 1
        assert embeds[0].description.endswith("*(...truncated)*")
        assert len(embeds[0].description) <= EMBED_DESC_LIMIT


class TestTopicSplittingRegex:
    def test_splits_on_bold_headers(self):
        text = "**Topic A**\n- point 1\n\n**Topic B**\n- point 2\n\n**Topic C**\n- point 3"
        sections = _split_into_topics(text)
        assert len(sections) == 3

    def test_preserves_content(self):
        text = "**Topic A**\n- point 1\n\n**Topic B**\n- point 2"
        sections = _split_into_topics(text)
        assert "**Topic A**" in sections[0]
        assert "- point 1" in sections[0]
        assert "**Topic B**" in sections[1]
        assert "- point 2" in sections[1]

    def test_single_topic_returns_one_section(self):
        text = "**Only Topic**\n- just one"
        sections = _split_into_topics(text)
        assert len(sections) == 1

    def test_no_bold_headers_returns_whole_text(self):
        text = "Just plain text with no headers"
        sections = _split_into_topics(text)
        assert len(sections) == 1
        assert sections[0] == text
