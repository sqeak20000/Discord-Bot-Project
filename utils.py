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

async def log_action(client, message, action_type, moderator):
    """Log moderation action to the log channel"""
    log_channel = client.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        # Send the text content first
        await log_channel.send(f"{message.content} {action_type} by {moderator.mention}: ")
        
        # Send any attachments (images)
        for attachment in message.attachments:
            await log_channel.send(attachment)

async def wait_for_user_response(client, original_message):
    """Wait for the next message from the same user in the same channel"""
    def check(msg):
        return msg.author == original_message.author and msg.channel == original_message.channel
    
    return await client.wait_for('message', check=check, timeout=COMMAND_TIMEOUT)

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
