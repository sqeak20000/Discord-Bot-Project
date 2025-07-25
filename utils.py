import discord
import asyncio
from datetime import timedelta
from config import LOG_CHANNEL_ID, COMMAND_TIMEOUT, MESSAGE_DELETE_DELAY

def has_permission(user, allowed_roles):
    """Check if user has any of the allowed roles"""
    return any(role.name in allowed_roles for role in user.roles)

def has_evidence(message):
    """Check if message contains a link or attachment"""
    has_link = "http://" in message.content or "https://" in message.content
    has_attachment = len(message.attachments) > 0
    return has_link or has_attachment

async def log_action(client, message, action_type, moderator, reason=None):
    """Log moderation action to the log channel"""
    log_channel = client.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        # Send the text content first with reason
        reason_text = f" - Reason: {reason}" if reason else ""
        await log_channel.send(f"{message.content} {action_type} by {moderator.mention} {reason_text}")
        
        # Send any attachments (images)
        for attachment in message.attachments:
            await log_channel.send(attachment)

async def notify_user_dm(user, action_type, guild_name, moderator, reason=None, duration=None):
    """Send a DM to the user informing them about the moderation action"""
    try:
        embed = discord.Embed(
            title=f"You have been {action_type.lower()}",
            color=discord.Color.red() if action_type.lower() in ["banned", "kicked"] else discord.Color.orange()
        )
        
        embed.add_field(name="Server", value=guild_name, inline=True)
        embed.add_field(name="Moderator", value=moderator.display_name, inline=True)
        
        if duration:
            embed.add_field(name="Duration", value=duration, inline=True)
        
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
        else:
            embed.add_field(name="Reason", value="No specific reason provided", inline=False)
        
        embed.set_footer(text="If you believe this action was taken in error, please contact server staff.")
        
        await user.send(embed=embed)
        return True  # Successfully sent DM
    except discord.Forbidden:
        # User has DMs disabled or blocked the bot
        return False
    except discord.HTTPException:
        # Other error sending DM
        return False

async def wait_for_user_response(client, original_message):
    """Wait for the next message from the same user in the same channel"""
    def check(msg):
        return msg.author == original_message.author and msg.channel == original_message.channel
    
    return await client.wait_for('message', check=check, timeout=COMMAND_TIMEOUT)

async def ensure_evidence_provided(client, message, evidence_message):
    """Ensure evidence is provided, give a second chance if missing"""
    if has_evidence(evidence_message):
        return evidence_message
    
    # No evidence found, give them a second chance
    await message.channel.send("❌ No evidence detected. Please send a message with a link or attachment as proof:")
    
    try:
        second_chance_message = await wait_for_user_response(client, message)
        
        if has_evidence(second_chance_message):
            return second_chance_message
        else:
            await message.channel.send("❌ Still no evidence provided. Command cancelled.")
            return None
            
    except asyncio.TimeoutError:
        await message.channel.send("❌ You took too long to provide evidence. Command cancelled.")
        return None

async def delete_message_after_delay(message, delay=MESSAGE_DELETE_DELAY):
    """Delete a message after a specified delay"""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except discord.Forbidden:
        pass  # Bot doesn't have permission to delete messages
    except discord.NotFound:
        pass  # Message was already deleted

def parse_duration(duration_text):
    """Parse duration string (e.g., '10m', '1h', '2d', '1w') into a datetime object"""
    duration_text = duration_text.lower().strip()
    
    if duration_text.endswith('m'):
        minutes = int(duration_text[:-1])
        return discord.utils.utcnow() + timedelta(minutes=minutes)
    elif duration_text.endswith('h'):
        hours = int(duration_text[:-1])
        return discord.utils.utcnow() + timedelta(hours=hours)
    elif duration_text.endswith('d'):
        days = int(duration_text[:-1])
        return discord.utils.utcnow() + timedelta(days=days)
    elif duration_text.endswith('w'):
        weeks = int(duration_text[:-1])
        return discord.utils.utcnow() + timedelta(weeks=weeks)
    else:
        return None
