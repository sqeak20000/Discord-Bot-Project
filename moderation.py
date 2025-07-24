import discord
import asyncio
from config import ALLOWED_ROLES
from utils import (
    has_permission, has_evidence, log_action, 
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
        
        if not has_evidence(next_message):
            await message.channel.send("❌ Please provide a link or image as evidence before banning.")
            return
        
        # Log the action
        await log_action(client, next_message, "Banned", message.author)
        
        # Perform the ban
        try:
            await message.guild.ban(user_to_ban, reason=f"Banned by {message.author}")
            await message.channel.send(f"✅ {user_to_ban.mention} has been banned!")
        except discord.Forbidden:
            await message.channel.send("❌ I don't have permission to ban this user.")
        except discord.HTTPException:
            await message.channel.send("❌ Failed to ban the user.")
        
        # Delete the evidence message after delay
        await delete_message_after_delay(next_message)
        
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
        
        if not has_evidence(next_message):
            await message.channel.send("❌ Please provide a link or image as evidence before kicking.")
            return
        
        # Log the action
        await log_action(client, next_message, "Kicked", message.author)
        
        # Perform the kick
        try:
            await message.guild.kick(user_to_kick, reason=f"Kicked by {message.author}")
            await message.channel.send(f"✅ {user_to_kick.mention} has been kicked!")
        except discord.Forbidden:
            await message.channel.send("❌ I don't have permission to kick this user.")
        except discord.HTTPException:
            await message.channel.send("❌ Failed to kick the user.")
        
        # Delete the evidence message after delay
        await delete_message_after_delay(next_message)
        
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
        
        if not has_evidence(next_message):
            await message.channel.send("❌ Please provide a link or image as evidence before timing out.")
            return
        
        # Ask for duration
        await message.channel.send("How long should the timeout be? (e.g., 10m, 1h, 2d, 1w)")
        
        duration_message = await wait_for_user_response(client, message)
        timeout_duration = parse_duration(duration_message.content)
        
        if not timeout_duration:
            await message.channel.send("❌ Invalid duration format. Use 10m, 1h, 2d, or 1w")
            return
        
        # Log the action
        await log_action(client, next_message, "Timed out", message.author)
        
        # Perform the timeout
        try:
            await user_to_timeout.timeout(timeout_duration, reason=f"Timed out by {message.author}")
            await message.channel.send(f"✅ {user_to_timeout.mention} has been timed out for {duration_message.content.lower().strip()}")
        except discord.Forbidden:
            await message.channel.send("❌ I don't have permission to timeout this user.")
        except discord.HTTPException:
            await message.channel.send("❌ Failed to timeout the user.")
        
        # Delete the evidence message after delay (longer for timeout)
        await delete_message_after_delay(next_message, delay=10)
        
    except asyncio.TimeoutError:
        await message.channel.send("You took too long to respond!")
