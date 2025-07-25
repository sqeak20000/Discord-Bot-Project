#!/usr/bin/env python3
"""
Simple test to check log channel access and permissions
"""

import asyncio
import discord
from discord.ext import commands
from config import BOT_TOKEN, LOG_CHANNEL_ID

async def test_log_channel():
    """Test if bot can access and send to log channel"""
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    @bot.event
    async def on_ready():
        print(f'✅ Bot logged in as {bot.user}')
        print(f'🔍 Looking for log channel ID: {LOG_CHANNEL_ID}')
        
        # Try to get the log channel
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        
        if log_channel:
            print(f'✅ Found log channel: #{log_channel.name} in {log_channel.guild.name}')
            
            # Test basic message sending
            try:
                test_msg = await log_channel.send("🧪 Test message from bot - logging system check")
                print(f'✅ Successfully sent test message! ID: {test_msg.id}')
                
                # Test embed sending
                embed = discord.Embed(
                    title="🧪 Test Embed",
                    description="Testing if embeds work in this channel",
                    color=discord.Color.green()
                )
                embed.add_field(name="Status", value="Testing", inline=True)
                
                embed_msg = await log_channel.send(embed=embed)
                print(f'✅ Successfully sent embed! ID: {embed_msg.id}')
                
                print("🎉 Log channel is working perfectly!")
                
            except discord.Forbidden:
                print("❌ Permission denied: Bot cannot send messages to this channel")
            except Exception as e:
                print(f"❌ Error sending to log channel: {e}")
        else:
            print(f'❌ Log channel {LOG_CHANNEL_ID} not found!')
            print("📋 Available channels:")
            for guild in bot.guilds:
                print(f"  Server: {guild.name}")
                for channel in guild.text_channels:
                    print(f"    #{channel.name} (ID: {channel.id})")
        
        print("🔄 Closing test bot...")
        await bot.close()
    
    try:
        await bot.start(BOT_TOKEN)
    except Exception as e:
        print(f"❌ Bot startup failed: {e}")

if __name__ == "__main__":
    print("🔍 Testing log channel access...")
    asyncio.run(test_log_channel())
