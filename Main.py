import discord
import asyncio
import logging
from discord.ext import commands
from config import BOT_TOKEN, FORUM_CHANNEL_ID, ALLOWED_ROLES
from moderation import setup_moderation_commands

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

intents = discord.Intents.default()
intents.message_content = True  # Required for message commands and evidence handling
intents.members = True  # Required for member update events and role management
intents.guilds = True  # Required for role management and guild operations

# Additional intents for comprehensive functionality
intents.guild_messages = True  # Required for message processing in guilds
intents.guild_reactions = True  # Useful for evidence confirmation reactions
intents.guild_typing = False  # Not needed - save bandwidth
intents.dm_messages = False  # Not needed - bot operates in guilds only
intents.dm_reactions = False  # Not needed - bot operates in guilds only
intents.dm_typing = False  # Not needed - bot operates in guilds only
intents.voice_states = False  # Not needed unless voice features added later
intents.presences = False  # Not needed - privacy conscious and saves bandwidth

# Use commands.Bot instead of discord.Client for slash command support
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user}')
    
    # Setup role management system
    try:
        from role_manager import setup_role_management
        await setup_role_management(bot)
        logging.info("✅ Role management system initialized")
    except Exception as e:
        logging.error(f"❌ Failed to setup role management: {e}")
    
    # Setup and sync slash commands when bot starts up
    try:
        logging.info("Setting up moderation commands...")
        await setup_moderation_commands(bot)

        # Verify forum channel access
        forum_channel = bot.get_channel(FORUM_CHANNEL_ID)
        if forum_channel:
            logging.info(f"✅ Found Forum Channel: {forum_channel.name} (ID: {forum_channel.id})")
        else:
            logging.error(f"❌ Could not find Forum Channel with ID: {FORUM_CHANNEL_ID}. Check permissions or ID.")

    except Exception as e:
        logging.error(f"❌ Failed to setup slash commands: {e}")
        logging.info("🤖 Bot will continue running with message commands only.")

@bot.event
async def on_thread_create(thread):
    """
    Event handler for when a new thread is created.
    Used to restrict commenting in the specific forum channel.
    """
    # Debug log to verify event triggering
    logging.info(f"DEBUG: Thread created: '{thread.name}' (ID: {thread.id}) in Channel ID: {thread.parent_id}")
    
    # Check if the thread is in the target forum channel
    if thread.parent_id == FORUM_CHANNEL_ID:
        try:
            # Delay slightly to ensure thread is fully created and accessible
            await asyncio.sleep(1)
            
            guild = thread.guild
            owner = thread.owner
            
            # If owner is not cached, try to fetch them
            if owner is None:
                try:
                    owner = await guild.fetch_member(thread.owner_id)
                except discord.NotFound:
                    logging.warning(f"⚠️ Could not find owner for thread {thread.id}")
                    # Continue without owner object
            
            # Send a system message explaining the restriction
            owner_mention = owner.mention if owner else "the author"
            await thread.send(
                f"🔒 **Thread Locked to Owner**\n"
                f"Only {owner_mention} and moderators can comment on this post.\n"
                f"Others can still view and react."
            )
            logging.info(f"✅ Sent restriction notice to forum post: {thread.name}")
            
        except Exception as e:
            logging.error(f"❌ Error configuring forum thread: {e}")

@bot.event
async def on_thread_join(thread):
    """Debug event to see if bot joins threads"""
    logging.info(f"DEBUG: Joined thread: '{thread.name}' (ID: {thread.id})")

async def handle_sync_commands(bot, message):
    """Handle the !synccommands command to manually sync slash commands"""
    from utils import has_permission
    from config import ALLOWED_ROLES
    
    # Check permissions - only moderators can sync commands
    if not has_permission(message.author, ALLOWED_ROLES):
        await message.channel.send("❌ You don't have permission to sync commands.", delete_after=5)
        return
    
    await message.channel.send("🔄 **Syncing slash commands...** This may take a moment.")
    
    try:
        # Re-setup commands first (in case there were changes)
        logging.info("🔄 Re-setting up moderation commands...")
        await setup_moderation_commands(bot)
        
        # Sync with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logging.info(f"🔄 Syncing slash commands (attempt {attempt + 1}/{max_retries})...")
                synced = await bot.tree.sync()
                
                # Success message
                command_list = "\n".join([f"• `/{cmd.name}` - {cmd.description}" for cmd in synced])
                await message.channel.send(
                    f"✅ **Successfully synced {len(synced)} slash commands!**\n\n"
                    f"**Available commands:**\n{command_list}\n\n"
                    f"*Slash commands should be available immediately in Discord.*"
                )
                logging.info(f"✅ Manual sync completed: {len(synced)} commands synced")
                return
                
            except discord.HTTPException as e:
                if e.status == 429:  # Rate limited
                    retry_after = getattr(e.response, 'headers', {}).get('Retry-After', 15)
                    if attempt < max_retries - 1:  # Not the last attempt
                        await message.channel.send(f"⚠️ Rate limited! Retrying in {retry_after} seconds...")
                        await asyncio.sleep(float(retry_after))
                    else:
                        await message.channel.send(
                            f"❌ **Sync failed after {max_retries} attempts due to rate limiting.**\n"
                            f"Please wait {retry_after} seconds and try again."
                        )
                        return
                else:
                    await message.channel.send(f"❌ **HTTP Error during sync:** {e}")
                    logging.error(f"❌ HTTP Error during manual sync: {e}")
                    return
                    
            except Exception as sync_error:
                await message.channel.send(f"❌ **Unexpected error during sync:** {sync_error}")
                logging.error(f"❌ Unexpected error during manual sync: {sync_error}")
                return
                
    except Exception as e:
        await message.channel.send(f"❌ **Failed to setup commands:** {e}")
        logging.error(f"❌ Failed to setup commands during manual sync: {e}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  # Ignore messages from the bot itself
    
    # Enforce forum channel restrictions (Only owner and mods can chat)
    if isinstance(message.channel, discord.Thread) and message.channel.parent_id == FORUM_CHANNEL_ID:
        is_owner = message.author.id == message.channel.owner_id
        is_mod = any(role.name in ALLOWED_ROLES for role in message.author.roles)
        
        if not (is_owner or is_mod):
            try:
                await message.delete()
                # Optional: Send a temporary warning message
                # await message.channel.send(f"{message.author.mention}, only the post owner can comment here.", delete_after=5)
            except Exception as e:
                logging.error(f"Failed to delete unauthorized forum message: {e}")
            return

    # Keep existing message commands for backward compatibility
    command = message.content.lower()
    
    if command.startswith("!ban"):
        from moderation import handle_ban_command
        await handle_ban_command(bot, message)
    elif command.startswith("!kick"):
        from moderation import handle_kick_command
        await handle_kick_command(bot, message)
    elif command.startswith("!timeout"):
        from moderation import handle_timeout_command
        await handle_timeout_command(bot, message)
    elif command.startswith("!unban"):
        # Simple message command handler for unban
        if not any(role.name in ALLOWED_ROLES for role in message.author.roles):
            return
            
        parts = message.content.split(" ", 2)
        if len(parts) < 3:
            await message.channel.send("Usage: !unban <user_id> <reason>")
            return
            
        user_id = parts[1]
        reason = parts[2]
        
        try:
            user_obj = await bot.fetch_user(int(user_id))
            await message.guild.unban(user_obj, reason=reason)
            await message.channel.send(f"✅ **{user_obj.name}** has been unbanned.")
            from utils import log_action
            
            # Create a mock message for logging since we don't have mentions in the command for ID-based unban
            mock_msg = type('MockMessage', (), {
                'mentions': [user_obj],
                'attachments': [],
                'content': message.content,
                'author': message.author,
                'channel': message.channel
            })()
            
            await log_action(bot, mock_msg, "Unban", message.author, reason)
        except Exception as e:
            await message.channel.send(f"❌ Failed to unban: {e}")

    elif command.startswith("!untimeout"):
        # Simple message command handler for untimeout
        if not any(role.name in ALLOWED_ROLES for role in message.author.roles):
            return
            
        parts = message.content.split(" ", 2)
        if len(parts) < 3:
            await message.channel.send("Usage: !untimeout <@user> <reason>")
            return
            
        if not message.mentions:
            await message.channel.send("❌ Please mention a user to untimeout.")
            return
            
        user = message.mentions[0]
        reason = parts[2]
        
        try:
            await user.timeout(None, reason=reason)
            await message.channel.send(f"✅ **{user.name}**'s timeout has been removed.")
            from utils import log_action, notify_user_dm
            
            # Debug logging.info to verify arguments and ensure new code is running
            logging.info(f"DEBUG: notify_user_dm args: user={type(user)}, guild_name={type(message.guild.name)}, moderator={type(message.author)}, reason={type(reason)}")
            
            # Correct order: user, action_type, guild_name, moderator, reason
            await notify_user_dm(user, "Timeout Removed", message.guild.name, message.author, reason)
            # Use the original message for logging since it has mentions
            await log_action(bot, message, "Untimeout", message.author, reason)
        except Exception as e:
            await message.channel.send(f"❌ Failed to remove timeout: {e}")
            logging.error(f"❌ Error in untimeout: {e}")

    elif command.startswith("!blacklist") or command.startswith("!ticketblacklist"):
        from moderation import handle_blacklist_command
        await handle_blacklist_command(bot, message)
    elif command.startswith("!synccommands"):
        await handle_sync_commands(bot, message)
    elif command.startswith("!checkroles"):
        await handle_check_roles_command(bot, message)
    elif command.startswith("!listrolecombo"):
        await handle_list_role_combos_command(bot, message)
    elif command.startswith("!rolepanel"):
        await handle_role_panel_command(bot, message)

@bot.event
async def on_member_update(before, after):
    """Handle member update events for automatic role management"""
    try:
        from role_manager import handle_member_update
        await handle_member_update(before, after)
    except Exception as e:
        logging.info(f"❌ Error in member update handler: {e}")

async def handle_check_roles_command(bot, message):
    """Handle the !checkroles command"""
    try:
        from role_manager import handle_check_roles_command
        await handle_check_roles_command(bot, message)
    except ImportError:
        await message.channel.send("❌ Role management system not available.", delete_after=10)
    except Exception as e:
        await message.channel.send(f"❌ Error checking roles: {e}")

async def handle_list_role_combos_command(bot, message):
    """Handle the !listrolecombo command"""
    try:
        from role_manager import handle_list_role_combos_command
        await handle_list_role_combos_command(bot, message)
    except ImportError:
        await message.channel.send("❌ Role management system not available.", delete_after=10)
    except Exception as e:
        await message.channel.send(f"❌ Error listing role combinations: {e}")

async def handle_role_panel_command(bot, message):
    """Handle the !rolepanel command"""
    try:
        from role_manager import handle_role_panel_command
        await handle_role_panel_command(bot, message)
    except ImportError:
        await message.channel.send("❌ Role management system not available.", delete_after=10)
    except Exception as e:
        await message.channel.send(f"❌ Error sending role panel: {e}")

if __name__ == "__main__":
    try:
        bot.run(BOT_TOKEN)
    except KeyboardInterrupt:
        logging.info("🔌 Bot shutting down...")
    except discord.errors.PrivilegedIntentsRequired:
        logging.error("❌ **PRIVILEGED INTENTS ERROR**")
        logging.info("Your bot needs privileged intents enabled in the Discord Developer Portal:")
        logging.info("1. Go to https://discord.com/developers/applications/")
        logging.info("2. Select your bot application")
        logging.info("3. Go to the 'Bot' section")
        logging.info("4. Enable 'Server Members Intent' under 'Privileged Gateway Intents'")
        logging.info("5. Save changes and restart your bot")
        logging.info("\nAlternatively, you can disable role management features by setting ENABLE_AUTO_ROLES=false in your .env file")
    except Exception as e:
        logging.info(f"❌ Unexpected error: {e}")