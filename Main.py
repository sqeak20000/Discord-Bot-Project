import discord
import asyncio
import logging
from discord.ext import commands
from config import BOT_TOKEN, ENABLE_CROSS_POSTING
from moderation import setup_moderation_commands
from crosspost import handle_discord_update_message, setup_cross_posting, cleanup_cross_posting

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

intents = discord.Intents.default()
intents.message_content = True  # Still needed for evidence handling

# Use commands.Bot instead of discord.Client for slash command support
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    
    # Setup cross-posting functionality
    if ENABLE_CROSS_POSTING:
        await setup_cross_posting()
    
    # Setup and sync slash commands when bot starts up
    try:
        print("Setting up moderation commands...")
        await setup_moderation_commands(bot)
        
        # Add delay to avoid rate limits on startup
        print("Waiting 5 seconds before syncing to avoid rate limits...")
        await asyncio.sleep(5)
        
        # Retry logic for rate-limited sync
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"Syncing slash commands (attempt {attempt + 1}/{max_retries})...")
                synced = await bot.tree.sync()
                print(f"✅ Synced {len(synced)} slash commands")
                for command in synced:
                    print(f"- /{command.name}: {command.description}")
                break
                
            except discord.HTTPException as e:
                if e.status == 429:  # Rate limited
                    retry_after = getattr(e.response, 'headers', {}).get('Retry-After', 15)
                    print(f"⚠️  Rate limited! Waiting {retry_after} seconds before retry...")
                    await asyncio.sleep(float(retry_after))
                    if attempt == max_retries - 1:
                        print("❌ Failed to sync after maximum retries. Commands may not be available.")
                        print("💡 Try running sync_commands.py manually later.")
                else:
                    print(f"❌ HTTP Error during sync: {e}")
                    break
            except Exception as sync_error:
                print(f"❌ Unexpected error during sync: {sync_error}")
                break
                
    except Exception as e:
        print(f"❌ Failed to setup slash commands: {e}")
        print("🤖 Bot will continue running with message commands only.")

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
        print("🔄 Re-setting up moderation commands...")
        await setup_moderation_commands(bot)
        
        # Sync with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"🔄 Syncing slash commands (attempt {attempt + 1}/{max_retries})...")
                synced = await bot.tree.sync()
                
                # Success message
                command_list = "\n".join([f"• `/{cmd.name}` - {cmd.description}" for cmd in synced])
                await message.channel.send(
                    f"✅ **Successfully synced {len(synced)} slash commands!**\n\n"
                    f"**Available commands:**\n{command_list}\n\n"
                    f"*Slash commands should be available immediately in Discord.*"
                )
                print(f"✅ Manual sync completed: {len(synced)} commands synced")
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
                    print(f"❌ HTTP Error during manual sync: {e}")
                    return
                    
            except Exception as sync_error:
                await message.channel.send(f"❌ **Unexpected error during sync:** {sync_error}")
                print(f"❌ Unexpected error during manual sync: {sync_error}")
                return
                
    except Exception as e:
        await message.channel.send(f"❌ **Failed to setup commands:** {e}")
        print(f"❌ Failed to setup commands during manual sync: {e}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  # Ignore messages from the bot itself
    
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
    elif command.startswith("!ticketblacklist"):
        from moderation import handle_ticketblacklist_command
        await handle_ticketblacklist_command(bot, message)
    elif command.startswith("!synccommands"):
        await handle_sync_commands(bot, message)
    elif command.startswith("!testcrosspost"):
        await handle_test_crosspost(bot, message)

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

@bot.event
async def on_disconnect():
    """Cleanup when bot disconnects"""
    if ENABLE_CROSS_POSTING:
        await cleanup_cross_posting()

if __name__ == "__main__":
    try:
        bot.run(BOT_TOKEN)
    except KeyboardInterrupt:
        print("🔌 Bot shutting down...")
    finally:
        # Cleanup cross-posting resources
        if ENABLE_CROSS_POSTING:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(cleanup_cross_posting())
            else:
                loop.run_until_complete(cleanup_cross_posting())