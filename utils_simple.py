import discord
import asyncio
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
            name="� Target User", 
            value=f"{target_user.mention}\n({target_user.display_name})", 
            inline=True
        )
    
    embed.add_field(
        name="🛡️ Moderator", 
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
            name="📎 Evidence", 
            value=evidence_text, 
            inline=False
        )
    
    embed.set_footer(text=f"Action ID: {discord.utils.utcnow().strftime('%Y%m%d_%H%M%S')}")
    
    try:
        # Create ping content
        ping_content = ""
        if target_user:
            ping_content = f"**Moderation Alert:** {target_mention} {moderator.mention}"
        else:
            ping_content = f"**Moderation Alert:** {moderator.mention}"
        
        # Send embed with pings
        await log_channel.send(content=ping_content, embed=embed)
        print(f"✅ Sent embedded log message with pings")
        
        # Send evidence attachments if they exist
        if hasattr(message, 'attachments') and message.attachments:
            await asyncio.sleep(0.5)  # Small delay to avoid rate limits
            for i, attachment in enumerate(message.attachments):
                try:
                    # For now, just send the attachment URL with a descriptive message
                    # This preserves the evidence without complex file handling
                    await log_channel.send(
                        content=f"📎 **Evidence {i+1}:** {attachment.filename}\n{attachment.url}"
                    )
                    print(f"✅ Posted evidence link: {attachment.filename}")
                except Exception as e:
                    print(f"❌ Error posting attachment {attachment.filename}: {e}")
        
    except discord.Forbidden:
        print(f"❌ PERMISSION ERROR: Cannot send to log channel")
    except Exception as e:
        print(f"❌ LOGGING ERROR: {e}")
        import traceback
        traceback.print_exc()
