import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

os.environ.setdefault("DISCORD_BOT_TOKEN", "test-token")

import discord
from discord.ext import commands

import commands.moderation_commands as moderation_commands


def make_interaction():
    moderator = SimpleNamespace(
        id=100,
        name="Moderator",
        display_name="Moderator",
        mention="<@100>",
        roles=[SimpleNamespace(name="Server Mod")],
    )
    target = SimpleNamespace(
        id=200,
        name="Compromised",
        display_name="Compromised",
        mention="<@200>",
    )
    guild = SimpleNamespace(
        id=300,
        name="Test Guild",
        ban=AsyncMock(),
        unban=AsyncMock(),
    )
    interaction = SimpleNamespace(
        user=moderator,
        channel=SimpleNamespace(id=400),
        guild=guild,
        response=SimpleNamespace(defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
    )
    evidence = SimpleNamespace(filename="evidence.png", url="https://example.com/evidence.png")
    return interaction, target, evidence


def run_softban(delete_hours=24, unban_error=None):
    async def run():
        bot = commands.Bot(command_prefix="!", intents=discord.Intents.none())
        await moderation_commands.setup_registered_moderation_commands(bot)
        command = bot.tree.get_command("softban")
        assert command is not None

        interaction, target, evidence = make_interaction()
        if unban_error:
            interaction.guild.unban.side_effect = unban_error

        original_permission = moderation_commands.has_permission
        original_evidence = moderation_commands.collect_additional_evidence
        original_log = moderation_commands.log_action
        original_cleanup = moderation_commands.cleanup_evidence_messages
        moderation_commands.has_permission = Mock(return_value=True)
        moderation_commands.collect_additional_evidence = AsyncMock(return_value=([evidence], []))
        moderation_commands.log_action = AsyncMock()
        moderation_commands.cleanup_evidence_messages = AsyncMock()
        try:
            await command.callback(
                interaction,
                target,
                "Compromised account",
                delete_hours,
                evidence,
            )
        finally:
            moderation_commands.has_permission = original_permission
            moderation_commands.collect_additional_evidence = original_evidence
            moderation_commands.log_action = original_log
            moderation_commands.cleanup_evidence_messages = original_cleanup
            await bot.close()
        return interaction, target

    return asyncio.run(run())


def test_softban_defaults_to_one_day_and_unbans_user():
    interaction, target = run_softban()

    interaction.guild.ban.assert_awaited_once_with(
        target,
        reason=f"Softban by {interaction.user}: Compromised account (delete last 24 hour(s))",
        delete_message_seconds=24 * 60 * 60,
    )
    interaction.guild.unban.assert_awaited_once()
    interaction.followup.send.assert_awaited_once()
    assert "immediately unbanned" in interaction.followup.send.await_args.args[0]


def test_softban_supports_custom_message_deletion_window():
    interaction, target = run_softban(delete_hours=48)

    assert interaction.guild.ban.await_args.kwargs["delete_message_seconds"] == 48 * 60 * 60
    interaction.guild.unban.assert_awaited_once_with(
        target,
        reason=f"Softban completed by {interaction.user}: Compromised account",
    )


def test_failed_unban_reports_user_remains_banned():
    response = SimpleNamespace(status=500, reason="Internal Server Error")
    interaction, _ = run_softban(
        unban_error=discord.HTTPException(response, "unban failed")
    )

    interaction.guild.ban.assert_awaited_once()
    interaction.guild.unban.assert_awaited_once()
    assert "remain banned" in interaction.followup.send.await_args.args[0]
