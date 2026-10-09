from datetime import datetime, timezone

import discord

import moderation_store


def use_temporary_database(tmp_path):
    previous_path = moderation_store.MODERATION_DB_PATH
    moderation_store.MODERATION_DB_PATH = tmp_path / "moderation.sqlite3"
    return previous_path


def test_live_moderation_actions_are_searchable(tmp_path):
    previous_path = use_temporary_database(tmp_path)
    try:
        moderation_store.record_action(
            entry_key="live:test-action",
            guild_id=10,
            target_id=20,
            target_name="Test User",
            moderator_id=30,
            moderator_name="Test Moderator",
            action_type="Timed Out",
            reason="Repeated spam",
            duration="10m",
            evidence=["https://example.com/evidence.png"],
            occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            action_id="test-action",
        )

        actions = moderation_store.find_actions(10, 20)
        assert len(actions) == 1
        assert actions[0]["action_type"] == "Timed Out"
        assert actions[0]["reason"] == "Repeated spam"
        assert actions[0]["duration"] == "10m"
    finally:
        moderation_store.MODERATION_DB_PATH = previous_path


def test_past_log_embeds_are_imported_once(tmp_path):
    previous_path = use_temporary_database(tmp_path)
    try:
        embed = discord.Embed(
            title="🔨 Moderation Action: Timed Out",
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        embed.add_field(name="👤 Target User", value="<@20>\n(Test User)")
        embed.add_field(name="❔ Moderator", value="<@30>\n(Test Moderator)")
        embed.add_field(name="📝 Reason", value="Repeated spam")
        embed.add_field(name="⏰ Duration", value="10m")
        embed.add_field(
            name="Evidence",
            value="• [Evidence 1](https://example.com/evidence.png)",
        )
        embed.set_footer(text="Action ID: 20260101_000000")

        assert moderation_store.index_log_embed(embed, 10, 100) is True
        assert moderation_store.index_log_embed(embed, 10, 100) is False

        actions = moderation_store.find_actions(10, 20)
        assert len(actions) == 1
        assert actions[0]["action_type"] == "Timed Out"
        assert actions[0]["reason"] == "Repeated spam"
        assert actions[0]["duration"] == "10m"

        assert moderation_store.history_was_indexed(10) is None
        moderation_store.finish_history_index(10, datetime(2026, 1, 2, tzinfo=timezone.utc))
        assert moderation_store.history_was_indexed(10) is not None
    finally:
        moderation_store.MODERATION_DB_PATH = previous_path
