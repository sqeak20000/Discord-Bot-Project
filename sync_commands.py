#!/usr/bin/env python3
"""
Helper script to manually sync slash commands with Discord.
Run this if slash commands aren't showing up in your server.
"""

import asyncio
import discord
from discord.ext import commands
from config import BOT_TOKEN
from moderation import setup_moderation_commands

async def sync_commands():
    """Manually sync slash commands"""
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    @bot.event
    async def on_ready():
        print(f'Logged in as {bot.user}')
        try:
            # First, setup the commands
            print("Setting up moderation commands...")
            await setup_moderation_commands(bot)
            
            # You can sync to a specific guild for faster testing:
            # guild = discord.Object(id=YOUR_GUILD_ID)  # Replace with your server ID
            # synced = await bot.tree.sync(guild=guild)
            # print(f"Synced {len(synced)} slash commands to guild {YOUR_GUILD_ID}")
            
            # Or sync globally (takes up to 1 hour to appear):
            print("Syncing commands globally...")
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} slash commands globally")
            
            for command in synced:
                print(f"- /{command.name}: {command.description}")
                
            print("\nCommands synced! They may take up to 1 hour to appear globally.")
            print("For faster testing, uncomment the guild-specific sync lines above.")
                
        except Exception as e:
            print(f"Failed to sync commands: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await bot.close()
    
    await bot.start(BOT_TOKEN)

if __name__ == "__main__":
    asyncio.run(sync_commands())
