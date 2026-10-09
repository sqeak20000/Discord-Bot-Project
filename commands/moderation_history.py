"""Private moderation history, action workflow, and one-time log import commands."""

import logging
from types import SimpleNamespace

import discord
from discord import app_commands

from config import (
    ALLOWED_ROLES,
    BLACKLIST_ROLE_NAMES,
    LOG_CHANNEL_ID,
    MODERATION_INDEXER_USER_ID,
)
from moderation import (
    BLACKLIST_CATEGORY_LABELS,
    apply_blacklist_roles,
    get_requested_blacklist_categories,
)
from moderation_store import (
    find_actions,
    finish_history_index,
    history_was_indexed,
    index_log_embed,
)
from utils import has_permission, log_action, notify_user_dm, parse_duration


def _history_embed(user, actions):
    embed = discord.Embed(
        title=f"Moderation history: {user}",
        color=discord.Color.orange(),
    )
    if not actions:
        embed.description = "No moderation history is recorded for this user."
        return embed

    lines = []
    for action in actions:
        timestamp = discord.utils.parse_time(action["occurred_at"])
        when = discord.utils.format_dt(timestamp, style="R") if timestamp else "Unknown date"
        details = [f"**{action['action_type']}** — {when}"]
        if action["reason"]:
            details.append(f"Reason: {action['reason']}")
        if action["duration"]:
            details.append(f"Duration: {action['duration']}")
        if action["moderator_name"]:
            details.append(f"Moderator: {action['moderator_name']}")
        lines.append("\n".join(details))

    embed.description = "\n\n".join(lines)[:4096]
    embed.set_footer(text=f"Showing the latest {len(actions)} recorded action(s)")
    return embed


class ModerateActionModal(discord.ui.Modal):
    def __init__(self, target, action, moderator_id):
        super().__init__(title=f"{action.title()} {target}", timeout=300)
        self.target = target
        self.action = action
        self.moderator_id = moderator_id

        self.reason = discord.ui.TextInput(
            label="Reason",
            placeholder="Reason for this moderation action",
            style=discord.TextStyle.paragraph,
            max_length=1000,
        )
        self.add_item(discord.ui.Label(text="Reason", component=self.reason))

        if action == "timeout":
            self.duration = discord.ui.TextInput(
                label="Duration",
                placeholder="Examples: 10m, 1h, 2d, 1w",
                max_length=20,
            )
            self.add_item(discord.ui.Label(text="Duration", component=self.duration))
        else:
            self.duration = None

        if action == "blacklist":
            self.categories = discord.ui.TextInput(
                label="Blacklist categories",
                placeholder="tickets, code_sharing, exalted, creations",
                default="tickets",
                max_length=100,
            )
            self.add_item(discord.ui.Label(text="Blacklist categories", component=self.categories))
        else:
            self.categories = None

        if action == "ban":
            self.delete_messages = discord.ui.TextInput(
                label="Delete last 7 days of messages? (yes/no)",
                default="no",
                max_length=3,
            )
            self.add_item(discord.ui.Label(text="Delete messages", component=self.delete_messages))
        else:
            self.delete_messages = None

        self.evidence_upload = discord.ui.FileUpload(
            min_values=1,
            max_values=5,
            required=True,
        )
        self.add_item(
            discord.ui.Label(
                text="Evidence files",
                description="Upload at least one evidence file.",
                component=self.evidence_upload,
            )
        )

    async def on_submit(self, interaction):
        if interaction.user.id != self.moderator_id or not has_permission(interaction.user, ALLOWED_ROLES):
            await interaction.response.send_message(
                "You are not authorized to submit this moderation action.",
                ephemeral=True,
            )
            return

        if interaction.guild is None:
            await interaction.response.send_message(
                "This moderation action must be submitted in a server.",
                ephemeral=True,
            )
            return

        reason = self.reason.value.strip()
        if not reason:
            await interaction.response.send_message("Please provide a reason.", ephemeral=True)
            return

        evidence = self.evidence_upload.values
        if not evidence:
            await interaction.response.send_message(
                "Please upload at least one evidence file.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)
        try:
            target_member = interaction.guild.get_member(self.target.id)
            if target_member is None and self.action != "ban":
                target_member = await interaction.guild.fetch_member(self.target.id)

            if self.action == "timeout":
                timeout_until = parse_duration(self.duration.value)
                if timeout_until in (None, "invalid"):
                    await interaction.followup.send(
                        "Invalid timeout duration. Use 10m, 1h, 2d, or 1w.",
                        ephemeral=True,
                    )
                    return
                duration = self.duration.value.strip()
                await target_member.timeout(
                    timeout_until,
                    reason=f"Timed out by {interaction.user}: {reason}",
                )
                action_type = "Timed Out"
                await notify_user_dm(
                    target_member,
                    action_type,
                    interaction.guild.name,
                    interaction.user,
                    reason=reason,
                    duration=duration,
                )
            elif self.action == "ban":
                delete_messages = self.delete_messages.value.strip().lower()
                if delete_messages not in {"yes", "no"}:
                    await interaction.followup.send(
                        "Choose `yes` or `no` for deleting the user's last 7 days of messages.",
                        ephemeral=True,
                    )
                    return
                await notify_user_dm(
                    self.target,
                    "Banned",
                    interaction.guild.name,
                    interaction.user,
                    reason=reason,
                )
                await interaction.guild.ban(
                    self.target,
                    reason=f"Banned by {interaction.user}: {reason}",
                    delete_message_days=7 if delete_messages == "yes" else 0,
                )
                action_type = "Banned"
                duration = None
            elif self.action == "kick":
                await interaction.guild.kick(
                    target_member,
                    reason=f"Kicked by {interaction.user}: {reason}",
                )
                action_type = "Kicked"
                duration = None
                await notify_user_dm(
                    target_member,
                    action_type,
                    interaction.guild.name,
                    interaction.user,
                    reason=reason,
                )
            else:
                selected_categories = get_requested_blacklist_categories(
                    self.categories.value.split(",")
                )
                if not selected_categories:
                    await interaction.followup.send(
                        "Select at least one valid blacklist category: tickets, code_sharing, exalted, creations.",
                        ephemeral=True,
                    )
                    return

                missing_roles = [
                    BLACKLIST_ROLE_NAMES[category]
                    for category in selected_categories
                    if discord.utils.get(
                        interaction.guild.roles,
                        name=BLACKLIST_ROLE_NAMES[category],
                    ) is None
                ]
                if missing_roles:
                    await interaction.followup.send(
                        f"Create the required role(s) first: {', '.join(missing_roles)}.",
                        ephemeral=True,
                    )
                    return
                await apply_blacklist_roles(
                    interaction.guild,
                    target_member,
                    selected_categories,
                    reason,
                    interaction.user,
                )
                category_names = [
                    BLACKLIST_CATEGORY_LABELS[category]
                    for category in selected_categories
                ]
                reason = f"{', '.join(category_names)}: {reason}"
                action_type = "Blacklisted"
                duration = None
                await notify_user_dm(
                    target_member,
                    action_type,
                    interaction.guild.name,
                    interaction.user,
                    reason=reason,
                )

            evidence_message = SimpleNamespace(
                attachments=evidence,
                content=f"/moderate {self.target} {self.action} {reason}",
                author=interaction.user,
                channel=interaction.channel,
                mentions=[self.target],
                guild=interaction.guild,
            )
            await log_action(
                interaction.client,
                evidence_message,
                action_type,
                interaction.user,
                reason,
                duration,
            )
            await interaction.followup.send(
                f"✅ {action_type} action applied to {self.target.mention}.",
                ephemeral=True,
            )
        except discord.NotFound:
            await interaction.followup.send(
                "The target user is no longer a member of this server.",
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "The bot does not have permission to perform this action.",
                ephemeral=True,
            )
        except discord.HTTPException:
            logging.exception(
                "Discord rejected %s action for user %s",
                self.action,
                self.target.id,
            )
            await interaction.followup.send(
                "Discord rejected the moderation action. No success was recorded.",
                ephemeral=True,
            )
        except ValueError as exc:
            await interaction.followup.send(f"❌ {exc}", ephemeral=True)
        except Exception:
            logging.exception(
                "Unexpected error applying %s action for user %s",
                self.action,
                self.target.id,
            )
            await interaction.followup.send(
                "An unexpected error occurred; check the bot logs.",
                ephemeral=True,
            )


class ModerateActionSelect(discord.ui.Select):
    def __init__(self, target, moderator_id):
        self.target = target
        self.moderator_id = moderator_id
        super().__init__(
            placeholder="Choose a moderation action",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label="Timeout", value="timeout"),
                discord.SelectOption(label="Ban", value="ban"),
                discord.SelectOption(label="Kick", value="kick"),
                discord.SelectOption(label="Blacklist", value="blacklist"),
            ],
        )

    async def callback(self, interaction):
        if interaction.user.id != self.moderator_id or not has_permission(interaction.user, ALLOWED_ROLES):
            await interaction.response.send_message(
                "You are not authorized to choose an action for this moderation session.",
                ephemeral=True,
            )
            return
        await interaction.response.send_modal(
            ModerateActionModal(self.target, self.values[0], self.moderator_id)
        )


class ModerateActionView(discord.ui.View):
    def __init__(self, target, moderator_id):
        super().__init__(timeout=180)
        self.add_item(ModerateActionSelect(target, moderator_id))

    async def interaction_check(self, interaction):
        if interaction.user.id == self.children[0].moderator_id:
            return True
        await interaction.response.send_message(
            "This private moderation session belongs to another moderator.",
            ephemeral=True,
        )
        return False


def register_moderation_history_commands(bot):
    if getattr(bot, "_moderation_history_commands_setup", False):
        return

    @app_commands.command(name="moderate", description="Review history and moderate a user")
    @app_commands.describe(user="The user whose moderation history you want to review")
    async def moderate(interaction: discord.Interaction, user: discord.User):
        if not has_permission(interaction.user, ALLOWED_ROLES):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True,
            )
            return
        if interaction.guild is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        try:
            actions = find_actions(interaction.guild.id, user.id)
            await interaction.response.send_message(
                embed=_history_embed(user, actions),
                view=ModerateActionView(user, interaction.user.id),
                ephemeral=True,
            )
        except Exception:
            logging.exception("Failed to retrieve moderation history for user %s", user.id)
            await interaction.response.send_message(
                "Failed to retrieve moderation history. Check the bot logs.",
                ephemeral=True,
            )

    if bot.tree.get_command("moderate") is None:
        bot.tree.add_command(moderate)

    @app_commands.command(
        name="index_moderation_history",
        description="Import past moderation actions from the moderation log channel",
    )
    async def index_moderation_history(interaction: discord.Interaction):
        if interaction.user.id != MODERATION_INDEXER_USER_ID:
            await interaction.response.send_message(
                "Only the configured history indexer may run this command.",
                ephemeral=True,
            )
            return
        if interaction.guild is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)
        try:
            if history_was_indexed(interaction.guild.id):
                await interaction.followup.send(
                    "Moderation history has already been indexed for this server.",
                    ephemeral=True,
                )
                return

            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            if log_channel is None:
                log_channel = await bot.fetch_channel(LOG_CHANNEL_ID)
            if not hasattr(log_channel, "history") or log_channel.guild.id != interaction.guild.id:
                await interaction.followup.send(
                    "The configured moderation log channel is unavailable in this server.",
                    ephemeral=True,
                )
                return

            indexed_count = 0
            scanned_count = 0
            async for log_message in log_channel.history(limit=None, oldest_first=True):
                scanned_count += 1
                for embed in log_message.embeds:
                    indexed_count += int(
                        index_log_embed(embed, interaction.guild.id, log_message.id)
                    )

            finish_history_index(interaction.guild.id, discord.utils.utcnow())
            await interaction.followup.send(
                f"✅ Indexed {indexed_count} moderation action(s) from "
                f"{scanned_count} log message(s). Future actions are saved automatically.",
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "The bot needs permission to view the moderation log channel and read its history.",
                ephemeral=True,
            )
        except discord.HTTPException:
            logging.exception("Discord failed while indexing moderation history")
            await interaction.followup.send(
                "Discord failed while reading the log channel; the index was not marked complete.",
                ephemeral=True,
            )
        except Exception:
            logging.exception("Failed to index moderation history")
            await interaction.followup.send(
                "Failed to index moderation history; check the bot logs. You may retry the command.",
                ephemeral=True,
            )

    if bot.tree.get_command("index_moderation_history") is None:
        bot.tree.add_command(index_moderation_history)

    bot._moderation_history_commands_setup = True
