#!/usr/bin/env python3
"""
Quick sync script for testing slash commands in a specific server.
Commands appear immediately instead of waiting up to 1 hour.

INSTRUCTIONS:
1. Get your Discord server ID (right-click server name -> Copy Server ID)
2. Replace YOUR_GUILD_ID below with your actual server ID
3. Run this script: python quick_sync.py
"""

import asyncio
import discord
from discord.ext import commands
from config import BOT_TOKEN
from moderation import setup_moderation_commands

# REPLACE THIS WITH YOUR ACTUAL DISCORD SERVER ID
YOUR_GUILD_ID = 123456789012345678  # <-- CHANGE THIS!

async def quick_sync():
    """Sync slash commands to a specific guild for immediate testing"""
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    @bot.event
    async def on_ready():
        print(f'Logged in as {bot.user}')
        try:
            # Setup the commands first
            print("Setting up moderation commands...")
            await setup_moderation_commands(bot)
            
            # Sync to specific guild (appears immediately)
            guild = discord.Object(id=YOUR_GUILD_ID)
            synced = await bot.tree.sync(guild=guild)
            print(f"Synced {len(synced)} slash commands to guild {YOUR_GUILD_ID}")
            
            for command in synced:
                print(f"- /{command.name}: {command.description}")
                
            print(f"\n✅ Commands should now appear immediately in your server!")
            print(f"If you don't see them, make sure:")
            print(f"1. You replaced YOUR_GUILD_ID with your actual server ID")
            print(f"2. The bot has the 'applications.commands' scope in your server")
                
        except Exception as e:
            print(f"Failed to sync commands: {e}")
            if "50001" in str(e):
                print("Error: Bot doesn't have permission to create slash commands in this guild.")
                print("Make sure the bot was invited with the 'applications.commands' scope.")
            elif "Unknown Guild" in str(e):
                print("Error: Invalid guild ID. Make sure you replaced YOUR_GUILD_ID with your actual server ID.")
            import traceback
            traceback.print_exc()
        finally:
            await bot.close()
    
    await bot.start(BOT_TOKEN)

if __name__ == "__main__":
    if YOUR_GUILD_ID == 123456789012345678:
        print("❌ ERROR: You need to replace YOUR_GUILD_ID with your actual Discord server ID!")
        print("\nTo get your server ID:")
        print("1. Enable Developer Mode in Discord (User Settings -> Advanced -> Developer Mode)")
        print("2. Right-click your server name")
        print("3. Click 'Copy Server ID'")
        print("4. Replace YOUR_GUILD_ID in this file with that number")
    else:
        asyncio.run(quick_sync())
