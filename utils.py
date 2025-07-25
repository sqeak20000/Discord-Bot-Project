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
    """Log moderation action to the log channel with embedded format"""
    try:
        print(f"🔍 Starting log_action: {action_type} by {moderator.display_name}")
        
        log_channel = client.get_channel(LOG_CHANNEL_ID)
        if not log_channel:
            print(f"❌ Error: Log channel {LOG_CHANNEL_ID} not found!")
            print(f"📋 Available channels: {[c.name for c in client.get_all_channels() if hasattr(c, 'name')][:10]}")
            return
        
        print(f"✅ Found log channel: #{log_channel.name}")
        
        # Determine embed color based on action type
        color_map = {
            "Banned": discord.Color.red(),
            "Kicked": discord.Color.orange(), 
            "Timed out": discord.Color.yellow(),
            "Warned": discord.Color.blue()
        }
        embed_color = color_map.get(action_type, discord.Color.gray())
        
        # Create the main embed
        embed = discord.Embed(
            title=f"🔨 User {action_type}",
            color=embed_color,
            timestamp=discord.utils.utcnow()
        )
        
        print(f"📝 Created embed with title: 🔨 User {action_type}")
        
        # Extract user mention from the message content or mentions
        target_user = None
        try:
            if hasattr(message, 'mentions') and message.mentions:
                target_user = message.mentions[0]
                embed.add_field(
                    name="👤 Target User", 
                    value=f"{target_user.mention}\n`{target_user.display_name}` (ID: {target_user.id})", 
                    inline=True
                )
                print(f"👤 Target user: {target_user.display_name}")
            else:
                # Fallback if no mentions found
                embed.add_field(name="👤 Target User", value="Unknown", inline=True)
                print("⚠️  No target user found in mentions")
        except Exception as e:
            print(f"❌ Error processing target user: {e}")
            embed.add_field(name="👤 Target User", value="Error retrieving user", inline=True)
        
        # Add moderator info
        try:
            embed.add_field(
                name="👮 Moderator", 
                value=f"{moderator.mention}\n`{moderator.display_name}`", 
                inline=True
            )
            print(f"👮 Moderator: {moderator.display_name}")
        except Exception as e:
            print(f"❌ Error processing moderator: {e}")
            embed.add_field(name="👮 Moderator", value="Unknown moderator", inline=True)
        
        # Add duration if applicable (for timeouts)
        if duration:
            embed.add_field(name="⏰ Duration", value=str(duration), inline=True)
            print(f"⏰ Duration: {duration}")
        
        # Add reason
        if reason:
            # Truncate reason if too long
            reason_text = str(reason)[:1000] if len(str(reason)) > 1000 else str(reason)
            embed.add_field(name="📝 Reason", value=reason_text, inline=False)
            print(f"📝 Reason: {reason_text}")
        else:
            embed.add_field(name="📝 Reason", value="No specific reason provided", inline=False)
            print("📝 No reason provided")
        
        # Add channel info safely
        try:
            if hasattr(message, 'channel') and message.channel:
                embed.add_field(
                    name="📍 Channel", 
                    value=f"{message.channel.mention} (`#{message.channel.name}`)", 
                    inline=True
                )
                print(f"📍 Channel: #{message.channel.name}")
        except Exception as e:
            print(f"❌ Error processing channel info: {e}")
            embed.add_field(name="📍 Channel", value="Unknown channel", inline=True)
        
        # Add original message link if available
        try:
            if hasattr(message, 'jump_url'):
                embed.add_field(
                    name="🔗 Original Message", 
                    value=f"[Jump to message]({message.jump_url})", 
                    inline=True
                )
                print("🔗 Added jump link")
        except Exception as e:
            print(f"❌ Error processing message link: {e}")
        
        # Set footer with moderator info
        try:
            embed.set_footer(
                text=f"Action performed by {moderator.display_name}",
                icon_url=moderator.display_avatar.url if moderator.display_avatar else None
            )
        except Exception as e:
            print(f"❌ Error setting footer: {e}")
            embed.set_footer(text="Moderation action performed")
        
        # Send the main embed
        print("📤 Attempting to send embed to log channel...")
        try:
            sent_message = await log_channel.send(embed=embed)
            print(f"✅ Successfully sent log embed! Message ID: {sent_message.id}")
        except discord.Forbidden:
            print("❌ Permission denied: Bot cannot send messages to log channel")
            return
        except discord.HTTPException as e:
            print(f"❌ HTTP Error sending embed: {e}")
            # Fallback to simple text message
            try:
                fallback_message = f"🔨 {action_type}: {target_user.mention if target_user else 'Unknown'} by {moderator.mention} - {reason or 'No reason'}"
                sent_fallback = await log_channel.send(fallback_message)
                print(f"✅ Sent fallback message instead: {sent_fallback.id}")
            except Exception as fallback_error:
                print(f"❌ Error sending fallback message: {fallback_error}")
                return
        except Exception as e:
            print(f"❌ Unexpected error sending embed: {e}")
            return
        
        # Send proof attachments separately with rate limiting (simplified)
        try:
            if hasattr(message, 'attachments') and message.attachments:
                print(f"📎 Processing {len(message.attachments)} attachments...")
                for i, attachment in enumerate(message.attachments):
                    if i > 0:  # Add delay between attachments
                        await asyncio.sleep(ATTACHMENT_SEND_DELAY)
                    
                    try:
                        att_message = await log_channel.send(f"📎 Evidence: {attachment.url}")
                        print(f"✅ Sent attachment {i+1}: {att_message.id}")
                    except Exception as attachment_error:
                        print(f"❌ Error sending attachment {i}: {attachment_error}")
            else:
                print("ℹ️  No attachments to process")
        except Exception as e:
            print(f"❌ Error processing attachments: {e}")
            
        print("✅ log_action completed successfully")
                        
    except Exception as e:
        print(f"💥 Critical error in log_action: {e}")
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
