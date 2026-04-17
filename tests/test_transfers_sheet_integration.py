"""Phase 13 Plan 02 — integration tests for /transfer-* commands with sheet targets.

Covers:
- Guards on /transfer-add + /transfer-remove for basketball+target (D-02).
- /transfer-list basketball render path using TransferTarget field set + synced-ago footer
  (D-16, D-21), with locally-managed outgoing entries rendered in a separate section.
- Football path unchanged (still uses bot.transfer_store + existing cache).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.commands.transfers import register_transfer_commands
from bot.storage.cache import TTLCache
from bot.storage.models import PlayerEntry, TransferTarget
from bot.storage.recruiting_store import RecruitingStore


BASKETBALL_CHANNEL_ID = 111
FOOTBALL_CHANNEL_ID = 222


def _make_bot(tmp_path: Path, sheet_targets=None, sheet_last_synced=None):
    """Build a fake bot with the attributes the transfer commands use."""
    transfers_path = tmp_path / "transfers.json"
    transfer_store = RecruitingStore(transfers_path)

    sheet_store = SimpleNamespace(
        targets=list(sheet_targets or []),
        last_synced_at=sheet_last_synced,
    )

    settings = SimpleNamespace(
        football_channel_ids=[FOOTBALL_CHANNEL_ID],
        basketball_channel_ids=[BASKETBALL_CHANNEL_ID],
        recruiting_editor_ids=[42],
        admin_user_ids=[42],
        cfbd_api_key="",
        cbbd_api_key="",
    )

    # Capture tree.command registrations — we invoke the underlying callback directly.
    registered: dict[str, object] = {}

    class FakeTree:
        def command(self, *args, **kwargs):
            def wrap(fn):
                registered[kwargs.get("name", fn.__name__)] = fn
                # Also return an object exposing .error(...) like real app_commands
                fn.error = lambda *_a, **_k: None
                return fn
            return wrap

    bot = SimpleNamespace(
        tree=FakeTree(),
        settings=settings,
        transfer_store=transfer_store,
        transfer_cache=TTLCache(default_ttl=900.0),
        sheet_target_store=sheet_store,
        registered=registered,
    )
    register_transfer_commands(bot)
    return bot


def _make_interaction(bot, channel_id: int, user_id: int = 42):
    """Build a mock Discord interaction with AsyncMock response helpers.

    interaction.client must expose the bot's settings because command handlers
    read `interaction.client.settings` directly (not via closure).
    """
    interaction = MagicMock()
    interaction.channel_id = channel_id
    interaction.user = SimpleNamespace(id=user_id, __str__=lambda self=None: "user#0001")
    interaction.client = SimpleNamespace(settings=bot.settings)
    interaction.response = MagicMock()
    interaction.response.defer = AsyncMock()
    interaction.edit_original_response = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()
    return interaction


def _get_callback(bot, name):
    """app_commands decorators wrap the callable — unwrap to get the actual coroutine."""
    obj = bot.registered[name]
    # Decorated command may be an app_commands.Command — it has .callback
    cb = getattr(obj, "callback", obj)
    return cb


# ====================================================================
# Task 1 — guards on /transfer-add and /transfer-remove
# ====================================================================


@pytest.mark.asyncio
async def test_transfer_add_basketball_target_is_blocked(tmp_path: Path):
    bot = _make_bot(tmp_path)
    interaction = _make_interaction(bot, BASKETBALL_CHANNEL_ID)
    add = _get_callback(bot, "transfer-add")

    with patch.object(bot.transfer_store, "add_player", wraps=bot.transfer_store.add_player) as spy:
        await add(interaction, name="Jon Doe", position="G", school="UCLA", stars=0, type=None)

    # Responded with the sheet-managed message
    interaction.edit_original_response.assert_awaited_once()
    content = interaction.edit_original_response.await_args.kwargs.get("content", "")
    assert "google sheet" in content.lower()
    # Store was never mutated
    spy.assert_not_called()
    assert bot.transfer_store.list_players("basketball") == []


@pytest.mark.asyncio
async def test_transfer_add_basketball_target_explicit_type_is_blocked(tmp_path: Path):
    bot = _make_bot(tmp_path)
    interaction = _make_interaction(bot, BASKETBALL_CHANNEL_ID)
    add = _get_callback(bot, "transfer-add")

    from discord import app_commands
    explicit = app_commands.Choice(name="Target (coming to KU)", value="target")
    with patch.object(bot.transfer_store, "add_player", wraps=bot.transfer_store.add_player) as spy:
        await add(interaction, name="Jon Doe", position="G", school="UCLA", stars=0, type=explicit)

    content = interaction.edit_original_response.await_args.kwargs.get("content", "")
    assert "google sheet" in content.lower()
    spy.assert_not_called()


@pytest.mark.asyncio
async def test_transfer_add_basketball_outgoing_still_works(tmp_path: Path):
    bot = _make_bot(tmp_path)
    interaction = _make_interaction(bot, BASKETBALL_CHANNEL_ID)
    add = _get_callback(bot, "transfer-add")

    from discord import app_commands
    outgoing = app_commands.Choice(name="Outgoing (leaving KU)", value="outgoing")

    # Patch stats fetch to avoid network + avoid bot.settings attributes needed there
    with patch("bot.commands.transfers.fetch_basketball_stats", new_callable=AsyncMock) as mock_stats:
        mock_stats.return_value = None
        await add(interaction, name="Leaving KU", position="G", school="KU", stars=0, type=outgoing)

    players = bot.transfer_store.list_players("basketball")
    assert len(players) == 1
    assert players[0].name == "Leaving KU"
    assert players[0].type == "outgoing"
    content = interaction.edit_original_response.await_args.kwargs.get("content", "")
    assert "added" in content.lower()


@pytest.mark.asyncio
async def test_transfer_add_football_target_still_works(tmp_path: Path):
    bot = _make_bot(tmp_path)
    interaction = _make_interaction(bot, FOOTBALL_CHANNEL_ID)
    add = _get_callback(bot, "transfer-add")

    with patch("bot.commands.transfers.fetch_football_stats", new_callable=AsyncMock) as mock_stats:
        mock_stats.return_value = None
        await add(interaction, name="FB Target", position="QB", school="Bama", stars=0, type=None)

    players = bot.transfer_store.list_players("football")
    assert len(players) == 1
    assert players[0].name == "FB Target"
    assert players[0].type == "target"
    content = interaction.edit_original_response.await_args.kwargs.get("content", "")
    assert "added" in content.lower()


@pytest.mark.asyncio
async def test_transfer_remove_basketball_target_is_blocked(tmp_path: Path):
    bot = _make_bot(tmp_path)
    # basketball basket is empty after self-heal; simulate that directly
    interaction = _make_interaction(bot, BASKETBALL_CHANNEL_ID)
    remove = _get_callback(bot, "transfer-remove")

    with patch.object(bot.transfer_store, "remove_player", wraps=bot.transfer_store.remove_player) as spy:
        await remove(interaction, name="Anyone")

    content = interaction.edit_original_response.await_args.kwargs.get("content", "")
    assert "google sheet" in content.lower()
    spy.assert_not_called()


@pytest.mark.asyncio
async def test_transfer_remove_basketball_outgoing_still_works(tmp_path: Path):
    """Sport=basketball remove for an existing OUTGOING player should still succeed."""
    bot = _make_bot(tmp_path)
    # Seed an outgoing basketball entry
    bot.transfer_store.add_player("basketball", "Out Guy", "G", "KU", 0, player_type="outgoing")

    interaction = _make_interaction(bot, BASKETBALL_CHANNEL_ID)
    remove = _get_callback(bot, "transfer-remove")

    await remove(interaction, name="Out Guy")

    content = interaction.edit_original_response.await_args.kwargs.get("content", "")
    assert "removed" in content.lower()
    assert bot.transfer_store.list_players("basketball") == []


@pytest.mark.asyncio
async def test_transfer_remove_football_still_works(tmp_path: Path):
    bot = _make_bot(tmp_path)
    bot.transfer_store.add_player("football", "FB Out", "QB", "Bama", 0, player_type="outgoing")

    interaction = _make_interaction(bot, FOOTBALL_CHANNEL_ID)
    remove = _get_callback(bot, "transfer-remove")

    await remove(interaction, name="FB Out")
    content = interaction.edit_original_response.await_args.kwargs.get("content", "")
    assert "removed" in content.lower()


# ====================================================================
# Task 2 — /transfer-list basketball render path
# ====================================================================


def _collect_embeds(interaction):
    """Pull embeds passed to edit_original_response + followup.send."""
    embeds = []
    call = interaction.edit_original_response.await_args
    if call and "embeds" in call.kwargs:
        embeds.extend(call.kwargs["embeds"])
    for c in interaction.followup.send.await_args_list:
        if "embeds" in c.kwargs:
            embeds.extend(c.kwargs["embeds"])
    return embeds


@pytest.mark.asyncio
async def test_transfer_list_basketball_renders_sheet_target_fields(tmp_path: Path):
    target = TransferTarget(
        name="Jon Doe", position="G", former_school="UCLA",
        height_weight="6'4\" / 195", ku_interest_level="HIGH",
        made_contact="Yes", notes="quick feet",
    )
    synced = datetime.now(timezone.utc) - timedelta(minutes=5)
    bot = _make_bot(tmp_path, sheet_targets=[target], sheet_last_synced=synced)
    interaction = _make_interaction(bot, BASKETBALL_CHANNEL_ID)
    tlist = _get_callback(bot, "transfer-list")

    await tlist(interaction, position=None)

    embeds = _collect_embeds(interaction)
    assert embeds, "expected at least one embed"
    # Find the field for Jon Doe
    all_field_text = ""
    for e in embeds:
        for f in e.fields:
            all_field_text += f.name + "\n" + (f.value or "") + "\n"

    assert "Jon Doe" in all_field_text
    assert "G" in all_field_text
    assert "UCLA" in all_field_text
    assert "6'4" in all_field_text
    assert "195" in all_field_text
    assert "HIGH" in all_field_text
    assert "Yes" in all_field_text
    assert "quick feet" in all_field_text
    # No stars / no "Unrated" filler for sheet-sourced targets (D-16)
    assert "\u2b50" not in all_field_text
    assert "Unrated" not in all_field_text


@pytest.mark.asyncio
async def test_transfer_list_basketball_footer_contains_synced_ago(tmp_path: Path):
    target = TransferTarget(name="Jon Doe", position="G", ku_interest_level="High")
    synced = datetime.now(timezone.utc) - timedelta(minutes=5)
    bot = _make_bot(tmp_path, sheet_targets=[target], sheet_last_synced=synced)
    interaction = _make_interaction(bot, BASKETBALL_CHANNEL_ID)
    tlist = _get_callback(bot, "transfer-list")

    await tlist(interaction, position=None)
    embeds = _collect_embeds(interaction)
    last_footer = embeds[-1].footer.text or ""
    assert "synced" in last_footer.lower()
    assert "minute" in last_footer.lower()


@pytest.mark.asyncio
async def test_transfer_list_basketball_footer_sync_pending_when_none(tmp_path: Path):
    target = TransferTarget(name="Jon Doe", position="G", ku_interest_level="High")
    bot = _make_bot(tmp_path, sheet_targets=[target], sheet_last_synced=None)
    interaction = _make_interaction(bot, BASKETBALL_CHANNEL_ID)
    tlist = _get_callback(bot, "transfer-list")

    await tlist(interaction, position=None)
    embeds = _collect_embeds(interaction)
    last_footer = (embeds[-1].footer.text or "").lower()
    assert "sync" in last_footer
    assert "pending" in last_footer


@pytest.mark.asyncio
async def test_transfer_list_basketball_includes_outgoing_section_from_transfer_store(tmp_path: Path):
    # One locally-managed outgoing entry + one sheet target
    target = TransferTarget(name="Sheet Target", position="G", former_school="UCLA", ku_interest_level="High")
    synced = datetime.now(timezone.utc) - timedelta(minutes=3)
    bot = _make_bot(tmp_path, sheet_targets=[target], sheet_last_synced=synced)
    bot.transfer_store.add_player("basketball", "Out Guy", "F", "KU", 3, player_type="outgoing")

    interaction = _make_interaction(bot, BASKETBALL_CHANNEL_ID)
    tlist = _get_callback(bot, "transfer-list")
    await tlist(interaction, position=None)

    embeds = _collect_embeds(interaction)
    all_text = ""
    for e in embeds:
        for f in e.fields:
            all_text += f.name + "\n" + (f.value or "") + "\n"

    # Both sections present
    assert "Transfers Out" in all_text
    assert "Transfer Targets" in all_text
    # Outgoing PlayerEntry-style uses stars (3 stars) in name
    assert "Out Guy" in all_text
    assert "\u2b50" in all_text  # stars appear for outgoing PlayerEntry
    # Sheet target present with no stars on its own field
    assert "Sheet Target" in all_text
    assert "UCLA" in all_text


@pytest.mark.asyncio
async def test_transfer_list_football_unchanged_does_not_consult_sheet(tmp_path: Path):
    target = TransferTarget(name="Should Not Appear", position="G")
    bot = _make_bot(tmp_path, sheet_targets=[target], sheet_last_synced=datetime.now(timezone.utc))
    bot.transfer_store.add_player("football", "FB Target", "QB", "Bama", 4, player_type="target")

    interaction = _make_interaction(bot, FOOTBALL_CHANNEL_ID)
    tlist = _get_callback(bot, "transfer-list")
    await tlist(interaction, position=None)

    embeds = _collect_embeds(interaction)
    all_text = ""
    for e in embeds:
        for f in e.fields:
            all_text += f.name + "\n" + (f.value or "") + "\n"

    assert "FB Target" in all_text
    assert "Should Not Appear" not in all_text


@pytest.mark.asyncio
async def test_transfer_list_basketball_empty_shows_empty_state_with_footer(tmp_path: Path):
    synced = datetime.now(timezone.utc) - timedelta(hours=2)
    bot = _make_bot(tmp_path, sheet_targets=[], sheet_last_synced=synced)
    interaction = _make_interaction(bot, BASKETBALL_CHANNEL_ID)
    tlist = _get_callback(bot, "transfer-list")

    await tlist(interaction, position=None)
    embeds = _collect_embeds(interaction)
    assert len(embeds) == 1
    desc = (embeds[0].description or "").lower()
    assert "no players" in desc
    footer = (embeds[0].footer.text or "").lower()
    assert "synced" in footer
    assert "hour" in footer


@pytest.mark.asyncio
async def test_transfer_list_basketball_targets_count_toward_pagination_cap(tmp_path: Path):
    # 12 targets → 2 embeds (10 + 2) at MAX_PLAYERS_PER_EMBED=10
    targets = [TransferTarget(name=f"Player {i}", position="G", ku_interest_level="High") for i in range(12)]
    synced = datetime.now(timezone.utc)
    bot = _make_bot(tmp_path, sheet_targets=targets, sheet_last_synced=synced)
    interaction = _make_interaction(bot, BASKETBALL_CHANNEL_ID)
    tlist = _get_callback(bot, "transfer-list")

    await tlist(interaction, position=None)
    embeds = _collect_embeds(interaction)
    assert len(embeds) == 2
