#!/usr/bin/env python3
"""
Helper script to manually sync slash commands with Discord.
Run this if slash commands aren't showing up in your server.
"""

import asyncio
import discord
from discord.ext import commands
from config import BOT_TOKEN

async def sync_commands():
    """Manually sync slash commands"""
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    @bot.event
    async def on_ready():
        print(f'Logged in as {bot.user}')
        try:
            # You can sync to a specific guild for faster testing:
            # guild = discord.Object(id=YOUR_GUILD_ID)  # Replace with your server ID
            # synced = await bot.tree.sync(guild=guild)
            
            # Or sync globally (takes up to 1 hour to appear):
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} slash commands globally")
            
            for command in synced:
                print(f"- {command.name}: {command.description}")
                
        except Exception as e:
            print(f"Failed to sync commands: {e}")
        finally:
            await bot.close()
    
    await bot.start(BOT_TOKEN)

if __name__ == "__main__":
    asyncio.run(sync_commands())
