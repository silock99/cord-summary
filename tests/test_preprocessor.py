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
    message_id=12345,
    mentions=None,
    channel_mentions=None,
    role_mentions=None,
    attachments=None,
    reactions=None,
    embeds=None,
    reference=None,
    mention_everyone=False,
    created_at=None,
):
    """Build a mock discord.Message for testing."""
    msg = MagicMock(spec=discord.Message)
    msg.author = MagicMock()
    msg.author.bot = bot
    msg.author.display_name = display_name
    msg.author.id = author_id
    msg.id = message_id
    msg.type = msg_type
    msg.content = content
    msg.mentions = mentions or []
    msg.channel_mentions = channel_mentions or []
    msg.role_mentions = role_mentions or []
    msg.attachments = attachments or []
    msg.reactions = reactions or []
    msg.embeds = embeds or []
    msg.mention_everyone = mention_everyone
    msg.reference = reference
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
    attachment = MagicMock(spec=discord.Attachment)
    attachment.filename = "doc.pdf"
    attachment.content_type = "application/pdf"
    msg = _make_message(content="check this", attachments=[attachment])
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert "[file: doc.pdf]" in result.content


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


# Phase 4: Basic smoke tests for new enriched metadata fields
def test_new_fields_have_defaults():
    """ProcessedMessage constructed with only author/content/timestamp still works."""
    pm = ProcessedMessage(author="Test", content="hello", timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert pm.message_id == 0
    assert pm.reply_to_id is None
    assert pm.is_important is False
    assert pm.is_popular is False
    assert pm.reaction_count == 0
    assert pm.reply_count == 0
    assert pm.embeds_text == []


def test_message_id_extracted():
    """preprocess_message sets message_id from message.id."""
    msg = _make_message(content="test", message_id=99999)
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert result.message_id == 99999


# --- Mock helpers for Phase 4 enriched metadata ---

def _make_attachment(filename="file.txt", content_type="application/octet-stream"):
    """Create a mock discord.Attachment."""
    att = MagicMock(spec=discord.Attachment)
    att.filename = filename
    att.content_type = content_type
    return att


def _make_embed(title=None, description=None):
    """Create a mock discord.Embed."""
    embed = MagicMock(spec=discord.Embed)
    embed.title = title
    embed.description = description
    return embed


def _make_reaction(count=1):
    """Create a mock discord.Reaction."""
    r = MagicMock(spec=discord.Reaction)
    r.count = count
    return r


def _make_reference(message_id=None):
    """Create a mock discord.MessageReference."""
    ref = MagicMock(spec=discord.MessageReference)
    ref.message_id = message_id
    return ref


# --- Phase 4: Typed attachment tests ---

def test_attachment_typed_image():
    """Image attachment produces '[image: photo.png]' in content."""
    att = _make_attachment("photo.png", "image/png")
    msg = _make_message(content="look", attachments=[att])
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert "[image: photo.png]" in result.content


def test_attachment_typed_video():
    """Video attachment produces '[video: clip.mp4]' in content."""
    att = _make_attachment("clip.mp4", "video/mp4")
    msg = _make_message(content="watch", attachments=[att])
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert "[video: clip.mp4]" in result.content


def test_attachment_typed_audio():
    """Audio attachment produces '[audio: song.mp3]' in content."""
    att = _make_attachment("song.mp3", "audio/mpeg")
    msg = _make_message(content="listen", attachments=[att])
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert "[audio: song.mp3]" in result.content


def test_attachment_no_content_type():
    """None content_type produces '[file: unknown.bin]' in content."""
    att = _make_attachment("unknown.bin", None)
    msg = _make_message(content="here", attachments=[att])
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert "[file: unknown.bin]" in result.content


# --- Phase 4: Reaction count tests ---

def test_reaction_count_extracted():
    """Message with multiple reactions sums counts correctly."""
    reactions = [_make_reaction(2), _make_reaction(3), _make_reaction(1)]
    msg = _make_message(content="popular", reactions=reactions)
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert result.reaction_count == 6


def test_no_reactions_zero_count():
    """Message with no reactions has reaction_count=0."""
    msg = _make_message(content="quiet")
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert result.reaction_count == 0


# --- Phase 4: Importance flag tests ---

def test_mention_everyone_sets_important():
    """Message with mention_everyone=True sets is_important=True."""
    msg = _make_message(content="@everyone wake up", mention_everyone=True)
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert result.is_important is True


def test_normal_message_not_important():
    """Default message has is_important=False."""
    msg = _make_message(content="just chatting")
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert result.is_important is False


# --- Phase 4: Reply reference tests ---

def test_reply_reference_extracted():
    """Message with reference.message_id=999 sets reply_to_id=999."""
    ref = _make_reference(999)
    msg = _make_message(content="replying to you", reference=ref)
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert result.reply_to_id == 999


def test_no_reference_returns_none():
    """Message without reference sets reply_to_id=None."""
    msg = _make_message(content="standalone")
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert result.reply_to_id is None


# --- Phase 4: Embed extraction tests ---

def test_embed_title_and_description():
    """Embed with title and description produces 'Title - Desc'."""
    embed = _make_embed("Title", "Desc")
    msg = _make_message(content="link", embeds=[embed])
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert result.embeds_text == ["Title - Desc"]


def test_embed_title_only():
    """Embed with only title produces just the title."""
    embed = _make_embed("Title", None)
    msg = _make_message(content="link", embeds=[embed])
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert result.embeds_text == ["Title"]


def test_embed_description_only():
    """Embed with only description produces just the description."""
    embed = _make_embed(None, "Some description")
    msg = _make_message(content="link", embeds=[embed])
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert result.embeds_text == ["Some description"]


def test_embed_limit_three():
    """Only first 3 embeds are extracted from a message with 5."""
    embeds = [_make_embed(f"E{i}", f"D{i}") for i in range(5)]
    msg = _make_message(content="many links", embeds=embeds)
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert len(result.embeds_text) == 3


def test_embed_description_truncated():
    """Embed with 300-char description is truncated to 200."""
    long_desc = "x" * 300
    embed = _make_embed("T", long_desc)
    msg = _make_message(content="link", embeds=[embed])
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert len(result.embeds_text) == 1
    # Should contain truncated description (200 chars)
    assert long_desc[:200] in result.embeds_text[0]
    assert long_desc[:201] not in result.embeds_text[0]


def test_embed_empty_skipped():
    """Embed with no title and no description is not included."""
    embed = _make_embed(None, None)
    msg = _make_message(content="link", embeds=[embed])
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert result.embeds_text == []


# --- Phase 4: message_id tests ---

def test_message_id_set():
    """Returned ProcessedMessage has message_id matching message.id."""
    msg = _make_message(content="test", message_id=42)
    guild = _make_guild()
    result = preprocess_message(msg, guild)
    assert result is not None
    assert result.message_id == 42


# --- Phase 4: to_line() marker tests ---

def test_to_line_important_marker():
    """to_line() includes [IMPORTANT] when is_important is True."""
    pm = ProcessedMessage(
        author="Alice", content="announcement",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        is_important=True,
    )
    assert "[IMPORTANT]" in pm.to_line()


def test_to_line_popular_marker():
    """to_line() includes [POPULAR] when is_popular is True."""
    pm = ProcessedMessage(
        author="Alice", content="hot take",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        is_popular=True,
    )
    assert "[POPULAR]" in pm.to_line()


def test_to_line_reaction_count():
    """to_line() includes reaction count when >= 5."""
    pm = ProcessedMessage(
        author="Alice", content="viral",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        reaction_count=7,
    )
    assert "[7 reactions]" in pm.to_line()


def test_to_line_no_reaction_count_below_threshold():
    """to_line() does not include reaction count when < 5."""
    pm = ProcessedMessage(
        author="Alice", content="quiet",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        reaction_count=3,
    )
    assert "reactions" not in pm.to_line()


def test_to_line_embeds():
    """to_line() includes embed text in parentheses."""
    pm = ProcessedMessage(
        author="Alice", content="link",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        embeds_text=["Title - Desc"],
    )
    assert "(Title - Desc)" in pm.to_line()
