#!/usr/bin/env python3
"""
Standalone script to sync Discord slash commands.
Run this when you want to update slash commands without restarting the bot.
"""

import discord
import asyncio
from config import BOT_TOKEN
from moderation import setup_moderation_commands

async def main():
    """Main function to sync commands"""
    print("🚀 Starting Discord Slash Command Sync...")
    
    # Create a temporary bot instance just for syncing
    intents = discord.Intents.default()
    intents.message_content = True
    
    bot = discord.Client(intents=intents)
    bot.tree = discord.app_commands.CommandTree(bot)
    
    @bot.event
    async def on_ready():
        print(f"✅ Connected as {bot.user}")
        
        try:
            # Setup moderation commands
            print("🔧 Setting up moderation commands...")
            await setup_moderation_commands(bot)
            
            # Sync commands
            print("🔄 Syncing slash commands...")
            synced = await bot.tree.sync()
            
            print(f"✅ Successfully synced {len(synced)} slash commands:")
            for command in synced:
                print(f"   • /{command.name} - {command.description}")
            
            print("\n🎉 Slash commands are now available in Discord!")
            
        except discord.HTTPException as e:
            if e.status == 429:
                retry_after = getattr(e.response, 'headers', {}).get('Retry-After', 60)
                print(f"⚠️ Rate limited! Please wait {retry_after} seconds and try again.")
            else:
                print(f"❌ HTTP Error: {e}")
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            print("🔌 Disconnecting...")
            await bot.close()
    
    # Connect and sync
    try:
        await bot.start(BOT_TOKEN)
    except Exception as e:
        print(f"❌ Failed to connect: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("    Discord Bot Slash Command Sync Tool")
    print("=" * 50)
    asyncio.run(main())
