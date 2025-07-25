import discord
import asyncio
from config import ALLOWED_ROLES
from utils import (
    has_permission, has_evidence, log_action, notify_user_dm, ensure_evidence_provided,
    wait_for_user_response, delete_message_after_delay, parse_duration
)

async def handle_ban_command(client, message):
    """Handle the ?ban command"""
    if not has_permission(message.author, ALLOWED_ROLES):
        return
    
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
        try:
            await message.guild.ban(user_to_ban, reason=f"Banned by {message.author}: {ban_reason}")
            dm_status = " (DM sent)" if dm_sent else " (DM failed - user may have DMs disabled)"
            await message.channel.send(f"✅ {user_to_ban.mention} has been banned!{dm_status}")
        except discord.Forbidden:
            await message.channel.send("❌ I don't have permission to ban this user.")
        except discord.HTTPException:
            await message.channel.send("❌ Failed to ban the user.")
        
        # Delete the evidence message after delay
        await delete_message_after_delay(evidence_message)
        
    except asyncio.TimeoutError:
        await message.channel.send("You took too long to respond!")





async def handle_kick_command(client, message):
    """Handle the ?kick command"""
    if not has_permission(message.author, ALLOWED_ROLES):
        return
    
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
        try:
            await message.guild.kick(user_to_kick, reason=f"Kicked by {message.author}: {kick_reason}")
            dm_status = " (DM sent)" if dm_sent else " (DM failed - user may have DMs disabled)"
            await message.channel.send(f"✅ {user_to_kick.mention} has been kicked!{dm_status}")
        except discord.Forbidden:
            await message.channel.send("❌ I don't have permission to kick this user.")
        except discord.HTTPException:
            await message.channel.send("❌ Failed to kick the user.")
        
        # Delete the evidence message after delay
        await delete_message_after_delay(evidence_message)
        
    except asyncio.TimeoutError:
        await message.channel.send("You took too long to respond!")





async def handle_timeout_command(client, message):
    """Handle the ?timeout command"""
    if not has_permission(message.author, ALLOWED_ROLES):
        return
    
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
        
        if not timeout_duration:
            await message.channel.send("❌ Invalid duration format. Use 10m, 1h, 2d, or 1w")
            return
        
        # Ask for reason
        await message.channel.send("Please provide a reason for the timeout:")
        
        reason_message = await wait_for_user_response(client, message)
        timeout_reason = reason_message.content.strip()
        
        # Log the action (use the evidence message for logging)
        await log_action(client, evidence_message, "Timed out", message.author, timeout_reason)
        
        # Send DM notification to user before timeout
        dm_sent = await notify_user_dm(
            user_to_timeout, 
            "Timed out", 
            message.guild.name, 
            message.author, 
            reason=timeout_reason,
            duration=duration_message.content.lower().strip()
        )
        
        # Perform the timeout
        try:
            await user_to_timeout.timeout(timeout_duration, reason=f"Timed out by {message.author}: {timeout_reason}")
            dm_status = " (DM sent)" if dm_sent else " (DM failed - user may have DMs disabled)"
            await message.channel.send(f"✅ {user_to_timeout.mention} has been timed out for {duration_message.content.lower().strip()}{dm_status}")
        except discord.Forbidden:
            await message.channel.send("❌ I don't have permission to timeout this user.")
        except discord.HTTPException:
            await message.channel.send("❌ Failed to timeout the user.")
        
        # Delete the evidence message after delay (longer for timeout)
        await delete_message_after_delay(evidence_message, delay=10)
        
    except asyncio.TimeoutError:
        await message.channel.send("You took too long to respond!")
