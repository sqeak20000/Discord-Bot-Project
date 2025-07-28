import discord
import asyncio
import io
from datetime import timedelta
from config import LOG_CHANNEL_ID, COMMAND_TIMEOUT, MESSAGE_DELETE_DELAY, RATE_LIMIT_DELAY, RATE_LIMIT_RETRY_DELAY, ATTACHMENT_SEND_DELAY

async def safe_send_message(channel, content=None, embed=None, file=None):
    """Send a message with rate limit handling"""
    try:
        return await channel.send(content=content, embed=embed, file=file)
    except discord.HTTPException as e:
        if e.status == 429:  # Rate limited
            print(f"Rate limited when sending message, waiting...")
            await asyncio.sleep(RATE_LIMIT_RETRY_DELAY)
            try:
                return await channel.send(content=content, embed=embed, file=file)
            except:
                print(f"Failed to send message after retry")
                return None
        else:
            print(f"Error sending message: {e}")
            return None

def has_permission(user, allowed_roles):
    """Check if user has any of the allowed roles"""
    return any(role.name in allowed_roles for role in user.roles)

def has_evidence(message):
    """Check if message contains a link or attachment"""
    has_link = "http://" in message.content or "https://" in message.content
    has_attachment = len(message.attachments) > 0
    return has_link or has_attachment

async def log_action(client, message, action_type, moderator, reason=None, duration=None):
    """Log moderation action to the log channel with embeds and pings"""
    print(f"🔍 LOGGING: {action_type} by {moderator.display_name}")
    
    # Get log channel
    log_channel = client.get_channel(LOG_CHANNEL_ID)
    if not log_channel:
        print(f"❌ CRITICAL: Log channel {LOG_CHANNEL_ID} not found!")
        return
    
    print(f"✅ Found log channel: #{log_channel.name}")
    
    # Get target user
    target_user = None
    target_mention = ""
    if hasattr(message, 'mentions') and message.mentions:
        target_user = message.mentions[0]
        target_mention = target_user.mention
    
    # Create embed
    embed = discord.Embed(
        title=f"🔨 Moderation Action: {action_type.title()}",
        color=discord.Color.red() if action_type.lower() == "ban" else 
              discord.Color.orange() if action_type.lower() == "timeout" else 
              discord.Color.yellow(),
        timestamp=discord.utils.utcnow()
    )
    
    # Add fields
    if target_user:
        embed.add_field(
            name="👤 Target User", 
            value=f"{target_user.mention}\n({target_user.display_name})", 
            inline=True
        )
    
    embed.add_field(
        name="�️ Moderator", 
        value=f"{moderator.mention}\n({moderator.display_name})", 
        inline=True
    )
    
    if reason:
        embed.add_field(
            name="📝 Reason", 
            value=reason, 
            inline=False
        )
    
    if duration:
        embed.add_field(
            name="⏰ Duration", 
            value=duration, 
            inline=True
        )
    
    # Add evidence if available
    evidence_urls = []
    if hasattr(message, 'attachments') and message.attachments:
        evidence_urls.extend([att.url for att in message.attachments])
    
    # Check for links in message content
    if hasattr(message, 'content') and message.content:
        words = message.content.split()
        for word in words:
            if word.startswith(('http://', 'https://')):
                evidence_urls.append(word)
    
    if evidence_urls:
        evidence_text = "\n".join([f"• [Evidence {i+1}]({url})" for i, url in enumerate(evidence_urls)])
        embed.add_field(
            name="� Evidence", 
            value=evidence_text, 
            inline=False
        )
    
    embed.set_footer(text=f"Action ID: {discord.utils.utcnow().strftime('%Y%m%d_%H%M%S')}")
    
    try:
        # Send embed
        await log_channel.send(embed=embed)
        print(f"✅ Sent embedded log message")
        
        # Send evidence attachments if they exist (download and re-upload)
        if hasattr(message, 'attachments') and message.attachments:
            await asyncio.sleep(0.5)  # Small delay to avoid rate limits
            for i, attachment in enumerate(message.attachments):
                try:
                    # Download the attachment data
                    print(f"⬇️ Downloading attachment: {attachment.filename}")
                    attachment_data = await attachment.read()
                    
                    # Create a new Discord file object
                    discord_file = discord.File(
                        fp=io.BytesIO(attachment_data),
                        filename=f"evidence_{i+1}_{attachment.filename}"
                    )
                    
                    # Upload the file to the log channel
                    await log_channel.send(
                        content=f"📎 **Evidence {i+1}:** {attachment.filename}",
                        file=discord_file
                    )
                    print(f"✅ Re-uploaded attachment: {attachment.filename}")
                    
                except Exception as e:
                    print(f"❌ Error re-uploading attachment {attachment.filename}: {e}")
                    # Fallback to link if download/upload fails
                    try:
                        await log_channel.send(
                            content=f"📎 **Evidence {i+1} (fallback link):** {attachment.filename}\n{attachment.url}"
                        )
                        print(f"⚠️ Sent fallback link for: {attachment.filename}")
                    except Exception as fallback_error:
                        print(f"❌ Error sending fallback link: {fallback_error}")
        
    except discord.Forbidden:
        print(f"❌ PERMISSION ERROR: Cannot send to log channel")
    except Exception as e:
        print(f"❌ LOGGING ERROR: {e}")
        import traceback
        traceback.print_exc()

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
    except discord.HTTPException as e:
        if e.status == 429:  # Rate limited
            print(f"Rate limited when sending DM to {user.display_name}, waiting...")
            await asyncio.sleep(RATE_LIMIT_RETRY_DELAY)
            try:
                await user.send(embed=embed)
                return True
            except:
                print(f"Failed to send DM to {user.display_name} after retry")
                return False
        else:
            print(f"Error sending DM: {e}")
            return False

async def wait_for_user_response(client, original_message):
    """Wait for the next message from the same user in the same channel with rate limit handling"""
    def check(msg):
        return msg.author == original_message.author and msg.channel == original_message.channel
    
    try:
        return await client.wait_for('message', check=check, timeout=COMMAND_TIMEOUT)
    except discord.HTTPException as e:
        if e.status == 429:  # Rate limited
            print(f"Rate limited in wait_for_user_response, waiting...")
            await asyncio.sleep(RATE_LIMIT_DELAY)
        return None
    except asyncio.TimeoutError:
        await original_message.channel.send("Command timed out. Please try again.")
        return None

async def ask_yes_no_question(client, message, question):
    """Ask a yes/no question and return True for yes, False for no with rate limit handling"""
    try:
        await message.channel.send(f"{question} (yes/no)")
    except discord.HTTPException as e:
        if e.status == 429:  # Rate limited
            print(f"Rate limited when asking question, waiting...")
            await asyncio.sleep(RATE_LIMIT_DELAY)
            try:
                await message.channel.send(f"{question} (yes/no)")
            except:
                print(f"Failed to send question after retry")
                return None
    
    try:
        response = await wait_for_user_response(client, message)
        if response is None:
            return None
            
        answer = response.content.lower().strip()
        
        if answer in ['yes', 'y', 'true', '1']:
            return True
        elif answer in ['no', 'n', 'false', '0']:
            return False
        else:
            await message.channel.send("❌ Please answer with 'yes' or 'no'. Defaulting to 'no'.")
            return False
            
    except asyncio.TimeoutError:
        await message.channel.send("❌ You took too long to respond. Defaulting to 'no'.")
        return False

def parse_yes_no(text):
    """Parse a yes/no string and return True for yes, False for no"""
    text = text.lower().strip()
    return text in ['yes', 'y', 'true']

def parse_moderation_command(message_content):
    """Parse moderation command arguments from a single message
    
    Examples:
    - "!ban @user yes spamming chat" -> (user, True, "spamming chat")
    - "!kick @user being rude" -> (user, "being rude")
    - "!timeout @user 1h harassment" -> (user, "1h", "harassment")
    """
    parts = message_content.split()
    command = parts[0].lower()
    
    # Remove the command (first part)
    parts = parts[1:]
    
    if len(parts) < 2:  # Need at least: mention, reason
        return None
    
    # Extract user mention (first remaining part)
    user_mention = parts[0]
    if not user_mention.startswith('<@'):
        return None
    
    if command == '!ban':
        # Ban: mention, yes/no, reason
        if len(parts) < 3:  # Need: mention, yes/no, reason
            return None
        delete_messages = parse_yes_no(parts[1])
        reason = ' '.join(parts[2:])
        return user_mention, delete_messages, reason
        
    elif command == '!kick':
        # Kick: mention, reason (no message deletion option)
        reason = ' '.join(parts[1:])
        return user_mention, reason
        
    elif command == '!timeout':
        # Timeout: mention, duration, reason
        if len(parts) < 3:  # Need: mention, duration, reason
            return None
        duration = parts[1]
        reason = ' '.join(parts[2:])
        return user_mention, duration, reason
    
    return None

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
    """Parse duration string (e.g., '10m', '1h', '2d', '1w', 'permanent') into a datetime object"""
    duration_text = duration_text.lower().strip()
    
    if duration_text in ['permanent', 'perm', 'forever', 'never']:
        return None  # None indicates permanent ban
    elif duration_text.endswith('m'):
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
        return "invalid"  # Invalid format
