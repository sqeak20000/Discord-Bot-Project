#!/usr/bin/env python3
"""
Simple logging test that mimics a moderation action
"""

import asyncio
import discord
from discord.ext import commands
from config import BOT_TOKEN, LOG_CHANNEL_ID

async def simple_log_test():
    """Test basic logging functionality"""
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    @bot.event
    async def on_ready():
        print(f'Bot ready: {bot.user}')
        
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            print(f'Found channel: #{log_channel.name}')
            
            # Simple text message
            try:
                await log_channel.send("🔨 Test Ban: @TestUser by @TestMod - Test reason")
                print("✅ Simple message sent!")
            except Exception as e:
                print(f"❌ Simple message failed: {e}")
            
            # Simple embed
            try:
                embed = discord.Embed(title="🔨 User Banned", color=0xff0000)
                embed.add_field(name="User", value="TestUser", inline=True)
                embed.add_field(name="Moderator", value="TestMod", inline=True)
                embed.add_field(name="Reason", value="Testing embed", inline=False)
                
                await log_channel.send(embed=embed)
                print("✅ Simple embed sent!")
            except Exception as e:
                print(f"❌ Simple embed failed: {e}")
        else:
            print(f"❌ Channel {LOG_CHANNEL_ID} not found")
        
        await bot.close()
    
    await bot.start(BOT_TOKEN)

if __name__ == "__main__":
    asyncio.run(simple_log_test())
