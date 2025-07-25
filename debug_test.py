#!/usr/bin/env python3
"""
Debug script to test the logging function and identify issues
"""

import asyncio
import discord
from discord.ext import commands
from config import BOT_TOKEN
from utils import log_action

# Mock objects for testing
class MockUser:
    def __init__(self, name, user_id):
        self.display_name = name
        self.mention = f"<@{user_id}>"
        self.id = user_id
        self.display_avatar = None

class MockChannel:
    def __init__(self, name, channel_id):
        self.name = name
        self.mention = f"<#{channel_id}>"
        self.id = channel_id

class MockMessage:
    def __init__(self, content, author, channel, mentions=None, attachments=None):
        self.content = content
        self.author = author
        self.channel = channel
        self.mentions = mentions or []
        self.attachments = attachments or []
        self.jump_url = "https://discord.com/channels/123/456/789"

async def test_logging():
    """Test the logging function with mock data"""
    print("🧪 Testing logging function...")
    
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    @bot.event
    async def on_ready():
        print(f'✅ Test bot logged in as {bot.user}')
        
        # Create mock objects
        target_user = MockUser("TestUser", 123456789)
        moderator = MockUser("TestMod", 987654321)
        channel = MockChannel("general", 555555555)
        
        # Create mock message with mention
        mock_message = MockMessage(
            content="!ban <@123456789> yes spamming",
            author=moderator,
            channel=channel,
            mentions=[target_user]
        )
        
        print("📝 Testing log_action function...")
        try:
            await log_action(bot, mock_message, "Banned", moderator, "spamming repeatedly")
            print("✅ log_action completed successfully!")
        except Exception as e:
            print(f"❌ log_action failed: {e}")
            import traceback
            traceback.print_exc()
        
        print("🔄 Closing test bot...")
        await bot.close()
    
    try:
        await bot.start(BOT_TOKEN)
    except Exception as e:
        print(f"❌ Bot startup failed: {e}")

if __name__ == "__main__":
    print("🔍 Starting debug test...")
    asyncio.run(test_logging())
