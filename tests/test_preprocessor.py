"""Unit tests for the message preprocessor."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import discord

from bot.models import ProcessedMessage
from bot.pipeline.preprocessor import preprocess_message


def _make_message(
    content="hello",
    *,
    bot=False,
    msg_type=discord.MessageType.default,
    display_name="Alice",
    author_id=100,
    mentions=None,
    channel_mentions=None,
    role_mentions=None,
    attachments=None,
    created_at=None,
):
    """Build a mock discord.Message for testing."""
    msg = MagicMock(spec=discord.Message)
    msg.author = MagicMock()
    msg.author.bot = bot
    msg.author.display_name = display_name
    msg.author.id = author_id
    msg.type = msg_type
    msg.content = content
    msg.mentions = mentions or []
    msg.channel_mentions = channel_mentions or []
    msg.role_mentions = role_mentions or []
    msg.attachments = attachments or []
    msg.created_at = created_at or datetime(2026, 3, 27, 12, 0, 0, tzinfo=timezone.utc)
    return msg


def _make_guild(members=None):
    """Build a mock guild with optional member lookup."""
    guild = MagicMock(spec=discord.Guild)
    member_map = {}
    if members:
        for mid, name in members.items():
            m = MagicMock()
            m.display_name = name
            member_map[mid] = m
    guild.get_member = lambda uid: member_map.get(uid)
    return guild


def test_filter_bot_messages():
    msg = _make_message(bot=True)
    guild = _make_guild()
    assert preprocess_message(msg, guild) is None


def test_filter_system_messages():
    msg = _make_message(msg_type=discord.MessageType.new_member)
    guild = _make_guild()
    assert preprocess_message(msg, guild) is None


def test_allow_default_messages():
    msg = _make_message(content="hi there", display_name="Bob")
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert isinstance(result, ProcessedMessage)
    assert result.content == "hi there"
    assert result.author == "Bob"


def test_allow_reply_messages():
    msg = _make_message(content="replying", msg_type=discord.MessageType.reply)
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert result.content == "replying"


def test_mention_resolution():
    user_mention = MagicMock()
    user_mention.id = 123
    user_mention.name = "fallback"
    msg = _make_message(content="hey <@123> check this", mentions=[user_mention])
    guild = _make_guild(members={123: "DisplayName"})
    result = preprocess_message(msg, guild)
    assert result is not None
    assert "@DisplayName" in result.content
    assert "<@123>" not in result.content


def test_channel_mention_resolution():
    ch = MagicMock()
    ch.id = 456
    ch.name = "channel-name"
    msg = _make_message(content="see <#456>", channel_mentions=[ch])
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert "#channel-name" in result.content
    assert "<#456>" not in result.content


def test_role_mention_resolution():
    role = MagicMock()
    role.id = 789
    role.name = "RoleName"
    msg = _make_message(content="ping <@&789>", role_mentions=[role])
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert "@RoleName" in result.content
    assert "<@&789>" not in result.content


def test_attachment_marker():
    attachment = MagicMock()
    msg = _make_message(content="check this", attachments=[attachment])
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert result.content == "check this [attachment]"


def test_custom_emoji_cleanup():
    msg = _make_message(content="nice <:emoji:123> and <a:animated:456>")
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert ":emoji:" in result.content
    assert ":animated:" in result.content
    assert "<:emoji:123>" not in result.content
    assert "<a:animated:456>" not in result.content


def test_empty_message_filtered():
    msg = _make_message(content="")
    guild = _make_guild()
    assert preprocess_message(msg, guild) is None


def test_author_display_name():
    msg = _make_message(content="hello", display_name="ServerNickname")
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert result.author == "ServerNickname"


def test_links_preserved():
    msg = _make_message(content="check https://example.com/path?q=1 out")
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert "https://example.com/path?q=1" in result.content
