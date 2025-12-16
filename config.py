import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot configuration
ALLOWED_ROLES = ["Administrator", "Server Mod", "Head Moderator", "Trainee"]
TICKETBLACKLIST_ROLE_NAME = "ticket blacklist"  # Role name for ticket blacklist
LOG_CHANNEL_ID = 1397806698596405268
FORUM_CHANNEL_ID = 1441865464740581561  # Forum channel ID for restricted commenting
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
ROBLOX_API_KEY = os.getenv("ROBLOX_API_KEY")
UNIVERSE_ID = os.getenv("UNIVERSE_ID")
ROBLOX_TOPIC_NAME = "DiscordBanRequest"

# Roblox feature toggle
ENABLE_ROBLOX_POSTING = all([
    ROBLOX_COOKIE,
    ROBLOX_GROUP_ID
])

# Guilded announcement update strategy
GUILDED_UPDATE_EXISTING = os.getenv('GUILDED_UPDATE_EXISTING', 'true').lower() == 'true'
GUILDED_FALLBACK_TO_NEW = os.getenv('GUILDED_FALLBACK_TO_NEW', 'true').lower() == 'true'

# Automatic role management configuration
# Role combinations that should trigger automatic role assignment
# Format: {'required_roles': ['Role1', 'Role2'], 'target_role': 'NewRole', 'enabled': True}
AUTO_ROLE_COMBINATIONS = [
    {
        'name': 'Verified',  # Friendly name for logging
        'required_roles': ['Rover verified', 'Double Counter verified'],  # User must have BOTH of these roles
        'target_role': 'Verified',  # Role to assign when user has both required roles
        'enabled': True,  # Whether this combination is active
        'remove_on_loss': False,  # Whether to remove target role if user loses a required role
    },
    # You can add more combinations here:
    # {
    #     'name': 'Super Moderator',
    #     'required_roles': ['Server Mod', 'Trusted Member'],
    #     'target_role': 'Super Moderator',
    #     'enabled': False,  # Disabled by default
    #     'remove_on_loss': True,
    # },
]

# Enable/disable automatic role management
ENABLE_AUTO_ROLES = os.getenv('ENABLE_AUTO_ROLES', 'true').lower() == 'true'

# Role management logging
AUTO_ROLE_LOG_CHANNEL_ID = int(os.getenv('AUTO_ROLE_LOG_CHANNEL_ID', LOG_CHANNEL_ID))  # Channel for role change logs

# Role self-service configuration
ROLE_CHECK_COOLDOWN = int(os.getenv('ROLE_CHECK_COOLDOWN', '60'))  # Cooldown in seconds between user role checks
