import discord
import asyncio
from discord import app_commands
from config import ALLOWED_ROLES, BLACKLIST_ROLE_NAMES
from utils import (
    has_permission, has_evidence, safe_send_message, log_action,
    notify_user_dm, ensure_evidence_provided, ask_yes_no_question,
    wait_for_user_response, delete_message_after_delay, parse_duration, parse_moderation_command
)

BLACKLIST_CATEGORY_LABELS = {
    "tickets": "Tickets",
    "code_sharing": "Code Sharing",
    "exalted": "Exalted",
    "creations": "Creations",
}

BLACKLIST_CATEGORY_ALIASES = {
    "tickets": "tickets",
    "ticket": "tickets",
    "code-sharing": "code_sharing",
    "code_sharing": "code_sharing",
    "codesharing": "code_sharing",
    "exalted": "exalted",
    "creations": "creations",
    "creation": "creations",
}


def get_requested_blacklist_categories(raw_values=None):
    """Convert a dict or iterable of category values into the canonical keys."""
    if raw_values is None:
        return []

    if isinstance(raw_values, dict):
        values = raw_values.items()
        selected = [key for key, enabled in values if enabled]
        return [BLACKLIST_CATEGORY_ALIASES.get(key.lower().replace('-', '_'), key.lower().replace('-', '_')) for key in selected]

    selected = []
    for value in raw_values:
        normalized = str(value).strip().lower().replace('-', '_')
        if normalized in BLACKLIST_CATEGORY_ALIASES:
            selected.append(BLACKLIST_CATEGORY_ALIASES[normalized])
        elif normalized in BLACKLIST_ROLE_NAMES:
            selected.append(normalized)
    return list(dict.fromkeys(selected))


async def apply_blacklist_roles(guild, user, selected_categories, reason, moderator):
    """Assign the matching blacklist roles to a member and return the list of applied roles."""
    assigned = []
    for category in selected_categories:
        role_name = BLACKLIST_ROLE_NAMES[category]
        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            raise ValueError(f"Role '{role_name}' not found in this server.")

        if role in user.roles:
            continue

        await user.add_roles(role, reason=f"{BLACKLIST_CATEGORY_LABELS.get(category, category.title())} blacklist by {moderator}: {reason}")
        assigned.append(role)

    return assigned

async def collect_additional_evidence(bot, interaction, initial_evidence):
    """Helper function to collect additional evidence after a slash command"""
    evidence_attachments = [initial_evidence] if initial_evidence else []
    evidence_messages_to_delete = []  # Track messages with evidence to delete later
    
    if not initial_evidence:
        return evidence_attachments, evidence_messages_to_delete
    
    # Ask if they want to add more evidence
    await interaction.followup.send(
        f"📎 Evidence received: `{initial_evidence.filename}`\n\n"
        "**Do you want to add more evidence?**\n"
        "• Send additional images/files in this channel within the next 30 seconds\n"
        "• Type `done` when finished\n"
        "• Type `proceed` to continue with just the current evidence",
        ephemeral=True
    )
    
    # Wait for additional evidence
    additional_evidence = []
    timeout_time = 30  # 30 seconds to add more evidence
    start_time = asyncio.get_event_loop().time()
    
    def check_additional_evidence(msg):
        return (msg.author == interaction.user and 
                msg.channel == interaction.channel and
                msg.created_at.timestamp() > start_time)
    
    while (asyncio.get_event_loop().time() - start_time) < timeout_time:
        try:
            additional_msg = await bot.wait_for('message', check=check_additional_evidence, timeout=5.0)
            
            if additional_msg.content.lower() in ['done', 'proceed', 'continue']:
                await additional_msg.delete()  # Clean up the command message immediately
                break
            elif additional_msg.attachments:
                additional_evidence.extend(additional_msg.attachments)
                evidence_messages_to_delete.append(additional_msg)  # Mark for deletion later
                await additional_msg.add_reaction('✅')  # Confirm we got the evidence
                await interaction.followup.send(
                    f"✅ Added {len(additional_msg.attachments)} more evidence file(s). "
                    f"Total: {len(evidence_attachments) + len(additional_evidence)} files.\n"
                    "Send more or type `done` to proceed.",
                    ephemeral=True
                )
            
        except asyncio.TimeoutError:
            continue  # Keep checking until the total timeout
    
    # Combine all evidence
    evidence_attachments.extend(additional_evidence)
    
    if additional_evidence:
        await interaction.followup.send(
            f"📎 **Final evidence count:** {len(evidence_attachments)} files collected.",
            ephemeral=True
        )
    
    return evidence_attachments, evidence_messages_to_delete

async def cleanup_evidence_messages(evidence_messages_to_delete, delay=3):
    """Clean up evidence messages after successful logging"""
    if not evidence_messages_to_delete:
        return
    
    print(f"🧹 Cleaning up {len(evidence_messages_to_delete)} evidence messages in {delay} seconds...")
    await asyncio.sleep(delay)  # Short delay to ensure logging is complete
    
    for msg in evidence_messages_to_delete:
        try:
            await msg.delete()
            print(f"🗑️ Deleted evidence message: {msg.id}")
        except discord.NotFound:
            print(f"⚠️ Evidence message {msg.id} was already deleted")
        except discord.Forbidden:
            print(f"❌ No permission to delete evidence message: {msg.id}")
        except Exception as e:
            print(f"❌ Error deleting evidence message {msg.id}: {e}")

async def setup_moderation_commands(bot):
    """Setup slash commands for moderation.

    This function is intentionally idempotent: re-running it on the same bot instance
    should not attempt to re-register the same slash commands, which leads to
    'Command ... already registered' errors during !synccommands.
    """
    if not hasattr(bot, "_moderation_commands_setup"):
        bot._moderation_commands_setup = False

    if bot._moderation_commands_setup:
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
        evidence: discord.Attachment = None
    ):
        """Slash command for banning users"""
        await interaction.response.defer(ephemeral=True)
        
        # Check permissions
        if not has_permission(interaction.user, ALLOWED_ROLES):
            await interaction.followup.send("❌ You don't have permission to use this command.", ephemeral=True)
            return
        
        # Handle evidence - collect initial and additional evidence
        evidence_attachments, evidence_messages_to_delete = await collect_additional_evidence(bot, interaction, evidence)
        
        if not evidence_attachments:
            await interaction.followup.send("❌ Please provide evidence (image or attachment) for the ban.", ephemeral=True)
            return
        
        # Create a mock message object with all evidence
        evidence_msg = type('MockMessage', (), {
            'attachments': evidence_attachments,
            'content': f"/ban {user.mention} {reason}",
            'author': interaction.user,
            'channel': interaction.channel,
            'mentions': [user],  # Add the target user to mentions
            'jump_url': f"https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}/slash_command"
        })()
        
        try:
            # Log the action (use the evidence message for logging)
            await log_action(bot, evidence_msg, "Banned", interaction.user, reason)
            
            # Send DM notification to user before banning
            dm_sent = await notify_user_dm(
                user, 
                "Banned", 
                interaction.guild.name, 
                interaction.user, 
                reason=reason
            )
            
            # Perform the ban
            delete_message_days = 7 if delete_messages else 0
            await interaction.guild.ban(
                user, 
                reason=f"Banned by {interaction.user}: {reason}",
                delete_message_days=delete_message_days
            )
            
            dm_status = " (DM sent)" if dm_sent else " (DM failed - user may have DMs disabled)"
            delete_status = f" Messages from last 7 days deleted." if delete_messages else ""
            await interaction.followup.send(f"✅ {user.mention} has been banned!{dm_status}{delete_status}")
            
            # Clean up evidence messages after successful ban and logging
            await cleanup_evidence_messages(evidence_messages_to_delete)
            
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to ban this user.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send("❌ Failed to ban the user.", ephemeral=True)
        except Exception as e:
            print(f"Ban failed: Unexpected error - {e}")
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
        evidence: discord.Attachment = None
    ):
        """Slash command for kicking users"""
        await interaction.response.defer(ephemeral=True)
        
        # Check permissions
        if not has_permission(interaction.user, ALLOWED_ROLES):
            await interaction.followup.send("❌ You don't have permission to use this command.", ephemeral=True)
            return
        
        # Handle evidence - collect initial and additional evidence
        evidence_attachments, evidence_messages_to_delete = await collect_additional_evidence(bot, interaction, evidence)
        
        if not evidence_attachments:
            await interaction.followup.send("❌ Please provide evidence (image or attachment) for the kick.", ephemeral=True)
            return
        
        # Create a mock message object with all evidence
        evidence_msg = type('MockMessage', (), {
            'attachments': evidence_attachments,
            'content': f"/kick {user.mention} {reason}",
            'author': interaction.user,
            'channel': interaction.channel,
            'mentions': [user],  # Add the target user to mentions
            'jump_url': f"https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}/slash_command"
        })()
        
        try:
            # Log the action
            await log_action(bot, evidence_msg, "Kicked", interaction.user, reason)
            
            # Send DM notification to user before kicking
            dm_sent = await notify_user_dm(
                user, 
                "Kicked", 
                interaction.guild.name, 
                interaction.user, 
                reason=reason
            )
            
            # Perform the kick
            await interaction.guild.kick(user, reason=f"Kicked by {interaction.user}: {reason}")
            
            dm_status = " (DM sent)" if dm_sent else " (DM failed - user may have DMs disabled)"
            await interaction.followup.send(f"✅ {user.mention} has been kicked!{dm_status}")
            
            # Clean up evidence messages after successful kick and logging
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
        evidence: discord.Attachment = None
    ):
        """Slash command for timing out users"""
        await interaction.response.defer(ephemeral=True)
        
        # Check permissions
        if not has_permission(interaction.user, ALLOWED_ROLES):
            await interaction.followup.send("❌ You don't have permission to use this command.", ephemeral=True)
            return
        
        # Parse duration
        timeout_duration = parse_duration(duration)
        if timeout_duration == "invalid" or timeout_duration is None:
            await interaction.followup.send("❌ Invalid duration format. Use 10m, 1h, 2d, or 1w", ephemeral=True)
            return
        
        # Handle evidence - collect initial and additional evidence
        evidence_attachments, evidence_messages_to_delete = await collect_additional_evidence(bot, interaction, evidence)
        
        if not evidence_attachments:
            await interaction.followup.send("❌ Please provide evidence (image or attachment) for the timeout.", ephemeral=True)
            return
        
        # Create a mock message object with all evidence
        evidence_msg = type('MockMessage', (), {
            'attachments': evidence_attachments,
            'content': f"/timeout {user.mention} {duration} {reason}",
            'author': interaction.user,
            'channel': interaction.channel,
            'mentions': [user],  # Add the target user to mentions
            'jump_url': f"https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}/slash_command"
        })()
        
        try:
            # Log the action
            await log_action(bot, evidence_msg, "Timed out", interaction.user, reason, duration)
            
            # Send DM notification to user before timeout
            dm_sent = await notify_user_dm(
                user, 
                "Timed out", 
                interaction.guild.name, 
                interaction.user, 
                reason=reason,
                duration=duration
            )
            
            # Perform the timeout
            await user.timeout(timeout_duration, reason=f"Timed out by {interaction.user}: {reason}")
            
            dm_status = " (DM sent)" if dm_sent else " (DM failed - user may have DMs disabled)"
            await interaction.followup.send(f"✅ {user.mention} has been timed out for {duration}!{dm_status}")
            
            # Clean up evidence messages after successful timeout and logging
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
        evidence: discord.Attachment = None
    ):
        """Slash command for blacklisting a user from one or more categories."""
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
                ephemeral=True
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
                reason=f"{blacklist_summary}: {reason}"
            )

            await apply_blacklist_roles(interaction.guild, user, selected_categories, reason, interaction.user)

            dm_status = " (DM sent)" if dm_sent else " (DM failed - user may have DMs disabled)"
            await interaction.followup.send(f"✅ {user.mention} has been blacklisted for: **{blacklist_summary}**{dm_status}")
            await cleanup_evidence_messages(evidence_messages_to_delete)

        except ValueError as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to manage roles for this user.", ephemeral=True)
        except discord.HTTPException:
            await interaction.followup.send("❌ Failed to apply the blacklist roles.", ephemeral=True)

    bot._moderation_commands_setup = True

    @bot.tree.command(name="unban", description="Unban a user from the server")
    @app_commands.describe(
        user_id="The ID of the user to unban",
        reason="Reason for the unban"
    )
    async def slash_unban(interaction: discord.Interaction, user_id: str, reason: str):
        if not has_permission(interaction.user):
            await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            user_obj = await bot.fetch_user(int(user_id))
            await interaction.guild.unban(user_obj, reason=reason)
            
            await log_action(interaction.guild, interaction.user, user_obj, "Unban", reason)
            await interaction.followup.send(f"✅ **{user_obj.name}** has been unbanned.\nReason: {reason}")
            
        except ValueError:
             await interaction.followup.send("❌ Invalid User ID provided.", ephemeral=True)
        except discord.NotFound:
            await interaction.followup.send("❌ User not found or not banned.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to unban user: {e}", ephemeral=True)

    @bot.tree.command(name="untimeout", description="Remove timeout from a user")
    @app_commands.describe(
        user="The user to untimeout",
        reason="Reason for removing timeout"
    )
    async def slash_untimeout(interaction: discord.Interaction, user: discord.Member, reason: str):
        if not has_permission(interaction.user):
            await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            if not user.is_timed_out():
                await interaction.followup.send(f"⚠️ **{user.name}** is not currently timed out.", ephemeral=True)
                return

            await user.timeout(None, reason=reason)
            
            # Notify user
            await notify_user_dm(user, "Timeout Removed", interaction.guild.name, interaction.user, reason)
            
            await log_action(interaction.guild, interaction.user, user, "Untimeout", reason)
            await interaction.followup.send(f"✅ **{user.name}**'s timeout has been removed.\nReason: {reason}")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to remove timeout: {e}", ephemeral=True)


# Keep existing message-based commands for backward compatibility
async def handle_ban_command(client, message):
    """Handle the !ban command
    
    Single-line format: !ban @user yes/no reason
    Interactive format: !ban (then follow prompts)
    """
    if not has_permission(message.author, ALLOWED_ROLES):
        return
    
    # Try to parse arguments from the original message
    parsed_args = parse_moderation_command(message.content)
    
    if parsed_args and len(parsed_args) == 3:
        # Single-line format: ?ban @user yes/no reason
        user_mention, delete_messages, ban_reason = parsed_args
        
        # Find the user from the mention
        if not message.mentions:
            await message.channel.send("❌ Please mention a valid user to ban.")
            return
        
        user_to_ban = message.mentions[0]
        
        # Check if the original message has evidence
        if not has_evidence(message):
            await message.channel.send("❌ Please provide a link or image as evidence in your ban command.")
            return
        
        evidence_message = message
        delete_message_days = 7 if delete_messages else 0
        
    else:
        # Interactive format
        await message.channel.send("Who do you want to ban? Please mention them and attach evidence.")
        
        try:
            next_message = await wait_for_user_response(client, message)
            
            if not next_message.mentions:
                await message.channel.send("❌ Please mention a valid user to ban.")
                return
            
            user_to_ban = next_message.mentions[0]
            
            # Ensure evidence is provided (give second chance if missing)
            evidence_message = await ensure_evidence_provided(client, message, next_message)
            if not evidence_message:
                return  # Command was cancelled due to lack of evidence
            
            # Ask for reason
            await message.channel.send("Please provide a reason for the ban:")
            
            reason_message = await wait_for_user_response(client, message)
            ban_reason = reason_message.content.strip()
            
            # Ask if they want to delete user's messages
            delete_messages = await ask_yes_no_question(client, message, "Do you want to delete the user's messages from the last 7 days?")
            
            # Determine delete_message_days parameter
            delete_message_days = 7 if delete_messages else 0
            
        except asyncio.TimeoutError:
            await message.channel.send("You took too long to respond!")
            return
    
    # Common ban logic for both formats
    try:
        # Log the action (use the evidence message for logging)
        await log_action(client, evidence_message, "Banned", message.author, ban_reason)
        
        # Send DM notification to user before banning
        dm_sent = await notify_user_dm(
            user_to_ban, 
            "Banned", 
            message.guild.name, 
            message.author, 
            reason=ban_reason
        )
        
        # Perform the ban
        await message.guild.ban(
            user_to_ban, 
            reason=f"Banned by {message.author}: {ban_reason}",
            delete_message_days=delete_message_days
        )
        dm_status = " (DM sent)" if dm_sent else " (DM failed - user may have DMs disabled)"
        delete_status = f" Messages from last 7 days deleted." if delete_messages else ""
        await message.channel.send(f"✅ {user_to_ban.mention} has been banned!{dm_status}{delete_status}")
        
        # Clean up evidence message after successful ban and logging (but not the original command message)
        if evidence_message != message and evidence_message.attachments:
            await cleanup_evidence_messages([evidence_message], delay=5)
            
    except discord.Forbidden:
        await message.channel.send("❌ I don't have permission to ban this user.")
    except discord.HTTPException:
        await message.channel.send("❌ Failed to ban the user.")





async def handle_kick_command(client, message):
    """Handle the !kick command
    
    Single-line format: !kick @user reason
    Interactive format: !kick (then follow prompts)
    """
    if not has_permission(message.author, ALLOWED_ROLES):
        return
    
    # Try to parse arguments from the original message
    parsed_args = parse_moderation_command(message.content)
    
    if parsed_args and len(parsed_args) == 2:
        # Single-line format: ?kick @user reason
        user_mention, kick_reason = parsed_args
        
        # Find the user from the mention
        if not message.mentions:
            await message.channel.send("❌ Please mention a valid user to kick.")
            return
        
        user_to_kick = message.mentions[0]
        
        # Check if the original message has evidence
        if not has_evidence(message):
            await message.channel.send("❌ Please provide a link or image as evidence in your kick command.")
            return
        
        evidence_message = message
        
    else:
        # Interactive format
        await message.channel.send("Who do you want to kick? Please mention them and attach evidence.")
        
        try:
            next_message = await wait_for_user_response(client, message)
            
            if not next_message.mentions:
                await message.channel.send("❌ Please mention a valid user to kick.")
                return
            
            user_to_kick = next_message.mentions[0]
            
            # Ensure evidence is provided (give second chance if missing)
            evidence_message = await ensure_evidence_provided(client, message, next_message)
            if not evidence_message:
                return  # Command was cancelled due to lack of evidence
            
            # Ask for reason
            await message.channel.send("Please provide a reason for the kick:")
            
            reason_message = await wait_for_user_response(client, message)
            kick_reason = reason_message.content.strip()
            
        except asyncio.TimeoutError:
            await message.channel.send("You took too long to respond!")
            return
    
    # Common kick logic for both formats
    try:
        # Log the action (use the evidence message for logging)
        await log_action(client, evidence_message, "Kicked", message.author, kick_reason)
        
        # Send DM notification to user before kicking
        dm_sent = await notify_user_dm(
            user_to_kick, 
            "Kicked", 
            message.guild.name, 
            message.author, 
            reason=kick_reason
        )
        
        # Perform the kick
        await message.guild.kick(user_to_kick, reason=f"Kicked by {message.author}: {kick_reason}")
        dm_status = " (DM sent)" if dm_sent else " (DM failed - user may have DMs disabled)"
        await message.channel.send(f"✅ {user_to_kick.mention} has been kicked!{dm_status}")
        
        # Clean up evidence message after successful kick and logging (but not the original command message)
        if evidence_message != message and evidence_message.attachments:
            await cleanup_evidence_messages([evidence_message], delay=5)
            
    except discord.Forbidden:
        await message.channel.send("❌ I don't have permission to kick this user.")
    except discord.HTTPException:
        await message.channel.send("❌ Failed to kick the user.")





async def handle_timeout_command(client, message):
    """Handle the !timeout command
    
    Single-line format: !timeout @user 1h reason
    Interactive format: !timeout (then follow prompts)
    """
    if not has_permission(message.author, ALLOWED_ROLES):
        return
    
    # Try to parse arguments from the original message
    parsed_args = parse_moderation_command(message.content)
    
    if parsed_args and len(parsed_args) == 3:
        # Single-line format: ?timeout @user duration reason
        user_mention, duration_text, timeout_reason = parsed_args
        
        # Find the user from the mention
        if not message.mentions:
            await message.channel.send("❌ Please mention a valid user to timeout.")
            return
        
        user_to_timeout = message.mentions[0]
        
        # Parse duration
        timeout_duration = parse_duration(duration_text)
        if timeout_duration == "invalid" or timeout_duration is None:
            await message.channel.send("❌ Invalid duration format. Use 10m, 1h, 2d, or 1w")
            return
        
        # Check if the original message has evidence
        if not has_evidence(message):
            await message.channel.send("❌ Please provide a link or image as evidence in your timeout command.")
            return
        
        evidence_message = message
        
    else:
        # Interactive format
        await message.channel.send("Who do you want to timeout? Please mention them and attach evidence.")
        
        try:
            next_message = await wait_for_user_response(client, message)
            
            if not next_message.mentions:
                await message.channel.send("❌ Please mention a valid user to timeout.")
                return
            
            user_to_timeout = next_message.mentions[0]
            
            # Ensure evidence is provided (give second chance if missing)
            evidence_message = await ensure_evidence_provided(client, message, next_message)
            if not evidence_message:
                return  # Command was cancelled due to lack of evidence
            
            # Ask for duration
            await message.channel.send("How long should the timeout be? (e.g., 10m, 1h, 2d, 1w)")
            
            duration_message = await wait_for_user_response(client, message)
            timeout_duration = parse_duration(duration_message.content)
            duration_text = duration_message.content.lower().strip()
            
            if timeout_duration == "invalid" or timeout_duration is None:
                await message.channel.send("❌ Invalid duration format. Use 10m, 1h, 2d, or 1w")
                return
            
            # Ask for reason
            await message.channel.send("Please provide a reason for the timeout:")
            
            reason_message = await wait_for_user_response(client, message)
            timeout_reason = reason_message.content.strip()
            
        except asyncio.TimeoutError:
            await message.channel.send("You took too long to respond!")
            return
    
    # Common timeout logic for both formats
    try:
        # Log the action (use the evidence message for logging)
        await log_action(client, evidence_message, "Timed out", message.author, timeout_reason, duration_text)
        
        # Send DM notification to user before timeout
        dm_sent = await notify_user_dm(
            user_to_timeout, 
            "Timed out", 
            message.guild.name, 
            message.author, 
            reason=timeout_reason,
            duration=duration_text
        )
        
        # Perform the timeout
        await user_to_timeout.timeout(timeout_duration, reason=f"Timed out by {message.author}: {timeout_reason}")
        dm_status = " (DM sent)" if dm_sent else " (DM failed - user may have DMs disabled)"
        await message.channel.send(f"✅ {user_to_timeout.mention} has been timed out for {duration_text}{dm_status}")
        
        # Clean up evidence message after successful timeout and logging (but not the original command message)
        if evidence_message != message and evidence_message.attachments:
            await cleanup_evidence_messages([evidence_message], delay=5)
            
    except discord.Forbidden:
        await message.channel.send("❌ I don't have permission to timeout this user.")
    except discord.HTTPException:
        await message.channel.send("❌ Failed to timeout the user.")


async def handle_blacklist_command(client, message):
    """Handle the !blacklist and !ticketblacklist commands.

    Supports selecting any number of blacklist categories using names such as
    tickets, code_sharing, exalted, and creations.
    """
    if not has_permission(message.author, ALLOWED_ROLES):
        return

    command = message.content.split()[0].lower()
    tokens = message.content.split()

    if not tokens or len(tokens) < 3:
        await message.channel.send("Usage: !blacklist @user [tickets|code_sharing|exalted|creations] <reason>")
        return

    mention = None
    selected_categories = []
    reason_tokens = []

    for token in tokens[1:]:
        if token.startswith('<@'):
            mention = token
            continue

        normalized = token.lower().replace('-', '_')
        if normalized in BLACKLIST_CATEGORY_ALIASES:
            selected_categories.append(BLACKLIST_CATEGORY_ALIASES[normalized])
            continue

        if normalized in BLACKLIST_ROLE_NAMES:
            selected_categories.append(normalized)
            continue

        reason_tokens.append(token)

    if not mention:
        await message.channel.send("❌ Please mention a valid user to blacklist.")
        return

    if not selected_categories:
        selected_categories = ["tickets"]

    if not reason_tokens:
        await message.channel.send("❌ Please provide a reason for the blacklist.")
        return

    user_to_blacklist = next((m for m in message.mentions if str(m.id) in mention.replace('<@', '').replace('>', '')), None)
    if user_to_blacklist is None and message.mentions:
        user_to_blacklist = message.mentions[0]
    if user_to_blacklist is None:
        await message.channel.send("❌ Please mention a valid user to blacklist.")
        return

    if not has_evidence(message):
        await message.channel.send("❌ Please provide a link or image as evidence in your blacklist command.")
        return

    selected_categories = list(dict.fromkeys(selected_categories))
    blacklist_reason = " ".join(reason_tokens)

    try:
        missing_roles = []
        for category in selected_categories:
            if not discord.utils.get(message.guild.roles, name=BLACKLIST_ROLE_NAMES[category]):
                missing_roles.append(BLACKLIST_ROLE_NAMES[category])

        if missing_roles:
            await message.channel.send(f"❌ Missing blacklist role(s): {', '.join(missing_roles)}. Create those roles first.")
            return

        await apply_blacklist_roles(message.guild, user_to_blacklist, selected_categories, blacklist_reason, message.author)

        category_names = [BLACKLIST_CATEGORY_LABELS.get(cat, cat.replace('_', ' ').title()) for cat in selected_categories]
        summary = ", ".join(category_names)

        await log_action(client, message, "Blacklisted", message.author, f"{summary}: {blacklist_reason}")

        dm_sent = await notify_user_dm(
            user_to_blacklist,
            "Blacklisted",
            message.guild.name,
            message.author,
            reason=f"{summary}: {blacklist_reason}"
        )

        dm_status = " (DM sent)" if dm_sent else " (DM failed - user may have DMs disabled)"
        await message.channel.send(f"✅ {user_to_blacklist.mention} has been blacklisted for: **{summary}**{dm_status}")

    except ValueError as e:
        await message.channel.send(f"❌ {e}")
    except discord.Forbidden:
        await message.channel.send("❌ I don't have permission to manage roles for this user.")
    except discord.HTTPException:
        await message.channel.send("❌ Failed to apply the blacklist roles.")


async def handle_ticketblacklist_command(client, message):
    """Backward-compatible alias for the generic blacklist command."""
    await handle_blacklist_command(client, message)
