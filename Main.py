import discord
import asyncio
import logging
from discord.ext import commands
from config import BOT_TOKEN, ENABLE_CROSS_POSTING, FORUM_CHANNEL_ID, ALLOWED_ROLES, UNIVERSE_ID, ROBLOX_API_KEY
from moderation import setup_moderation_commands
from crosspost import handle_discord_update_message, setup_cross_posting, cleanup_cross_posting
from robloxBan import setup_roblox_ban_command, get_id_from_username, send_ban_request

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
    
    # Setup cross-posting functionality
    if ENABLE_CROSS_POSTING:
        await setup_cross_posting()
    
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

        logging.info("Setting up Roblox ban commands...")
        try:
            await setup_roblox_ban_command(bot)
            logging.info("✅ Roblox ban commands initialized")
        except Exception as e:
            logging.error(f"❌ Failed to setup Roblox commands: {e}")

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

    # Handle cross-posting for updates channel
    if ENABLE_CROSS_POSTING:
        await handle_discord_update_message(message)
    
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

    elif command.startswith("!ticketblacklist"):
        from moderation import handle_ticketblacklist_command
        await handle_ticketblacklist_command(bot, message)
    elif command.startswith("!synccommands"):
        await handle_sync_commands(bot, message)
    elif command.startswith("!testcrosspost"):
        await handle_test_crosspost(bot, message)
    elif command.startswith("!debugguilded"):
        await handle_debug_guilded(bot, message)
    elif command.startswith("!testroblox"):
        await handle_test_roblox(bot, message)
    elif command.startswith("!debugroblox"):
        await handle_debug_roblox(bot, message)
    elif command.startswith("!testupdate"):
        await handle_test_update(bot, message)
    elif command.startswith("!listannouncements"):
        await handle_list_announcements(bot, message)
    elif command.startswith("!checkroles"):
        await handle_check_roles_command(bot, message)
    elif command.startswith("!listrolecombo"):
        await handle_list_role_combos_command(bot, message)
    elif command.startswith("!rolepanel"):
        await handle_role_panel_command(bot, message)
    elif command.startswith("!robloxban"):
        # 1. Permission Check
        if not any(role.name in ALLOWED_ROLES for role in message.author.roles):
            await message.channel.send("❌ You don't have permission to use this command.")
            return

        # 2. Parse Arguments
        # Expected format: !robloxban <username_or_id> <reason> [duration]
        parts = message.content.split(" ", 3)
        
        if len(parts) < 3:
            await message.channel.send("Usage: `!robloxban <username_or_id> <reason> [duration_seconds]`\nExample: `!robloxban Player1 Being mean 60` (or leave duration blank for permanent)")
            return

        target_input = parts[1]
        # Check if duration is provided in the 3rd slot, otherwise assume it's part of the reason?
        # Actually, let's stick to a simpler parser: Last argument is duration IF it's a number, otherwise default to -1.
        
        # Re-parsing to handle multi-word reasons safely
        args = message.content.split(" ")
        target_input = args[1]
        
        # Check if the last argument is a number (duration)
        possible_duration = args[-1]
        if possible_duration.isdigit() or (possible_duration.startswith("-") and possible_duration[1:].isdigit()):
             duration = int(possible_duration)
             # Re-join everything between target and duration as the reason
             reason = " ".join(args[2:-1])
        else:
             duration = -1 # Permanent
             # Re-join everything after target as the reason
             reason = " ".join(args[2:])

        if not reason:
             await message.channel.send("❌ You must provide a ban reason.")
             return

        await message.channel.send(f"🔄 **Processing Roblox ban for '{target_input}'...**")

        # 3. Resolve ID (if username was given)
        target_id = None
        if target_input.isdigit():
            target_id = int(target_input)
            target_name = f"ID: {target_id}"
        else:
            # It's a username, look it up
            found_id, error = await get_id_from_username(target_input)
            if not found_id:
                await message.channel.send(f"❌ **Error:** {error}")
                return
            target_id = found_id
            target_name = target_input

        # 4. Execute Ban
        success, api_response = await send_ban_request(target_id, reason, duration)

        if success:
            await message.channel.send(f"✅ **Success!** {target_name} has been banned from Roblox.\nReason: {reason}\nDuration: {'Permanent' if duration == -1 else str(duration) + 's'}")
        else:
            await message.channel.send(f"❌ **Roblox API Failed:** {api_response}")

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

async def handle_test_crosspost(bot, message):
    """Handle the !testcrosspost command to test cross-posting functionality"""
    from utils import has_permission
    from config import ALLOWED_ROLES
    from crosspost import cross_poster
    
    # Check permissions - only moderators can test cross-posting
    if not has_permission(message.author, ALLOWED_ROLES):
        await message.channel.send("❌ You don't have permission to test cross-posting.", delete_after=5)
        return
    
    if not ENABLE_CROSS_POSTING:
        await message.channel.send("❌ Cross-posting is disabled. Check your environment variables.", delete_after=10)
        return
    
    await message.channel.send("🧪 **Testing cross-posting to Guilded...**")
    
    try:
        # Send a test message
        test_content = f"🧪 **Cross-posting Test**\n\nThis is a test message from Discord to verify the cross-posting functionality is working correctly.\n\n*Sent by: {message.author.display_name}*"
        
        success = await cross_poster.send_to_guilded(content=test_content)
        
        if success:
            await message.channel.send(
                "✅ **Cross-posting test successful!**\n"
                "The test message has been sent to the Guilded announcements channel."
            )
        else:
            await message.channel.send(
                "❌ **Cross-posting test failed!**\n"
                "Check the bot logs for error details."
            )
            
    except Exception as e:
        await message.channel.send(f"❌ **Error during cross-posting test:** {e}")

async def handle_debug_guilded(bot, message):
    """Handle the !debugguilded command to debug Guilded API connection"""
    from utils import has_permission
    from config import ALLOWED_ROLES, GUILDED_SERVER_ID, GUILDED_ANNOUNCEMENTS_CHANNEL_ID
    from crosspost import cross_poster
    import aiohttp
    
    # Check permissions - only moderators can debug
    if not has_permission(message.author, ALLOWED_ROLES):
        await message.channel.send("❌ You don't have permission to debug Guilded.", delete_after=5)
        return
    
    if not ENABLE_CROSS_POSTING:
        await message.channel.send("❌ Cross-posting is disabled. Check your environment variables.", delete_after=10)
        return
    
    await message.channel.send("🔍 **Debugging Guilded API connection...**")
    
    try:
        await cross_poster.init_session()
        
        # Test basic API connectivity
        url = f"{cross_poster.guilded_base_url}/users/@me"
        
        async with cross_poster.session.get(url, headers=cross_poster.guilded_headers) as response:
            if response.status == 200:
                bot_info = await response.json()
                bot_name = bot_info.get('user', {}).get('name', 'Unknown')
                await message.channel.send(f"✅ **Bot Authentication Successful**\nBot Name: {bot_name}")
            else:
                error_text = await response.text()
                await message.channel.send(f"❌ **Bot Authentication Failed**\nStatus: {response.status}\nError: {error_text}")
                return
        
        # Test channel info
        channel_url = f"{cross_poster.guilded_base_url}/channels/{GUILDED_ANNOUNCEMENTS_CHANNEL_ID}"
        
        async with cross_poster.session.get(channel_url, headers=cross_poster.guilded_headers) as response:
            if response.status == 200:
                channel_info = await response.json()
                channel_data = channel_info.get('channel', {})
                channel_name = channel_data.get('name', 'Unknown')
                channel_type = channel_data.get('type', 'Unknown')
                server_id = channel_data.get('serverId', 'Unknown')
                
                await message.channel.send(
                    f"✅ **Channel Info Retrieved**\n"
                    f"Channel Name: {channel_name}\n"
                    f"Channel Type: {channel_type}\n"
                    f"Server ID: {server_id}\n"
                    f"Expected Server ID: {GUILDED_SERVER_ID}"
                )
                
                # Verify server match
                if server_id != GUILDED_SERVER_ID:
                    await message.channel.send("⚠️ **Warning:** Channel's server ID doesn't match configured server ID!")
                
            else:
                error_text = await response.text()
                await message.channel.send(f"❌ **Channel Info Failed**\nStatus: {response.status}\nError: {error_text}")
        
        # Test server permissions
        server_url = f"{cross_poster.guilded_base_url}/servers/{GUILDED_SERVER_ID}/members/@me"
        
        async with cross_poster.session.get(server_url, headers=cross_poster.guilded_headers) as response:
            if response.status == 200:
                member_info = await response.json()
                await message.channel.send("✅ **Bot is a member of the server**")
            else:
                await message.channel.send(f"⚠️ **Server Membership Check Failed:** {response.status}")
                
    except Exception as e:
        await message.channel.send(f"❌ **Debug Error:** {e}")

async def handle_test_roblox(bot, message):
    """Handle the !testroblox command to test Roblox posting functionality"""
    from utils import has_permission
    from config import ALLOWED_ROLES, ENABLE_ROBLOX_POSTING
    from roblox_integration import roblox_poster, format_message_for_roblox
    
    # Check permissions - only moderators can test Roblox posting
    if not has_permission(message.author, ALLOWED_ROLES):
        await message.channel.send("❌ You don't have permission to test Roblox posting.", delete_after=5)
        return
    
    if not ENABLE_ROBLOX_POSTING:
        await message.channel.send("❌ Roblox posting is disabled. Check your environment variables.", delete_after=10)
        return
    
    await message.channel.send("🧪 **Testing Roblox posting...**")
    
    try:
        # Format test message
        test_content = f"🧪 **Roblox Posting Test**\n\nThis is a test message from Discord to verify the Roblox posting functionality is working correctly.\n\n*Sent by: {message.author.display_name}*"
        roblox_message = await format_message_for_roblox(test_content, "Test Update")
        
        # Try group shout first
        await message.channel.send("🔄 Trying group shout...")
        shout_success = await roblox_poster.post_to_group_shout(roblox_message)
        
        if shout_success:
            await message.channel.send("✅ **Group shout test successful!**")
        else:
            # Try wall post as fallback
            await message.channel.send("🔄 Group shout failed, trying wall post...")
            wall_success = await roblox_poster.post_to_group_wall(roblox_message)
            
            if wall_success:
                await message.channel.send("✅ **Wall post test successful!**")
            else:
                await message.channel.send("❌ **Both group shout and wall post failed!** Check the bot logs for error details.")
            
    except Exception as e:
        await message.channel.send(f"❌ **Error during Roblox test:** {e}")

async def handle_debug_roblox(bot, message):
    """Handle the !debugroblox command to debug Roblox API connection"""
    from utils import has_permission
    from config import ALLOWED_ROLES, ROBLOX_GROUP_ID, ENABLE_ROBLOX_POSTING
    from roblox_integration import roblox_poster
    
    # Check permissions - only moderators can debug
    if not has_permission(message.author, ALLOWED_ROLES):
        await message.channel.send("❌ You don't have permission to debug Roblox.", delete_after=5)
        return
    
    if not ENABLE_ROBLOX_POSTING:
        await message.channel.send("❌ Roblox posting is disabled. Check your environment variables.", delete_after=10)
        return
    
    await message.channel.send("🔍 **Debugging Roblox API connection...**")
    
    try:
        # Test authentication
        await message.channel.send("🔐 Testing authentication...")
        user_info = await roblox_poster.get_user_info()
        
        if user_info:
            await message.channel.send(
                f"✅ **Authentication Successful**\n"
                f"• Username: {user_info.get('name', 'Unknown')}\n"
                f"• User ID: {user_info.get('id', 'Unknown')}\n"
                f"• Display Name: {user_info.get('displayName', 'Unknown')}"
            )
        else:
            await message.channel.send("❌ **Authentication Failed** - Invalid cookie or expired session")
            return
        
        # Test group access
        await message.channel.send("👥 Testing group access...")
        group_info = await roblox_poster.get_group_info()
        
        if group_info:
            await message.channel.send(
                f"✅ **Group Access Successful**\n"
                f"• Group Name: {group_info.get('name', 'Unknown')}\n"
                f"• Group ID: {group_info.get('id', 'Unknown')}\n"
                f"• Description: {group_info.get('description', 'No description')[:100]}...\n"
                f"• Member Count: {group_info.get('memberCount', 'Unknown')}"
            )
        else:
            await message.channel.send(f"❌ **Group Access Failed** - Cannot access group {ROBLOX_GROUP_ID}")
            return
        
        # Check CSRF token
        if roblox_poster.csrf_token:
            await message.channel.send("✅ **CSRF Token Obtained** - Ready for API calls")
        else:
            await message.channel.send("⚠️ **CSRF Token Missing** - May not be able to post")
        
        await message.channel.send("✅ **Roblox debug completed successfully!**")
        
    except Exception as e:
        await message.channel.send(f"❌ **Debug Error:** {e}")

async def handle_test_update(bot, message):
    """Handle the !testupdate command to test updating existing announcements"""
    from utils import has_permission
    from config import ALLOWED_ROLES, ENABLE_CROSS_POSTING
    from crosspost import cross_poster
    
    # Check permissions - only moderators can test updates
    if not has_permission(message.author, ALLOWED_ROLES):
        await message.channel.send("❌ You don't have permission to test announcement updates.", delete_after=5)
        return
    
    if not ENABLE_CROSS_POSTING:
        await message.channel.send("❌ Cross-posting is disabled. Check your environment variables.", delete_after=10)
        return
    
    await message.channel.send("🧪 **Testing announcement update functionality...**")
    
    try:
        # Get the latest announcement
        latest = await cross_poster.get_latest_announcement()
        
        if not latest:
            await message.channel.send("❌ **No existing announcements found to update.**\nCreate an announcement first, then try this command.")
            return
        
        announcement_id = latest.get('id')
        original_title = latest.get('title', 'No title')
        
        await message.channel.send(f"📢 **Found announcement to update:**\n• ID: `{announcement_id}`\n• Title: `{original_title}`")
        
        # Test updating it
        test_content = f"🧪 **Update Test**\n\nThis announcement was updated by the Discord bot to test the update functionality.\n\n*Updated by: {message.author.display_name}*"
        test_title = f"Test Update - {original_title}"
        
        success = await cross_poster.update_announcement(announcement_id, test_content, test_title)
        
        if success:
            await message.channel.send(
                "✅ **Announcement update successful!**\n"
                "The existing announcement has been updated. This should help with Roblox syncing if the original was created by a developer account."
            )
        else:
            await message.channel.send(
                "❌ **Announcement update failed!**\n"
                "Check the bot logs for error details."
            )
            
    except Exception as e:
        await message.channel.send(f"❌ **Error during update test:** {e}")

async def handle_list_announcements(bot, message):
    """Handle the !listannouncements command to show recent announcements"""
    from utils import has_permission
    from config import ALLOWED_ROLES, ENABLE_CROSS_POSTING, GUILDED_ANNOUNCEMENTS_CHANNEL_ID
    from crosspost import cross_poster
    
    # Check permissions - only moderators can list announcements
    if not has_permission(message.author, ALLOWED_ROLES):
        await message.channel.send("❌ You don't have permission to list announcements.", delete_after=5)
        return
    
    if not ENABLE_CROSS_POSTING:
        await message.channel.send("❌ Cross-posting is disabled. Check your environment variables.", delete_after=10)
        return
    
    await message.channel.send("📋 **Fetching announcements from Guilded...**")
    
    try:
        # Get announcements list
        await cross_poster.init_session()
        url = f"{cross_poster.guilded_base_url}/channels/{GUILDED_ANNOUNCEMENTS_CHANNEL_ID}/announcements"
        
        async with cross_poster.session.get(url, headers=cross_poster.guilded_headers) as response:
            if response.status == 200:
                data = await response.json()
                announcements = data.get('announcements', [])
                
                if not announcements:
                    await message.channel.send("📭 **No announcements found in the channel.**")
                    return
                
                # Show up to 5 most recent announcements
                announcement_list = "📋 **Recent Announcements:**\n\n"
                
                for i, announcement in enumerate(announcements[:5], 1):
                    title = announcement.get('title', 'No title')
                    created_at = announcement.get('createdAt', 'Unknown time')
                    created_by = announcement.get('createdBy', 'Unknown')
                    ann_id = announcement.get('id', 'Unknown')
                    
                    # Format the date
                    try:
                        from datetime import datetime
                        if created_at != 'Unknown time':
                            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            formatted_date = dt.strftime('%Y-%m-%d %H:%M UTC')
                        else:
                            formatted_date = created_at
                    except:
                        formatted_date = created_at
                    
                    announcement_list += f"**{i}.** `{title}`\n"
                    announcement_list += f"   • ID: `{ann_id}`\n"
                    announcement_list += f"   • Created: {formatted_date}\n"
                    announcement_list += f"   • Author: {created_by}\n\n"
                
                await message.channel.send(announcement_list)
                
            else:
                await message.channel.send(f"❌ **Failed to fetch announcements:** {response.status}")
                
    except Exception as e:
        await message.channel.send(f"❌ **Error fetching announcements:** {e}")

@bot.event
async def on_disconnect():
    """Cleanup when bot disconnects"""
    if ENABLE_CROSS_POSTING:
        await cleanup_cross_posting()

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
    finally:
        # Cleanup cross-posting resources with proper event loop handling
        if ENABLE_CROSS_POSTING:
            try:
                # Try to get existing event loop
                try:
                    loop = asyncio.get_running_loop()
                    # If we're in an async context, create a task
                    loop.create_task(cleanup_cross_posting())
                except RuntimeError:
                    # No running loop, create a new one for cleanup
                    try:
                        loop = asyncio.get_event_loop()
                        if not loop.is_closed():
                            loop.run_until_complete(cleanup_cross_posting())
                    except RuntimeError:
                        # Create a new event loop for cleanup
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(cleanup_cross_posting())
                        finally:
                            loop.close()
            except Exception as cleanup_error:
                logging.error(f"⚠️ Cleanup error (non-critical): {cleanup_error}")