import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot configuration
ALLOWED_ROLES = ["Administrator", "Server Mod", "Head Moderator", "Trainee"]
TICKETBLACKLIST_ROLE_NAME = "ticket blacklist"  # Role name for ticket blacklist
LOG_CHANNEL_ID = 1397806698596405268
COMMAND_TIMEOUT = 30.0
MESSAGE_DELETE_DELAY = 5

# Rate limiting configuration
RATE_LIMIT_DELAY = 2  # seconds between API calls when rate limited
RATE_LIMIT_RETRY_DELAY = 5  # seconds to wait before retrying after rate limit
ATTACHMENT_SEND_DELAY = 1  # seconds between sending multiple attachments

# Bot token from environment variable
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN environment variable is not set")

# Cross-posting configuration
DISCORD_UPDATES_CHANNEL_ID = int(os.getenv('DISCORD_UPDATES_CHANNEL_ID', 0))  # Discord channel to monitor
GUILDED_BOT_TOKEN = os.getenv('GUILDED_BOT_TOKEN')  # Guilded bot token
GUILDED_SERVER_ID = os.getenv('GUILDED_SERVER_ID')  # Guilded server ID
GUILDED_ANNOUNCEMENTS_CHANNEL_ID = os.getenv('GUILDED_ANNOUNCEMENTS_CHANNEL_ID')  # Guilded channel ID

# Cross-posting feature toggle
ENABLE_CROSS_POSTING = all([
    DISCORD_UPDATES_CHANNEL_ID,
    GUILDED_BOT_TOKEN,
    GUILDED_SERVER_ID,
    GUILDED_ANNOUNCEMENTS_CHANNEL_ID
])

# Roblox integration configuration
ROBLOX_COOKIE = os.getenv('ROBLOX_COOKIE')  # Roblox account cookie (.ROBLOSECURITY)
ROBLOX_GROUP_ID = os.getenv('ROBLOX_GROUP_ID')  # Roblox group ID where bot has permission to post

# Roblox feature toggle
ENABLE_ROBLOX_POSTING = all([
    ROBLOX_COOKIE,
    ROBLOX_GROUP_ID
])

# Guilded announcement update strategy
GUILDED_UPDATE_EXISTING = os.getenv('GUILDED_UPDATE_EXISTING', 'true').lower() == 'true'
GUILDED_FALLBACK_TO_NEW = os.getenv('GUILDED_FALLBACK_TO_NEW', 'true').lower() == 'true'
