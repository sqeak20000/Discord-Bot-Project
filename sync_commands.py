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
    """Manually sync slash commands with rate limit protection"""
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    @bot.event
    async def on_ready():
        print(f'Logged in as {bot.user}')
        try:
            # First, setup the commands
            print("Setting up moderation commands...")
            await setup_moderation_commands(bot)
            
            # Add delay before syncing to avoid rate limits
            print("Waiting 3 seconds before syncing to avoid rate limits...")
            await asyncio.sleep(3)
            
            # You can sync to a specific guild for faster testing:
            # guild = discord.Object(id=YOUR_GUILD_ID)  # Replace with your server ID
            # synced = await bot.tree.sync(guild=guild)
            # print(f"Synced {len(synced)} slash commands to guild {YOUR_GUILD_ID}")
            
            # Or sync globally (takes up to 1 hour to appear):
            print("Syncing commands globally...")
            
            # Retry logic for rate limits
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    synced = await bot.tree.sync()
                    print(f"Synced {len(synced)} slash commands globally")
                    
                    for command in synced:
                        print(f"- /{command.name}: {command.description}")
                    break
                    
                except discord.HTTPException as e:
                    if e.status == 429:  # Rate limited
                        retry_after = getattr(e.response, 'headers', {}).get('Retry-After', 10)
                        print(f"Rate limited! Waiting {retry_after} seconds before retry {attempt + 1}/{max_retries}...")
                        await asyncio.sleep(float(retry_after))
                        if attempt == max_retries - 1:
                            raise e
                    else:
                        raise e
                        
            print("\nCommands synced! They may take up to 1 hour to appear globally.")
            print("For faster testing, uncomment the guild-specific sync lines above.")
                
        except Exception as e:
            print(f"Failed to sync commands: {e}")
            if "429" in str(e) or "rate limit" in str(e).lower():
                print("\n🚨 RATE LIMIT DETECTED!")
                print("The bot is being rate limited by Discord.")
                print("\nPossible causes:")
                print("1. Too many sync attempts in a short time")
                print("2. Bot is making too many API calls elsewhere")
                print("3. Multiple bot instances running simultaneously")
                print("\nSolutions:")
                print("1. Wait 10-15 minutes before trying again")
                print("2. Check if the main bot is running and making API calls")
                print("3. Use guild-specific sync instead of global sync")
                print("4. Ensure only one bot instance is running")
            import traceback
            traceback.print_exc()
        finally:
            await bot.close()
    
    await bot.start(BOT_TOKEN)

if __name__ == "__main__":
    asyncio.run(sync_commands())
