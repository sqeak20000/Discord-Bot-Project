import discord
import asyncio
from discord import app_commands
from config import ALLOWED_ROLES
from utils_simple import (
    has_permission, has_evidence, safe_send_message, log_action
)
from utils import (
    notify_user_dm, ensure_evidence_provided, ask_yes_no_question,
    wait_for_user_response, delete_message_after_delay, parse_duration, parse_moderation_command
)

async def collect_additional_evidence(bot, interaction, initial_evidence):
    """Helper function to collect additional evidence after a slash command"""
    evidence_attachments = [initial_evidence] if initial_evidence else []
    
    if not initial_evidence:
        return evidence_attachments
    
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
                await additional_msg.delete()  # Clean up the command message
                break
            elif additional_msg.attachments:
                additional_evidence.extend(additional_msg.attachments)
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
    
    return evidence_attachments

async def setup_moderation_commands(bot):
    """Setup slash commands for moderation"""
    
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
        evidence_attachments = await collect_additional_evidence(bot, interaction, evidence)
        
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
        evidence_attachments = await collect_additional_evidence(bot, interaction, evidence)
        
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
        evidence_attachments = await collect_additional_evidence(bot, interaction, evidence)
        
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
            
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to timeout this user.", ephemeral=True)
        except discord.HTTPException:
            await interaction.followup.send("❌ Failed to timeout the user.", ephemeral=True)


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
        
        # Delete the evidence message after delay (only if it's not the original command message)
        if evidence_message != message:
            await delete_message_after_delay(evidence_message)
            
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
        
        # Delete the evidence message after delay (only if it's not the original command message)
        if evidence_message != message:
            await delete_message_after_delay(evidence_message)
            
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
        
        # Delete the evidence message after delay (longer for timeout, only if it's not the original command message)
        if evidence_message != message:
            await delete_message_after_delay(evidence_message, delay=10)
            
    except discord.Forbidden:
        await message.channel.send("❌ I don't have permission to timeout this user.")
    except discord.HTTPException:
        await message.channel.send("❌ Failed to timeout the user.")
