import discord
from discord.ext import commands
from config import BOT_TOKEN
from moderation import setup_moderation_commands

intents = discord.Intents.default()
intents.message_content = True  # Still needed for evidence handling

# Use commands.Bot instead of discord.Client for slash command support
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    # Setup and sync slash commands when bot starts up
    try:
        await setup_moderation_commands(bot)
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands")
        for command in synced:
            print(f"- /{command.name}: {command.description}")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  # Ignore messages from the bot itself
    
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

if __name__ == "__main__":
    bot.run(BOT_TOKEN)