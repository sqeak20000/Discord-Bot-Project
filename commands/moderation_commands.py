"""Moderation slash commands, moved out of the main moderation logic file."""

import discord
from discord import app_commands

from config import ALLOWED_ROLES, BLACKLIST_ROLE_NAMES
from moderation import (
    BLACKLIST_CATEGORY_LABELS,
    apply_blacklist_roles,
    cleanup_evidence_messages,
    collect_additional_evidence,
    get_requested_blacklist_categories,
)
from utils import has_permission, log_action, notify_user_dm, parse_duration


async def register_moderation_commands(bot):
    """Register the moderation slash-command tree.

    This keeps the command definitions out of moderation.py while still using the shared
    helper functions already defined there for evidence handling, blacklist logic, and logging.
    """
    if getattr(bot, "_moderation_commands_setup", False):
        return

    existing = bot.tree.get_command("ban")
    if existing is not None:
        bot._moderation_commands_setup = True
        return

    @bot.tree.command(name="ban", description="Ban a user from the server")
    @app_commands.describe(
        user="The user to ban",
        reason="Reason for the ban",
        delete_messages="Whether to delete the user's messages from the last 7 days",
        evidence="Evidence for the ban (image or link)"
    )
    async def slash_ban(
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str,
        delete_messages: bool = False,
        evidence: discord.Attachment = None,
    ):
        await interaction.response.defer(ephemeral=True)

        if not has_permission(interaction.user, ALLOWED_ROLES):
            await interaction.followup.send("❌ You don't have permission to use this command.", ephemeral=True)
            return

        evidence_attachments, evidence_messages_to_delete = await collect_additional_evidence(bot, interaction, evidence)

        if not evidence_attachments:
            await interaction.followup.send("❌ Please provide evidence (image or attachment) for the ban.", ephemeral=True)
            return

        evidence_msg = type('MockMessage', (), {
            'attachments': evidence_attachments,
            'content': f"/ban {user.mention} {reason}",
            'author': interaction.user,
            'channel': interaction.channel,
            'mentions': [user],
            'jump_url': f"https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}/slash_command"
        })()

        try:
            await log_action(bot, evidence_msg, "Banned", interaction.user, reason)
            dm_sent = await notify_user_dm(user, "Banned", interaction.guild.name, interaction.user, reason=reason)

            delete_message_days = 7 if delete_messages else 0
            await interaction.guild.ban(
                user,
                reason=f"Banned by {interaction.user}: {reason}",
                delete_message_days=delete_message_days,
            )

            dm_status = " (DM sent)" if dm_sent else " (DM failed - user may have DMs disabled)"
            delete_status = " Messages from last 7 days deleted." if delete_messages else ""
            await interaction.followup.send(f"✅ {user.mention} has been banned!{dm_status}{delete_status}")
            await cleanup_evidence_messages(evidence_messages_to_delete)
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to ban this user.", ephemeral=True)
        except discord.HTTPException:
            await interaction.followup.send("❌ Failed to ban the user.", ephemeral=True)
        except Exception as exc:
            print(f"Ban failed: Unexpected error - {exc}")
            await interaction.followup.send("❌ An unexpected error occurred during the ban.", ephemeral=True)

    @bot.tree.command(name="kick", description="Kick a user from the server")
    @app_commands.describe(
        user="The user to kick",
        reason="Reason for the kick",
        evidence="Evidence for the kick (image or link)"
    )
    async def slash_kick(
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str,
        evidence: discord.Attachment = None,
    ):
        await interaction.response.defer(ephemeral=True)

        if not has_permission(interaction.user, ALLOWED_ROLES):
            await interaction.followup.send("❌ You don't have permission to use this command.", ephemeral=True)
            return

        evidence_attachments, evidence_messages_to_delete = await collect_additional_evidence(bot, interaction, evidence)

        if not evidence_attachments:
            await interaction.followup.send("❌ Please provide evidence (image or attachment) for the kick.", ephemeral=True)
            return

        evidence_msg = type('MockMessage', (), {
            'attachments': evidence_attachments,
            'content': f"/kick {user.mention} {reason}",
            'author': interaction.user,
            'channel': interaction.channel,
            'mentions': [user],
            'jump_url': f"https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}/slash_command"
        })()

        try:
            await log_action(bot, evidence_msg, "Kicked", interaction.user, reason)
            dm_sent = await notify_user_dm(user, "Kicked", interaction.guild.name, interaction.user, reason=reason)

            await interaction.guild.kick(user, reason=f"Kicked by {interaction.user}: {reason}")

            dm_status = " (DM sent)" if dm_sent else " (DM failed - user may have DMs disabled)"
            await interaction.followup.send(f"✅ {user.mention} has been kicked!{dm_status}")
            await cleanup_evidence_messages(evidence_messages_to_delete)
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to kick this user.", ephemeral=True)
        except discord.HTTPException:
            await interaction.followup.send("❌ Failed to kick the user.", ephemeral=True)

    @bot.tree.command(name="timeout", description="Timeout a user")
    @app_commands.describe(
        user="The user to timeout",
        duration="Duration (e.g., 10m, 1h, 2d, 1w)",
        reason="Reason for the timeout",
        evidence="Evidence for the timeout (image or link)"
    )
    async def slash_timeout(
        interaction: discord.Interaction,
        user: discord.Member,
        duration: str,
        reason: str,
        evidence: discord.Attachment = None,
    ):
        await interaction.response.defer(ephemeral=True)

        if not has_permission(interaction.user, ALLOWED_ROLES):
            await interaction.followup.send("❌ You don't have permission to use this command.", ephemeral=True)
            return

        timeout_duration = parse_duration(duration)
        if timeout_duration == "invalid" or timeout_duration is None:
            await interaction.followup.send("❌ Invalid duration format. Use 10m, 1h, 2d, or 1w", ephemeral=True)
            return

        evidence_attachments, evidence_messages_to_delete = await collect_additional_evidence(bot, interaction, evidence)

        if not evidence_attachments:
            await interaction.followup.send("❌ Please provide evidence (image or attachment) for the timeout.", ephemeral=True)
            return

        evidence_msg = type('MockMessage', (), {
            'attachments': evidence_attachments,
            'content': f"/timeout {user.mention} {duration} {reason}",
            'author': interaction.user,
            'channel': interaction.channel,
            'mentions': [user],
            'jump_url': f"https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}/slash_command"
        })()

        try:
            await log_action(bot, evidence_msg, "Timed out", interaction.user, reason, duration)
            dm_sent = await notify_user_dm(
                user,
                "Timed out",
                interaction.guild.name,
                interaction.user,
                reason=reason,
                duration=duration,
            )

            await user.timeout(timeout_duration, reason=f"Timed out by {interaction.user}: {reason}")

            dm_status = " (DM sent)" if dm_sent else " (DM failed - user may have DMs disabled)"
            await interaction.followup.send(f"✅ {user.mention} has been timed out for {duration}!{dm_status}")
            await cleanup_evidence_messages(evidence_messages_to_delete)
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to timeout this user.", ephemeral=True)
        except discord.HTTPException:
            await interaction.followup.send("❌ Failed to timeout the user.", ephemeral=True)

    @bot.tree.command(name="blacklist", description="Blacklist a user from specific server access and moderation categories")
    @app_commands.describe(
        user="The user to blacklist",
        reason="Reason for the blacklist",
        tickets="Apply the ticket blacklist",
        code_sharing="Apply the code sharing blacklist",
        exalted="Apply the exalted blacklist",
        creations="Apply the creations blacklist",
        evidence="Evidence for the blacklist (image or link)"
    )
    async def slash_blacklist(
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str,
        tickets: bool = False,
        code_sharing: bool = False,
        exalted: bool = False,
        creations: bool = False,
        evidence: discord.Attachment = None,
    ):
        await interaction.response.defer(ephemeral=True)

        if not has_permission(interaction.user, ALLOWED_ROLES):
            await interaction.followup.send("❌ You don't have permission to use this command.", ephemeral=True)
            return

        selected_categories = get_requested_blacklist_categories({
            "tickets": tickets,
            "code_sharing": code_sharing,
            "exalted": exalted,
            "creations": creations,
        })

        if not selected_categories:
            await interaction.followup.send("❌ Please select at least one blacklist category before continuing.", ephemeral=True)
            return

        evidence_attachments, evidence_messages_to_delete = await collect_additional_evidence(bot, interaction, evidence)

        if not evidence_attachments:
            await interaction.followup.send("❌ Please provide evidence (image or attachment) for the blacklist.", ephemeral=True)
            return

        missing_roles = []
        for category in selected_categories:
            role_name = BLACKLIST_ROLE_NAMES[category]
            if not discord.utils.get(interaction.guild.roles, name=role_name):
                missing_roles.append(role_name)

        if missing_roles:
            await interaction.followup.send(
                f"❌ Missing required blacklist role(s): {', '.join(missing_roles)}. Create those roles first.",
                ephemeral=True,
            )
            return

        evidence_msg = type('MockMessage', (), {
            'attachments': evidence_attachments,
            'content': f"/blacklist {user.mention} {reason}",
            'author': interaction.user,
            'channel': interaction.channel,
            'mentions': [user],
            'jump_url': f"https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}/slash_command"
        })()

        try:
            category_names = [BLACKLIST_CATEGORY_LABELS.get(cat, cat.replace('_', ' ').title()) for cat in selected_categories]
            blacklist_summary = ", ".join(category_names)

            await log_action(bot, evidence_msg, "Blacklisted", interaction.user, f"{blacklist_summary}: {reason}")
            dm_sent = await notify_user_dm(
                user,
                "Blacklisted",
                interaction.guild.name,
                interaction.user,
                reason=f"{blacklist_summary}: {reason}",
            )

            await apply_blacklist_roles(interaction.guild, user, selected_categories, reason, interaction.user)

            dm_status = " (DM sent)" if dm_sent else " (DM failed - user may have DMs disabled)"
            await interaction.followup.send(f"✅ {user.mention} has been blacklisted for: **{blacklist_summary}**{dm_status}")
            await cleanup_evidence_messages(evidence_messages_to_delete)
        except ValueError as exc:
            await interaction.followup.send(f"❌ {exc}", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to manage roles for this user.", ephemeral=True)
        except discord.HTTPException:
            await interaction.followup.send("❌ Failed to apply the blacklist roles.", ephemeral=True)

    @bot.tree.command(name="unban", description="Unban a user from the server")
    @app_commands.describe(
        user_id="The ID of the user to unban",
        reason="Reason for the unban"
    )
    async def slash_unban(interaction: discord.Interaction, user_id: str, reason: str):
        if not has_permission(interaction.user, ALLOWED_ROLES):
            await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            user_obj = await bot.fetch_user(int(user_id))
            await interaction.guild.unban(user_obj, reason=reason)

            mock_msg = type('MockMessage', (), {
                'mentions': [user_obj],
                'attachments': [],
                'content': f"/unban {user_id} {reason}",
                'author': interaction.user,
                'channel': interaction.channel,
                'guild': interaction.guild,
            })()

            await log_action(bot, mock_msg, "Unban", interaction.user, reason)
            await interaction.followup.send(f"✅ **{user_obj.name}** has been unbanned.\nReason: {reason}")
        except ValueError:
            await interaction.followup.send("❌ Invalid User ID provided.", ephemeral=True)
        except discord.NotFound:
            await interaction.followup.send("❌ User not found or not banned.", ephemeral=True)
        except Exception as exc:
            await interaction.followup.send(f"❌ Failed to unban user: {exc}", ephemeral=True)

    @bot.tree.command(name="untimeout", description="Remove timeout from a user")
    @app_commands.describe(
        user="The user to untimeout",
        reason="Reason for removing timeout"
    )
    async def slash_untimeout(interaction: discord.Interaction, user: discord.Member, reason: str):
        if not has_permission(interaction.user, ALLOWED_ROLES):
            await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            if not user.is_timed_out():
                await interaction.followup.send(f"⚠️ **{user.name}** is not currently timed out.", ephemeral=True)
                return

            await user.timeout(None, reason=reason)

            mock_msg = type('MockMessage', (), {
                'mentions': [user],
                'attachments': [],
                'content': f"/untimeout {user.mention} {reason}",
                'author': interaction.user,
                'channel': interaction.channel,
                'guild': interaction.guild,
            })()

            await notify_user_dm(user, "Timeout Removed", interaction.guild.name, interaction.user, reason)
            await log_action(bot, mock_msg, "Untimeout", interaction.user, reason)
            await interaction.followup.send(f"✅ **{user.name}**'s timeout has been removed.\nReason: {reason}")
        except Exception as exc:
            await interaction.followup.send(f"❌ Failed to remove timeout: {exc}", ephemeral=True)

    bot._moderation_commands_setup = True


async def setup_registered_moderation_commands(bot):
    """Public hook used by the command registry."""
    await register_moderation_commands(bot)
